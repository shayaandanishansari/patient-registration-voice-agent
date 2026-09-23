from datetime import datetime, timezone

from app.core.migrations import migrate_legacy_records
from tests.conftest import API_HEADERS

NOW = datetime(2026, 9, 20, tzinfo=timezone.utc)

# A record exactly as the first backend version wrote it.
LEGACY_PATIENT = {
    "member_id": "12345678",
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "1990-03-05",
    "sex": "female",
    "phone": "+15125550123",
    "email": None,
    "address": {
        "line1": "123 Main St",
        "line2": None,
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
    },
    "preferred_language": "English",
    "created_at": NOW,
    "updated_at": NOW,
    "created_via_call_id": "call-old",
    "update_history": [],
}


async def test_legacy_records_are_upgraded_once(client, db):
    await db.patients.insert_one(dict(LEGACY_PATIENT))
    await db.calls.insert_one(
        {
            "call_id": "call-old",
            "patients_created": ["12345678"],
            "verified_member_id": "12345678",
            "verification_attempts": 1,
        }
    )

    await migrate_legacy_records(db)
    await migrate_legacy_records(db)  # idempotent

    patient = await db.patients.find_one({"member_id": "12345678"})
    assert patient["phone_number"] == "5125550123"
    assert patient["sex"] == "Female"
    assert patient["address_line_1"] == "123 Main St"
    assert "address" not in patient and "phone" not in patient

    call = await db.calls.find_one({"call_id": "call-old"})
    assert call["patients_created"] == [patient["patient_id"]]
    assert call["verified_patient_id"] == patient["patient_id"]
    assert "verified_member_id" not in call

    # And the upgraded record is readable through the new API.
    response = await client.get(f"/patients/{patient['patient_id']}", headers=API_HEADERS)
    assert response.status_code == 200
    assert response.json()["data"]["city"] == "Austin"
