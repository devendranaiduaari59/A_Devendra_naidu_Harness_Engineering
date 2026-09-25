import time
from dataclasses import dataclass


class BudgetExceeded(Exception):
    """Raised when the agent exceeds its configured budget."""

    pass


@dataclass
class Budget:
    max_input_tokens: int = 500_000
    max_wall_clock_s: float = 300.0

    _start: float = 0.0
    input_tokens_used: int = 0

    def __post_init__(self) -> None:
        self._start = time.monotonic()

    def record_input_tokens(self, n: int) -> None:
        """Record input tokens consumed by a model call."""
        self.input_tokens_used += n

    def check(self) -> None:
        """Raise BudgetExceeded if any configured budget is exceeded."""

        if self.input_tokens_used > self.max_input_tokens:
            raise BudgetExceeded(
                f"input_tokens_used={self.input_tokens_used} exceeded "
                f"max_input_tokens={self.max_input_tokens}"
            )

        elapsed = time.monotonic() - self._start

        if elapsed > self.max_wall_clock_s:
            raise BudgetExceeded(
                f"elapsed={elapsed:.1f}s exceeded "
                f"max_wall_clock_s={self.max_wall_clock_s}"
            )