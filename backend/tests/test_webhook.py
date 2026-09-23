from tests.conftest import post_signed


def _webhook_body(event: str, call_id: str, **call_overrides):
    call = {
        "call_id": call_id,
        "from_number": "+15125551234",
        "to_number": "+15125555678",
        "direction": "inbound",
        "call_status": "ended",
        "start_timestamp": 1000,
        "end_timestamp": 5000,
        **call_overrides,
    }
    return {"event": event, "call": call}


async def test_webhook_unsigned_rejected(client):
    import json

    response = await client.post(
        "/retell/webhook",
        content=json.dumps(_webhook_body("call_started", "call-wh-0")),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401


async def test_webhook_upserts_call(client, db):
    body = _webhook_body("call_ended", "call-wh-1", disconnection_reason="user_hangup")
    response = await post_signed(client, "/retell/webhook", body)
    assert response.status_code == 204

    call_doc = await db.calls.find_one({"call_id": "call-wh-1"})
    assert call_doc["from_number"] == "+15125551234"
    assert call_doc["duration_ms"] == 4000
    assert call_doc["disconnection_reason"] == "user_hangup"


async def test_webhook_is_idempotent(client, db):
    body = _webhook_body("call_ended", "call-wh-2")
    await post_signed(client, "/retell/webhook", body)
    await post_signed(client, "/retell/webhook", body)

    count = await db.calls.count_documents({"call_id": "call-wh-2"})
    assert count == 1


async def test_webhook_never_overwrites_verification_state(client, db):
    call_id = "call-wh-3"
    await db.calls.update_one(
        {"call_id": call_id},
        {"$set": {"verified_member_id": "12345678", "patients_created": ["12345678"]}},
        upsert=True,
    )

    body = _webhook_body("call_ended", call_id)
    await post_signed(client, "/retell/webhook", body)

    call_doc = await db.calls.find_one({"call_id": call_id})
    assert call_doc["verified_member_id"] == "12345678"
    assert call_doc["patients_created"] == ["12345678"]


async def test_webhook_ignores_unknown_event(client, db):
    body = _webhook_body("call_ringing", "call-wh-4")
    response = await post_signed(client, "/retell/webhook", body)
    assert response.status_code == 204
    call_doc = await db.calls.find_one({"call_id": "call-wh-4"})
    assert call_doc is None
