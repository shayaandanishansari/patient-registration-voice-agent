"""Exception handlers that keep every error in the API's
{"data": null, "error": {...}} envelope."""

from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import EventLogger

log = EventLogger("app.core.errors")

ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    500: "internal_error",
    503: "service_unavailable",
}


def error_response(
    status_code: int,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "data": None,
                "error": {
                    "code": ERROR_CODES.get(status_code, "error"),
                    "message": message,
                    "details": details,
                },
            }
        ),
        headers=headers,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return error_response(exc.status_code, message, headers=exc.headers)


def _field_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details = []
    for err in errors:
        loc = [str(part) for part in err.get("loc", ()) if part not in ("body", "query", "path")]
        original = (err.get("ctx") or {}).get("error")
        details.append(
            {
                "field": ".".join(loc) or None,
                "message": str(original) if original else err.get("msg"),
            }
        )
    return details


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    if any(err.get("type") == "json_invalid" for err in errors):
        log.warning("request_invalid_json", path=request.url.path)
        return error_response(400, "Request body is not valid JSON.")
    details = _field_errors(errors)
    # Field names only: the rejected values may be patient data.
    log.warning(
        "request_validation_failed",
        path=request.url.path,
        fields=[d["field"] for d in details],
    )
    if all(err.get("loc", ("",))[0] in ("query", "path") for err in errors):
        # Malformed query string / path: a bad request, not a bad resource.
        return error_response(400, "Invalid request parameters.", details)
    return error_response(422, "Some fields are invalid.", details)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", method=request.method, path=request.url.path)
    return error_response(500, "Something went wrong on our side. Please try again.")
