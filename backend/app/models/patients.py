from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.core import validation as v
from app.models.common import UtcDatetime

# --- Patient input -----------------------------------------------------------
# One set of validators serves both the REST API and the voice tools, so the
# rules in docs/patient_field_spec.xlsx are enforced identically no matter who
# writes the record. Every normalizer raises app.validation.ValidationError
# with a short, speakable message; the voice path reads that message back to
# the caller, the REST API returns it in a 422.

_NORMALIZERS: dict[str, Callable[[str], Any]] = {
    "first_name": lambda s: v.normalize_name(s, "first name"),
    "last_name": lambda s: v.normalize_name(s, "last name"),
    "date_of_birth": v.parse_date_of_birth,
    "sex": v.normalize_sex,
    "phone_number": v.normalize_phone,
    "email": v.normalize_email,
    "address_line_1": lambda s: v.normalize_address_line(
        s, "street address", required=True
    ),
    "address_line_2": lambda s: v.normalize_address_line(
        s, "apartment or unit", required=False
    ),
    "city": v.normalize_city,
    "state": v.normalize_state,
    "zip_code": v.normalize_zip,
    "insurance_provider": v.normalize_insurance_provider,
    "insurance_member_id": v.normalize_insurance_member_id,
    "preferred_language": v.normalize_language,
    "emergency_contact_name": lambda s: v.normalize_full_name(
        s, "emergency contact's name"
    ),
    "emergency_contact_phone": lambda s: v.normalize_phone(
        s, "emergency contact's phone number"
    ),
}

PATIENT_FIELDS = tuple(_NORMALIZERS)
REQUIRED_FIELDS = frozenset(
    {
        "first_name",
        "last_name",
        "date_of_birth",
        "sex",
        "phone_number",
        "address_line_1",
        "city",
        "state",
        "zip_code",
    }
)
DEFAULT_LANGUAGE = "English"


class PatientUpdate(BaseModel):
    """Partial update: only the fields present in the request are changed.
    Sending null clears an optional field; required fields can't be cleared."""

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: str | None = Field(
        default=None, description="MM/DD/YYYY or YYYY-MM-DD; stored as YYYY-MM-DD."
    )
    sex: str | None = Field(
        default=None, description="Male, Female, Other, or Decline to Answer."
    )
    phone_number: str | None = Field(
        default=None, description="U.S. 10-digit number; stored as digits only."
    )
    email: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = Field(
        default=None, description="2-letter code or full state name."
    )
    zip_code: str | None = None
    insurance_provider: str | None = None
    insurance_member_id: str | None = None
    preferred_language: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    @field_validator(*PATIENT_FIELDS, mode="before")
    @classmethod
    def _normalize(cls, value: Any, info: ValidationInfo) -> Any:
        field = info.field_name
        if value is not None and not isinstance(value, (str, int, float)):
            raise ValueError(f"{field} must be a string.")
        text = None if value is None else str(value)
        if text is None or not text.strip():
            if field in REQUIRED_FIELDS:
                # Let the normalizer produce its own speakable "I need a ..." error.
                return _NORMALIZERS[field]("")
            return None
        return _NORMALIZERS[field](text)


class PatientCreate(PatientUpdate):
    first_name: str
    last_name: str
    date_of_birth: str = Field(
        description="MM/DD/YYYY or YYYY-MM-DD; stored as YYYY-MM-DD."
    )
    sex: str = Field(description="Male, Female, Other, or Decline to Answer.")
    phone_number: str = Field(
        description="U.S. 10-digit number; stored as digits only."
    )
    address_line_1: str
    city: str
    state: str = Field(description="2-letter code or full state name.")
    zip_code: str
    preferred_language: str | None = Field(
        default=None, description=f"Defaults to {DEFAULT_LANGUAGE}."
    )


def first_error_message(exc: Exception) -> str:
    """The speakable message from the first failing field of a pydantic
    ValidationError (our normalizers' own text, without pydantic's prefix)."""
    errors = getattr(exc, "errors", lambda: [])()
    if not errors:
        return "Some of those details don't look right."
    first = errors[0]
    original = (first.get("ctx") or {}).get("error")
    return str(original) if original else first.get("msg", "Invalid value.")


# --- Patient output ----------------------------------------------------------


class UpdateHistoryEntry(BaseModel):
    source: str = "voice"
    call_id: str | None = None
    fields_changed: list[str]
    at: UtcDatetime


class PatientOut(BaseModel):
    """REST API shape: every field from the spec plus audit metadata, minus
    internal DB mechanics (Mongo _id, idempotency key)."""

    patient_id: str = Field(description="UUID; the REST resource identifier.")
    member_id: str = Field(
        description="8-digit ID read to the caller and used for phone verification."
    )
    first_name: str
    last_name: str
    date_of_birth: str = Field(description="YYYY-MM-DD.")
    sex: str
    phone_number: str
    email: str | None = None
    address_line_1: str
    address_line_2: str | None = None
    city: str
    state: str
    zip_code: str
    insurance_provider: str | None = None
    insurance_member_id: str | None = None
    preferred_language: str = DEFAULT_LANGUAGE
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    deleted_at: UtcDatetime | None = None
    created_via: str | None = Field(
        default=None, description="voice, api, or seed."
    )
    created_via_call_id: str | None = None
    update_history: list[UpdateHistoryEntry] = Field(default_factory=list)
