from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# --- Retell request envelope ---------------------------------------------
# Retell posts {"name": <tool name>, "call": {...}, "args": {...}} to every
# custom tool endpoint. `call` and `args` carry whatever Retell sends; we
# only rely on the subset of `call` fields we actually read, and validate
# `args` field-by-field in app/validation.py rather than at this boundary,
# so bad input produces a 200 {"status": "invalid", ...} instead of a 422.


class RetellCall(BaseModel):
    model_config = ConfigDict(extra="allow")

    call_id: str
    from_number: str | None = None
    to_number: str | None = None
    direction: str | None = None
    transcript: str | None = None


class RetellToolRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    call: RetellCall
    args: dict[str, Any] = Field(default_factory=dict)
