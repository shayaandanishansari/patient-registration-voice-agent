import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from retell.lib.webhook_auth import symmetric

from app.core.config import get_settings
from app.core.database import Database
from app.main import create_app

TEST_RETELL_API_KEY = "test-retell-signing-key"
TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("RETELL_API_KEY", TEST_RETELL_API_KEY)
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
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
    # raise_app_exceptions=False so unhandled errors surface as the 500
    # envelope a real client would see, not as a test-side exception.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
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


API_HEADERS = {"x-api-key": TEST_API_KEY}

# A complete, valid registration as the Retell flow sends it.
VOICE_ARGS = {
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "1990-03-05",
    "sex": "female",
    "phone_number": "5125550123",
    "address_line_1": "123 Main St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
}


async def register_by_voice(client, call_id: str, args: dict | None = None) -> dict:
    response = await post_signed(
        client,
        "/retell/tools/create-patient",
        retell_tool_body("create_patient", call_id, args or VOICE_ARGS),
    )
    return response.json()


async def verify_by_voice(client, call_id: str, member_id: str, **overrides) -> dict:
    args = {
        "member_id": member_id,
        "first_name": "Jane",
        "last_name": "Doe",
        "date_of_birth": "1990-03-05",
        **overrides,
    }
    response = await post_signed(
        client, "/retell/tools/verify-patient", retell_tool_body("verify_patient", call_id, args)
    )
    return response.json()
