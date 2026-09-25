from pathlib import Path
import pytest

from claims_intake.session import ClaimSession
from claims_intake.tools import (
    CLAIM_TYPES,
    SEVERITY_LEVELS,
    TOOL_SCHEMAS,
    dispatch_tool,
)


def _session(tmp_path: Path) -> ClaimSession:
    return ClaimSession(
        claim_id="claim_test",
        runs_dir=tmp_path,
        clarification_responses={"locked": "yes it was locked"},
    )


def test_seven_tools_registered_with_schemas() -> None:
    names = {t["name"] for t in TOOL_SCHEMAS}
    assert names == {
        "lookup_policy",
        "record_claim_fact",
        "classify_claim",
        "assess_severity",
        "request_clarification",
        "route_to_adjuster",
        "escalate_to_human",
    }


def test_categorical_fields_use_enums() -> None:
    by_name = {t["name"]: t for t in TOOL_SCHEMAS}
    assert by_name["classify_claim"]["input_schema"]["properties"]["claim_type"]["enum"] == CLAIM_TYPES
    assert by_name["assess_severity"]["input_schema"]["properties"]["severity"]["enum"] == SEVERITY_LEVELS


def test_lookup_policy_returns_record(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.fixture = {
        "policies": {
            "POL-1": {
                "policy_id": "POL-1",
                "policy_holder": "Alex Doe",
                "coverage": ["property_damage", "theft"],
                "deductible": 500,
                "status": "active",
            }
        }
    }
    res = dispatch_tool("lookup_policy", {"policy_id": "POL-1"}, s)
    assert res["status"] == "ok"
    assert res["result"]["policy_holder"] == "Alex Doe"


def test_lookup_policy_unknown_id_returns_graceful_error(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = dispatch_tool("lookup_policy", {"policy_id": "UNKNOWN"}, s)
    assert res["status"] == "error"
    assert "not found" in res["error"].lower()


def test_unknown_tool_returns_graceful_error(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = dispatch_tool("nonexistent_tool", {}, s)
    assert res["status"] == "error"


def test_request_clarification_returns_scripted_reply(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = dispatch_tool("request_clarification", {"question": "Was the door locked?"}, s)
    assert res["status"] == "ok"
    assert res["result"]["response"] == "yes it was locked"


def test_request_clarification_no_response_when_unscripted(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = dispatch_tool("request_clarification", {"question": "What color was the car?"}, s)
    assert res["status"] == "ok"
    assert res["result"]["response"] == "NO_RESPONSE"


def test_routing_requires_classification_and_severity(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = dispatch_tool("route_to_adjuster", {"summary": "all good"}, s)
    assert res["status"] == "error"


def test_routing_writes_jsonl_and_marks_terminal(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.claim_type = "theft"
    s.severity = "low"
    res = dispatch_tool("route_to_adjuster", {"summary": "stolen items"}, s)
    assert res["status"] == "ok"
    assert s.terminal_called is True
    assert (tmp_path / "queues" / "theft.jsonl").exists()


def test_escalation_writes_jsonl_and_marks_terminal(tmp_path: Path) -> None:
    s = _session(tmp_path)
    summary = {
        "claim_type": "unknown",
        "severity": "low",
        "key_facts": {"details": "unclear"},
    }
    res = dispatch_tool(
        "escalate_to_human",
        {"reason": "too ambiguous", "structured_summary": summary},
        s,
    )
    assert res["status"] == "ok"
    assert s.terminal_called is True
    assert (tmp_path / "escalations.jsonl").exists()


def test_double_terminal_is_graceful_error(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.claim_type = "theft"
    s.severity = "low"
    dispatch_tool("route_to_adjuster", {"summary": "first call"}, s)
    res = dispatch_tool("route_to_adjuster", {"summary": "second call"}, s)
    assert res["status"] == "error"
    assert "already" in res["error"].lower()


def test_handler_exception_is_caught_as_transient_error(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = dispatch_tool("route_to_adjuster", None, s)  # type: ignore
    assert res["status"] == "error"