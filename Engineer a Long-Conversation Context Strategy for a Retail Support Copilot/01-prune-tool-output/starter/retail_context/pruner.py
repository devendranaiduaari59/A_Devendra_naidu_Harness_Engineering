"""Deterministic tool-output pruning for the verbose `lookup_order` response.

The "Tool Context Pruning" pattern: application-side filtering of a verbose
tool result so only the fields needed for the immediate decision survive into
context. For return/refund reasoning, exactly five fields matter:

- order_id: Uniquely identifies the target order to confirm the return request applies to the correct transaction.
- order_date: Provides the purchase timestamp to establish when the transaction occurred.
- order_total_usd: Provides the monetary value necessary to validate max refund limits or issue exact credit amounts.
- fulfillment_status: Indicates current delivery state to verify whether items were actually shipped or delivered before accepting a return.
- return_eligible_until: Defines the exact cutoff deadline date that the agent compares against today's date to determine return eligibility.
"""

from __future__ import annotations

# These are the only fields the pruner returns; everything else in the raw
# response is dropped. The output dict preserves this declaration order.
KEPT_FIELDS: tuple[str, ...] = (
    "order_id",
    "order_date",
    "order_total_usd",
    "fulfillment_status",
    "return_eligible_until",
)


class PrunerMissingFieldError(KeyError):
    """Raised when the raw tool response is missing one of the required kept fields."""


def prune_lookup_order(raw: dict) -> dict:
    """Prune a raw `lookup_order` response down to only the 5 required fields.

    Args:
        raw: The raw dictionary returned by the lookup_order tool.

    Returns:
        A dictionary containing only the 5 KEPT_FIELDS in declaration order.

    Raises:
        PrunerMissingFieldError: If any required field in KEPT_FIELDS is missing.
    """
    missing = [field for field in KEPT_FIELDS if field not in raw]
    if missing:
        raise PrunerMissingFieldError(f"Missing required fields: {', '.join(missing)}")

    return {field: raw[field] for field in KEPT_FIELDS}