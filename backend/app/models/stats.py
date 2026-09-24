from pydantic import BaseModel, Field

from app.models.common import UtcDatetime

# --- Stats ----------------------------------------------------------------
# The dashboard homepage's headline numbers. "Last 24h" is a rolling window
# ending at generated_at, not a calendar day.


class StatsOut(BaseModel):
    generated_at: UtcDatetime
    live_calls: int = Field(
        description="Calls in progress: status ongoing and started within the "
        "last hour (Retell's default maximum call length), so a call whose "
        "call_ended webhook never arrived stops counting."
    )
    calls_24h: int
    avg_call_duration_ms_24h: int | None = Field(
        default=None, description="Across ended calls started in the last 24h."
    )
    calls_total: int
    patients_total: int = Field(description="Active (not deleted) patients.")
    patients_24h: int
    possible_duplicates: int = Field(
        description="People with more than one active record (same name, DOB "
        "and phone). Voice registers them anyway rather than reveal a record to "
        "an unverified caller; staff merge them in person."
    )
    spend_cents_24h: float = Field(
        description="Retell's charge (call_cost.combined_cost) for calls started "
        "in the last 24h, in cents. Calls whose cost hasn't arrived yet count as 0."
    )
    spend_cents_total: float
    errors_24h: int = Field(description="ERROR and CRITICAL log records.")
    warnings_24h: int
