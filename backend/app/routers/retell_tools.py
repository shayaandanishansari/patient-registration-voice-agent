import json

from fastapi import APIRouter, Depends, Request, Response
from fastapi.routing import APIRoute

from app.core.database import DbDep
from app.core.logger import EventLogger
from app.core.security import verify_retell_signature
from app.models.retell import RetellToolRequest
from app.services import calls as calls_service
from app.services import patients as patients_service

log = EventLogger("app.routers.retell_tools")


class LoggedToolRoute(APIRoute):
    """Logs every tool call once: what Retell sent and what we answered.

    The `call` object is left out except for its ID: Retell repeats the whole
    call (transcript so far included) on every tool call, and the webhook
    delivers the final one anyway. Requests that fail the signature check
    never reach this handler; they're logged as retell_signature_*."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def logged_handler(request: Request) -> Response:
            response = await handler(request)
            body = await request.json()  # already read and cached by the handler
            log.info(
                "retell_tool",
                tool=body.get("name"),
                call_id=(body.get("call") or {}).get("call_id"),
                args=body.get("args"),
                response=json.loads(response.body),
            )
            return response

        return logged_handler


router = APIRouter(
    prefix="/retell/tools",
    tags=["retell-tools"],
    dependencies=[Depends(verify_retell_signature)],
    route_class=LoggedToolRoute,
)

NOT_VERIFIED = {"status": "not_verified", "message": "This caller is not verified."}


@router.post("/create-patient")
async def create_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    result, patient_id = await patients_service.voice_create_patient(db, call_id, body.args)
    if patient_id:
        await calls_service.record_patient_created(db, call_id, patient_id)
    return result


@router.post("/verify-patient")
async def verify_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    patient_id = await patients_service.verify_patient(db, body.args)
    await calls_service.record_verification_attempt(db, call_id, patient_id)
    result = {"verification_result": "verified" if patient_id else "not_verified"}
    return result


@router.post("/get-patient")
async def get_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    patient_id = await calls_service.get_verified_patient_id(db, call_id)
    patient = await patients_service.get_patient(db, patient_id) if patient_id else None
    if not patient:
        return NOT_VERIFIED

    return {"status": "ok", "patient": patients_service.to_voice_dict(patient)}


@router.post("/update-patient")
async def update_patient(body: RetellToolRequest, db: DbDep) -> dict:
    call_id = body.call.call_id
    patient_id = await calls_service.get_verified_patient_id(db, call_id)
    if not patient_id:
        return NOT_VERIFIED

    result = await patients_service.voice_update_patient(db, call_id, patient_id, body.args)
    return result
