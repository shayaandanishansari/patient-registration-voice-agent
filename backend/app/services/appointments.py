"""Mock appointment scheduling (the brief's scheduling bonus).

Availability is generated, not stored: every weekday has the same few slots
across two providers, over the next couple of weeks, minus anything already
booked. Slot IDs are clinic-local start times ("2026-10-01T09:00") — this is a
demo calendar, so there is deliberately no timezone math.
"""

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.core.database import Database

logger = logging.getLogger("app.services.appointments")

UTC = timezone.utc
VISIT_TYPE = "New patient visit"
SLOT_TIMES = (time(9, 0), time(10, 30), time(13, 0), time(14, 30), time(16, 0))
PROVIDERS = ("Dr. Maya Patel", "Dr. Daniel Nguyen")
BOOKING_WINDOW_DAYS = 14
MAX_SLOTS_OFFERED = 3


class SlotUnavailable(Exception):
    pass


def _spoken(start: datetime) -> str:
    hour = start.strftime("%I").lstrip("0")
    minutes = "" if start.minute == 0 else f":{start.minute:02d}"
    suffix = "a.m." if start.hour < 12 else "p.m."
    return f"{start.strftime('%A, %B')} {start.day} at {hour}{minutes} {suffix}"


def _slot(start: datetime) -> dict[str, str]:
    # Alternate providers through the day so both show up in the offer.
    provider = PROVIDERS[SLOT_TIMES.index(start.time()) % len(PROVIDERS)]
    return {
        "slot_id": start.strftime("%Y-%m-%dT%H:%M"),
        "provider": provider,
        "spoken": _spoken(start),
    }


def _all_slots(today: date) -> list[dict[str, str]]:
    slots = []
    for offset in range(1, BOOKING_WINDOW_DAYS + 1):
        day = today + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        slots.extend(_slot(datetime.combine(day, t)) for t in SLOT_TIMES)
    return slots


def _preference_matches(slot: dict[str, str], preference: str) -> bool:
    start = datetime.strptime(slot["slot_id"], "%Y-%m-%dT%H:%M")
    words = preference.lower()
    if "morning" in words and start.hour >= 12:
        return False
    if "afternoon" in words and start.hour < 12:
        return False
    weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday")
    asked_days = [d for d in weekdays if d in words]
    if asked_days and start.strftime("%A").lower() not in asked_days:
        return False
    return True


async def available_slots(
    db: Database, preference: str = "", today: date | None = None, limit: int = MAX_SLOTS_OFFERED
) -> list[dict[str, str]]:
    today = today or date.today()
    booked = {
        doc["slot_id"]
        async for doc in db.appointments.find({"status": "booked"}, {"slot_id": 1})
    }
    open_slots = [s for s in _all_slots(today) if s["slot_id"] not in booked]
    preferred = [s for s in open_slots if _preference_matches(s, preference or "")]
    return (preferred or open_slots)[:limit]


async def book(
    db: Database, patient_id: str, slot_id: str, call_id: str | None, today: date | None = None
) -> dict[str, Any]:
    """Book an open slot. Raises SlotUnavailable if it's not a real open slot."""
    today = today or date.today()
    slot = next((s for s in _all_slots(today) if s["slot_id"] == slot_id), None)
    if slot is None:
        raise SlotUnavailable(slot_id)

    doc = {
        "appointment_id": str(uuid.uuid4()),
        "patient_id": patient_id,
        **slot,
        "visit_type": VISIT_TYPE,
        "status": "booked",
        "booked_via_call_id": call_id,
        "created_at": datetime.now(UTC),
    }
    try:
        await db.appointments.insert_one(dict(doc))
    except DuplicateKeyError as exc:
        # Unique index on slot_id. A retried tool call for the same patient
        # gets its existing booking back; anyone else lost the race.
        existing = await db.appointments.find_one({"slot_id": slot_id})
        if existing and existing["patient_id"] == patient_id:
            return existing
        raise SlotUnavailable(slot_id) from exc
    logger.info(
        "appointment_booked patient_id=%s slot_id=%s call_id=%s",
        patient_id,
        slot_id,
        call_id,
    )
    return doc
