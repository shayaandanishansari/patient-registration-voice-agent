from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# --- Retell request envelope ---------------------------------------------
# Retell posts {"name": <tool name>, "call": {...}, "args": {...}} to every
# custom tool endpoint. `call` and `args` carry whatever Retell sends; we
# only rely on the subset of `call` fields we actually read, and validate
# `args` field-by-field in app/validation.py rather than at this boundary,
# so bad input produces a 200 {"status": "invalid", ...} instead of a 422.


class RetellCall(BaseModel):
    model_config = ConfigDict(extra="allow")

    call_id: str
    from_number: str | None = None
    to_number: str | None = None
    direction: str | None = None
    transcript: str | None = None


class RetellToolRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    call: RetellCall
    args: dict[str, Any] = Field(default_factory=dict)


# --- Patient ---------------------------------------------------------------


class Address(BaseModel):
    line1: str
    line2: str | None = None
    city: str
    state: str
    zip_code: str


class UpdateHistoryEntry(BaseModel):
    call_id: str
    fields_changed: list[str]
    at: datetime


class PatientPublic(BaseModel):
    """Read-only REST API shape: everything except internal DB mechanics."""

    member_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    sex: str
    phone: str
    email: str | None = None
    address: Address
    insurance_provider: str | None = None
    insurance_member_id: str | None = None
    preferred_language: str = "English"
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    created_at: datetime
    updated_at: datetime
    created_via_call_id: str
    update_history: list[UpdateHistoryEntry] = Field(default_factory=list)


# --- Call --------------------------------------------------------------


class CallPublic(BaseModel):
    call_id: str
    from_number: str | None = None
    to_number: str | None = None
    direction: str | None = None
    status: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    disconnection_reason: str | None = None
    transcript: str | None = None
    recording_url: str | None = None
    call_analysis: dict[str, Any] | None = None
    verified_member_id: str | None = None
    verified_at: datetime | None = None
    verification_attempts: int = 0
    patients_created: list[str] = Field(default_factory=list)


class PaginatedPatients(BaseModel):
    items: list[PatientPublic]
    next_cursor: str | None = None


class PaginatedCalls(BaseModel):
    items: list[CallPublic]
    next_cursor: str | None = None
