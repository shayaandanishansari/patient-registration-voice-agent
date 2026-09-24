import pytest

from app.routers import dashboard


@pytest.fixture
def built_dashboard(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "index-abc.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("nope")
    monkeypatch.setattr(dashboard, "DASHBOARD_DIR", tmp_path)
    return tmp_path


async def test_root_redirects_to_trailing_slash(client, built_dashboard):
    response = await client.get("/dashboard")
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard/"


async def test_serves_index_and_assets(client, built_dashboard):
    index = await client.get("/dashboard/")
    assert index.status_code == 200
    assert index.text == "<html>app</html>"
    assert index.headers["cache-control"] == "no-cache"

    asset = await client.get("/dashboard/assets/index-abc.js")
    assert asset.text == "console.log(1)"
    assert "immutable" in asset.headers["cache-control"]


async def test_client_routes_fall_back_to_index(client, built_dashboard):
    response = await client.get("/dashboard/patients/1234")
    assert response.status_code == 200
    assert response.text == "<html>app</html>"


async def test_cannot_escape_the_dashboard_folder(client, built_dashboard):
    response = await client.get("/dashboard/..%2Fsecret.txt")
    assert "nope" not in response.text


async def test_missing_build_is_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "DASHBOARD_DIR", tmp_path / "missing")
    response = await client.get("/dashboard/")
    assert response.status_code == 404


async def test_dashboard_needs_no_api_key(client, built_dashboard):
    # The page itself is public; the data it loads still needs X-API-Key.
    assert (await client.get("/dashboard/")).status_code == 200
    assert (await client.get("/patients")).status_code == 401
