import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.database import Database, DbDep
from app.core.security import require_api_key
from app.models.common import Envelope
from app.models.stats import StatsOut
from app.services.patients import ACTIVE, possible_duplicate_ids

router = APIRouter(
    prefix="/stats", tags=["stats"], dependencies=[Depends(require_api_key)]
)

# Retell's default max_call_duration_ms. An "ongoing" call older than this
# lost its call_ended webhook rather than still being on the line.
LIVE_CALL_WINDOW = timedelta(hours=1)


async def _avg_duration_ms(db: Database, since: datetime) -> int | None:
    rows = await db.calls.aggregate(
        [
            {"$match": {"started_at": {"$gte": since}, "duration_ms": {"$gt": 0}}},
            {"$group": {"_id": None, "avg": {"$avg": "$duration_ms"}}},
        ]
    ).to_list(length=1)
    return round(rows[0]["avg"]) if rows and rows[0]["avg"] is not None else None


@router.get("", response_model=Envelope[StatsOut])
async def get_stats(db: DbDep) -> Envelope[StatsOut]:
    """Headline counts for the dashboard homepage."""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    (
        live_calls,
        calls_24h,
        avg_duration,
        calls_total,
        patients_total,
        patients_24h,
        errors_24h,
        warnings_24h,
        duplicate_groups,
    ) = await asyncio.gather(
        db.calls.count_documents(
            {"status": "ongoing", "started_at": {"$gte": now - LIVE_CALL_WINDOW}}
        ),
        db.calls.count_documents({"started_at": {"$gte": day_ago}}),
        _avg_duration_ms(db, day_ago),
        db.calls.count_documents({}),
        db.patients.count_documents(ACTIVE),
        db.patients.count_documents({**ACTIVE, "created_at": {"$gte": day_ago}}),
        db.logs.count_documents(
            {"ts": {"$gte": day_ago}, "level": {"$in": ["ERROR", "CRITICAL"]}}
        ),
        db.logs.count_documents({"ts": {"$gte": day_ago}, "level": "WARNING"}),
        possible_duplicate_ids(db),
    )

    return Envelope(
        data=StatsOut(
            generated_at=now,
            live_calls=live_calls,
            calls_24h=calls_24h,
            avg_call_duration_ms_24h=avg_duration,
            calls_total=calls_total,
            patients_total=patients_total,
            patients_24h=patients_24h,
            possible_duplicates=len(duplicate_groups),
            errors_24h=errors_24h,
            warnings_24h=warnings_24h,
        )
    )
