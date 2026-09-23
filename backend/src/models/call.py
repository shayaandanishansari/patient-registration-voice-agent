from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CallStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED_REGISTRATION = "completed_registration"
    COMPLETED_UPDATE = "completed_update"
    ABANDONED = "abandoned"
    ERROR = "error"


class TranscriptTurn(BaseModel):
    role: str
    text: str
    ts: datetime


class Call(BaseModel):
    call_id: UUID = Field(default_factory=uuid4)
    patient_id: UUID | None = None
    phone_number: str
    provider_call_id: str | None = None
    status: CallStatus
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    collected_data: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
