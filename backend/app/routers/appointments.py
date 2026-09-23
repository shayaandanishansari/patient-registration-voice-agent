from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.database import DbDep
from app.models.appointments import AppointmentOut
from app.models.common import ListEnvelope, ListMeta
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, paginate
from app.core.security import require_api_key

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=ListEnvelope[AppointmentOut])
async def list_appointments(
    db: DbDep,
    patient_id: str | None = None,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = None,
) -> ListEnvelope[AppointmentOut]:
    query: dict[str, Any] = {}
    if patient_id:
        query["patient_id"] = patient_id
    docs, next_cursor = await paginate(db.appointments, query, limit, cursor)
    return ListEnvelope(
        data=[AppointmentOut.model_validate(d) for d in docs],
        meta=ListMeta(limit=limit, next_cursor=next_cursor),
    )
