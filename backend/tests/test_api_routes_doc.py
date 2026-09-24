"""docs/api-routes.md lists every route by hand (the dashboard's Docs page shows
it). Keep it honest: each route the app serves must appear there once, with
the auth it actually requires, and the doc must not list routes that are gone."""

import re
from pathlib import Path

from fastapi.routing import APIRoute

from app.main import create_app

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "api-routes.md"
ROW = re.compile(r"^\| `(\w+)` \| `([^`]+)` \| ([^|]+?) \|", re.MULTILINE)

AUTH_LABELS = {
    "require_api_key": "API key",
    "require_browser_access": "Browser login",
    "verify_retell_signature": "Retell signature",
}


def _auth(route: APIRoute) -> str:
    names = {d.call.__name__ for d in route.dependant.dependencies}
    labels = {AUTH_LABELS[n] for n in names if n in AUTH_LABELS}
    assert len(labels) <= 1, route.path
    return labels.pop() if labels else "Public"


def _app_routes() -> dict[tuple[str, str], str]:
    routes = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path.replace(":path}", "}")
        for method in route.methods - {"HEAD"}:
            routes[(method, path)] = _auth(route)
    return routes


def _doc_routes() -> list[tuple[tuple[str, str], str]]:
    text = DOC_PATH.read_text(encoding="utf-8")
    return [((method, path), auth.strip()) for method, path, auth in ROW.findall(text)]


def test_doc_lists_each_route_once():
    listed = [key for key, _ in _doc_routes()]
    assert len(listed) == len(set(listed)), "a route is listed twice"
    assert set(listed) == set(_app_routes())


def test_doc_auth_matches_app():
    app = _app_routes()
    for key, auth in _doc_routes():
        assert auth == app.get(key), key
