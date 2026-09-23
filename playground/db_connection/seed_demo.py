import asyncio
import os

import certifi
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())
    db = client["demo"]
    collection = db["demo_collection"]

    await collection.delete_many({})
    await collection.insert_many([
        {"name": "Alice", "age": 30, "role": "engineer"},
        {"name": "Bob", "age": 25, "role": "designer"},
        {"name": "Charlie", "age": 35, "role": "manager"},
    ])

    count = await collection.count_documents({})
    print(f"Inserted {count} documents into demo.demo_collection")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
