"""Case-facts extraction into a persistent block at the top of context.

Extraction is LLM-driven: one Claude call against the full transcript that
returns strict JSON for the 12 required fields. Missing-field behavior raises
`CaseFactExtractionError` listing the gaps — silent null-fill is forbidden.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from retail_context.client import complete_with_system, get_model
from retail_context.transcript import Transcript

# Required fields contract (12 total in exact declaration order)
REQUIRED_FIELDS: tuple[str, ...] = (
    "customer_id",
    "refund_order_id",
    "refund_amount_usd",
    "refund_status",
    "subscription_id",
    "subscription_plan",
    "subscription_cancel_reason",
    "subscription_status",
    "active_payment_method_last4",
    "new_payment_method_last4",
    "payment_update_failure_code",
    "payment_update_status",
)


class CaseFactExtractionError(ValueError):
    """Raised when one or more required case facts are missing from extraction."""

    def __init__(self, missing: list[str], raw: dict[str, Any]):
        self.missing = missing
        self.raw = raw
        super().__init__(f"Missing required case fields: {missing}")


@dataclass
class CaseFacts:
    """Structured, immutable-by-contract facts for the persistent block."""

    customer_id: str
    refund_order_id: str
    refund_amount_usd: float
    refund_status: str
    subscription_id: str
    subscription_plan: str
    subscription_cancel_reason: str
    subscription_status: str
    active_payment_method_last4: str
    new_payment_method_last4: str
    payment_update_failure_code: str
    payment_update_status: str

    def to_markdown(self) -> str:
        """Render the persistent block for injection at the top of context."""
        return (
            "# Case Facts\n"
            f"- **Customer**: {self.customer_id}\n"
            f"- **Refund (resolved)**: order={self.refund_order_id}, amount=${self.refund_amount_usd:.2f}, status={self.refund_status}\n"
            f"- **Subscription (resolved)**: id={self.subscription_id}, plan={self.subscription_plan}, reason={self.subscription_cancel_reason}, status={self.subscription_status}\n"
            f"- **Payment update (active)**: active_last4={self.active_payment_method_last4}, new_last4={self.new_payment_method_last4}, failure_code={self.payment_update_failure_code}, status={self.payment_update_status}"
        )


_SYSTEM_PROMPT = """You are an expert support case fact extractor.
Analyze the transcript and return a single valid JSON object containing exactly the 12 required keys listed below.

Required JSON Keys:
- "customer_id": string
- "refund_order_id": string
- "refund_amount_usd": float/numeric
- "refund_status": snake_case status token copied verbatim from CRM (e.g., COMPLETED, ISSUED, NOT_APPLICABLE)
- "subscription_id": string
- "subscription_plan": string
- "subscription_cancel_reason": string
- "subscription_status": snake_case status token copied verbatim
- "active_payment_method_last4": string (4 digits, keep leading zeros)
- "new_payment_method_last4": string (4 digits, keep leading zeros)
- "payment_update_failure_code": snake_case status token copied verbatim from CRM (e.g., AVS_MISMATCH, NONE)
- "payment_update_status": snake_case status token copied verbatim

Rules:
1. Every field is required. If a fact was not explicitly mentioned or is missing, use null (do not invent or guess).
2. All status tokens and failure codes must be preserved verbatim in snake_case.
3. Return ONLY raw valid JSON. No conversational prose, no markdown code fences (```json).
"""


def _parse_json(text: str) -> dict[str, Any]:
    """Helper to parse raw model response text, stripping code fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def extract(
    transcript: Transcript,
    *,
    model: str | None = None,
    log_path: Path | None = None,
) -> CaseFacts:
    """Extract case facts from full transcript via single LLM call."""
    user_message = f"Transcript:\n\n{transcript.full_text}"
    raw_response = complete_with_system(
        _SYSTEM_PROMPT,
        user_message,
        model=model,
        max_tokens=2048,
    )

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(raw_response, encoding="utf-8")

    data = _parse_json(raw_response)

    missing = []
    for field_name in REQUIRED_FIELDS:
        val = data.get(field_name)
        if val is None or val == "":
            missing.append(field_name)

    if missing:
        raise CaseFactExtractionError(missing=missing, raw=data)

    return CaseFacts(
        customer_id=str(data["customer_id"]),
        refund_order_id=str(data["refund_order_id"]),
        refund_amount_usd=float(data["refund_amount_usd"]),
        refund_status=str(data["refund_status"]),
        subscription_id=str(data["subscription_id"]),
        subscription_plan=str(data["subscription_plan"]),
        subscription_cancel_reason=str(data["subscription_cancel_reason"]),
        subscription_status=str(data["subscription_status"]),
        active_payment_method_last4=str(data["active_payment_method_last4"]),
        new_payment_method_last4=str(data["new_payment_method_last4"]),
        payment_update_failure_code=str(data["payment_update_failure_code"]),
        payment_update_status=str(data["payment_update_status"]),
    )