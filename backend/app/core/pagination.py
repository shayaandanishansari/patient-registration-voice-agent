import base64
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def _encode_cursor(object_id: ObjectId) -> str:
    return base64.urlsafe_b64encode(str(object_id).encode()).decode()


def _decode_cursor(cursor: str) -> ObjectId:
    try:
        return ObjectId(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, InvalidId) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor.") from exc


async def paginate(
    collection, query: dict[str, Any], limit: int, cursor: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    """Newest-first keyset pagination on Mongo's _id. Returns (docs,
    next_cursor)."""
    query = dict(query)
    if cursor:
        query["_id"] = {"$lt": _decode_cursor(cursor)}
    docs = await collection.find(query).sort("_id", -1).limit(limit + 1).to_list(
        length=limit + 1
    )
    has_more = len(docs) > limit
    docs = docs[:limit]
    next_cursor = _encode_cursor(docs[-1]["_id"]) if has_more and docs else None
    return docs, next_cursor
