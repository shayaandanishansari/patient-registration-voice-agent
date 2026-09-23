import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.db import Database
from app.validation import (
    ValidationError,
    normalize_address_line,
    normalize_city,
    normalize_email,
    normalize_member_id,
    normalize_name,
    normalize_phone,
    normalize_sex,
    normalize_state,
    normalize_zip,
    parse_date_of_birth,
)

logger = logging.getLogger("app.services.patients")

UTC = timezone.utc
MEMBER_ID_LENGTH = 8
MAX_MEMBER_ID_ATTEMPTS = 10

# Fields update-patient is allowed to touch, mapped to their normalizer.
UPDATABLE_FIELDS = {
    "phone",
    "email",
    "address_line1",
    "address_line2",
    "city",
    "state",
    "zip_code",
}
READ_ONLY_FIELDS = {"first_name", "last_name", "date_of_birth", "sex", "member_id"}


class InvalidField(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _generate_member_id() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(MEMBER_ID_LENGTH))


def _idempotency_key(call_id: str, first_name: str, last_name: str, dob: str) -> str:
    raw = f"{call_id}|{first_name.lower()}|{last_name.lower()}|{dob}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_create_args(args: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize create-patient args. Raises InvalidField on the
    first problem, in the order a human would naturally give the details."""
    first_name = normalize_name(args.get("first_name", ""), "first name")
    last_name = normalize_name(args.get("last_name", ""), "last name")
    dob = parse_date_of_birth(args.get("date_of_birth", ""))
    sex = normalize_sex(args.get("sex", ""))
    phone = normalize_phone(args.get("phone", ""))
    email = args.get("email")
    email = normalize_email(email) if email else None
    line1 = normalize_address_line(
        args.get("address_line1", ""), "street address", required=True
    )
    line2 = normalize_address_line(
        args.get("address_line2", ""), "apartment or unit", required=False
    )
    city = normalize_city(args.get("city", ""))
    state = normalize_state(args.get("state", ""))
    zip_code = normalize_zip(args.get("zip_code", ""))

    return {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": dob,
        "sex": sex,
        "phone": phone,
        "email": email,
        "address": {
            "line1": line1,
            "line2": line2,
            "city": city,
            "state": state,
            "zip_code": zip_code,
        },
    }


async def create_patient(
    db: Database, call_id: str, args: dict[str, Any]
) -> dict[str, str]:
    try:
        normalized = _normalize_create_args(args)
    except ValidationError as exc:
        return {"status": "invalid", "member_id": "", "message": str(exc)}

    idempotency_key = _idempotency_key(
        call_id,
        normalized["first_name"],
        normalized["last_name"],
        normalized["date_of_birth"],
    )

    existing = await db.patients.find_one({"create_idempotency_key": idempotency_key})
    if existing:
        return {
            "status": "created",
            "member_id": existing["member_id"],
            "message": "Registration saved.",
        }

    now = datetime.now(UTC)
    doc = {
        **normalized,
        "insurance_provider": None,
        "insurance_member_id": None,
        "preferred_language": "English",
        "emergency_contact_name": None,
        "emergency_contact_phone": None,
        "created_at": now,
        "updated_at": now,
        "created_via_call_id": call_id,
        "create_idempotency_key": idempotency_key,
        "update_history": [],
    }

    for _ in range(MAX_MEMBER_ID_ATTEMPTS):
        member_id = _generate_member_id()
        doc["member_id"] = member_id
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
                return {
                    "status": "created",
                    "member_id": existing["member_id"],
                    "message": "Registration saved.",
                }
            raise
        else:
            logger.info("patient_created call_id=%s", call_id)
            return {
                "status": "created",
                "member_id": member_id,
                "message": "Registration saved.",
            }

    raise RuntimeError("Could not allocate a unique member_id after several attempts.")


async def verify_patient(db: Database, args: dict[str, Any]) -> tuple[bool, str | None]:
    """Returns (matched, member_id_if_matched). Does the same DB work whether
    or not the member_id exists, so timing and response shape don't leak
    which part of the input was wrong."""
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

    patient = await db.patients.find_one({"member_id": member_id})

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

    if matched:
        return True, patient["member_id"]
    return False, None


def _to_public_dict(patient: dict[str, Any]) -> dict[str, Any]:
    return {
        "first_name": patient["first_name"],
        "last_name": patient["last_name"],
        "date_of_birth": patient["date_of_birth"],
        "sex": patient["sex"],
        "phone": patient["phone"],
        "email": patient.get("email"),
        "address": patient["address"],
    }


async def get_patient_by_member_id(
    db: Database, member_id: str
) -> dict[str, Any] | None:
    patient = await db.patients.find_one({"member_id": member_id})
    if not patient:
        return None
    return _to_public_dict(patient)


def _normalize_update_args(
    args: dict[str, Any],
) -> tuple[dict[str, Any], list[str], bool]:
    """Returns (set_fields keyed by dotted patient path, fields_changed names,
    attempted_read_only). Raises InvalidField on the first bad provided value."""
    set_fields: dict[str, Any] = {}
    fields_changed: list[str] = []
    attempted_read_only = any(f in args for f in READ_ONLY_FIELDS)

    if "phone" in args:
        try:
            set_fields["phone"] = normalize_phone(args["phone"])
        except ValidationError as exc:
            raise InvalidField(str(exc)) from exc
        fields_changed.append("phone")

    if "email" in args:
        try:
            set_fields["email"] = normalize_email(args["email"])
        except ValidationError as exc:
            raise InvalidField(str(exc)) from exc
        fields_changed.append("email")

    if "address_line1" in args:
        try:
            set_fields["address.line1"] = normalize_address_line(
                args["address_line1"], "street address", required=True
            )
        except ValidationError as exc:
            raise InvalidField(str(exc)) from exc
        fields_changed.append("address_line1")

    if "address_line2" in args:
        try:
            set_fields["address.line2"] = normalize_address_line(
                args["address_line2"], "apartment or unit", required=False
            )
        except ValidationError as exc:
            raise InvalidField(str(exc)) from exc
        fields_changed.append("address_line2")

    if "city" in args:
        try:
            set_fields["address.city"] = normalize_city(args["city"])
        except ValidationError as exc:
            raise InvalidField(str(exc)) from exc
        fields_changed.append("city")

    if "state" in args:
        try:
            set_fields["address.state"] = normalize_state(args["state"])
        except ValidationError as exc:
            raise InvalidField(str(exc)) from exc
        fields_changed.append("state")

    if "zip_code" in args:
        try:
            set_fields["address.zip_code"] = normalize_zip(args["zip_code"])
        except ValidationError as exc:
            raise InvalidField(str(exc)) from exc
        fields_changed.append("zip_code")

    return set_fields, fields_changed, attempted_read_only


_SPEAKABLE_NAMES = {
    "phone": "phone number",
    "email": "email",
    "address_line1": "street address",
    "address_line2": "apartment or unit",
    "city": "city",
    "state": "state",
    "zip_code": "ZIP code",
}


def _describe_fields(fields_changed: list[str]) -> str:
    names = [_SPEAKABLE_NAMES.get(f, f) for f in fields_changed]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


async def update_patient(
    db: Database, call_id: str, member_id: str, args: dict[str, Any]
) -> dict[str, Any]:
    try:
        set_fields, fields_changed, attempted_read_only = _normalize_update_args(args)
    except InvalidField as exc:
        return {"status": "invalid", "message": exc.message}

    if not fields_changed:
        message = "I didn't get any details to update."
        if attempted_read_only:
            message = (
                "Name and date of birth can only be changed in person, "
                "and nothing else was given to update."
            )
        return {"status": "invalid", "message": message}

    set_fields["updated_at"] = datetime.now(UTC)
    now = datetime.now(UTC)

    await db.patients.update_one(
        {"member_id": member_id},
        {
            "$set": set_fields,
            "$push": {
                "update_history": {
                    "call_id": call_id,
                    "fields_changed": fields_changed,
                    "at": now,
                }
            },
        },
    )

    message = f"Updated {_describe_fields(fields_changed)}."
    if attempted_read_only:
        message += " Name and date of birth can only be changed in person."

    return {
        "status": "updated",
        "updated_fields": fields_changed,
        "message": message,
    }
