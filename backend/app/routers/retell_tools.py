import logging

from fastapi import APIRouter, Depends

from app.deps import DbDep
from app.models import RetellToolRequest
from app.security import verify_retell_signature
from app.services import calls as calls_service
from app.services import patients as patients_service

logger = logging.getLogger("app.retell_tools")

router = APIRouter(
    prefix="/retell/tools",
    tags=["retell-tools"],
    dependencies=[Depends(verify_retell_signature)],
)


@router.post("/create-patient")
async def create_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    result = await patients_service.create_patient(db, call_id, body.args)
    if result["status"] == "created":
        await calls_service.record_patient_created(db, call_id, result["member_id"])
    logger.info("tool=create-patient call_id=%s status=%s", call_id, result["status"])
    return result


@router.post("/verify-patient")
async def verify_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    matched, member_id = await patients_service.verify_patient(db, body.args)
    await calls_service.record_verification_attempt(db, call_id, member_id)
    result = {"verification_result": "verified" if matched else "not_verified"}
    logger.info(
        "tool=verify-patient call_id=%s result=%s", call_id, result["verification_result"]
    )
    return result


@router.post("/get-patient")
async def get_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    member_id = await calls_service.get_verified_member_id(db, call_id)
    if not member_id:
        logger.info("tool=get-patient call_id=%s status=not_verified", call_id)
        return {"status": "not_verified", "message": "This caller is not verified."}

    patient = await patients_service.get_patient_by_member_id(db, member_id)
    if not patient:
        logger.info("tool=get-patient call_id=%s status=not_verified", call_id)
        return {"status": "not_verified", "message": "This caller is not verified."}

    logger.info("tool=get-patient call_id=%s status=ok", call_id)
    return {"status": "ok", "patient": patient}


@router.post("/update-patient")
async def update_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    member_id = await calls_service.get_verified_member_id(db, call_id)
    if not member_id:
        logger.info("tool=update-patient call_id=%s status=not_verified", call_id)
        return {"status": "not_verified", "message": "This caller is not verified."}

    result = await patients_service.update_patient(db, call_id, member_id, body.args)
    logger.info("tool=update-patient call_id=%s status=%s", call_id, result["status"])
    return result
