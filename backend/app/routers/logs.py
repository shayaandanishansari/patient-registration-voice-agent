from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from app.core.database import DbDep
from app.core.pagination import MAX_LIMIT, paginate
from app.core.security import require_api_key
from app.models.common import Envelope, ListEnvelope, ListMeta
from app.models.logs import LogOut

router = APIRouter(
    prefix="/logs", tags=["logs"], dependencies=[Depends(require_api_key)]
)

LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
Level = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@router.get("", response_model=ListEnvelope[LogOut])
async def list_logs(
    db: DbDep,
    since: datetime | None = Query(
        default=None, description="Only records at or after this time."
    ),
    until: datetime | None = Query(
        default=None, description="Only records before this time."
    ),
    level: Level | None = Query(default=None, description="Minimum level."),
    event: str | None = None,
    hide_http: bool = Query(
        default=False, description="Leave out the per-request http_request records."
    ),
    call_id: str | None = None,
    request_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
    cursor: str | None = None,
) -> ListEnvelope[LogOut]:
    """Log records, newest first. Kept for 90 days."""
    query: dict[str, Any] = {}
    if since or until:
        query["ts"] = {}
        if since:
            query["ts"]["$gte"] = since
        if until:
            query["ts"]["$lt"] = until
    if level:
        query["level"] = {"$in": LEVELS[LEVELS.index(level) :]}
    if event:
        query["event"] = event
    elif hide_http:
        query["event"] = {"$ne": "http_request"}
    if call_id:
        query["fields.call_id"] = call_id
    if request_id:
        query["request_id"] = request_id

    docs, next_cursor = await paginate(db.logs, query, limit, cursor)
    return ListEnvelope(
        data=[LogOut.model_validate({**d, "id": str(d["_id"])}) for d in docs],
        meta=ListMeta(limit=limit, next_cursor=next_cursor),
    )


@router.get("/events", response_model=Envelope[list[str]])
async def list_log_events(db: DbDep) -> Envelope[list[str]]:
    """Every event name that has been logged, for filtering."""
    events = await db.logs.distinct("event")
    return Envelope(data=sorted(e for e in events if e))
