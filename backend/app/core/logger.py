"""Structured event logging, persisted to MongoDB.

Modules log through EventLogger:

    log = EventLogger("app.services.patients")
    log.info("patient_created", patient_id=patient_id, source="voice")

That writes one readable line to stdout
(``patient_created patient_id=... source=voice``) and, once the app has
started, one document to the ``logs`` collection:

    {ts, level, logger, event, fields: {...}, request_id, environment,
     func, line, exception?}

Plain ``logging`` calls (libraries, anything not yet on EventLogger) are stored
too, with ``message`` in place of ``event``/``fields``.

MongoLogHandler never blocks or fails a request: records are buffered in
memory and written in batches by a background task. If Atlas is unreachable
the batch is dropped and reported on stderr; stdout still has every line.
"""

import asyncio
import contextlib
import json
import logging
import sys
import time
import uuid
from collections import deque
from contextvars import ContextVar
from datetime import date, datetime, timezone
from typing import Any

UTC = timezone.utc

# Set per HTTP request by RequestLogMiddleware; stamped on every record
# logged while that request is being handled.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# The driver's own loggers would log the handler's inserts, which would be
# logged, which would be inserted...
_IGNORED_LOGGERS = ("pymongo", "motor")

_exception_formatter = logging.Formatter()


def _render(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, default=str, sort_keys=True)
    return str(value)


def _bson_safe(value: Any) -> Any:
    """Coerce log fields into types BSON can store (it has no bare date)."""
    if isinstance(value, dict):
        return {str(k): _bson_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_bson_safe(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool, datetime)):
        return value
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


class EventLogger:
    """A named logger whose records carry an event name and structured
    fields, so they can be queried in MongoDB rather than grepped."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def debug(self, event: str, **fields: Any) -> None:
        self._log(logging.DEBUG, event, fields)

    def info(self, event: str, **fields: Any) -> None:
        self._log(logging.INFO, event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._log(logging.WARNING, event, fields)

    def error(self, event: str, **fields: Any) -> None:
        self._log(logging.ERROR, event, fields)

    def exception(self, event: str, **fields: Any) -> None:
        """Log at ERROR with the active exception's traceback."""
        self._log(logging.ERROR, event, fields, exc_info=True)

    def log(self, level: int, event: str, **fields: Any) -> None:
        self._log(level, event, fields)

    def _log(
        self, level: int, event: str, fields: dict[str, Any], exc_info: bool = False
    ) -> None:
        if not self._logger.isEnabledFor(level):
            return
        line = " ".join([event, *(f"{k}={_render(v)}" for k, v in fields.items())])
        self._logger.log(
            level,
            line,
            exc_info=exc_info,
            extra={"event": event, "fields": fields},
            # Report the caller's function and line, not this module's.
            stacklevel=3,
        )


class MongoLogHandler(logging.Handler):
    """Buffers log records and writes them to a MongoDB collection in batches
    from a background task. Attach with install(); detach with aclose(),
    which writes whatever is still buffered."""

    def __init__(
        self,
        collection,
        *,
        environment: str,
        level: int = logging.INFO,
        flush_interval: float = 1.0,
        batch_size: int = 500,
        max_buffer: int = 10_000,
    ) -> None:
        super().__init__(level)
        self._collection = collection
        self._environment = environment
        self._flush_interval = flush_interval
        self._batch_size = batch_size
        self._max_buffer = max_buffer
        self._buffer: deque[dict[str, Any]] = deque()
        self._dropped = 0
        self._task: asyncio.Task | None = None

    def install(self) -> None:
        logging.getLogger().addHandler(self)
        self._task = asyncio.create_task(self._run())

    async def aclose(self) -> None:
        logging.getLogger().removeHandler(self)
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await self.drain()
        self.close()

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(_IGNORED_LOGGERS):
            return
        if len(self._buffer) >= self._max_buffer:
            self._dropped += 1
            return
        try:
            self._buffer.append(self._to_document(record))
        except Exception:
            self.handleError(record)

    async def drain(self) -> None:
        """Write everything buffered so far."""
        while self._buffer:
            count = min(self._batch_size, len(self._buffer))
            batch = [self._buffer.popleft() for _ in range(count)]
            try:
                await self._collection.insert_many(batch, ordered=False)
            except Exception as exc:
                # Never log from here: that would feed this handler.
                self._dropped += len(batch)
                print(f"log persistence failed: {exc!r}", file=sys.stderr)
                break
        if self._dropped:
            print(f"log persistence dropped {self._dropped} records", file=sys.stderr)
            self._dropped = 0

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._flush_interval)
            await self.drain()

    def _to_document(self, record: logging.LogRecord) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "environment": self._environment,
            "func": record.funcName,
            "line": record.lineno,
        }
        event = getattr(record, "event", None)
        if event:
            doc["event"] = event
            doc["fields"] = _bson_safe(getattr(record, "fields", {}))
        else:
            doc["message"] = record.getMessage()
        if record.exc_info:
            doc["exception"] = _exception_formatter.formatException(record.exc_info)
        return doc


_request_log = EventLogger("app.http")


class RequestLogMiddleware:
    """Gives every HTTP request an ID (echoed as X-Request-ID, stamped on each
    log record it produces) and logs one http_request event per request."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        # Deliberately not reset afterwards: the 500 handler runs outside this
        # middleware and should still see the ID. Each request runs in its own
        # task, so the value never leaks into another request.
        request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500  # stays 500 if the app raises before responding

        async def send_with_id(message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            level = (
                logging.ERROR
                if status >= 500
                else logging.WARNING if status >= 400 else logging.INFO
            )
            _request_log.log(
                level,
                "http_request",
                method=scope["method"],
                path=scope["path"],
                status=status,
                # No query string: patient searches filter by name and DOB.
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                client_ip=_client_ip(scope),
            )


def _client_ip(scope) -> str | None:
    # Railway terminates TLS at its proxy, so the caller is in X-Forwarded-For.
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-for":
            return value.decode("latin-1").split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else None
