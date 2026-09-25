"""Three invocation shapes.

thin     — prompt only.
rich     — hot state + new defects.
resumed  — prior partial findings + new defects since the last manifest step.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .state import HotState

InvocationShape = Literal["thin", "rich", "resumed"]


@dataclass(frozen=True)
class Invocation:
    shape: InvocationShape
    prompt: str


def thin(prompt: str) -> Invocation:
    """Return an Invocation with shape="thin" and the prompt unchanged."""
    return Invocation(shape="thin", prompt=prompt)


def rich(
    role: str, hot_state: HotState, new_defects: Sequence[Mapping[str, Any]]
) -> Invocation:
    """Build a rich prompt and return an Invocation with shape="rich"."""
    lines = [
        f"You are the on-call {role} for Northridge Plant 3.",
        "",
        "## Current hot state",
        f"- recent_defect_hashes: {hot_state.recent_defect_hashes}",
        f"- current_shift_summary: {hot_state.current_shift_summary}",
        f"- active_alerts: {hot_state.active_alerts}",
        f"- threshold_statuses: {hot_state.threshold_statuses}",
        "",
        "## New defects since last shift",
    ]

    if not new_defects:
        lines.append("- (none)")
    else:
        for d in new_defects:
            lines.append(
                f"- {d.get('id')} / {d.get('ts')} / {d.get('shift')} / "
                f"{d.get('component')} / {d.get('severity')} / {d.get('description')}"
            )

    lines.extend([
        "",
        "Please provide:",
        "1. Summary",
        "2. Findings",
        "3. Recommended actions",
        "4. An Updated hot state proposal as a JSON block with current_shift_summary, "
        "active_alerts, and threshold_statuses.",
    ])

    prompt = "\n".join(lines)
    return Invocation(shape="rich", prompt=prompt)


def resumed(
    session_id: str,
    summary: str,
    latest_message: str,
    prior_steps: Sequence[Mapping[str, Any]],
    new_defects: Sequence[Mapping[str, Any]],
) -> Invocation:
    """Build a resumed prompt and return an Invocation with shape="resumed"."""
    lines = ["## Prior partial findings"]

    if not prior_steps:
        lines.append("- (none)")
    else:
        for step in prior_steps:
            name = step.get("name", "")
            payload = str(step.get("payload", ""))
            if len(payload) > 100:
                payload = payload[:97] + "..."
            lines.append(f"- {name}: {payload}")

    lines.extend([
        "",
        "## Prior summary",
        summary,
        "",
        "## New defects since last partial step",
    ])

    if not new_defects:
        lines.append("- (none)")
    else:
        for d in new_defects:
            lines.append(
                f"- {d.get('id')} / {d.get('ts')} / {d.get('component')} / "
                f"{d.get('severity')} / {d.get('description')}"
            )

    lines.extend([
        "",
        "## Latest instruction",
        latest_message,
    ])

    prompt = "\n".join(lines)
    return Invocation(shape="resumed", prompt=prompt)