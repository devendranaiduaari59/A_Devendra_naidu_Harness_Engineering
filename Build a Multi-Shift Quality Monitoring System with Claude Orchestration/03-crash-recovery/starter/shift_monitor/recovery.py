"""Resume-vs-fresh decision logic for crash recovery.

The 30-minute threshold is ~1/16 of an 8-hour shift cycle: a resume inside this
window is still operating on the same shift's working set; anything older is
treated as a stale partial that should be re-started from scratch with whatever
findings the manifest already captured injected as a summary.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from .manifest import ManifestState

# The 30-minute staleness threshold represents ~1/16 of an 8-hour shift cycle.
# Resumes within this window are still operating on the current shift's active
# working set. Any older partial manifests are considered stale and should restart fresh.
STALE_RESUME_THRESHOLD_MINUTES = 30

Decision = Literal["resume", "fresh"]


def decide(state: ManifestState, now: datetime) -> Decision:
    # 1. Empty manifest: no recorded steps -> start fresh
    if not state.steps:
        return "fresh"

    # 2. Completed manifest: last step is marked "complete" -> start fresh
    if state.complete:
        return "fresh"

    # 3. Incomplete manifest: evaluate staleness window
    last_step_ts = state.steps[-1].ts
    if (now - last_step_ts) <= timedelta(minutes=STALE_RESUME_THRESHOLD_MINUTES):
        return "resume"

    return "fresh"