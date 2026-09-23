"""The Retell flow in assets/ and the backend must agree on tool URLs,
argument names and response keys — a mismatch there fails silently on a live
call (the flow just takes its else-edge), so catch it here instead."""

import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from app.main import create_app
from app.core.validation import SEX_VALUES
from app.models.patients import PATIENT_FIELDS, REQUIRED_FIELDS
from app.services.patients import LEGACY_ARG_NAMES, VOICE_UPDATABLE_FIELDS

FLOW_PATH = Path(__file__).resolve().parent.parent / "assets" / "retell_agent_scripts" / "agent_import.json"
FLOW = json.loads(FLOW_PATH.read_text(encoding="utf-8"))["conversation_flow"]
TOOLS = {t["name"]: t for t in FLOW["tools"]}


def _canonical(names) -> set[str]:
    # The flow uses the older names phone/address_line1/address_line2, which
    # the backend maps to phone_number/address_line_1/address_line_2.
    return {LEGACY_ARG_NAMES.get(n, n) for n in names}


def test_every_tool_url_is_a_backend_route():
    routes = {route.path for route in create_app().routes}
    for tool in FLOW["tools"]:
        assert urlparse(tool["url"]).path in routes, tool["name"]


def test_create_patient_args_match_patient_model():
    params = TOOLS["create_patient"]["parameters"]
    assert _canonical(params["required"]) == REQUIRED_FIELDS
    assert _canonical(params["properties"]) == set(PATIENT_FIELDS)


def test_update_patient_args_are_voice_updatable():
    props = TOOLS["update_patient_profile"]["parameters"]["properties"]
    assert _canonical(props) <= set(VOICE_UPDATABLE_FIELDS)


@pytest.mark.parametrize(
    "tool,response_keys",
    [
        ("create_patient", {"status", "member_id", "message", "patient_name"}),
        ("verify_patient", {"verification_result"}),
    ],
)
def test_response_variables_read_real_keys(tool, response_keys):
    assert set(TOOLS[tool]["response_variables"].values()) <= response_keys


def test_equation_edges_use_real_status_values():
    statuses = {
        "create_status": {"created", "invalid", "duplicate"},
        "verification_result": {"verified", "not_verified"},
    }
    for node in FLOW["nodes"]:
        for edge in node.get("edges", []):
            condition = edge["transition_condition"]
            for eq in condition.get("equations", []):
                variable = eq["left"].strip("{}")
                assert eq["right"] in statuses[variable], (node["id"], eq)


def test_sex_options_match_schema():
    sex = TOOLS["create_patient"]["parameters"]["properties"]["sex"]
    assert sex["enum"] == list(SEX_VALUES)
