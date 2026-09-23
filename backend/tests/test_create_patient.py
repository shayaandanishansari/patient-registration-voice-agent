from tests.conftest import post_signed, retell_tool_body

VALID_ARGS = {
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "1990-03-05",
    "sex": "female",
    "phone": "5125550123",
    "email": "jane@example.com",
    "address_line1": "123 Main St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
}


async def test_create_patient_success(client):
    body = retell_tool_body("create_patient", "call-create-1", VALID_ARGS)
    response = await post_signed(client, "/retell/tools/create-patient", body)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert len(data["member_id"]) == 8
    assert data["member_id"].isdigit()
    assert data["message"]


async def test_create_patient_invalid_field(client):
    args = {**VALID_ARGS, "zip_code": "abc"}
    body = retell_tool_body("create_patient", "call-create-2", args)
    response = await post_signed(client, "/retell/tools/create-patient", body)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid"
    assert data["member_id"] == ""
    assert "ZIP" in data["message"]


async def test_create_patient_retry_is_idempotent(client, db):
    call_id = "call-create-3"
    body = retell_tool_body("create_patient", call_id, VALID_ARGS)

    first = await post_signed(client, "/retell/tools/create-patient", body)
    second = await post_signed(client, "/retell/tools/create-patient", body)

    assert first.json()["member_id"] == second.json()["member_id"]
    count = await db.patients.count_documents({})
    assert count == 1

    call_doc = await db.calls.find_one({"call_id": call_id})
    assert call_doc["patients_created"] == [first.json()["member_id"]]


async def test_create_patient_two_people_same_call(client, db):
    call_id = "call-create-4"
    first_args = VALID_ARGS
    second_args = {**VALID_ARGS, "first_name": "John", "last_name": "Smith"}

    first = await post_signed(
        client, "/retell/tools/create-patient", retell_tool_body("create_patient", call_id, first_args)
    )
    second = await post_signed(
        client, "/retell/tools/create-patient", retell_tool_body("create_patient", call_id, second_args)
    )

    assert first.json()["member_id"] != second.json()["member_id"]
    count = await db.patients.count_documents({})
    assert count == 2

    call_doc = await db.calls.find_one({"call_id": call_id})
    assert sorted(call_doc["patients_created"]) == sorted(
        [first.json()["member_id"], second.json()["member_id"]]
    )
