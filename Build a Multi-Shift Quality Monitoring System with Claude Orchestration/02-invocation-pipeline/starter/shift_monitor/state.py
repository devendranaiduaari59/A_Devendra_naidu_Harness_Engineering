
"""Hot-state schema and atomic disk I/O."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

MAX_RECENT_HASHES = 20
HOT_STATE_BYTE_BUDGET = 5_120


class HotState(BaseModel):
    """In-context shift state. Kept under ~5 KB so it fits in every prompt."""

    model_config = ConfigDict(frozen=True)

    shift_id: str = ""

    recent_defect_hashes: list[str] = Field(
        default_factory=list,
        max_length=MAX_RECENT_HASHES,
    )

    current_shift_summary: str = ""

    active_alerts: list[str] = Field(
        default_factory=list,
    )

    threshold_statuses: dict[str, str] = Field(
        default_factory=dict,
    )

    def to_json_bytes(self) -> bytes:
        """Serialize state to JSON bytes."""
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_json_bytes(cls, payload: bytes) -> Self:
        """Deserialize state from JSON bytes."""
        return cls.model_validate_json(payload)

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """Read state from disk."""
        return cls.from_json_bytes(path.read_bytes())

    def write_atomic(self, path: Path) -> None:
        """Atomically write state to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = self.to_json_bytes()

        if len(payload) > HOT_STATE_BYTE_BUDGET:
            raise ValueError(
                f"hot state {len(payload)} bytes exceeds "
                f"{HOT_STATE_BYTE_BUDGET}-byte budget"
            )

        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            delete=False,
            prefix=".hot_state.",
            suffix=".tmp",
        ) as tmp:
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)

        os.replace(tmp_path, path)


class HotStateStore:
    """File-backed store for the current HotState."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def read(self) -> HotState:
        """Read the current hot state from disk."""
        return HotState.from_path(self.path)

    def write_atomic(self, state: HotState) -> None:
        """Atomically replace the stored hot state."""
        state.write_atomic(self.path)
