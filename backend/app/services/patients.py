"""Patient registration, verification and update logic.

Both the REST API (app/routers/patients.py) and the Retell voice tools
(app/routers/retell_tools.py) write through this module, so there is exactly
one place that allocates IDs, detects duplicates, applies updates and logs the
collected payload.
"""

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.database import Database
from app.models.patients import (
    DEFAULT_LANGUAGE,
    PATIENT_FIELDS,
    REQUIRED_FIELDS,
    PatientCreate,
    PatientUpdate,
    first_error_message,
)
from app.core.validation import ValidationError, normalize_member_id, parse_date_of_birth

logger = logging.getLogger("app.services.patients")

UTC = timezone.utc
MEMBER_ID_LENGTH = 8
MAX_MEMBER_ID_ATTEMPTS = 10

# Soft-deleted patients are invisible to every lookup except an explicit
# include_deleted listing. {"deleted_at": None} also matches legacy documents
# that predate the field.
ACTIVE = {"deleted_at": None}

# Over the phone a verified caller may change contact, address and the
# optional fields. Identity fields need a photo ID in person.
VOICE_READ_ONLY_FIELDS = frozenset(
    {"first_name", "last_name", "date_of_birth", "sex", "member_id"}
)
VOICE_UPDATABLE_FIELDS = tuple(
    f for f in PATIENT_FIELDS if f not in VOICE_READ_ONLY_FIELDS
)

# Earlier versions of the Retell flow used these argument names; accept them
# so a flow and backend deployed a few minutes apart still work together.
LEGACY_ARG_NAMES = {
    "phone": "phone_number",
    "address_line1": "address_line_1",
    "address_line2": "address_line_2",
}

SPEAKABLE_NAMES = {
    "phone_number": "phone number",
    "email": "email",
    "address_line_1": "street address",
    "address_line_2": "apartment or unit",
    "city": "city",
    "state": "state",
    "zip_code": "ZIP code",
    "insurance_provider": "insurance company",
    "insurance_member_id": "insurance member ID",
    "preferred_language": "preferred language",
    "emergency_contact_name": "emergency contact name",
    "emergency_contact_phone": "emergency contact phone number",
}


class DuplicatePatient(Exception):
    def __init__(self, existing: dict[str, Any]) -> None:
        super().__init__("A patient with these details already exists.")
        self.existing = existing


# --- Shared helpers ------------------------------------------------------------


def _now() -> datetime:
    # Mongo stores milliseconds; truncate so a freshly-created record reads
    # back identically to what POST returned.
    now = datetime.now(UTC)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


def _generate_member_id() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(MEMBER_ID_LENGTH))


def _idempotency_key(call_id: str, first_name: str, last_name: str, dob: str) -> str:
    raw = f"{call_id}|{first_name.lower()}|{last_name.lower()}|{dob}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _log_payload(event: str, patient_id: str, source: str, payload: dict[str, Any]) -> None:
    # The brief asks for the final collected payload in the logs. Test data
    # only — a production system would redact PHI here.
    logger.info(
        "%s patient_id=%s source=%s payload=%s",
        event,
        patient_id,
        source,
        json.dumps(payload, default=str, sort_keys=True),
    )


def _canonical_args(args: dict[str, Any]) -> dict[str, Any]:
    return {LEGACY_ARG_NAMES.get(k, k): val for k, val in args.items()}


def display_name(patient: dict[str, Any]) -> str:
    return f"{patient['first_name']} {patient['last_name']}"


async def find_duplicate(db: Database, data: dict[str, Any]) -> dict[str, Any] | None:
    """An active patient with the same phone number, name and date of birth.

    Phone number alone is not identity — households share lines — so a
    phone match only counts as a duplicate when the name and DOB the caller
    just gave also match. That way the agent never discloses a name the
    caller didn't say themselves."""
    candidates = await db.patients.find(
        {
            **ACTIVE,
            "phone_number": data["phone_number"],
            "date_of_birth": data["date_of_birth"],
        }
    ).to_list(length=50)
    first = data["first_name"].lower()
    last = data["last_name"].lower()
    for candidate in candidates:
        if (
            candidate["first_name"].lower() == first
            and candidate["last_name"].lower() == last
        ):
            return candidate
    return None


async def insert_patient(
    db: Database,
    data: dict[str, Any],
    *,
    source: str,
    call_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Insert a validated patient and return the stored document. Raises
    DuplicatePatient if the same person is already registered."""
    if idempotency_key:
        existing = await db.patients.find_one({"create_idempotency_key": idempotency_key})
        if existing:
            return existing

    duplicate = await find_duplicate(db, data)
    if duplicate:
        raise DuplicatePatient(duplicate)

    now = _now()
    doc: dict[str, Any] = {
        **{field: data.get(field) for field in PATIENT_FIELDS},
        "preferred_language": data.get("preferred_language") or DEFAULT_LANGUAGE,
        "patient_id": str(uuid.uuid4()),
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
        "created_via": source,
        "created_via_call_id": call_id,
        "update_history": [],
    }
    if idempotency_key:
        doc["create_idempotency_key"] = idempotency_key

    for _ in range(MAX_MEMBER_ID_ATTEMPTS):
        doc["member_id"] = _generate_member_id()
        try:
            await db.patients.insert_one(dict(doc))
        except DuplicateKeyError as exc:
            if "member_id" in str(exc.details):
                continue
            # Idempotency key collided with a concurrent identical request.
            existing = await db.patients.find_one(
                {"create_idempotency_key": idempotency_key}
            )
            if existing:
                return existing
            raise
        _log_payload("patient_created", doc["patient_id"], source, data)
        return doc

    raise RuntimeError("Could not allocate a unique member_id after several attempts.")


async def apply_update(
    db: Database,
    patient_id: str,
    changes: dict[str, Any],
    *,
    source: str,
    call_id: str | None = None,
) -> dict[str, Any] | None:
    """Apply already-validated field changes to an active patient and record
    them in update_history. Returns the updated document, or None if the
    patient doesn't exist or was deleted."""
    if not changes:
        return await db.patients.find_one({**ACTIVE, "patient_id": patient_id})

    changes = dict(changes)
    if "preferred_language" in changes and not changes["preferred_language"]:
        changes["preferred_language"] = DEFAULT_LANGUAGE

    now = _now()
    updated = await db.patients.find_one_and_update(
        {**ACTIVE, "patient_id": patient_id},
        {
            "$set": {**changes, "updated_at": now},
            "$push": {
                "update_history": {
                    "source": source,
                    "call_id": call_id,
                    "fields_changed": list(changes),
                    "at": now,
                }
            },
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated:
        _log_payload("patient_updated", patient_id, source, changes)
    return updated


# --- REST API --------------------------------------------------------------------


async def api_create_patient(db: Database, body: PatientCreate) -> dict[str, Any]:
    return await insert_patient(db, body.model_dump(), source="api")


async def get_patient(
    db: Database, patient_id: str, include_deleted: bool = False
) -> dict[str, Any] | None:
    query: dict[str, Any] = {"patient_id": patient_id}
    if not include_deleted:
        query.update(ACTIVE)
    return await db.patients.find_one(query)


async def api_update_patient(
    db: Database, patient_id: str, body: PatientUpdate
) -> dict[str, Any] | None:
    changes = body.model_dump(include=body.model_fields_set)
    return await apply_update(db, patient_id, changes, source="api")


async def soft_delete_patient(db: Database, patient_id: str) -> dict[str, Any] | None:
    now = _now()
    deleted = await db.patients.find_one_and_update(
        {**ACTIVE, "patient_id": patient_id},
        {"$set": {"deleted_at": now, "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if deleted:
        logger.info("patient_deleted patient_id=%s", patient_id)
    return deleted


# --- Voice tools -----------------------------------------------------------------
# Tool endpoints always answer 200 with a small status payload the Retell flow
# branches on; validation problems come back as {"status": "invalid"} with a
# speakable message rather than an HTTP error.


def _validate_voice_fields(
    args: dict[str, Any], fields: tuple[str, ...] | frozenset[str]
) -> dict[str, Any]:
    """Validate just `fields` from voice args (missing required ones count as
    blank so the caller hears "I need a ... to continue"). Raises
    ValidationError with the first speakable problem."""
    subset = {f: args.get(f) for f in fields}
    for f in fields:
        if f in REQUIRED_FIELDS and subset[f] is None:
            subset[f] = ""
    try:
        return PatientUpdate(**subset).model_dump(include=set(fields))
    except PydanticValidationError as exc:
        raise ValidationError(first_error_message(exc)) from exc


async def voice_check_existing(db: Database, args: dict[str, Any]) -> dict[str, str]:
    args = _canonical_args(args)
    try:
        data = _validate_voice_fields(
            args, ("first_name", "last_name", "date_of_birth", "phone_number")
        )
    except ValidationError as exc:
        return {"status": "invalid", "patient_name": "", "message": str(exc)}

    duplicate = await find_duplicate(db, data)
    if duplicate:
        return {
            "status": "existing",
            "patient_name": display_name(duplicate),
            "message": "A registration with these details already exists.",
        }
    return {"status": "none", "patient_name": "", "message": ""}


async def voice_create_patient(
    db: Database, call_id: str, args: dict[str, Any]
) -> tuple[dict[str, str], str | None]:
    """Returns (tool response, patient_id if a record now exists for it)."""
    args = _canonical_args(args)
    try:
        data = _validate_voice_fields(args, PATIENT_FIELDS)
    except ValidationError as exc:
        return {"status": "invalid", "member_id": "", "patient_name": "", "message": str(exc)}, None

    key = _idempotency_key(
        call_id, data["first_name"], data["last_name"], data["date_of_birth"]
    )
    try:
        doc = await insert_patient(
            db, data, source="voice", call_id=call_id, idempotency_key=key
        )
    except DuplicatePatient as dup:
        return {
            "status": "duplicate",
            "member_id": "",
            "patient_name": display_name(dup.existing),
            "message": "A registration with these details already exists.",
        }, None

    return {
        "status": "created",
        "member_id": doc["member_id"],
        "patient_name": display_name(doc),
        "message": "Registration saved.",
    }, doc["patient_id"]


async def verify_patient(db: Database, args: dict[str, Any]) -> str | None:
    """Returns the patient_id if member ID, full name and DOB all match an
    active patient, else None. Does the same DB work whether or not the
    member_id exists, so timing and response shape don't leak which part of
    the input was wrong."""
    try:
        member_id = normalize_member_id(args.get("member_id", ""))
    except ValidationError:
        member_id = ""
    first_name = " ".join((args.get("first_name") or "").split()).lower()
    last_name = " ".join((args.get("last_name") or "").split()).lower()
    try:
        dob = parse_date_of_birth(args.get("date_of_birth", ""))
    except ValidationError:
        dob = None

    patient = await db.patients.find_one({**ACTIVE, "member_id": member_id})

    candidate_first = (patient or {}).get("first_name", "").lower()
    candidate_last = (patient or {}).get("last_name", "").lower()
    candidate_dob = (patient or {}).get("date_of_birth")

    matched = (
        patient is not None
        and dob is not None
        and candidate_first == first_name
        and candidate_last == last_name
        and candidate_dob == dob
    )
    return patient["patient_id"] if matched else None


def to_voice_dict(patient: dict[str, Any]) -> dict[str, Any]:
    """What the agent may read back to a verified caller."""
    fields = {field: patient.get(field) for field in PATIENT_FIELDS}
    fields["preferred_language"] = fields["preferred_language"] or DEFAULT_LANGUAGE
    return fields


def _describe_fields(fields: list[str]) -> str:
    names = [SPEAKABLE_NAMES.get(f, f) for f in fields]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


async def voice_update_patient(
    db: Database, call_id: str, patient_id: str, args: dict[str, Any]
) -> dict[str, Any]:
    args = _canonical_args(args)
    attempted_read_only = any(f in args for f in VOICE_READ_ONLY_FIELDS)
    provided = tuple(f for f in VOICE_UPDATABLE_FIELDS if f in args)

    if not provided:
        message = "I didn't get any details to update."
        if attempted_read_only:
            message = (
                "Name, date of birth and sex can only be changed in person, "
                "and nothing else was given to update."
            )
        return {"status": "invalid", "updated_fields": [], "message": message}

    try:
        changes = _validate_voice_fields(args, provided)
    except ValidationError as exc:
        return {"status": "invalid", "updated_fields": [], "message": str(exc)}

    updated = await apply_update(db, patient_id, changes, source="voice", call_id=call_id)
    if not updated:
        return {
            "status": "error",
            "updated_fields": [],
            "message": "I couldn't find that registration any more.",
        }

    fields_changed = list(changes)
    message = f"Updated {_describe_fields(fields_changed)}."
    if attempted_read_only:
        message += " Name, date of birth and sex can only be changed in person."
    return {"status": "updated", "updated_fields": fields_changed, "message": message}
