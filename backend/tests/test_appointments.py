from datetime import date

from app.services import appointments as appointments_service
from tests.conftest import API_HEADERS, post_signed, register_by_voice, retell_tool_body


async def _tool(client, path: str, call_id: str, args: dict) -> dict:
    response = await post_signed(
        client, f"/retell/tools/{path}", retell_tool_body(path, call_id, args)
    )
    assert response.status_code == 200
    return response.json()


async def test_slots_are_weekdays_only_and_respect_preference(db):
    friday = date(2026, 9, 25)
    slots = await appointments_service.available_slots(db, "afternoon", today=friday, limit=50)
    assert slots
    for slot in slots:
        assert not slot["slot_id"].startswith(("2026-09-26", "2026-09-27"))  # weekend
        assert int(slot["slot_id"][11:13]) >= 12
    assert slots[0]["spoken"] == "Monday, September 28 at 1 p.m."


async def test_scheduling_requires_a_patient_on_the_call(client):
    slots = await _tool(client, "get-appointment-slots", "call-anon", {})
    assert slots["status"] == "not_eligible"
    booked = await _tool(client, "book-appointment", "call-anon", {"slot_id": "2030-01-01T09:00"})
    assert booked["status"] == "not_eligible"


async def test_book_after_registration(client, db):
    call_id = "call-appt-1"
    await register_by_voice(client, call_id)
    patient = await db.patients.find_one({})

    offered = await _tool(client, "get-appointment-slots", call_id, {"preference": "morning"})
    assert offered["status"] == "ok"
    assert len(offered["slots"]) == 3
    slot = offered["slots"][0]

    booked = await _tool(client, "book-appointment", call_id, {"slot_id": slot["slot_id"]})
    assert booked["status"] == "booked"
    assert booked["spoken"] == slot["spoken"]

    # Retried tool call returns the same booking, not an error.
    again = await _tool(client, "book-appointment", call_id, {"slot_id": slot["slot_id"]})
    assert again["status"] == "booked"
    assert await db.appointments.count_documents({}) == 1

    # The slot is no longer offered, and someone else can't take it.
    reoffered = await _tool(client, "get-appointment-slots", call_id, {"preference": "morning"})
    assert slot["slot_id"] not in {s["slot_id"] for s in reoffered["slots"]}

    await register_by_voice(client, "call-appt-2", {
        "first_name": "Sam", "last_name": "Poe", "date_of_birth": "1980-01-01",
        "sex": "male", "phone_number": "5125550100", "address_line_1": "1 A St",
        "city": "Austin", "state": "TX", "zip_code": "78701",
    })
    taken = await _tool(client, "book-appointment", "call-appt-2", {"slot_id": slot["slot_id"]})
    assert taken["status"] == "unavailable"

    listed = (
        await client.get(f"/appointments?patient_id={patient['patient_id']}", headers=API_HEADERS)
    ).json()
    assert listed["error"] is None
    assert [a["slot_id"] for a in listed["data"]] == [slot["slot_id"]]


async def test_book_rejects_made_up_slot(client):
    call_id = "call-appt-3"
    await register_by_voice(client, call_id)
    result = await _tool(client, "book-appointment", call_id, {"slot_id": "tomorrow at noon"})
    assert result["status"] == "unavailable"
