from tests.conftest import API_HEADERS, register_by_voice, verify_by_voice


async def test_verify_success_sets_call_session(client, db):
    member_id = (await register_by_voice(client, "call-register"))["member_id"]
    call_id = "call-verify-1"

    assert await verify_by_voice(client, call_id, member_id) == {"verification_result": "verified"}

    patient = await db.patients.find_one({"member_id": member_id})
    call_doc = await db.calls.find_one({"call_id": call_id})
    assert call_doc["verified_patient_id"] == patient["patient_id"]
    assert call_doc["verified_at"] is not None
    assert call_doc["verification_attempts"] == 1


async def test_verify_is_case_insensitive_and_accepts_us_date(client):
    member_id = (await register_by_voice(client, "call-register"))["member_id"]
    result = await verify_by_voice(
        client, "call-verify-us", member_id, first_name="jane", date_of_birth="03/05/1990"
    )
    assert result == {"verification_result": "verified"}


async def test_verify_wrong_dob_matches_not_verified_shape(client):
    member_id = (await register_by_voice(client, "call-register"))["member_id"]
    result = await verify_by_voice(client, "call-verify-2", member_id, date_of_birth="1991-03-05")
    assert result == {"verification_result": "not_verified"}


async def test_verify_wrong_name_matches_not_verified_shape(client):
    member_id = (await register_by_voice(client, "call-register"))["member_id"]
    result = await verify_by_voice(client, "call-verify-3", member_id, first_name="Janet")
    assert result == {"verification_result": "not_verified"}


async def test_verify_nonexistent_member_id_matches_not_verified_shape(client):
    await register_by_voice(client, "call-register")
    result = await verify_by_voice(client, "call-verify-4", "00000000")
    assert result == {"verification_result": "not_verified"}


async def test_verify_soft_deleted_patient_fails(client, db):
    member_id = (await register_by_voice(client, "call-register"))["member_id"]
    patient = await db.patients.find_one({"member_id": member_id})
    await client.delete(f"/patients/{patient['patient_id']}", headers=API_HEADERS)

    result = await verify_by_voice(client, "call-verify-deleted", member_id)
    assert result == {"verification_result": "not_verified"}


async def test_verification_attempts_increments_even_on_failure(client, db):
    call_id = "call-verify-5"
    await verify_by_voice(client, call_id, "11111111", first_name="Nobody", last_name="Home")
    call_doc = await db.calls.find_one({"call_id": call_id})
    assert call_doc["verification_attempts"] == 1
    assert call_doc.get("verified_patient_id") is None
