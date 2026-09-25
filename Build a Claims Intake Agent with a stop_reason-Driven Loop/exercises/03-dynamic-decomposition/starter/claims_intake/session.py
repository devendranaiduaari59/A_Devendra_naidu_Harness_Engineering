from pathlib import Path
from typing import Any


class ClaimSession:
    def __init__(
        self,
        claim_id: str = "",
        policy_id: str = "",
        runs_dir: Path | None = None,
        policies: dict[str, Any] | None = None,
        fixture: dict[str, Any] | None = None,
        clarification_responses: dict[str, Any] | None = None,
    ):
        fixture = fixture or {}

        self.claim_id = (
            claim_id
            or fixture.get("claim_id", "")
        )

        self.policy_id = (
            policy_id
            or fixture.get("policy_id", "")
        )

        self.runs_dir = runs_dir or Path("runs")

        # ---------------------------------------------------------
        # Policies
        # ---------------------------------------------------------

        if policies is not None:
            self.policies = policies

        elif "policies" in fixture:
            self.policies = fixture["policies"]

        else:
            self.policies = {}

        # ---------------------------------------------------------
        # Clarification responses
        # ---------------------------------------------------------

        if clarification_responses is not None:
            self.clarification_responses = (
                clarification_responses
            )

        elif "clarification_responses" in fixture:
            self.clarification_responses = (
                fixture["clarification_responses"]
            )

        else:
            self.clarification_responses = {}

        # ---------------------------------------------------------
        # Agent state
        # ---------------------------------------------------------

        self.facts: dict[str, str] = {}

        self.claim_type: str | None = None

        self.severity: str | None = None

        self.clarifications_asked: list[str] = []

        self.terminal_called = False

        self.routing: dict[str, Any] | None = None

        self.escalation: dict[str, Any] | None = None