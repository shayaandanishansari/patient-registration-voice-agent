import base64
import re
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import DbDep
from app.models import CallPublic, PaginatedCalls, PaginatedPatients, PatientPublic
from app.security import require_api_key

router = APIRouter(prefix="/api", tags=["api"])


def _encode_cursor(object_id: ObjectId) -> str:
    return base64.urlsafe_b64encode(str(object_id).encode()).decode()


def _decode_cursor(cursor: str) -> ObjectId:
    try:
        return ObjectId(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, InvalidId) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor.") from exc


def _clean(doc: dict[str, Any], drop: tuple[str, ...]) -> dict[str, Any]:
    doc = dict(doc)
    doc.pop("_id", None)
    for field in drop:
        doc.pop(field, None)
    return doc


@router.get("/health")
async def health(db: DbDep) -> dict:
    try:
        await db.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail={"status": "ok", "db": "error"}
        ) from exc
    return {"status": "ok", "db": "ok"}


@router.get(
    "/patients", response_model=PaginatedPatients, dependencies=[Depends(require_api_key)]
)
async def list_patients(
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    last_name: str | None = None,
) -> PaginatedPatients:
    query: dict[str, Any] = {}
    if last_name:
        query["last_name"] = {"$regex": f"^{re.escape(last_name)}$", "$options": "i"}
    if cursor:
        query["_id"] = {"$lt": _decode_cursor(cursor)}

    docs = await db.patients.find(query).sort("_id", -1).limit(limit + 1).to_list(
        length=limit + 1
    )
    has_more = len(docs) > limit
    docs = docs[:limit]
    next_cursor = _encode_cursor(docs[-1]["_id"]) if has_more and docs else None
    items = [
        PatientPublic(**_clean(d, ("create_idempotency_key",))) for d in docs
    ]
    return PaginatedPatients(items=items, next_cursor=next_cursor)


@router.get(
    "/patients/{member_id}",
    response_model=PatientPublic,
    dependencies=[Depends(require_api_key)],
)
async def get_patient(db: DbDep, member_id: str) -> PatientPublic:
    doc = await db.patients.find_one({"member_id": member_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return PatientPublic(**_clean(doc, ("create_idempotency_key",)))


@router.get(
    "/calls", response_model=PaginatedCalls, dependencies=[Depends(require_api_key)]
)
async def list_calls(
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> PaginatedCalls:
    query: dict[str, Any] = {}
    if cursor:
        query["_id"] = {"$lt": _decode_cursor(cursor)}

    docs = await db.calls.find(query).sort("_id", -1).limit(limit + 1).to_list(
        length=limit + 1
    )
    has_more = len(docs) > limit
    docs = docs[:limit]
    next_cursor = _encode_cursor(docs[-1]["_id"]) if has_more and docs else None
    items = [CallPublic(**_clean(d, ())) for d in docs]
    return PaginatedCalls(items=items, next_cursor=next_cursor)


@router.get(
    "/calls/{call_id}", response_model=CallPublic, dependencies=[Depends(require_api_key)]
)
async def get_call(db: DbDep, call_id: str) -> CallPublic:
    doc = await db.calls.find_one({"call_id": call_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Call not found.")
    return CallPublic(**_clean(doc, ()))
