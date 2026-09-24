import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import DbDep
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, paginate
from app.models.common import Envelope, ListEnvelope, ListMeta
from app.core.security import require_api_key
from app.services import patients as patients_service
from app.models.patients import PatientCreate, PatientOut, PatientUpdate
from app.core.validation import ValidationError, normalize_phone, parse_date_of_birth

router = APIRouter(
    prefix="/patients", tags=["patients"], dependencies=[Depends(require_api_key)]
)

NOT_FOUND = "Patient not found."


def _out(doc: dict[str, Any]) -> PatientOut:
    return PatientOut.model_validate(doc)


def _require_uuid(patient_id: str) -> str:
    try:
        return str(uuid.UUID(patient_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="patient_id must be a UUID."
        ) from exc


def _filter_value(name: str, normalize, raw: str) -> str:
    try:
        return normalize(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"{name}: {exc}") from exc


@router.get("", response_model=ListEnvelope[PatientOut])
async def list_patients(
    db: DbDep,
    last_name: str | None = Query(default=None, description="Exact, case-insensitive."),
    date_of_birth: str | None = Query(
        default=None, description="MM/DD/YYYY or YYYY-MM-DD."
    ),
    phone_number: str | None = Query(
        default=None, description="Any common U.S. format."
    ),
    member_id: str | None = None,
    possible_duplicates: bool = Query(
        default=False,
        description="Only patients who share name, DOB and phone with another "
        "active record (voice registrations that need merging in person).",
    ),
    include_deleted: bool = False,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = None,
) -> ListEnvelope[PatientOut]:
    query: dict[str, Any] = {} if include_deleted else dict(patients_service.ACTIVE)
    if last_name and last_name.strip():
        query["last_name"] = {
            "$regex": f"^{re.escape(last_name.strip())}$",
            "$options": "i",
        }
    if date_of_birth:
        query["date_of_birth"] = _filter_value(
            "date_of_birth", parse_date_of_birth, date_of_birth
        )
    if phone_number:
        query["phone_number"] = _filter_value(
            "phone_number", normalize_phone, phone_number
        )
    if member_id:
        query["member_id"] = member_id.strip()
    if possible_duplicates:
        groups = await patients_service.possible_duplicate_ids(db)
        query["patient_id"] = {"$in": [pid for group in groups for pid in group]}

    docs, next_cursor = await paginate(db.patients, query, limit, cursor)
    return ListEnvelope(
        data=[_out(d) for d in docs],
        meta=ListMeta(limit=limit, next_cursor=next_cursor),
    )


@router.get("/{patient_id}", response_model=Envelope[PatientOut])
async def get_patient(db: DbDep, patient_id: str) -> Envelope[PatientOut]:
    doc = await patients_service.get_patient(db, _require_uuid(patient_id))
    if not doc:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return Envelope(data=_out(doc))


@router.get("/{patient_id}/duplicates", response_model=Envelope[list[PatientOut]])
async def get_patient_duplicates(db: DbDep, patient_id: str) -> Envelope[list[PatientOut]]:
    """Other active records with the same name, DOB and phone, oldest first.

    Voice registration saves these instead of telling an unverified caller
    that a record already exists (see app/services/patients.py). Staff use
    this list to merge them in person."""
    doc = await patients_service.get_patient(db, _require_uuid(patient_id))
    if not doc:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    matches = await patients_service.find_possible_duplicates(db, doc)
    return Envelope(data=[_out(d) for d in matches])


@router.post(
    "", response_model=Envelope[PatientOut], status_code=status.HTTP_201_CREATED
)
async def create_patient(db: DbDep, body: PatientCreate) -> Envelope[PatientOut]:
    try:
        doc = await patients_service.api_create_patient(db, body)
    except patients_service.DuplicatePatient as dup:
        raise HTTPException(
            status_code=409,
            detail=(
                "A patient with this name, date of birth and phone number already "
                f"exists (patient_id {dup.existing['patient_id']}). "
                "Update that record instead."
            ),
        ) from dup
    return Envelope(data=_out(doc))


@router.put("/{patient_id}", response_model=Envelope[PatientOut])
async def update_patient(
    db: DbDep, patient_id: str, body: PatientUpdate
) -> Envelope[PatientOut]:
    patient_id = _require_uuid(patient_id)
    if not body.model_fields_set:
        raise HTTPException(
            status_code=400, detail="Provide at least one field to update."
        )
    doc = await patients_service.api_update_patient(db, patient_id, body)
    if not doc:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return Envelope(data=_out(doc))


@router.delete("/{patient_id}", response_model=Envelope[PatientOut])
async def delete_patient(db: DbDep, patient_id: str) -> Envelope[PatientOut]:
    """Soft delete: sets deleted_at. The record stays in the database but no
    longer appears in lookups (use ?include_deleted=true to list it)."""
    doc = await patients_service.soft_delete_patient(db, _require_uuid(patient_id))
    if not doc:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return Envelope(data=_out(doc))
