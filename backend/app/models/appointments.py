from pydantic import BaseModel, Field

from app.models.common import UtcDatetime

# --- Appointment (scheduling bonus; slots are mock data) ---------------------


class SlotOut(BaseModel):
    slot_id: str = Field(description="Clinic-local start time, YYYY-MM-DDTHH:MM.")
    provider: str
    spoken: str = Field(description="How the agent reads the slot aloud.")


class AppointmentOut(BaseModel):
    appointment_id: str
    patient_id: str
    slot_id: str
    provider: str
    spoken: str
    visit_type: str
    status: str
    booked_via_call_id: str | None = None
    created_at: UtcDatetime
