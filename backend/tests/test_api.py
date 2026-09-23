from tests.conftest import TEST_API_READ_KEY, post_signed, retell_tool_body


async def test_health_no_auth_required(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


async def test_patients_requires_api_key(client):
    response = await client.get("/api/patients")
    assert response.status_code == 401


async def test_patients_rejects_wrong_key(client):
    response = await client.get("/api/patients", headers={"x-api-key": "wrong"})
    assert response.status_code == 401


async def test_list_and_get_patient(client):
    create_args = {
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
    create_resp = await post_signed(
        client, "/retell/tools/create-patient", retell_tool_body("create_patient", "call-api-1", create_args)
    )
    member_id = create_resp.json()["member_id"]

    headers = {"x-api-key": TEST_API_READ_KEY}
    list_resp = await client.get("/api/patients", headers=headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert any(p["member_id"] == member_id for p in body["items"])
    assert "create_idempotency_key" not in body["items"][0]

    get_resp = await client.get(f"/api/patients/{member_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["first_name"] == "Jane"

    missing_resp = await client.get("/api/patients/00000000", headers=headers)
    assert missing_resp.status_code == 404


async def test_list_and_get_call(client):
    call_id = "call-api-2"
    await post_signed(
        client,
        "/retell/tools/verify-patient",
        retell_tool_body(
            "verify_patient",
            call_id,
            {
                "member_id": "11111111",
                "first_name": "Nobody",
                "last_name": "Home",
                "date_of_birth": "1990-01-01",
            },
        ),
    )

    headers = {"x-api-key": TEST_API_READ_KEY}
    list_resp = await client.get("/api/calls", headers=headers)
    assert list_resp.status_code == 200
    assert any(c["call_id"] == call_id for c in list_resp.json()["items"])

    get_resp = await client.get(f"/api/calls/{call_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["verification_attempts"] == 1

    missing_resp = await client.get("/api/calls/does-not-exist", headers=headers)
    assert missing_resp.status_code == 404
