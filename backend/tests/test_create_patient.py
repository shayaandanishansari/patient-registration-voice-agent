from tests.conftest import VOICE_ARGS, post_signed, register_by_voice, retell_tool_body


async def test_create_patient_success(client, db):
    data = await register_by_voice(client, "call-create-1", {**VOICE_ARGS, "email": "jane@example.com"})
    assert data["status"] == "created"
    assert len(data["member_id"]) == 8
    assert data["member_id"].isdigit()
    assert data["patient_name"] == "Jane Doe"

    patient = await db.patients.find_one({"member_id": data["member_id"]})
    assert patient["phone_number"] == "5125550123"
    assert patient["sex"] == "Female"
    assert patient["preferred_language"] == "English"
    assert patient["deleted_at"] is None
    assert patient["created_via"] == "voice"
    assert len(patient["patient_id"]) == 36


async def test_create_patient_with_optional_fields(client, db):
    args = {
        **VOICE_ARGS,
        "insurance_provider": "Blue Cross",
        "insurance_member_id": "xyz 123-456",
        "preferred_language": "spanish",
        "emergency_contact_name": "John Doe",
        "emergency_contact_phone": "(512) 555-0199",
    }
    data = await register_by_voice(client, "call-create-opt", args)
    assert data["status"] == "created"

    patient = await db.patients.find_one({"member_id": data["member_id"]})
    assert patient["insurance_member_id"] == "XYZ123456"
    assert patient["preferred_language"] == "Spanish"
    assert patient["emergency_contact_phone"] == "5125550199"


async def test_create_patient_decline_to_answer_sex(client, db):
    data = await register_by_voice(client, "call-create-sex", {**VOICE_ARGS, "sex": "decline to answer"})
    patient = await db.patients.find_one({"member_id": data["member_id"]})
    assert patient["sex"] == "Decline to Answer"


async def test_create_patient_accepts_legacy_arg_names(client, db):
    args = {k: v for k, v in VOICE_ARGS.items() if k not in ("phone_number", "address_line_1")}
    args |= {"phone": "5125550123", "address_line1": "123 Main St"}
    data = await register_by_voice(client, "call-create-legacy", args)
    assert data["status"] == "created"


async def test_create_patient_invalid_field(client):
    data = await register_by_voice(client, "call-create-2", {**VOICE_ARGS, "zip_code": "abc"})
    assert data["status"] == "invalid"
    assert data["member_id"] == ""
    assert "ZIP" in data["message"]


async def test_create_patient_future_dob_gets_speakable_message(client):
    data = await register_by_voice(client, "call-create-dob", {**VOICE_ARGS, "date_of_birth": "2999-01-01"})
    assert data["status"] == "invalid"
    assert data["message"] == "The date of birth can't be in the future."


async def test_create_patient_missing_required_field_is_speakable(client):
    args = {k: v for k, v in VOICE_ARGS.items() if k != "city"}
    data = await register_by_voice(client, "call-create-missing", args)
    assert data["status"] == "invalid"
    assert "city" in data["message"]
    assert "Field required" not in data["message"]


async def test_create_patient_retry_is_idempotent(client, db):
    call_id = "call-create-3"
    first = await register_by_voice(client, call_id)
    second = await register_by_voice(client, call_id)

    assert first["status"] == second["status"] == "created"
    assert first["member_id"] == second["member_id"]
    assert await db.patients.count_documents({}) == 1

    patient = await db.patients.find_one({})
    call_doc = await db.calls.find_one({"call_id": call_id})
    assert call_doc["patients_created"] == [patient["patient_id"]]


async def test_create_patient_two_people_same_call(client, db):
    call_id = "call-create-4"
    first = await register_by_voice(client, call_id)
    second = await register_by_voice(
        client, call_id, {**VOICE_ARGS, "first_name": "John", "last_name": "Smith"}
    )

    assert first["member_id"] != second["member_id"]
    assert await db.patients.count_documents({}) == 2
    call_doc = await db.calls.find_one({"call_id": call_id})
    assert len(call_doc["patients_created"]) == 2


async def test_same_person_on_a_later_call_is_a_duplicate(client, db):
    await register_by_voice(client, "call-dup-1")
    data = await register_by_voice(client, "call-dup-2", {**VOICE_ARGS, "first_name": "JANE"})
    assert data["status"] == "duplicate"
    assert data["patient_name"] == "Jane Doe"
    assert data["member_id"] == ""
    assert await db.patients.count_documents({}) == 1


async def test_household_member_on_same_phone_is_not_a_duplicate(client, db):
    await register_by_voice(client, "call-house-1")
    data = await register_by_voice(
        client,
        "call-house-2",
        {**VOICE_ARGS, "first_name": "Jimmy", "date_of_birth": "2015-06-01"},
    )
    assert data["status"] == "created"


async def test_check_existing_patient(client):
    await register_by_voice(client, "call-check-1")

    async def check(args):
        response = await post_signed(
            client,
            "/retell/tools/check-existing-patient",
            retell_tool_body("check_existing_patient", "call-check-2", args),
        )
        return response.json()

    identity = {k: VOICE_ARGS[k] for k in ("first_name", "last_name", "date_of_birth", "phone_number")}
    found = await check(identity)
    assert found == {
        "status": "existing",
        "patient_name": "Jane Doe",
        "message": "A registration with these details already exists.",
    }

    other = await check({**identity, "first_name": "Jimmy"})
    assert other["status"] == "none"
    assert other["patient_name"] == ""

    bad_phone = await check({**identity, "phone_number": "123"})
    assert bad_phone["status"] == "invalid"
    assert "phone number" in bad_phone["message"]


async def test_db_failure_returns_error_not_silence(client, db, monkeypatch):
    async def broken_insert(*args, **kwargs):
        raise RuntimeError("database is down")

    monkeypatch.setattr(type(db.patients), "insert_one", broken_insert)
    response = await post_signed(
        client,
        "/retell/tools/create-patient",
        retell_tool_body("create_patient", "call-db-down", VOICE_ARGS),
    )
    # Non-2xx makes Retell take the flow's else-edge to the spoken error node.
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
