from typing import Annotated

import certifi
from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings

# Log documents expire after this long (TTL index on logs.ts). Changing it
# needs the existing index dropped or collMod'ed first.
LOG_RETENTION_DAYS = 90


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

    @property
    def logs(self):
        return self.db["logs"]

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
        await self.logs.create_index(
            "ts", expireAfterSeconds=LOG_RETENTION_DAYS * 24 * 60 * 60
        )
        await self.logs.create_index([("event", 1), ("ts", -1)])
        await self.logs.create_index([("level", 1), ("ts", -1)])
        await self.logs.create_index("request_id")
        await self.logs.create_index("fields.call_id", sparse=True)
        await self.logs.create_index("fields.patient_id", sparse=True)


def connect(settings: Settings) -> Database:
    client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    return Database(client, client[settings.mongodb_db])


def get_db(request: Request) -> Database:
    return request.app.state.db


DbDep = Annotated[Database, Depends(get_db)]
