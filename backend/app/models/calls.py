from typing import Any

from pydantic import BaseModel, Field

from app.models.common import UtcDatetime

# --- Call --------------------------------------------------------------


class CallOut(BaseModel):
    call_id: str
    from_number: str | None = None
    to_number: str | None = None
    direction: str | None = None
    status: str | None = None
    started_at: UtcDatetime | None = None
    ended_at: UtcDatetime | None = None
    duration_ms: int | None = None
    disconnection_reason: str | None = None
    transcript: str | None = None
    recording_url: str | None = None
    call_analysis: dict[str, Any] | None = None
    call_cost: dict[str, Any] | None = Field(
        default=None,
        description="Retell's charge for the call, in cents: combined_cost, and "
        "product_costs per product (LLM, voice engine, TTS, telephony).",
    )
    verified_patient_id: str | None = Field(
        default=None, description="patient_id this call verified as, if any."
    )
    verified_at: UtcDatetime | None = None
    verification_attempts: int = 0
    patients_created: list[str] = Field(
        default_factory=list, description="patient_ids registered during this call."
    )
