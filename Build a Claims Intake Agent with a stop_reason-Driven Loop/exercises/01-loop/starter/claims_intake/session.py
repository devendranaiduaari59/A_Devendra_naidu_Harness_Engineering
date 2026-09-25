"""Per-claim runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class UnexpectedStopReason(Exception):
    """Raised when the loop encounters a stop_reason it cannot handle."""

    def __init__(self, turn: int, stop_reason: str):
        self.turn = turn
        self.stop_reason = stop_reason
        super().__init__(
            f"Unexpected stop_reason '{stop_reason}' on turn {turn}."
        )


@dataclass
class FinalState:
    """Terminal state returned when the loop terminates with end_turn."""

    messages: list[dict[str, Any]]
    total_input_tokens: int
    total_output_tokens: int
    turn_count: int
    final_content: Any


@dataclass
class ClaimSession:
    """Holds the live state for one claim while the loop runs."""

    claim_id: str
    raw_input: dict[str, Any]
    history: list[dict[str, Any]] = field(default_factory=list)
    routing: str | None = None
    escalation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)