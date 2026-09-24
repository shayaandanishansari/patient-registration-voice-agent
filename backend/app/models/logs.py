from typing import Any

from pydantic import BaseModel, Field

from app.models.common import UtcDatetime

# --- Log entry ------------------------------------------------------------
# One document from the logs collection (see app/core/logger.py).


class LogOut(BaseModel):
    id: str
    ts: UtcDatetime
    level: str
    logger: str
    event: str | None = Field(
        default=None,
        description="Set for EventLogger records; plain logging has message.",
    )
    message: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
    environment: str | None = None
    func: str | None = None
    line: int | None = None
    exception: str | None = None
