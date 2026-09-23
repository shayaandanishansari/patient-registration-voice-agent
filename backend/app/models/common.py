from datetime import datetime, timezone
from typing import Annotated, Any, Generic, TypeVar

from pydantic import AfterValidator, BaseModel

T = TypeVar("T")


def _assume_utc(value: datetime) -> datetime:
    # Mongo stores UTC but hands back naive datetimes; make that explicit so
    # the API serializes "...+00:00" instead of an ambiguous local-looking time.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(_assume_utc)]


# --- Response envelope -------------------------------------------------------
# Every REST response is {"data": ..., "error": null} on success and
# {"data": null, "error": {...}} on failure. List endpoints add "meta".


class ApiError(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class Envelope(BaseModel, Generic[T]):
    data: T | None = None
    error: ApiError | None = None


class ListMeta(BaseModel):
    limit: int
    next_cursor: str | None = None


class ListEnvelope(BaseModel, Generic[T]):
    data: list[T]
    error: ApiError | None = None
    meta: ListMeta
