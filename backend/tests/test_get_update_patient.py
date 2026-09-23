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
VERIFY_ARGS = {
    "member_id": None,
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "1990-03-05",
}


async def _register_and_verify(client, call_id: str) -> str:
    create_resp = await post_signed(
        client,
        "/retell/tools/create-patient",
        retell_tool_body("create_patient", f"{call_id}-register", CREATE_ARGS),
    )
    member_id = create_resp.json()["member_id"]
    args = {**VERIFY_ARGS, "member_id": member_id}
    await post_signed(
        client, "/retell/tools/verify-patient", retell_tool_body("verify_patient", call_id, args)
    )
    return member_id


async def test_get_patient_rejected_without_verification(client):
    response = await post_signed(
        client, "/retell/tools/get-patient", retell_tool_body("get_patient_profile", "call-noauth-1", {})
    )
    assert response.status_code == 200
    assert response.json()["status"] == "not_verified"


async def test_update_patient_rejected_without_verification(client):
    response = await post_signed(
        client,
        "/retell/tools/update-patient",
        retell_tool_body("update_patient_profile", "call-noauth-2", {"phone": "5125550199"}),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "not_verified"


async def test_get_patient_returns_own_record(client):
    call_id = "call-get-1"
    member_id = await _register_and_verify(client, call_id)
    response = await post_signed(
        client, "/retell/tools/get-patient", retell_tool_body("get_patient_profile", call_id, {})
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["patient"]["first_name"] == "Jane"
    assert "member_id" not in data["patient"]
    assert member_id  # sanity: registration actually happened


async def test_get_patient_ignores_member_id_in_args(client):
    """Args may contain a member_id, but only the verified session counts."""
    call_id = "call-get-2"
    await _register_and_verify(client, call_id)
    response = await post_signed(
        client,
        "/retell/tools/get-patient",
        retell_tool_body("get_patient_profile", call_id, {"member_id": "99999999"}),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["patient"]["first_name"] == "Jane"


async def test_update_patient_success(client, db):
    call_id = "call-update-1"
    member_id = await _register_and_verify(client, call_id)
    response = await post_signed(
        client,
        "/retell/tools/update-patient",
        retell_tool_body(
            "update_patient_profile", call_id, {"phone": "5125559999", "zip_code": "78702"}
        ),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert sorted(data["updated_fields"]) == ["phone", "zip_code"]

    patient = await db.patients.find_one({"member_id": member_id})
    assert patient["phone"] == "+15125559999"
    assert patient["address"]["zip_code"] == "78702"
    assert len(patient["update_history"]) == 1
    assert sorted(patient["update_history"][0]["fields_changed"]) == ["phone", "zip_code"]


async def test_update_patient_ignores_name_and_dob(client, db):
    call_id = "call-update-2"
    member_id = await _register_and_verify(client, call_id)
    response = await post_signed(
        client,
        "/retell/tools/update-patient",
        retell_tool_body(
            "update_patient_profile",
            call_id,
            {"first_name": "Janet", "date_of_birth": "1991-01-01", "phone": "5125551111"},
        ),
    )
    data = response.json()
    assert data["status"] == "updated"
    assert "in person" in data["message"]

    patient = await db.patients.find_one({"member_id": member_id})
    assert patient["first_name"] == "Jane"
    assert patient["date_of_birth"] == "1990-03-05"
    assert patient["phone"] == "+15125551111"


async def test_update_patient_invalid_zip_writes_nothing(client, db):
    call_id = "call-update-3"
    member_id = await _register_and_verify(client, call_id)
    response = await post_signed(
        client,
        "/retell/tools/update-patient",
        retell_tool_body("update_patient_profile", call_id, {"zip_code": "not-a-zip"}),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "invalid"

    patient = await db.patients.find_one({"member_id": member_id})
    assert patient["address"]["zip_code"] == "78701"
    assert patient["update_history"] == []
