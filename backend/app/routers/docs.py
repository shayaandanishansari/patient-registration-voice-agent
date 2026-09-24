"""The OpenAPI schema and its docs pages, behind the same API key as the
REST API (see require_browser_access for how a browser supplies it)."""

from fastapi import APIRouter, Depends, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.core.security import require_browser_access, set_session_cookie

router = APIRouter(include_in_schema=False, dependencies=[Depends(require_browser_access)])


@router.get("/openapi.json")
async def openapi(request: Request) -> dict:
    return request.app.openapi()


@router.get("/docs")
async def swagger_ui(request: Request) -> HTMLResponse:
    response = get_swagger_ui_html(openapi_url="/openapi.json", title=request.app.title)
    # Lets "Try it out" call the API without typing the key again.
    set_session_cookie(response)
    return response


@router.get("/redoc")
async def redoc(request: Request) -> HTMLResponse:
    return get_redoc_html(openapi_url="/openapi.json", title=request.app.title)
