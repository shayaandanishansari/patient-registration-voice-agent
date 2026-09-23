import json

from tests.conftest import retell_tool_body, sign_body


async def test_unsigned_request_rejected(client):
    body = retell_tool_body("get_patient_profile", "call-1", {})
    response = await client.post(
        "/retell/tools/get-patient",
        content=json.dumps(body, separators=(",", ":")),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401


async def test_tampered_body_rejected(client):
    body = retell_tool_body("get_patient_profile", "call-1", {})
    _, signature = sign_body(body)
    tampered = json.dumps({**body, "args": {"member_id": "99999999"}})
    response = await client.post(
        "/retell/tools/get-patient",
        content=tampered,
        headers={
            "content-type": "application/json",
            "x-retell-signature": signature,
        },
    )
    assert response.status_code == 401


async def test_properly_signed_request_accepted(client):
    body = retell_tool_body("get_patient_profile", "call-1", {})
    raw, signature = sign_body(body)
    response = await client.post(
        "/retell/tools/get-patient",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-retell-signature": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "not_verified"
