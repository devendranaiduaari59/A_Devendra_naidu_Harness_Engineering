"""Incremental crash-recovery manifest backed by JSON lines + fsync."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict


class Step(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    name: str
    ts: datetime
    invocation_shape: Literal["thin", "rich", "resumed"]
    payload: dict[str, Any]


class ManifestState(BaseModel):
    model_config = ConfigDict(frozen=True)

    complete: bool
    steps: list[Step]


class Manifest:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append_step(self, step: Step) -> None:
        # 1. Ensure the parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # 2. Open in binary append mode ("ab") for proper fsync semantics
        with open(self.path, "ab") as f:
            # 3. Serialize to JSON line and encode to bytes
            line_bytes = (step.model_dump_json() + "\n").encode("utf-8")
            f.write(line_bytes)

            # 4. Flush Python's buffer and force OS-level disk sync before returning
            f.flush()
            os.fsync(f.fileno())

    @classmethod
    def load(cls, path: Path) -> ManifestState:
        # Return empty/incomplete state if the file does not exist
        if not path.exists():
            return ManifestState(complete=False, steps=[])

        steps: list[Step] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    steps.append(Step.model_validate_json(line))

        # Manifest is complete ONLY if steps exist AND the last step's name is "complete"
        is_complete = bool(steps) and steps[-1].name == "complete"

        return ManifestState(complete=is_complete, steps=steps)