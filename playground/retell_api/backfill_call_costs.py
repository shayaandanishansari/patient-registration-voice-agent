"""One-off: fill call_cost on calls stored before the webhook saved it.

The webhook now stores Retell's call_cost on each call; calls from before that
change don't have it. This fetches each one from Retell's API and $sets only
call_cost, so nothing else on the call changes. Safe to re-run.

Run from backend/ (it reads backend/.env):
    python ../playground/retell_api/backfill_call_costs.py          # dry run
    python ../playground/retell_api/backfill_call_costs.py --write
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from retell import Retell  # noqa: E402

from app.core.config import get_settings  # noqa: E402


async def main(write: bool) -> None:
    settings = get_settings()
    db = AsyncIOMotorClient(settings.mongodb_uri)[settings.mongodb_db]
    key = settings.retell_api_key
    retell = Retell(api_key=getattr(key, "get_secret_value", lambda: key)())

    missing = db.calls.find({"call_cost": {"$exists": False}}, {"call_id": 1})
    total = 0.0
    async for doc in missing:
        call_id = doc["call_id"]
        try:
            cost = retell.call.retrieve(call_id).model_dump().get("call_cost")
        except Exception as exc:  # e.g. the probe call, which Retell never saw
            print(f"{call_id}: skipped ({type(exc).__name__})")
            continue
        if not cost or cost.get("combined_cost") is None:
            print(f"{call_id}: no cost yet")
            continue
        total += cost["combined_cost"]
        print(f"{call_id}: ${cost['combined_cost'] / 100:.2f}")
        if write:
            await db.calls.update_one({"call_id": call_id}, {"$set": {"call_cost": cost}})

    print(f"{'Wrote' if write else 'Would write'} ${total / 100:.2f} across these calls.")


if __name__ == "__main__":
    asyncio.run(main(write="--write" in sys.argv))
