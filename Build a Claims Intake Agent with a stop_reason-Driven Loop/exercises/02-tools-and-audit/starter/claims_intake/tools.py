import json
from typing import Any
from claims_intake.session import ClaimSession

CLAIM_TYPES = ["auto", "property", "injury", "liability"]
SEVERITIES = ["low", "medium", "high"]

# ----------------------------------------------------------------------------
# Tool Schemas
# ----------------------------------------------------------------------------
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "lookup_policy",
        "description": "Retrieves the policy record for a given policy ID from the policy database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_id": {
                    "type": "string",
                    "description": "The unique identifier of the policy to look up."
                }
            },
            "required": ["policy_id"]
        }
    },
    {
        "name": "record_claim_fact",
        "description": "Appends a key-value fact detailing the claim (such as incident date or location) to the active case file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "The field or key name of the fact being recorded."
                },
                "value": {
                    "type": "string",
                    "description": "The value associated with the specified fact field."
                }
            },
            "required": ["field", "value"]
        }
    },
    {
        "name": "classify_claim",
        "description": "Commits the model's determination for the claim type along with confidence and rationale.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_type": {
                    "type": "string",
                    "enum": CLAIM_TYPES,
                    "description": "The categorical type of the claim."
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score in [0, 1] representing belief in the classification."
                },
                "rationale": {
                    "type": "string",
                    "description": "Explanation supporting the selected claim classification."
                }
            },
            "required": ["claim_type", "confidence", "rationale"]
        }
    },
    {
        "name": "assess_severity",
        "description": "Commits the model's assessment of claim severity along with justifying rationale.",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": SEVERITIES,
                    "description": "The assessed severity level of the claim."
                },
                "rationale": {
                    "type": "string",
                    "description": "Explanation supporting the assigned severity assessment."
                }
            },
            "required": ["severity", "rationale"]
        }
    }
]


# ----------------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------------

def _err(category: str, is_retryable: bool, message: str) -> str:
    """Formats a graceful tool failure response as a JSON string."""
    return json.dumps({
        "is_error": True,
        "error_category": category,
        "is_retryable": is_retryable,
        "message": message
    })


def _ok(data: dict[str, Any]) -> str:
    """Formats a successful tool execution response as a JSON string."""
    return json.dumps(data)


# ----------------------------------------------------------------------------
# Tool Implementations
# ----------------------------------------------------------------------------

def _t_lookup_policy(session: ClaimSession, inp: dict[str, Any]) -> str:
    policy_id = inp.get("policy_id")
    if not isinstance(policy_id, str):
        return _err("permanent", False, "policy_id must be a string")

    if policy_id not in session.policies:
        return _err("permanent", False, f"Policy ID '{policy_id}' not found")

    return _ok(session.policies[policy_id])


def _t_record_claim_fact(session: ClaimSession, inp: dict[str, Any]) -> str:
    field = inp.get("field")
    value = inp.get("value")

    if not isinstance(field, str) or not isinstance(value, str):
        return _err("permanent", False, "Both field and value must be strings")

    session.case_facts[field] = value
    return _ok({
        "recorded": True,
        "field": field,
        "case_facts_count": len(session.case_facts)
    })


def _t_classify_claim(session: ClaimSession, inp: dict[str, Any]) -> str:
    claim_type = inp.get("claim_type")
    confidence = inp.get("confidence")
    rationale = inp.get("rationale")

    if claim_type not in CLAIM_TYPES:
        return _err("permanent", False, f"Invalid claim_type: '{claim_type}'")

    if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
        return _err("permanent", False, "confidence must be a number between 0 and 1")

    if not isinstance(rationale, str):
        return _err("permanent", False, "rationale must be a string")

    session.classification = {
        "claim_type": claim_type,
        "confidence": confidence,
        "rationale": rationale
    }

    return _ok({
        "recorded": True,
        "claim_type": claim_type,
        "confidence": confidence,
        "rationale": rationale
    })


def _t_assess_severity(session: ClaimSession, inp: dict[str, Any]) -> str:
    severity = inp.get("severity")
    rationale = inp.get("rationale")

    if severity not in SEVERITIES:
        return _err("permanent", False, f"Invalid severity: '{severity}'")

    if not isinstance(rationale, str):
        return _err("permanent", False, "rationale must be a string")

    session.severity = {
        "severity": severity,
        "rationale": rationale
    }

    return _ok({
        "recorded": True,
        "severity": severity,
        "rationale": rationale
    })


# ----------------------------------------------------------------------------
# Tool Executor / Dispatcher
# ----------------------------------------------------------------------------

DISPATCHER_MAP = {
    "lookup_policy": _t_lookup_policy,
    "record_claim_fact": _t_record_claim_fact,
    "classify_claim": _t_classify_claim,
    "assess_severity": _t_assess_severity,
}


def make_executor(session: ClaimSession):
    """
    Returns an executor function that takes (tool_name, tool_input) 
    and dispatches to the corresponding handler gracefully.
    """
    def execute(name: str, inp: dict[str, Any]) -> str:
        handler = DISPATCHER_MAP.get(name)
        if not handler:
            return _err("permanent", False, f"Unknown tool: '{name}'")
        try:
            return handler(session, inp)
        except Exception as e:
            return _err("transient", True, f"Internal handler exception: {str(e)}")

    return execute