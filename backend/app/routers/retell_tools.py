import logging

from fastapi import APIRouter, Depends

from app.core.database import DbDep
from app.core.security import verify_retell_signature
from app.models.retell import RetellToolRequest
from app.services import appointments as appointments_service
from app.services import calls as calls_service
from app.services import patients as patients_service

logger = logging.getLogger("app.routers.retell_tools")

router = APIRouter(
    prefix="/retell/tools",
    tags=["retell-tools"],
    dependencies=[Depends(verify_retell_signature)],
)

NOT_VERIFIED = {"status": "not_verified", "message": "This caller is not verified."}


@router.post("/check-existing-patient")
async def check_existing_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    result = await patients_service.voice_check_existing(db, body.args)
    logger.info("tool=check-existing-patient call_id=%s status=%s", call_id, result["status"])
    return result


@router.post("/create-patient")
async def create_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    result, patient_id = await patients_service.voice_create_patient(db, call_id, body.args)
    if patient_id:
        await calls_service.record_patient_created(db, call_id, patient_id)
    logger.info("tool=create-patient call_id=%s status=%s", call_id, result["status"])
    return result


@router.post("/verify-patient")
async def verify_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    patient_id = await patients_service.verify_patient(db, body.args)
    await calls_service.record_verification_attempt(db, call_id, patient_id)
    result = {"verification_result": "verified" if patient_id else "not_verified"}
    logger.info(
        "tool=verify-patient call_id=%s result=%s", call_id, result["verification_result"]
    )
    return result


@router.post("/get-patient")
async def get_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    patient_id = await calls_service.get_verified_patient_id(db, call_id)
    patient = await patients_service.get_patient(db, patient_id) if patient_id else None
    if not patient:
        logger.info("tool=get-patient call_id=%s status=not_verified", call_id)
        return NOT_VERIFIED

    logger.info("tool=get-patient call_id=%s status=ok", call_id)
    return {"status": "ok", "patient": patients_service.to_voice_dict(patient)}


@router.post("/update-patient")
async def update_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    patient_id = await calls_service.get_verified_patient_id(db, call_id)
    if not patient_id:
        logger.info("tool=update-patient call_id=%s status=not_verified", call_id)
        return NOT_VERIFIED

    result = await patients_service.voice_update_patient(db, call_id, patient_id, body.args)
    logger.info("tool=update-patient call_id=%s status=%s", call_id, result["status"])
    return result


# --- Scheduling ------------------------------------------------------------------
# Booking is bound server-side to the patient this call registered or
# verified, never to an ID the LLM passes in.


@router.post("/get-appointment-slots")
async def get_appointment_slots(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    if not await calls_service.get_call_patient_id(db, call_id):
        logger.info("tool=get-appointment-slots call_id=%s status=not_eligible", call_id)
        return {"status": "not_eligible", "slots": []}

    preference = str(body.args.get("preference") or "")
    slots = await appointments_service.available_slots(db, preference)
    logger.info("tool=get-appointment-slots call_id=%s count=%d", call_id, len(slots))
    return {"status": "ok" if slots else "none_available", "slots": slots}


@router.post("/book-appointment")
async def book_appointment(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    patient_id = await calls_service.get_call_patient_id(db, call_id)
    if not patient_id:
        logger.info("tool=book-appointment call_id=%s status=not_eligible", call_id)
        return {"status": "not_eligible", "message": "No registered patient on this call."}

    slot_id = str(body.args.get("slot_id") or "").strip()
    try:
        appt = await appointments_service.book(db, patient_id, slot_id, call_id)
    except appointments_service.SlotUnavailable:
        logger.info("tool=book-appointment call_id=%s status=unavailable", call_id)
        return {"status": "unavailable", "message": "That time is no longer available."}

    logger.info("tool=book-appointment call_id=%s status=booked", call_id)
    return {
        "status": "booked",
        "spoken": appt["spoken"],
        "provider": appt["provider"],
        "message": f"Booked a {appt['visit_type'].lower()} with {appt['provider']} on {appt['spoken']}.",
    }
