"""Serves the pre-built dashboard (dashboard/, `npm run build:backend`) at
/dashboard/, so reviewers get it from the same URL as the API. The build is
committed under assets/dashboard/ because Railway only builds Python here."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

DASHBOARD_DIR = Path(__file__).resolve().parents[2] / "assets" / "dashboard"

router = APIRouter(include_in_schema=False)


@router.get("/dashboard")
async def dashboard_root() -> RedirectResponse:
    return RedirectResponse("/dashboard/")


@router.get("/dashboard/{path:path}")
async def dashboard(path: str) -> FileResponse:
    root = DASHBOARD_DIR.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Dashboard is not built.")

    requested = (root / path).resolve()
    if path and requested.is_relative_to(root) and requested.is_file():
        # Vite fingerprints everything under assets/, so it can be cached forever.
        cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
        return FileResponse(requested, headers={"Cache-Control": cache})

    # Anything else is a client-side route (/dashboard/patients/<id>, ...):
    # hand back the app and let React Router resolve it.
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
