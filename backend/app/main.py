import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import connect
from app.routers import api, retell_tools, retell_webhook

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
    await db.create_indexes()
    app.state.db = db

    yield

    db.client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CareCloud VoiceAgent", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(retell_tools.router)
    app.include_router(retell_webhook.router)
    app.include_router(api.router)

    return app


app = create_app()
