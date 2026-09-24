"""docs/agent-flow.html is drawn from the Retell agent by
scripts/render_agent_flow.py. Fail if someone edits agent.json and forgets to
redraw it, so the Docs page never shows an old flow."""

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_agent_flow.py"
spec = importlib.util.spec_from_file_location("render_agent_flow", SCRIPT)
render_agent_flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_agent_flow)


def test_flow_page_is_up_to_date():
    agent = json.loads(render_agent_flow.AGENT_PATH.read_text(encoding="utf-8"))
    committed = render_agent_flow.OUT_PATH.read_text(encoding="utf-8")
    assert committed == render_agent_flow.render(agent), (
        "docs/agent-flow.html is stale: run python scripts/render_agent_flow.py"
    )


def test_every_node_is_drawn():
    agent = json.loads(render_agent_flow.AGENT_PATH.read_text(encoding="utf-8"))
    page = render_agent_flow.render(agent)
    for node in agent["conversationFlow"]["nodes"]:
        assert node["name"] in page, node["id"]
