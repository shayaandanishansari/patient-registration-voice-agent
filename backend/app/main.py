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
from app.core.migrations import migrate_legacy_records
from app.routers import (
    appointments,
    calls,
    health,
    patients,
    retell_tools,
    retell_webhook,
)

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if settings.allow_unsigned_requests:
        logger.warning(
            "ALLOW_UNSIGNED_REQUESTS is true — Retell signature verification is "
            "DISABLED. This must never be true outside local development."
        )

    db = connect(settings)
    await migrate_legacy_records(db)
    await db.create_indexes()
    await apply_patient_schema(db)
    app.state.db = db

    yield

    db.client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CareCloud VoiceAgent",
        description=(
            "Patient registration API behind the CareCloud voice agent. "
            "Every response uses the envelope {\"data\": ..., \"error\": null}."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(patients.router)
    app.include_router(calls.router)
    app.include_router(appointments.router)
    app.include_router(retell_tools.router)
    app.include_router(retell_webhook.probe_router)
    app.include_router(retell_webhook.router)

    return app


app = create_app()
