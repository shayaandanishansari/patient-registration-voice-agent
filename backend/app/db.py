import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import Settings


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

    async def ping(self) -> None:
        await self.db.command("ping")

    async def create_indexes(self) -> None:
        await self.patients.create_index("member_id", unique=True)
        await self.patients.create_index(
            "create_idempotency_key", unique=True, sparse=True
        )
        await self.patients.create_index("last_name")
        await self.calls.create_index("call_id", unique=True)


def connect(settings: Settings) -> Database:
    client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    db = client[settings.mongodb_db]
    return Database(client, db)
