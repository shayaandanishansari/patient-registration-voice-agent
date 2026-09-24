from datetime import datetime, timezone
from typing import Any

from app.core.database import Database

UTC = timezone.utc


async def touch_call(db: Database, call_id: str) -> None:
    """Ensure a call document exists with sane defaults, without clobbering
    fields the webhook or other tool calls may already own."""
    await db.calls.update_one(
        {"call_id": call_id},
        {
            "$setOnInsert": {
                "verification_attempts": 0,
                "patients_created": [],
            }
        },
        upsert=True,
    )


async def get_verified_patient_id(db: Database, call_id: str) -> str | None:
    doc = await db.calls.find_one({"call_id": call_id}, {"verified_patient_id": 1})
    return doc.get("verified_patient_id") if doc else None


async def record_verification_attempt(
    db: Database, call_id: str, patient_id: str | None
) -> None:
    update: dict[str, Any] = {"$inc": {"verification_attempts": 1}}
    if patient_id is not None:
        update["$set"] = {
            "verified_patient_id": patient_id,
            "verified_at": datetime.now(UTC),
        }
    await db.calls.update_one({"call_id": call_id}, update, upsert=True)


async def record_patient_created(db: Database, call_id: str, patient_id: str) -> None:
    await db.calls.update_one(
        {"call_id": call_id},
        {
            "$addToSet": {"patients_created": patient_id},
            "$setOnInsert": {"verification_attempts": 0},
        },
        upsert=True,
    )


async def upsert_from_webhook(db: Database, call_id: str, fields: dict[str, Any]) -> None:
    """Upsert call metadata from the Retell webhook. Never touches
    verified_patient_id, verified_at or patients_created — those are owned by
    the tool endpoints only."""
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        await touch_call(db, call_id)
        return
    await db.calls.update_one(
        {"call_id": call_id},
        {
            "$set": fields,
            "$setOnInsert": {"verification_attempts": 0, "patients_created": []},
        },
        upsert=True,
    )
