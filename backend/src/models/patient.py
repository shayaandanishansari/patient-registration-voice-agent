import re
from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
    "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}

NAME_PATTERN = re.compile(r"^[A-Za-z'-]{1,50}$")
ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")


class Sex(StrEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE_TO_ANSWER = "Decline to Answer"


def _validate_us_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 10:
        raise ValueError("phone number must be a valid U.S. 10-digit number")
    return digits


class PatientBase(BaseModel):
    first_name: str = Field(..., pattern=NAME_PATTERN.pattern)
    last_name: str = Field(..., pattern=NAME_PATTERN.pattern)
    date_of_birth: date
    sex: Sex
    phone_number: str
    email: EmailStr | None = None
    address_line_1: str
    address_line_2: str | None = None
    city: str = Field(..., min_length=1, max_length=100)
    state: str
    zip_code: str
    insurance_provider: str | None = None
    insurance_member_id: str | None = None
    preferred_language: str = "English"
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    @field_validator("phone_number", "emergency_contact_phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_us_phone(value)

    @field_validator("date_of_birth")
    @classmethod
    def validate_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return value

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        upper = value.upper()
        if upper not in US_STATES:
            raise ValueError("state must be a valid 2-letter U.S. state abbreviation")
        return upper

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, value: str) -> str:
        if not ZIP_PATTERN.match(value):
            raise ValueError("zip_code must be 5 digits or ZIP+4 (#####-####)")
        return value


class PatientCreate(PatientBase):
    """Fields collected from the caller during pre-registration."""


class Patient(PatientBase):
    """Full patient record, including server-assigned fields."""

    patient_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None
