from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.database import DbDep
from app.core.logger import EventLogger
from app.core.security import verify_retell_signature
from app.services import calls as calls_service

log = EventLogger("app.routers.retell_webhook")

# No signature dependency here: a bare GET connectivity check from the Retell
# dashboard's "Test" button carries no signature to verify.
probe_router = APIRouter(prefix="/retell", tags=["retell-webhook"])

router = APIRouter(
    prefix="/retell",
    tags=["retell-webhook"],
    dependencies=[Depends(verify_retell_signature)],
)

HANDLED_EVENTS = {"call_started", "call_ended", "call_analyzed"}


def _ms_to_datetime(value: Any) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _extract_call_fields(call: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_number": call.get("from_number"),
        "to_number": call.get("to_number"),
        "direction": call.get("direction"),
        "status": call.get("call_status"),
        "started_at": _ms_to_datetime(call.get("start_timestamp")),
        "ended_at": _ms_to_datetime(call.get("end_timestamp")),
        "duration_ms": (
            call.get("end_timestamp") - call.get("start_timestamp")
            if call.get("end_timestamp") and call.get("start_timestamp")
            else None
        ),
        "disconnection_reason": call.get("disconnection_reason"),
        "transcript": call.get("transcript"),
        "recording_url": call.get("recording_url"),
        "call_analysis": call.get("call_analysis"),
        "call_cost": call.get("call_cost"),
    }


@probe_router.get("/webhook")
async def retell_webhook_probe() -> dict[str, str]:
    """Retell's dashboard 'Test' / connectivity check may GET this URL before
    ever sending a real event. No signature required for a plain reachability
    check with no payload."""
    return {"status": "ok"}


@router.post("/webhook")
async def retell_webhook(request: Request, db: DbDep) -> dict[str, Any]:
    raw = await request.body()
    if not raw:
        # Retell's dashboard connectivity test may send an empty POST just to
        # confirm the URL is reachable and returns 2xx.
        log.info("webhook_empty_probe")
        return {"status": "ok"}

    try:
        body: dict[str, Any] = await request.json()
    except ValueError:
        log.info("webhook_unparseable_body", body=raw.decode("utf-8", "replace"))
        return {"status": "ok"}

    event = body.get("event")
    call = body.get("call") or {}
    call_id = call.get("call_id")
    # Everything Retell sent, as sent. This is also the conversation log the
    # brief asks for: call_ended carries the transcript, call_analyzed the
    # summary. Both also land on the calls document, linked to the patient.
    log.info("retell_webhook", webhook_event=event, call_id=call_id, body=body)

    if not call_id or event not in HANDLED_EVENTS:
        return {"status": "ok"}

    await calls_service.upsert_from_webhook(db, call_id, _extract_call_fields(call))
    return {"status": "ok"}
