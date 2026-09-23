from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import DbDep
from app.models.calls import CallOut
from app.models.common import Envelope, ListEnvelope, ListMeta
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, paginate
from app.core.security import require_api_key

router = APIRouter(
    prefix="/calls", tags=["calls"], dependencies=[Depends(require_api_key)]
)


@router.get("", response_model=ListEnvelope[CallOut])
async def list_calls(
    db: DbDep,
    patient_id: str | None = Query(
        default=None,
        description="Only calls that registered or verified this patient.",
    ),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = None,
) -> ListEnvelope[CallOut]:
    query: dict[str, Any] = {}
    if patient_id:
        query["$or"] = [
            {"patients_created": patient_id},
            {"verified_patient_id": patient_id},
        ]
    docs, next_cursor = await paginate(db.calls, query, limit, cursor)
    return ListEnvelope(
        data=[CallOut.model_validate(d) for d in docs],
        meta=ListMeta(limit=limit, next_cursor=next_cursor),
    )


@router.get("/{call_id}", response_model=Envelope[CallOut])
async def get_call(db: DbDep, call_id: str) -> Envelope[CallOut]:
    doc = await db.calls.find_one({"call_id": call_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Call not found.")
    return Envelope(data=CallOut.model_validate(doc))
