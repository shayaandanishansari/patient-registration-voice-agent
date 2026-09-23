from typing import Annotated

import certifi
from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings


class Database:
    def __init__(self, client: AsyncIOMotorClient, db: AsyncIOMotorDatabase) -> None:
        self.client = client
        self.db = db

    @property
    def patients(self):
        return self.db["patients"]

    @property
    def calls(self):
        return self.db["calls"]

    @property
    def appointments(self):
        return self.db["appointments"]

    async def ping(self) -> None:
        await self.db.command("ping")

    async def create_indexes(self) -> None:
        # sparse: records from before patient_id existed have none until
        # app.core.migrations backfills them.
        await self.patients.create_index("patient_id", unique=True, sparse=True)
        await self.patients.create_index("member_id", unique=True)
        await self.patients.create_index(
            "create_idempotency_key", unique=True, sparse=True
        )
        await self.patients.create_index("last_name")
        await self.patients.create_index([("phone_number", 1), ("date_of_birth", 1)])
        await self.calls.create_index("call_id", unique=True)
        # Unique slot_id is what makes double-booking impossible.
        await self.appointments.create_index("slot_id", unique=True)
        await self.appointments.create_index("patient_id")


def connect(settings: Settings) -> Database:
    client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    return Database(client, client[settings.mongodb_db])


def get_db(request: Request) -> Database:
    return request.app.state.db


DbDep = Annotated[Database, Depends(get_db)]
