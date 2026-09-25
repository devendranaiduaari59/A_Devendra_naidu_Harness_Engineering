"""Orchestration pipeline for shift quality monitoring."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .client import Message
from .scratchpad import ScratchpadEntry


def gather_new_defects(
    warm: Any,
    since_ts: str,
    limit: int = 50,
) -> Sequence[Mapping[str, Any]]:
    """Fetch new defects from SQL warm tier without Python-side filtering."""
    return warm.defects_since(since_ts, limit=limit)


def build_rich_prompt(
    role: str,
    hot_state: Any,
    new_defects: Sequence[Mapping[str, Any]],
) -> str:
    """Build rich prompt using invocation.rich and ensure character budget."""
    from .invocation import rich

    invocation = rich(
        role=role,
        hot_state=hot_state,
        new_defects=new_defects,
    )

    prompt = invocation.prompt

    if len(prompt) > 4000:
        prompt = _trim_to_budget(prompt, max_chars=4000)

    return prompt


def run_shift(
    role: str = "on-call lead",
    hot_store: Any = None,
    warm: Any = None,
    scratchpad: Any = None,
    client: Any = None,
    since_ts: str = "2026-04-30T00:00:00Z",
    shift_id: str | None = None,
    limit: int = 50,
    **kwargs: Any,
) -> Any:
    """Execute shift monitoring step."""

    if hot_store is None and "hot_state_path" in kwargs:
        from .state import HotStateStore

        hot_store = HotStateStore(kwargs["hot_state_path"])

    if scratchpad is None and "scratchpad_path" in kwargs:
        from .scratchpad import Scratchpad

        scratchpad = Scratchpad(kwargs["scratchpad_path"])

    hot_state = hot_store.read()

    new_defects = gather_new_defects(
        warm,
        since_ts=since_ts,
        limit=limit,
    )

    prompt = build_rich_prompt(
        role,
        hot_state,
        new_defects,
    )

    messages = [
        Message(
            role="user",
            content=prompt,
        )
    ]

    response = client.complete(messages)

    if hasattr(response, "content"):
        response_text = response.content
    elif isinstance(response, str):
        response_text = response
    else:
        response_text = str(response)

    updated_hot_state = _parse_hot_state_update(
        hot_state,
        response_text,
        new_defects,
        shift_id=shift_id,
    )

    hot_store.write_atomic(updated_hot_state)

    short_summary = _short_summary_from_response(response_text)

    entry = ScratchpadEntry(
        hypothesis_id=f"shift-{shift_id or 'default'}",
        evidence=_format_evidence(new_defects),
        conclusion=short_summary,
        ts=datetime.now(timezone.utc),
    )

    scratchpad.append(entry)

    return updated_hot_state


def _parse_hot_state_update(
    current: Any,
    response_text: str,
    new_defects: Sequence[Mapping[str, Any]],
    shift_id: str | None = None,
) -> Any:
    """Parse JSON state proposal and merge it into HotState."""
    from .state import HotState

    effective_shift_id = (
        shift_id
        if shift_id is not None
        else getattr(current, "shift_id", "")
    )

    json_match = re.search(
        r"```json\s*(.*?)\s*```",
        response_text,
        re.DOTALL,
    )

    if json_match:
        try:
            data = json.loads(json_match.group(1))

            new_hashes = _new_hashes(
                current.recent_defect_hashes,
                new_defects,
            )

            return HotState(
                shift_id=effective_shift_id,
                recent_defect_hashes=new_hashes,
                current_shift_summary=data.get(
                    "current_shift_summary",
                    current.current_shift_summary,
                ),
                active_alerts=data.get(
                    "active_alerts",
                    current.active_alerts,
                ),
                threshold_statuses=data.get(
                    "threshold_statuses",
                    current.threshold_statuses,
                ),
            )

        except json.JSONDecodeError:
            pass

    return HotState(
        shift_id=effective_shift_id,
        recent_defect_hashes=_new_hashes(
            current.recent_defect_hashes,
            new_defects,
        ),
        current_shift_summary=current.current_shift_summary,
        active_alerts=current.active_alerts,
        threshold_statuses=current.threshold_statuses,
    )


def _new_hashes(
    existing_hashes: Sequence[str],
    new_defects: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Append new defect IDs/hashes while deduplicating."""
    updated = list(existing_hashes)

    for defect in new_defects:
        d_id = defect.get("id") or defect.get("hash")

        if d_id and str(d_id) not in updated:
            updated.append(str(d_id))

    return updated[-20:]


def _short_summary_from_response(response_text: str) -> str:
    """Extract first meaningful line from response."""
    lines = [
        line.strip()
        for line in response_text.splitlines()
        if line.strip()
    ]

    for line in lines:
        if not line.startswith("```") and not line.startswith("#"):
            return line[:120]

    return "Shift summary generated."


def _format_evidence(
    new_defects: Sequence[Mapping[str, Any]],
) -> str:
    """Convert defect records into scratchpad evidence text."""
    if not new_defects:
        return "No new defects since the previous shift step."

    evidence_lines: list[str] = []

    for defect in new_defects:
        evidence_lines.append(
            f"id={defect.get('id')}; "
            f"ts={defect.get('ts')}; "
            f"shift={defect.get('shift')}; "
            f"component={defect.get('component')}; "
            f"severity={defect.get('severity')}; "
            f"description={defect.get('description')}"
        )

    return "\n".join(evidence_lines)


def _trim_to_budget(
    prompt: str,
    max_chars: int = 4000,
) -> str:
    """Truncate prompt if it exceeds maximum character limit."""
    if len(prompt) <= max_chars:
        return prompt

    return prompt[: max_chars - 3] + "..."
