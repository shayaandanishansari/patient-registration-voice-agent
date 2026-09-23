import logging
import secrets

from fastapi import Header, HTTPException, Request
from retell import Retell

from app.core.config import Settings, get_settings

logger = logging.getLogger("app.core.security")

_retell_client: Retell | None = None


def _client(settings: Settings) -> Retell:
    global _retell_client
    if _retell_client is None:
        _retell_client = Retell(api_key=settings.retell_api_key or "unset")
    return _retell_client


async def verify_retell_signature(
    request: Request,
    x_retell_signature: str | None = Header(default=None),
) -> None:
    settings = get_settings()

    if settings.allow_unsigned_requests:
        return

    if not x_retell_signature:
        logger.warning("retell_signature_missing path=%s", request.url.path)
        raise HTTPException(status_code=401, detail="Missing X-Retell-Signature.")

    raw_body = (await request.body()).decode("utf-8")
    valid = _client(settings).verify(
        raw_body, api_key=settings.retell_api_key, signature=x_retell_signature
    )
    if not valid:
        logger.warning("retell_signature_invalid path=%s", request.url.path)
        raise HTTPException(status_code=401, detail="Invalid X-Retell-Signature.")


async def require_api_key(
    x_api_key: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.api_key or not x_api_key or not secrets.compare_digest(
        x_api_key, settings.api_key
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")
