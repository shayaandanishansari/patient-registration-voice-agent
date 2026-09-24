import json

from tests.conftest import retell_tool_body, sign_body


async def test_unsigned_request_rejected(client):
    body = retell_tool_body("get_patient_profile", "call-1", {})
    response = await client.post(
        "/retell/tools/get-patient",
        content=json.dumps(body, separators=(",", ":")),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401


async def test_tampered_body_rejected(client):
    body = retell_tool_body("get_patient_profile", "call-1", {})
    _, signature = sign_body(body)
    tampered = json.dumps({**body, "args": {"member_id": "99999999"}})
    response = await client.post(
        "/retell/tools/get-patient",
        content=tampered,
        headers={
            "content-type": "application/json",
            "x-retell-signature": signature,
        },
    )
    assert response.status_code == 401


async def test_properly_signed_request_accepted(client):
    body = retell_tool_body("get_patient_profile", "call-1", {})
    raw, signature = sign_body(body)
    response = await client.post(
        "/retell/tools/get-patient",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-retell-signature": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "not_verified"


# Routes anyone may reach: the healthcheck and the webhook reachability probe.
PUBLIC_PATHS = {"/health"}
PUBLIC_ROUTES = {("GET", "/retell/webhook")}


def _protected_routes(app):
    for route in app.routes:
        if route.path in PUBLIC_PATHS:
            continue
        for method in route.methods - {"HEAD", "OPTIONS"}:
            if (method, route.path) not in PUBLIC_ROUTES:
                yield method, route.path


async def test_every_non_public_route_rejects_anonymous_requests(app, client):
    routes = list(_protected_routes(app))
    assert routes
    for method, path in routes:
        url = path.replace("{patient_id}", "00000000-0000-0000-0000-000000000000")
        url = url.replace("{call_id}", "call-1").replace("{appointment_id}", "a-1")
        url = url.replace("{path:path}", "patients")
        assert "{" not in url, f"add a placeholder for {path}"
        response = await client.request(
            method, url, content="{}", headers={"content-type": "application/json"}
        )
        assert response.status_code == 401, f"{method} {path} -> {response.status_code}"


async def test_wrong_api_key_rejected(client):
    response = await client.get("/patients", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


async def test_empty_retell_key_rejects_empty_secret_signature(client, monkeypatch):
    from retell.lib.webhook_auth import symmetric

    from app.core.config import get_settings

    monkeypatch.setenv("RETELL_API_KEY", "")
    get_settings.cache_clear()
    body = retell_tool_body("get_patient_profile", "call-1", {})
    raw = json.dumps(body, separators=(",", ":"))
    response = await client.post(
        "/retell/tools/get-patient",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-retell-signature": symmetric["sign"](raw, ""),
        },
    )
    assert response.status_code == 401


async def test_unsigned_mode_refused_on_railway(monkeypatch):
    import pytest

    from app.core.config import get_settings
    from app.main import create_app, lifespan

    monkeypatch.setenv("ALLOW_UNSIGNED_REQUESTS", "true")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        async with lifespan(create_app()):
            pass


async def test_docs_accept_api_key_header_or_basic_auth(client):
    import base64

    from tests.conftest import TEST_API_KEY

    basic = base64.b64encode(f"reviewer:{TEST_API_KEY}".encode()).decode()
    for path in ("/docs", "/redoc", "/openapi.json"):
        anonymous = await client.get(path)
        assert anonymous.status_code == 401
        assert anonymous.headers["www-authenticate"].startswith("Basic")
        assert (await client.get(path, headers={"X-API-Key": TEST_API_KEY})).status_code == 200
        assert (await client.get(path, headers={"Authorization": f"Basic {basic}"})).status_code == 200

    wrong = base64.b64encode(b"reviewer:wrong").decode()
    response = await client.get("/openapi.json", headers={"Authorization": f"Basic {wrong}"})
    assert response.status_code == 401
    schema = (await client.get("/openapi.json", headers={"X-API-Key": TEST_API_KEY})).json()
    assert "/patients" in schema["paths"]


async def test_forged_session_cookie_rejected(client):
    client.cookies.set("api_session", "0" * 64)
    response = await client.get("/patients")
    assert response.status_code == 401
