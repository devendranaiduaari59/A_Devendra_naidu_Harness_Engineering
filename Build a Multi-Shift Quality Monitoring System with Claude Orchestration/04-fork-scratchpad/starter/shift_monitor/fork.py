"""
Layer 3 fork: copy hot state into an isolated working directory per hypothesis.

`fork_session` here is the application-side framing: the SDK / CLI primitive lives at Layer 2;
here we reproduce the *semantics* (shared baseline, isolated scratchpads, no cross-contamination)
using state-file copies.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Sequence

from shift_monitor.scratchpad import Scratchpad


def fork_for_hypothesis(
    base_hot_state_path: str | Path,
    hypothesis_id: str,
    forks_root: str | Path,
) -> Path:
    """
    Creates an isolated working directory for a hypothesis and copies the baseline hot state.

    Args:
        base_hot_state_path: Path to the current base hot-state JSON file.
        hypothesis_id: Identifier for the hypothesis (e.g., 'H1', 'H2').
        forks_root: Root directory where hypothesis forks are stored.

    Returns:
        Path: Path to the created per-hypothesis directory containing the hot_state.json copy.
    """
    base_path = Path(base_hot_state_path)
    root_path = Path(forks_root)

    # 1. Create forks_root / hypothesis_id directory if it doesn't exist
    fork_dir = root_path / hypothesis_id
    fork_dir.mkdir(parents=True, exist_ok=True)

    # 2. Copy base_hot_state_path to /hot_state.json non-destructively
    target_state_path = fork_dir / "hot_state.json"
    shutil.copyfile(base_path, target_state_path)

    return fork_dir


def merge_findings(
    scratchpad_paths: Sequence[str | Path],
    main_scratchpad: Scratchpad | str | Path,
) -> None:
    """
    Merges findings from multiple fork scratchpads into the main shift scratchpad
    without modifying existing entries, using Scratchpad.append for durable writes.

    Args:
        scratchpad_paths: Sequence of paths to fork scratchpad files.
        main_scratchpad: The primary Scratchpad instance or path to merge entries into.
    """
    # Ensure main_scratchpad is a Scratchpad instance if a path was passed
    if not isinstance(main_scratchpad, Scratchpad):
        main_scratchpad = Scratchpad(Path(main_scratchpad))

    for path in scratchpad_paths:
        fork_sp_path = Path(path)

        # Skip paths that do not exist
        if not fork_sp_path.exists():
            continue

        # Instantiate a Scratchpad helper to read entries from the fork scratchpad
        fork_scratchpad = Scratchpad(fork_sp_path)

        # Read and re-append each entry into the main scratchpad through Scratchpad.append
        for entry in fork_scratchpad.read():
            main_scratchpad.append(entry)