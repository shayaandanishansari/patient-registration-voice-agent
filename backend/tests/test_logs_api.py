from datetime import datetime, timedelta, timezone

import pytest_asyncio

from tests.conftest import API_HEADERS

NOW = datetime.now(timezone.utc)


def _log(minutes_ago: int, level: str = "INFO", event: str = "thing", **fields):
    return {
        "ts": NOW - timedelta(minutes=minutes_ago),
        "level": level,
        "logger": "tests",
        "event": event,
        "fields": fields,
        "request_id": None,
    }


@pytest_asyncio.fixture
async def seeded(db):
    # Inserted oldest first, as the handler would write them.
    await db.logs.insert_many(
        [
            _log(3 * 24 * 60, event="old"),
            _log(90, level="WARNING", event="retell_tool", call_id="call-1"),
            _log(30, level="ERROR", event="unhandled_error"),
            _log(5, event="http_request", call_id="call-2"),
        ]
    )


async def _events(client, **params):
    response = await client.get("/logs", params=params, headers=API_HEADERS)
    assert response.status_code == 200
    return [entry["event"] for entry in response.json()["data"]]


async def test_lists_newest_first(client, seeded):
    assert await _events(client) == ["http_request", "unhandled_error", "retell_tool", "old"]


async def test_filters_by_time_range(client, seeded):
    since = (NOW - timedelta(hours=2)).isoformat()
    until = (NOW - timedelta(minutes=10)).isoformat()
    assert await _events(client, since=since, until=until) == [
        "unhandled_error",
        "retell_tool",
    ]


async def test_filters_by_minimum_level(client, seeded):
    assert await _events(client, level="WARNING") == ["unhandled_error", "retell_tool"]


async def test_filters_by_event_and_call_id(client, seeded):
    assert await _events(client, event="old") == ["old"]
    assert await _events(client, call_id="call-1") == ["retell_tool"]


async def test_can_hide_http_request_records(client, seeded):
    assert await _events(client, hide_http="true") == [
        "unhandled_error",
        "retell_tool",
        "old",
    ]


async def test_pages_with_cursor(client, seeded):
    first = await client.get("/logs", params={"limit": 3}, headers=API_HEADERS)
    cursor = first.json()["meta"]["next_cursor"]
    second = await client.get(
        "/logs", params={"limit": 3, "cursor": cursor}, headers=API_HEADERS
    )
    assert [e["event"] for e in second.json()["data"]] == ["old"]
    assert second.json()["meta"]["next_cursor"] is None


async def test_lists_event_names(client, seeded):
    response = await client.get("/logs/events", headers=API_HEADERS)
    assert response.json()["data"] == [
        "http_request",
        "old",
        "retell_tool",
        "unhandled_error",
    ]


async def test_rejects_unknown_level(client, seeded):
    response = await client.get("/logs", params={"level": "LOUD"}, headers=API_HEADERS)
    assert response.status_code == 400
