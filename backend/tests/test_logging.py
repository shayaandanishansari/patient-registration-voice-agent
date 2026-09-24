import logging
from datetime import date

import pytest_asyncio

from app.core.logger import EventLogger, MongoLogHandler
from tests.conftest import (
    API_HEADERS,
    VOICE_ARGS,
    post_signed,
    register_by_voice,
    verify_by_voice,
)


@pytest_asyncio.fixture
async def log_sink(db):
    root = logging.getLogger()
    previous_level = root.level
    root.setLevel(logging.INFO)
    sink = MongoLogHandler(db.logs, environment="test", flush_interval=3600)
    sink.install()
    yield sink
    await sink.aclose()
    root.setLevel(previous_level)


async def test_event_is_persisted_with_structured_fields(db, log_sink):
    EventLogger("tests").info(
        "something_happened", call_id="call-1", dob=date(1990, 3, 5)
    )
    await log_sink.drain()

    doc = await db.logs.find_one({"event": "something_happened"})
    assert doc["level"] == "INFO"
    assert doc["logger"] == "tests"
    assert doc["environment"] == "test"
    assert doc["fields"] == {"call_id": "call-1", "dob": "1990-03-05"}
    assert doc["func"] == "test_event_is_persisted_with_structured_fields"
    assert "message" not in doc


async def test_plain_logging_is_persisted_as_message(db, log_sink):
    logging.getLogger("some.library").warning("disk %s", "low")
    await log_sink.drain()

    doc = await db.logs.find_one({"logger": "some.library"})
    assert doc["message"] == "disk low"
    assert doc["level"] == "WARNING"


async def test_exception_traceback_is_stored(db, log_sink):
    try:
        raise ValueError("boom")
    except ValueError:
        EventLogger("tests").exception("it_broke")
    await log_sink.drain()

    doc = await db.logs.find_one({"event": "it_broke"})
    assert doc["level"] == "ERROR"
    assert "ValueError: boom" in doc["exception"]


async def test_voice_registration_is_logged_with_payload_and_request_id(
    client, db, log_sink
):
    await register_by_voice(client, "call-log-1")
    await log_sink.drain()

    created = await db.logs.find_one({"event": "patient_created"})
    assert created["fields"]["call_id"] == "call-log-1"
    assert created["fields"]["source"] == "voice"
    assert created["fields"]["payload"]["last_name"] == VOICE_ARGS["last_name"]

    request = await db.logs.find_one({"event": "http_request"})
    assert request["fields"]["path"] == "/retell/tools/create-patient"
    assert request["fields"]["status"] == 200
    # Every record from one request shares its ID.
    assert created["request_id"] == request["request_id"] is not None


async def test_tool_call_logs_what_retell_sent_and_what_we_answered(
    client, db, log_sink
):
    await verify_by_voice(client, "call-log-2", "00000000")
    await log_sink.drain()

    doc = await db.logs.find_one({"event": "retell_tool"})
    assert doc["fields"]["tool"] == "verify_patient"
    assert doc["fields"]["call_id"] == "call-log-2"
    assert doc["fields"]["args"]["member_id"] == "00000000"
    assert doc["fields"]["response"] == {"verification_result": "not_verified"}


async def test_webhook_logs_the_full_body(client, db, log_sink):
    body = {
        "event": "call_ended",
        "call": {
            "call_id": "call-log-3",
            "transcript": "Agent: Hi\nUser: Hello",
            "disconnection_reason": "user_hangup",
        },
    }
    await post_signed(client, "/retell/webhook", body)
    await log_sink.drain()

    doc = await db.logs.find_one({"event": "retell_webhook"})
    assert doc["fields"]["call_id"] == "call-log-3"
    assert doc["fields"]["body"] == body


async def test_response_carries_request_id(client, log_sink):
    response = await client.get("/health")
    assert len(response.headers["x-request-id"]) == 32


async def test_validation_failure_logs_field_names_not_values(client, db, log_sink):
    response = await client.post(
        "/patients", json={"first_name": "Jane123"}, headers=API_HEADERS
    )
    assert response.status_code == 422
    await log_sink.drain()

    doc = await db.logs.find_one({"event": "request_validation_failed"})
    assert "first_name" in doc["fields"]["fields"]
    assert "Jane123" not in str(doc)


async def test_rejected_request_is_logged_as_warning(client, db, log_sink):
    await client.get("/patients")
    await log_sink.drain()

    doc = await db.logs.find_one({"event": "http_request"})
    assert doc["level"] == "WARNING"
    assert doc["fields"]["status"] == 401


async def test_database_failure_never_reaches_the_caller(capsys):
    class BrokenCollection:
        async def insert_many(self, docs, ordered):
            raise ConnectionError("atlas unreachable")

    sink = MongoLogHandler(BrokenCollection(), environment="test")
    logging.getLogger("tests").addHandler(sink)
    try:
        logging.getLogger("tests").error("still fine")
        await sink.drain()
    finally:
        logging.getLogger("tests").removeHandler(sink)

    assert "log persistence failed" in capsys.readouterr().err


async def test_voice_duplicate_is_logged_for_staff(client, db, log_sink):
    # Voice registers a returning caller anyway; the log is the trail of
    # when and on which call it happened.
    first = await register_by_voice(client, "call-duplog-1")
    await register_by_voice(client, "call-duplog-2")
    await log_sink.drain()

    doc = await db.logs.find_one({"event": "patient_duplicate_detected"})
    existing = await db.patients.find_one({"member_id": first["member_id"]})
    assert doc["fields"]["existing_patient_id"] == existing["patient_id"]
    assert doc["fields"]["call_id"] == "call-duplog-2"
    assert doc["fields"]["action"] == "registered_anyway"
