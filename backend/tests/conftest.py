import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from retell.lib.webhook_auth import symmetric

from app.config import get_settings
from app.db import Database
from app.main import create_app

TEST_RETELL_API_KEY = "test-retell-signing-key"
TEST_API_READ_KEY = "test-api-read-key"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("RETELL_API_KEY", TEST_RETELL_API_KEY)
    monkeypatch.setenv("API_READ_KEY", TEST_API_READ_KEY)
    monkeypatch.setenv("ALLOW_UNSIGNED_REQUESTS", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def app():
    fastapi_app = create_app()
    mock_client = AsyncMongoMockClient()
    db = Database(mock_client, mock_client["test"])
    await db.create_indexes()
    fastapi_app.state.db = db
    return fastapi_app


@pytest_asyncio.fixture
async def db(app):
    return app.state.db


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def sign_body(body: dict) -> tuple[str, str]:
    """Returns (raw_body_str, signature_header) for a Retell tool/webhook body."""
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    signature = symmetric["sign"](raw, TEST_RETELL_API_KEY)
    return raw, signature


async def post_signed(client: AsyncClient, url: str, body: dict):
    raw, signature = sign_body(body)
    return await client.post(
        url,
        content=raw,
        headers={
            "content-type": "application/json",
            "x-retell-signature": signature,
        },
    )


def retell_tool_body(name: str, call_id: str, args: dict) -> dict:
    return {
        "name": name,
        "call": {
            "call_id": call_id,
            "from_number": "+15125551234",
            "to_number": "+15125555678",
            "direction": "inbound",
        },
        "args": args,
    }
