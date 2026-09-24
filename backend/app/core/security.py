import base64
import binascii
import hashlib
import hmac
import logging
import secrets

from fastapi import Cookie, Header, HTTPException, Request, Response
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

    # An empty secret makes the HMAC computable by anyone, so fail closed.
    if not settings.retell_api_key:
        logger.error("retell_api_key_unset path=%s", request.url.path)
        raise HTTPException(status_code=401, detail="Invalid X-Retell-Signature.")

    raw_body = (await request.body()).decode("utf-8")
    valid = _client(settings).verify(
        raw_body, api_key=settings.retell_api_key, signature=x_retell_signature
    )
    if not valid:
        logger.warning("retell_signature_invalid path=%s", request.url.path)
        raise HTTPException(status_code=401, detail="Invalid X-Retell-Signature.")


# Browsers that got past the login prompt on /dashboard or /docs carry this
# cookie, so the dashboard's own API calls need no X-API-Key. SameSite=Strict
# keeps other sites from riding on it.
SESSION_COOKIE = "api_session"


def _session_token(api_key: str) -> str:
    # Derived from API_KEY, so rotating the key signs every browser out.
    return hmac.new(api_key.encode(), b"browser-session", hashlib.sha256).hexdigest()


def set_session_cookie(response: Response) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        _session_token(get_settings().api_key),
        httponly=True,
        secure=True,
        samesite="strict",
    )


def _authorized(key: str | None, session: str | None) -> bool:
    api_key = get_settings().api_key
    if not api_key:
        return False
    if key and secrets.compare_digest(key, api_key):
        return True
    return bool(session) and secrets.compare_digest(session, _session_token(api_key))


async def require_api_key(
    x_api_key: str | None = Header(default=None),
    api_session: str | None = Cookie(default=None),
) -> None:
    if not _authorized(x_api_key, api_session):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")


def _basic_auth_password(authorization: str | None) -> str | None:
    scheme, _, encoded = (authorization or "").partition(" ")
    if scheme.lower() != "basic":
        return None
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    return decoded.partition(":")[2]


async def require_browser_access(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    api_session: str | None = Cookie(default=None),
) -> None:
    """Pages opened in a browser: /dashboard, /docs, /redoc, /openapi.json. A
    browser can't attach X-API-Key when you open a page, so the key is also
    accepted as the password of the browser's own Basic auth prompt (any
    username)."""
    if not _authorized(x_api_key or _basic_auth_password(authorization), api_session):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": 'Basic realm="Hospital VoiceAgent"'},
        )
