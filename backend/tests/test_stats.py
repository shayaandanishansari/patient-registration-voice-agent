from datetime import datetime, timedelta, timezone

from tests.conftest import API_HEADERS

NOW = datetime.now(timezone.utc)


def _ago(**delta) -> datetime:
    return NOW - timedelta(**delta)


async def _stats(client) -> dict:
    response = await client.get("/stats", headers=API_HEADERS)
    assert response.status_code == 200
    return response.json()["data"]


async def test_empty_database(client):
    stats = await _stats(client)
    assert stats["live_calls"] == 0
    assert stats["calls_total"] == 0
    assert stats["patients_total"] == 0
    assert stats["avg_call_duration_ms_24h"] is None


async def test_counts_calls(client, db):
    await db.calls.insert_many(
        [
            {"call_id": "live", "status": "ongoing", "started_at": _ago(minutes=3)},
            # call_ended never arrived: too old to still be on the line.
            {"call_id": "stuck", "status": "ongoing", "started_at": _ago(hours=3)},
            {
                "call_id": "ended",
                "status": "ended",
                "started_at": _ago(hours=2),
                "duration_ms": 60_000,
            },
            {
                "call_id": "ended-2",
                "status": "ended",
                "started_at": _ago(hours=1),
                "duration_ms": 120_000,
            },
            {
                "call_id": "old",
                "status": "ended",
                "started_at": _ago(days=2),
                "duration_ms": 900_000,
            },
        ]
    )

    stats = await _stats(client)
    assert stats["live_calls"] == 1
    assert stats["calls_24h"] == 4
    assert stats["avg_call_duration_ms_24h"] == 90_000
    assert stats["calls_total"] == 5


async def test_counts_active_patients(client, db):
    def patient(n: int, created_at: datetime, deleted_at: datetime | None = None):
        # member_id is uniquely indexed, so each needs its own.
        return {
            "patient_id": f"p{n}",
            "member_id": f"1000000{n}",
            "created_at": created_at,
            "deleted_at": deleted_at,
        }

    await db.patients.insert_many(
        [
            patient(1, _ago(hours=1)),
            patient(2, _ago(days=5)),
            patient(3, _ago(hours=1), deleted_at=NOW),
        ]
    )

    stats = await _stats(client)
    assert stats["patients_total"] == 2
    assert stats["patients_24h"] == 1


async def test_counts_recent_problems(client, db):
    await db.logs.insert_many(
        [
            {"ts": _ago(minutes=5), "level": "ERROR"},
            {"ts": _ago(minutes=5), "level": "CRITICAL"},
            {"ts": _ago(minutes=5), "level": "WARNING"},
            {"ts": _ago(minutes=5), "level": "INFO"},
            {"ts": _ago(days=2), "level": "ERROR"},
        ]
    )

    stats = await _stats(client)
    assert stats["errors_24h"] == 2
    assert stats["warnings_24h"] == 1
