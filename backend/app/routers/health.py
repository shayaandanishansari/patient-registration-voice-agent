from fastapi import APIRouter

from app.core.database import DbDep
from app.core.errors import error_response

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: DbDep):
    """Unauthenticated liveness + database check (Railway's health check)."""
    try:
        await db.ping()
    except Exception:
        return error_response(503, "Database is unreachable.")
    return {"data": {"status": "ok", "db": "ok"}, "error": None}
