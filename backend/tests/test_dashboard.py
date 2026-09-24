import pytest

from app.routers import dashboard
from tests.conftest import TEST_API_KEY

KEY = {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def built_dashboard(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "index-abc.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("nope")
    monkeypatch.setattr(dashboard, "DASHBOARD_DIR", tmp_path)
    return tmp_path


async def test_root_redirects_to_trailing_slash(client, built_dashboard):
    response = await client.get("/dashboard", headers=KEY)
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard/"


async def test_serves_index_and_assets(client, built_dashboard):
    index = await client.get("/dashboard/", headers=KEY)
    assert index.status_code == 200
    assert index.text == "<html>app</html>"
    assert index.headers["cache-control"] == "no-cache"

    asset = await client.get("/dashboard/assets/index-abc.js", headers=KEY)
    assert asset.text == "console.log(1)"
    assert "immutable" in asset.headers["cache-control"]


async def test_client_routes_fall_back_to_index(client, built_dashboard):
    response = await client.get("/dashboard/patients/1234", headers=KEY)
    assert response.status_code == 200
    assert response.text == "<html>app</html>"


async def test_cannot_escape_the_dashboard_folder(client, built_dashboard):
    response = await client.get("/dashboard/..%2Fsecret.txt", headers=KEY)
    assert "nope" not in response.text


async def test_missing_build_is_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "DASHBOARD_DIR", tmp_path / "missing")
    response = await client.get("/dashboard/", headers=KEY)
    assert response.status_code == 404


async def test_dashboard_needs_the_api_key(client, built_dashboard):
    for path in ("/dashboard", "/dashboard/", "/dashboard/assets/index-abc.js"):
        response = await client.get(path)
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Basic")


async def test_dashboard_login_lets_its_api_calls_through(client, built_dashboard):
    import base64

    basic = base64.b64encode(f"reviewer:{TEST_API_KEY}".encode()).decode()
    index = await client.get("/dashboard/", headers={"Authorization": f"Basic {basic}"})
    assert index.status_code == 200
    set_cookie = index.headers["set-cookie"]
    assert "HttpOnly" in set_cookie and "SameSite=strict" in set_cookie
    assert TEST_API_KEY not in set_cookie

    # The dashboard's fetch() then sends only the cookie, no X-API-Key.
    session = index.cookies["api_session"]
    client.cookies.set("api_session", session)
    response = await client.get("/patients")
    assert response.status_code == 200
