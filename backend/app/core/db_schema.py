"""Database-side enforcement for the patients collection: the
$jsonSchema validator that enforces docs/patient_field_spec.xlsx."""


from pymongo.errors import OperationFailure

from app.core.database import Database
from app.core.logger import EventLogger
from app.core.validation import SEX_VALUES, US_STATE_CODES

log = EventLogger("app.core.db_schema")

_STRING = {"bsonType": "string"}
_OPTIONAL_STRING = {"bsonType": ["string", "null"]}
_PHONE = r"^[0-9]{10}$"

# Database-level enforcement of docs/patient_field_spec.xlsx. The application
# validates (and normalizes) first, with speakable messages; this is the
# backstop that stops anything else — a script, a bug, a manual edit — from
# writing a record that breaks the model.
PATIENT_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "patient_id",
            "member_id",
            "first_name",
            "last_name",
            "date_of_birth",
            "sex",
            "phone_number",
            "address_line_1",
            "city",
            "state",
            "zip_code",
            "preferred_language",
            "created_at",
            "updated_at",
        ],
        "properties": {
            "patient_id": {
                **_STRING,
                "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            },
            "member_id": {**_STRING, "pattern": r"^[0-9]{8}$"},
            "first_name": {**_STRING, "pattern": r"^[A-Za-z .'-]{1,50}$"},
            "last_name": {**_STRING, "pattern": r"^[A-Za-z .'-]{1,50}$"},
            "date_of_birth": {**_STRING, "pattern": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
            "sex": {"enum": list(SEX_VALUES)},
            "phone_number": {**_STRING, "pattern": _PHONE},
            "email": _OPTIONAL_STRING,
            "address_line_1": {**_STRING, "minLength": 1, "maxLength": 200},
            "address_line_2": _OPTIONAL_STRING,
            "city": {**_STRING, "minLength": 1, "maxLength": 100},
            "state": {"enum": sorted(US_STATE_CODES)},
            "zip_code": {**_STRING, "pattern": r"^[0-9]{5}(-[0-9]{4})?$"},
            "insurance_provider": _OPTIONAL_STRING,
            "insurance_member_id": {
                "bsonType": ["string", "null"],
                "pattern": r"^[A-Z0-9]{1,30}$",
            },
            "preferred_language": {**_STRING, "minLength": 1},
            "emergency_contact_name": _OPTIONAL_STRING,
            "emergency_contact_phone": {"bsonType": ["string", "null"], "pattern": _PHONE},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
            "deleted_at": {"bsonType": ["date", "null"]},
        },
    }
}


async def apply_patient_schema(db: Database) -> None:
    """Attach PATIENT_SCHEMA to the patients collection. Needs the collMod
    privilege (Atlas "dbAdmin"); without it, log and carry on — the
    app-level validation still applies."""
    try:
        if "patients" not in await db.db.list_collection_names():
            await db.db.create_collection("patients")
        await db.db.command(
            "collMod",
            "patients",
            validator=PATIENT_SCHEMA,
            validationLevel="moderate",
            validationAction="error",
        )
    except OperationFailure as exc:
        log.warning("patient_schema_not_applied", error=str(exc))
