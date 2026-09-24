"""Draw the Retell conversation flow (assets/retell_agent_scripts/agent.json) as
a standalone page, docs/agent-flow.html: the registration path on top,
returning callers below. Hover a node or an arrow for its full instruction or
condition.

Run from backend/ after editing the agent:
    python scripts/render_agent_flow.py

tests/test_agent_flow_doc.py fails if the committed page is out of date.
"""

import json
from html import escape
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
AGENT_PATH = BACKEND / "assets" / "retell_agent_scripts" / "agent.json"
OUT_PATH = BACKEND.parent / "docs" / "agent-flow.html"

NODE_W, NODE_H = 265, 84
COL_W, ROW_H = 390, 160
MARGIN = 60

# The node every step can hand off to when the caller is done.
GOODBYE = "end_goodbye"

# (column, row) per node. Registration runs along the top, returning callers
# along the bottom. A node not listed here (added to the flow later) goes in
# an extra row at the bottom, so it still shows up.
GRID = {
    "welcome": (0, 1.5),
    "reg_collect": (1, 0),
    "reg_create": (2, 0),
    "reg_success": (3, 0),
    "reg_fix": (2, 1),
    "system_error": (3, 1),
    "forgot_member_id": (1, 2),
    "verify_collect": (1, 3),
    "verify_check": (2, 3),
    "manage_profile": (3, 3),
    "verify_failed": (2, 4),
    "end_goodbye": (4, 1.5),
}

# Short arrow labels. The full condition is in each arrow's tooltip; an edge
# missing here falls back to the start of its condition.
EDGE_LABELS = {
    "e_welcome_register": "new patient",
    "e_welcome_existing": "check or update",
    "e_welcome_forgot": "forgot member ID",
    "e_reg_confirmed": "summary confirmed",
    "e_fix_confirmed": "fix confirmed",
    "e_success_another": "register another",
    "e_success_existing": "check or update",
    "e_verify_ready": "details confirmed",
    "e_verify_forgot": "forgot member ID",
    "e_forgot_register": "register new",
}

NODE_STYLES = {
    "conversation": ("#e6f5f2", "#0f7667", "Conversation"),
    "function": ("#fff4e0", "#b26a00", "Tool call"),
    "subagent": ("#efeafd", "#5b3fc4", "Subagent (tools)"),
    "end": ("#f1f5f9", "#475569", "Ends the call"),
}


def _condition(edge: dict) -> str:
    cond = edge["transition_condition"]
    if cond["type"] == "prompt":
        return cond["prompt"]
    return f" {cond['operator']} ".join(
        f"{e['left'].strip('{}')} {e['operator']} {e['right']}" for e in cond["equations"]
    )


def _label(edge: dict, is_else: bool) -> str:
    if is_else:
        return "otherwise"
    if edge["transition_condition"]["type"] == "equation":
        return " & ".join(e["right"] for e in edge["transition_condition"]["equations"])
    if edge["id"] in EDGE_LABELS:
        return EDGE_LABELS[edge["id"]]
    words = _condition(edge).split()
    return " ".join(words[:3]) + ("…" if len(words) > 3 else "")


def _route(src, dst, two_way: bool, channel: float):
    """SVG path for an arrow between two node boxes, and where its label goes."""
    (sx, sy), (tx, ty) = src, dst
    if abs(tx - sx) < 1:  # same column: straight up or down
        down = ty > sy
        x = sx + NODE_W / 2 + ((-30 if down else 30) if two_way else 0)
        y1, y2 = (sy + NODE_H, ty) if down else (sy, ty + NODE_H)
        return f"M{x},{y1} L{x},{y2}", (x, (y1 + y2) / 2)
    if tx > sx:  # forward: right side to left side
        x1, y1, x2, y2 = sx + NODE_W, sy + NODE_H / 2, tx, ty + NODE_H / 2
        bend = (x2 - x1) / 2
        path = f"M{x1},{y1} C{x1 + bend},{y1} {x2 - bend},{y2} {x2},{y2}"
        return path, ((x1 + x2) / 2, (y1 + y2) / 2 - 10)
    if abs(ty - sy) < 1:  # backward on the same row: arc over the top
        x1, x2, y = sx + NODE_W / 2, tx + NODE_W / 2, sy
        path = f"M{x1},{y} C{x1},{y - 55} {x2},{y - 55} {x2},{y}"
        return path, ((x1 + x2) / 2, y - 42)
    # backward to another row: out the right side, along the bottom channel,
    # up into the target from below.
    x1, y1 = sx + NODE_W, sy + NODE_H / 2
    xo, x2, y2 = x1 + 30, tx + NODE_W / 2 + 40, ty + NODE_H
    path = (
        f"M{x1},{y1} L{xo - 12},{y1} Q{xo},{y1} {xo},{y1 + 12} L{xo},{channel - 12} "
        f"Q{xo},{channel} {xo - 12},{channel} L{x2 + 12},{channel} "
        f"Q{x2},{channel} {x2},{channel - 12} L{x2},{y2}"
    )
    return path, ((xo + x2) / 2, channel - 10)


def render(agent: dict) -> str:
    flow = agent["conversationFlow"]
    nodes = flow["nodes"]
    tools = {t["tool_id"]: t["name"] for t in flow["tools"]}

    unplaced = [n["id"] for n in nodes if n["id"] not in GRID]
    grid = {**GRID, **{nid: (i, 5) for i, nid in enumerate(unplaced)}}
    pos = {
        n["id"]: (MARGIN + grid[n["id"]][0] * COL_W, MARGIN + 40 + grid[n["id"]][1] * ROW_H)
        for n in nodes
    }
    width = max(x for x, _ in pos.values()) + NODE_W + MARGIN
    bottom = max(y for _, y in pos.values()) + NODE_H
    channel = bottom + 45  # backward arrows between lanes run along here
    height = channel + MARGIN

    pairs = {
        (n["id"], e.get("destination_node_id"))
        for n in nodes
        for e in n.get("edges", []) + ([n["else_edge"]] if n.get("else_edge") else [])
    }

    edges_svg, labels_svg = [], []
    for node in nodes:
        outgoing = [(e, False) for e in node.get("edges", [])]
        if node.get("else_edge"):
            outgoing.append((node["else_edge"], True))
        for edge, is_else in outgoing:
            target = edge.get("destination_node_id")
            # "Caller is done" arrows to End Call would cross everything; the
            # legend explains them instead.
            if target not in pos or target == GOODBYE:
                continue
            path, (mx, my) = _route(pos[node["id"]], pos[target], (target, node["id"]) in pairs, channel)
            title = escape(f"{node['name']} → {_name(nodes, target)}: {_condition(edge)}")
            edges_svg.append(
                f'<path class="edge" d="{path}" marker-end="url(#arrow)"><title>{title}</title></path>'
            )
            text = escape(_label(edge, is_else))
            labels_svg.append(
                f'<g class="label"><title>{title}</title>'
                f'<text x="{mx:.0f}" y="{my:.0f}">{text}</text></g>'
            )

    nodes_svg = []
    for node in nodes:
        x, y = pos[node["id"]]
        fill, stroke, kind = NODE_STYLES.get(node["type"], ("#fff", "#334155", node["type"]))
        tool_ids = node.get("tool_ids") or ([node["tool_id"]] if node.get("tool_id") else [])
        # One line per tool, so a subagent's tool list fits the box.
        subs = [tools.get(t, t) for t in tool_ids] or [kind]
        if node["id"] == flow["start_node_id"]:
            subs[-1] += " · start"
        sub_svg = "".join(
            f'<text class="sub" x="{x + 14}" y="{y + 50 + i * 17}" fill="{stroke}">{escape(line)}</text>'
            for i, line in enumerate(subs)
        )
        instruction = escape((node.get("instruction") or {}).get("text", ""))
        nodes_svg.append(
            f'<g class="node"><title>{instruction}</title>'
            f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="12" '
            f'fill="{fill}" stroke="{stroke}"/>'
            f'<text class="name" x="{x + 14}" y="{y + 30}">{escape(node["name"])}</text>'
            f"{sub_svg}"
            f"</g>"
        )

    legend = "".join(
        f'<span><i style="background:{fill};border-color:{stroke}"></i>{kind}</span>'
        for fill, stroke, kind in NODE_STYLES.values()
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Voice agent flow</title>
<style>
  body {{ margin: 0; font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color: #1e293b; background: #f8fafc; }}
  header {{ max-width: 1100px; margin: 0 auto; padding: 28px 20px 8px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  p {{ margin: 0 0 10px; color: #475569; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px; color: #475569; }}
  .legend i {{ display: inline-block; width: 14px; height: 14px; border: 1.5px solid; border-radius: 4px; margin-right: 6px; vertical-align: -2px; }}
  .canvas {{ padding: 8px 20px 32px; }}
  svg {{ display: block; width: 100%; max-width: {width}px; height: auto; margin: 0 auto; }}
  .node rect {{ stroke-width: 1.5; }}
  .node .name {{ font-weight: 600; font-size: 15px; fill: #0f172a; }}
  .node .sub {{ font-size: 12.5px; font-family: ui-monospace, Consolas, monospace; }}
  .edge {{ fill: none; stroke: #64748b; stroke-width: 1.6; }}
  .label text {{ font-size: 12.5px; fill: #334155; text-anchor: middle; dominant-baseline: middle;
    paint-order: stroke; stroke: #f8fafc; stroke-width: 5px; stroke-linejoin: round; }}
  .node:hover rect {{ stroke-width: 3; }}
  .edge:hover {{ stroke: #0f7667; stroke-width: 3; }}
</style>
</head>
<body>
<header>
  <h1>Voice agent flow</h1>
  <p>The Retell conversation flow Sarah follows: registering a new patient along the top,
  returning callers along the bottom. The global prompt (identity, voice style, scope and
  security rules) applies in every step. Hover a step for its instruction, or an arrow for
  its full condition. Generated from <code>agent.json</code>.</p>
  <div class="legend">{legend}<span>Every conversation step also goes to <b>End Call</b> when the caller is done (not drawn).</span></div>
</header>
<div class="canvas">
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Voice agent conversation flow">
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
{chr(10).join(edges_svg)}
{chr(10).join(nodes_svg)}
{chr(10).join(labels_svg)}
</svg>
</div>
</body>
</html>
"""


def _name(nodes: list[dict], node_id: str) -> str:
    return next((n["name"] for n in nodes if n["id"] == node_id), node_id)


def main() -> None:
    agent = json.loads(AGENT_PATH.read_text(encoding="utf-8"))
    OUT_PATH.write_text(render(agent), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
