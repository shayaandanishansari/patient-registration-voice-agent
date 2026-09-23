from tests.conftest import post_signed, register_by_voice, retell_tool_body, verify_by_voice


async def _register_and_verify(client, call_id: str) -> str:
    member_id = (await register_by_voice(client, f"{call_id}-register"))["member_id"]
    await verify_by_voice(client, call_id, member_id)
    return member_id


async def _update(client, call_id: str, args: dict) -> dict:
    response = await post_signed(
        client,
        "/retell/tools/update-patient",
        retell_tool_body("update_patient_profile", call_id, args),
    )
    assert response.status_code == 200
    return response.json()


async def _get(client, call_id: str, args: dict | None = None) -> dict:
    response = await post_signed(
        client,
        "/retell/tools/get-patient",
        retell_tool_body("get_patient_profile", call_id, args or {}),
    )
    assert response.status_code == 200
    return response.json()


async def test_get_patient_rejected_without_verification(client):
    assert (await _get(client, "call-noauth-1"))["status"] == "not_verified"


async def test_update_patient_rejected_without_verification(client):
    data = await _update(client, "call-noauth-2", {"phone_number": "5125550199"})
    assert data["status"] == "not_verified"


async def test_get_patient_returns_own_record(client):
    call_id = "call-get-1"
    await _register_and_verify(client, call_id)
    data = await _get(client, call_id)
    assert data["status"] == "ok"
    assert data["patient"]["first_name"] == "Jane"
    assert data["patient"]["preferred_language"] == "English"
    assert "member_id" not in data["patient"]
    assert "patient_id" not in data["patient"]


async def test_get_patient_ignores_member_id_in_args(client):
    """Args may contain a member_id, but only the verified session counts."""
    call_id = "call-get-2"
    await _register_and_verify(client, call_id)
    data = await _get(client, call_id, {"member_id": "99999999"})
    assert data["status"] == "ok"
    assert data["patient"]["first_name"] == "Jane"


async def test_update_patient_success(client, db):
    call_id = "call-update-1"
    member_id = await _register_and_verify(client, call_id)
    data = await _update(client, call_id, {"phone_number": "5125559999", "zip_code": "78702"})
    assert data["status"] == "updated"
    assert sorted(data["updated_fields"]) == ["phone_number", "zip_code"]

    patient = await db.patients.find_one({"member_id": member_id})
    assert patient["phone_number"] == "5125559999"
    assert patient["zip_code"] == "78702"
    assert len(patient["update_history"]) == 1
    entry = patient["update_history"][0]
    assert sorted(entry["fields_changed"]) == ["phone_number", "zip_code"]
    assert entry["source"] == "voice"
    assert entry["call_id"] == call_id


async def test_update_optional_fields_over_the_phone(client, db):
    call_id = "call-update-opt"
    member_id = await _register_and_verify(client, call_id)
    data = await _update(
        client,
        call_id,
        {"insurance_provider": "Aetna", "emergency_contact_name": "John Doe"},
    )
    assert data["status"] == "updated"
    assert "insurance company" in data["message"]

    patient = await db.patients.find_one({"member_id": member_id})
    assert patient["insurance_provider"] == "Aetna"


async def test_update_patient_ignores_identity_fields(client, db):
    call_id = "call-update-2"
    member_id = await _register_and_verify(client, call_id)
    data = await _update(
        client,
        call_id,
        {"first_name": "Janet", "date_of_birth": "1991-01-01", "phone_number": "5125551111"},
    )
    assert data["status"] == "updated"
    assert "in person" in data["message"]

    patient = await db.patients.find_one({"member_id": member_id})
    assert patient["first_name"] == "Jane"
    assert patient["date_of_birth"] == "1990-03-05"
    assert patient["phone_number"] == "5125551111"


async def test_update_patient_invalid_zip_writes_nothing(client, db):
    call_id = "call-update-3"
    member_id = await _register_and_verify(client, call_id)
    data = await _update(client, call_id, {"zip_code": "not-a-zip"})
    assert data["status"] == "invalid"

    patient = await db.patients.find_one({"member_id": member_id})
    assert patient["zip_code"] == "78701"
    assert patient["update_history"] == []
