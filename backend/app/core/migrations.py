"""One-way, idempotent upgrade of records written by the first backend version
(nested `address`, E.164 `phone`, lowercase `sex`, no `patient_id`; calls
linked by member_id). Runs at startup; only touches patients that still lack
`patient_id`, so it's a no-op once everything is upgraded."""

import uuid
from typing import Any

from app.core.database import Database
from app.core.logger import EventLogger
from app.core.validation import SEX_SYNONYMS

log = EventLogger("app.core.migrations")


async def migrate_legacy_records(db: Database) -> None:
    member_to_patient: dict[str, str] = {}
    async for doc in db.patients.find({"patient_id": {"$exists": False}}):
        address = doc.get("address") or {}
        phone = str(doc.get("phone") or doc.get("phone_number") or "")
        sex = str(doc.get("sex") or "")
        patient_id = str(uuid.uuid4())
        await db.patients.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "patient_id": patient_id,
                    "phone_number": phone[-10:],
                    "address_line_1": address.get("line1"),
                    "address_line_2": address.get("line2"),
                    "city": address.get("city"),
                    "state": address.get("state"),
                    "zip_code": address.get("zip_code"),
                    "sex": SEX_SYNONYMS.get(sex.lower(), sex),
                    "deleted_at": doc.get("deleted_at"),
                    "created_via": doc.get("created_via") or "voice",
                },
                "$unset": {"address": "", "phone": ""},
            },
        )
        member_to_patient[doc["member_id"]] = patient_id

    if not member_to_patient:
        return

    async for call in db.calls.find(
        {
            "$or": [
                {"verified_member_id": {"$exists": True}},
                {"patients_created": {"$in": list(member_to_patient)}},
            ]
        }
    ):
        update: dict[str, Any] = {
            "$set": {
                "patients_created": [
                    member_to_patient.get(m, m) for m in call.get("patients_created", [])
                ]
            },
            "$unset": {"verified_member_id": ""},
        }
        verified = member_to_patient.get(call.get("verified_member_id") or "")
        if verified:
            update["$set"]["verified_patient_id"] = verified
        await db.calls.update_one({"_id": call["_id"]}, update)

    log.info("legacy_records_migrated", count=len(member_to_patient))
