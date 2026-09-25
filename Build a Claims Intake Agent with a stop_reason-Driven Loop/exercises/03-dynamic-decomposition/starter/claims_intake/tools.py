import json
from pathlib import Path

CLAIM_TYPES = ["auto_collision", "property_water", "property_fire", "liability"]
SEVERITY_LEVELS = ["low", "medium", "high"]

TOOL_SCHEMAS = [
    {
        "name": "lookup_policy",
        "description": "Look up policy coverage details by policy number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_id": {"type": "string"}
            },
            "required": ["policy_id"]
        }
    },
    {
        "name": "record_claim_fact",
        "description": "Record extracted key facts about the claim event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "facts": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["facts"]
        }
    },
    {
        "name": "classify_claim",
        "description": "Assign an initial claim category and confidence score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_type": {"type": "string", "enum": CLAIM_TYPES},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
            },
            "required": ["claim_type", "confidence"]
        }
    },
    {
        "name": "assess_severity",
        "description": "Assess the severity bucket based on damage and injuries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": SEVERITY_LEVELS},
                "reasoning": {"type": "string"}
            },
            "required": ["severity", "reasoning"]
        }
    },
    {
        "name": "request_clarification",
        "description": "Ask the claimant a single clarifying question when facts are ambiguous.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The specific clarifying question to ask."
                },
                "ambiguity_between": {
                    "type": "array",
                    "items": {"type": "string", "enum": CLAIM_TYPES},
                    "description": "The plausible claim types causing ambiguity."
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "route_to_adjuster",
        "description": "Terminal tool: Route claim to an adjuster queue when fully processed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {"type": "string"},
                "claim_type": {"type": "string", "enum": CLAIM_TYPES},
                "severity": {"type": "string", "enum": SEVERITY_LEVELS},
                "summary": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
            },
            "required": ["summary"]
        }
    },
    {
        "name": "escalate_to_human",
        "description": "Terminal tool: Escalate to human reviewer when confidence is low or ambiguity remains.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {"type": "string"},
                "reason": {"type": "string"},
                "structured_summary": {
                    "type": "object"
                }
            },
            "required": ["reason", "structured_summary"]
        }
    }
]


def _err(msg: str) -> dict:
    return {"status": "error", "error": msg}


def _ok(data: dict) -> dict:
    return {"status": "ok", "result": data}


def _append_jsonl(path: Path, record: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _t_lookup_policy(session, args: dict) -> dict:
    if not isinstance(args, dict):
        return _err("Invalid arguments format.")
    policy_id = args.get("policy_id")
    fixture_policies = getattr(session, "fixture", {}).get("policies", {})
    if policy_id in fixture_policies:
        session.policy_number = policy_id
        return _ok(fixture_policies[policy_id])
    return _err(f"Policy ID {policy_id} not found")


def _t_record_claim_fact(session, args: dict) -> dict:
    if not isinstance(args, dict):
        return _err("Invalid arguments format.")
    facts = args.get("facts", [])
    if hasattr(session, "facts"):
        session.facts.extend(facts)
    return _ok({"facts_recorded_count": len(facts)})


def _t_classify_claim(session, args: dict) -> dict:
    if not isinstance(args, dict):
        return _err("Invalid arguments format.")
    session.claim_type = args.get("claim_type")
    session.classification = args
    return _ok(args)


def _t_assess_severity(session, args: dict) -> dict:
    if not isinstance(args, dict):
        return _err("Invalid arguments format.")
    session.severity = args.get("severity")
    return _ok(args)


def _t_request_clarification(session, args: dict) -> dict:
    if not isinstance(args, dict):
        return _err("Invalid arguments format.")
    question = args.get("question")
    if not question or not isinstance(question, str):
        return _err("Missing or invalid 'question' parameter.")

    if hasattr(session, "clarifications_asked"):
        session.clarifications_asked.append(question)

    question_lower = question.lower()
    matched_response = "NO_RESPONSE"

    clarification_map = {}
    if hasattr(session, "fixture") and isinstance(session.fixture, dict):
        clarification_map = session.fixture.get("clarification_responses", {})
    elif hasattr(session, "clarification_responses"):
        clarification_map = session.clarification_responses

    if isinstance(clarification_map, dict):
        for key, response in clarification_map.items():
            if isinstance(key, str) and key.lower() in question_lower:
                matched_response = response
                break

    return _ok({"question": question, "response": matched_response})


def _t_route_to_adjuster(session, args: dict) -> dict:
    if getattr(session, "terminal_called", False):
        return _err("Terminal tool has already been called for this session.")

    if not isinstance(args, dict):
        return _err("Invalid arguments format.")

    claim_type = getattr(session, "claim_type", None)
    severity = getattr(session, "severity", None)

    if not claim_type or not severity:
        return _err("Cannot route: Missing required classification or severity.")

    summary = args.get("summary")
    if not summary:
        return _err("Missing required 'summary' parameter.")

    record = {
        "claim_id": getattr(session, "claim_id", "unknown"),
        "claim_type": claim_type,
        "severity": severity,
        "summary": summary
    }

    queue_file = Path(session.runs_dir) / "queues" / f"{claim_type}.jsonl"
    _append_jsonl(queue_file, record)

    session.routing = record
    session.terminal_called = True
    return _ok(record)


def _t_escalate_to_human(session, args: dict) -> dict:
    if getattr(session, "terminal_called", False):
        return _err("Terminal tool has already been called for this session.")

    if not isinstance(args, dict):
        return _err("Invalid arguments format.")

    reason = args.get("reason")
    summary = args.get("structured_summary")

    if not reason or summary is None:
        return _err("Missing required 'reason' or 'structured_summary'.")

    record = {
        "claim_id": getattr(session, "claim_id", "unknown"),
        "reason": reason,
        "structured_summary": summary
    }

    escalations_file = Path(session.runs_dir) / "escalations.jsonl"
    _append_jsonl(escalations_file, record)

    session.escalation = record
    session.terminal_called = True
    return _ok(record)


DISPATCH_TABLE = {
    "lookup_policy": _t_lookup_policy,
    "record_claim_fact": _t_record_claim_fact,
    "classify_claim": _t_classify_claim,
    "assess_severity": _t_assess_severity,
    "request_clarification": _t_request_clarification,
    "route_to_adjuster": _t_route_to_adjuster,
    "escalate_to_human": _t_escalate_to_human,
}


def dispatch_tool(tool_name: str, args: dict, session) -> dict:
    try:
        if tool_name not in DISPATCH_TABLE:
            return _err(f"Unknown tool name: {tool_name}")
        return DISPATCH_TABLE[tool_name](session, args)
    except Exception as e:
        return _err(f"Handler exception caught: {str(e)}")