"""Push retell/conversation_flow.json to Retell.

Rewrites every placeholder tool URL to PUBLIC_BASE_URL, then creates a new
conversation flow or updates the one named by RETELL_CONVERSATION_FLOW_ID.

Usage (from backend/):
    python scripts/deploy_retell_flow.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from retell import Retell

PLACEHOLDER_URL = "https://YOUR-BACKEND.up.railway.app"
FLOW_PATH = Path(__file__).resolve().parent.parent / "retell" / "conversation_flow.json"


def main() -> None:
    load_dotenv()

    api_key = os.environ.get("RETELL_API_KEY")
    if not api_key:
        print("RETELL_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    base_url = os.environ.get("PUBLIC_BASE_URL")
    if not base_url:
        print("PUBLIC_BASE_URL is not set.", file=sys.stderr)
        sys.exit(1)
    base_url = base_url.rstrip("/")

    raw = FLOW_PATH.read_text(encoding="utf-8")
    raw = raw.replace(PLACEHOLDER_URL, base_url)
    flow = json.loads(raw)

    client = Retell(api_key=api_key)
    flow_id = os.environ.get("RETELL_CONVERSATION_FLOW_ID")

    if flow_id:
        response = client.conversation_flow.update(conversation_flow_id=flow_id, **flow)
        print(f"Updated conversation flow {response.conversation_flow_id}")
    else:
        response = client.conversation_flow.create(**flow)
        print(f"Created conversation flow {response.conversation_flow_id}")
        print("Set RETELL_CONVERSATION_FLOW_ID to this value to update it next time.")


if __name__ == "__main__":
    main()
