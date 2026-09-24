import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.database import connect
from app.core.db_schema import apply_patient_schema
from app.core.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logger import EventLogger, MongoLogHandler, RequestLogMiddleware
from app.core.migrations import migrate_legacy_records
from app.routers import (
    appointments,
    calls,
    dashboard,
    docs,
    health,
    patients,
    retell_tools,
    retell_webhook,
)

log = EventLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Persist logs from here on, so the startup warnings below are kept too.
    db = connect(settings)
    log_sink = MongoLogHandler(db.logs, environment=settings.environment)
    log_sink.install()

    if settings.allow_unsigned_requests and settings.is_deployed:
        raise RuntimeError(
            "ALLOW_UNSIGNED_REQUESTS is true on a deployed environment. Refusing to "
            "start with Retell signature verification disabled."
        )
    if settings.allow_unsigned_requests:
        log.warning(
            "unsigned_requests_allowed",
            message="Retell signature verification is DISABLED. This must never "
            "be true outside local development.",
        )

    if not settings.retell_api_key:
        log.warning(
            "retell_api_key_unset", message="Every /retell/* request will be rejected."
        )
    if not settings.api_key:
        log.warning("api_key_unset", message="Every REST API request will be rejected.")

    await migrate_legacy_records(db)
    await db.create_indexes()
    await apply_patient_schema(db)
    app.state.db = db
    log.info("app_started", environment=settings.environment)

    yield

    log.info("app_stopping")
    await log_sink.aclose()
    db.client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Hospital VoiceAgent",
        description=(
            "Patient registration API behind the voice agent. "
            "Every response uses the envelope {\"data\": ..., \"error\": null}."
        ),
        lifespan=lifespan,
        # Served by routers/docs.py instead, behind the API key.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Added last, so it wraps every other middleware and sees each response.
    app.add_middleware(RequestLogMiddleware)

    app.add_exception_handler(StarletteHTTPException,http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(docs.router)
    app.include_router(patients.router)
    app.include_router(calls.router)
    app.include_router(appointments.router)
    app.include_router(retell_tools.router)
    app.include_router(retell_webhook.probe_router)
    app.include_router(retell_webhook.router)
    app.include_router(dashboard.router)

    return app


app = create_app()
