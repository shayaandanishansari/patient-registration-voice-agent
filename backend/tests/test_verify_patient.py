from tests.conftest import post_signed, retell_tool_body

CREATE_ARGS = {
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "1990-03-05",
    "sex": "female",
    "phone": "5125550123",
    "address_line1": "123 Main St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
}


async def _register(client) -> str:
    body = retell_tool_body("create_patient", "call-register", CREATE_ARGS)
    response = await post_signed(client, "/retell/tools/create-patient", body)
    return response.json()["member_id"]


async def test_verify_success_sets_call_session(client, db):
    member_id = await _register(client)
    call_id = "call-verify-1"
    args = {
        "member_id": member_id,
        "first_name": "Jane",
        "last_name": "Doe",
        "date_of_birth": "1990-03-05",
    }
    response = await post_signed(
        client, "/retell/tools/verify-patient", retell_tool_body("verify_patient", call_id, args)
    )
    assert response.status_code == 200
    assert response.json() == {"verification_result": "verified"}

    call_doc = await db.calls.find_one({"call_id": call_id})
    assert call_doc["verified_member_id"] == member_id
    assert call_doc["verified_at"] is not None
    assert call_doc["verification_attempts"] == 1


async def test_verify_wrong_dob_matches_not_verified_shape(client):
    member_id = await _register(client)
    args = {
        "member_id": member_id,
        "first_name": "Jane",
        "last_name": "Doe",
        "date_of_birth": "1991-03-05",
    }
    response = await post_signed(
        client, "/retell/tools/verify-patient", retell_tool_body("verify_patient", "call-verify-2", args)
    )
    assert response.status_code == 200
    assert response.json() == {"verification_result": "not_verified"}
    assert set(response.json().keys()) == {"verification_result"}


async def test_verify_wrong_name_matches_not_verified_shape(client):
    member_id = await _register(client)
    args = {
        "member_id": member_id,
        "first_name": "Janet",
        "last_name": "Doe",
        "date_of_birth": "1990-03-05",
    }
    response = await post_signed(
        client, "/retell/tools/verify-patient", retell_tool_body("verify_patient", "call-verify-3", args)
    )
    assert response.status_code == 200
    assert response.json() == {"verification_result": "not_verified"}


async def test_verify_nonexistent_member_id_matches_not_verified_shape(client):
    await _register(client)
    args = {
        "member_id": "00000000",
        "first_name": "Jane",
        "last_name": "Doe",
        "date_of_birth": "1990-03-05",
    }
    response = await post_signed(
        client, "/retell/tools/verify-patient", retell_tool_body("verify_patient", "call-verify-4", args)
    )
    assert response.status_code == 200
    assert response.json() == {"verification_result": "not_verified"}


async def test_verification_attempts_increments_even_on_failure(client, db):
    call_id = "call-verify-5"
    args = {
        "member_id": "11111111",
        "first_name": "Nobody",
        "last_name": "Home",
        "date_of_birth": "1990-01-01",
    }
    await post_signed(
        client, "/retell/tools/verify-patient", retell_tool_body("verify_patient", call_id, args)
    )
    call_doc = await db.calls.find_one({"call_id": call_id})
    assert call_doc["verification_attempts"] == 1
    assert call_doc.get("verified_member_id") is None
