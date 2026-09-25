from __future__ import annotations

from typing import Dict, Any, List, Optional

from retail_context.case_facts import CaseFacts
from retail_context.compressor import Compressed
from retail_context import tokens


CASE_FACTS_TITLE = "# Case Facts"

RESOLVED_TITLES = {
    "refund": "# Resolved: Refund inquiry",
    "subscription": "# Resolved: Subscription cancellation",
}

ACTIVE_TITLES = {
    "payment_update": "# Active issue: Payment-method update",
}


class AssembledContext:
    def __init__(
        self,
        markdown: str,
        case_facts_block: str,
        resolved_blocks: List[str],
        active_block: str,
        active_raw_text: str,
    ):
        self.markdown = markdown
        self.case_facts_block = case_facts_block
        self.resolved_blocks = resolved_blocks
        self.active_block = active_block
        self.active_raw_text = active_raw_text

    def section_tokens(self) -> Dict[str, int]:
        """Returns token count breakdown per section."""
        counts = {
            "case_facts": tokens.count(self.case_facts_block),
            "active_issue": tokens.count(self.active_block),
        }

        for idx, block in enumerate(self.resolved_blocks, start=1):
            counts[f"resolved_{idx}"] = tokens.count(block)

        return counts

    def total_tokens(self) -> int:
        """Returns total token count for the assembled markdown context."""
        return tokens.count(self.markdown)


def build(
    case_facts: CaseFacts,
    compressed: Compressed,
) -> AssembledContext:
    """Build the position-aware context.

    Layout:

    1. Case Facts
    2. Resolved refund
    3. Resolved subscription
    4. Active issue

    The active issue text is preserved byte-for-byte.
    """

    # 1. Top boundary: Case Facts
    case_facts_block = case_facts.to_markdown()

    # 2. Middle: resolved sections in required order
    resolved_blocks: List[str] = []

    for issue_id in ("refund", "subscription"):
        if issue_id not in compressed.summaries:
            raise KeyError(
                f"Missing required resolved summary for issue_id: '{issue_id}'"
            )

        summary = compressed.summaries[issue_id]

        title = RESOLVED_TITLES[issue_id]

        # Summary text can be normalized because it is a compressed section.
        summary_text = summary.text.strip()

        block = f"{title}\n\n{summary_text}\n"
        resolved_blocks.append(block)

    # 3. Bottom boundary: active issue
    #
    # The test fixture uses:
    #     active_issue_id="payment_update"
    #
    # which must render as:
    #     # Active issue: Payment-method update
    active_title = ACTIVE_TITLES.get(
        compressed.active_issue_id,
        f"# Active issue: {compressed.active_issue_id}",
    )

    # IMPORTANT:
    # Do not strip, modify, or re-render active_text.
    # It must remain byte-exact.
    active_block = f"{active_title}\n\n{compressed.active_text}"

    # 4. Assemble sections in strict order.
    parts = [
        case_facts_block,
        *resolved_blocks,
        active_block,
    ]

    markdown = "\n\n".join(parts)

    # 5. Return assembled context.
    return AssembledContext(
        markdown=markdown,
        case_facts_block=case_facts_block,
        resolved_blocks=resolved_blocks,
        active_block=active_block,
        active_raw_text=compressed.active_text,
    )