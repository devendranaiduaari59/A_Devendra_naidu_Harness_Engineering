import time
from typing import Any, Callable

from claims_intake.budget import Budget, BudgetExceeded
from claims_intake.session import FinalState
from claims_intake.tracer import Tracer


class UnexpectedStopReason(Exception):
    """Raised when the model returns an unexpected stop_reason."""

    def __init__(self, turn: int, stop_reason: str) -> None:
        super().__init__(
            f"Turn {turn}: unexpected stop_reason '{stop_reason}'"
        )
        self.turn = turn
        self.stop_reason = stop_reason


def run(
    client: Any,
    model: str,
    system: str | list[dict[str, Any]] | None = None,
    tools: list[dict[str, Any]] | None = None,
    messages: list[dict[str, Any]] | None = None,
    tool_executor: Callable[[str, dict[str, Any]], Any] | None = None,
    budget: Budget | None = None,
    tracer: Tracer | None = None,
) -> FinalState:
    """Run the main agent loop until stop_reason == 'end_turn'."""

    working_messages = list(messages) if messages else []

    total_input_tokens = 0
    total_output_tokens = 0
    turn_count = 0

    while True:
        turn_count += 1

        # Check wall-clock / other pre-request budget constraints.
        if budget:
            budget.check()

        start_time = time.perf_counter()

        # ---------------------------------------------------------
        # Build request parameters dynamically
        # ---------------------------------------------------------
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": working_messages,
        }

        if system is not None:
            kwargs["system"] = system

        if tools is not None:
            kwargs["tools"] = tools

        # ---------------------------------------------------------
        # Call the model
        # ---------------------------------------------------------
        response = client.messages.create(**kwargs)

        latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        # ---------------------------------------------------------
        # Update token usage totals
        # ---------------------------------------------------------
        input_tokens = getattr(
            response.usage,
            "input_tokens",
            0,
        )

        output_tokens = getattr(
            response.usage,
            "output_tokens",
            0,
        )

        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        # ---------------------------------------------------------
        # IMPORTANT:
        # Check cumulative input-token budget immediately after
        # receiving the model response.
        #
        # Example:
        #   Turn 1 = 500
        #   Turn 2 = 600
        #   Total  = 1100
        #
        # If max_input_tokens = 1000, raise BudgetExceeded here.
        # ---------------------------------------------------------
        if budget:
            max_input_tokens = getattr(
                budget,
                "max_input_tokens",
                None,
            )

            if (
                max_input_tokens is not None
                and total_input_tokens > max_input_tokens
            ):
                raise BudgetExceeded(
                    "Input token budget exceeded: "
                    f"{total_input_tokens} > "
                    f"{max_input_tokens}"
                )

        # ---------------------------------------------------------
        # Collect tool_use blocks from the assistant response
        # ---------------------------------------------------------
        tool_calls: list[dict[str, Any]] = []

        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": dict(block.input),
                    }
                )

        # ---------------------------------------------------------
        # Write trace record
        # ---------------------------------------------------------
        if tracer:
            tracer.write(
                {
                    "turn": turn_count,
                    "stop_reason": response.stop_reason,
                    "tool_calls": tool_calls,
                    "latency_ms": latency_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            )

        # ---------------------------------------------------------
        # Handle stop_reason
        # ---------------------------------------------------------

        # =========================================================
        # CASE 1: Model finished
        # =========================================================
        if response.stop_reason == "end_turn":

            working_messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                }
            )

            return FinalState(
                messages=working_messages,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                turn_count=turn_count,
                final_content=response.content,
            )

        # =========================================================
        # CASE 2: Model requested one or more tools
        # =========================================================
        elif response.stop_reason == "tool_use":

            # -----------------------------------------------------
            # 1. Append assistant response containing tool_use
            # -----------------------------------------------------
            working_messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                }
            )

            # -----------------------------------------------------
            # Safety check
            # -----------------------------------------------------
            if not tool_calls:
                raise RuntimeError(
                    f"Turn {turn_count}: "
                    "stop_reason was 'tool_use' but no "
                    "tool_use blocks were returned."
                )

            # -----------------------------------------------------
            # 2. Execute all requested tools
            # -----------------------------------------------------
            tool_results: list[dict[str, Any]] = []

            for call in tool_calls:

                if tool_executor is None:
                    raise RuntimeError(
                        f"Turn {turn_count}: "
                        f"tool '{call['name']}' was requested, "
                        "but no tool_executor was provided."
                    )

                result_content = tool_executor(
                    call["name"],
                    call["input"],
                )

                # -------------------------------------------------
                # Convert tool result into Claude tool_result block
                # -------------------------------------------------
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call["id"],
                        "content": result_content,
                    }
                )

            # -----------------------------------------------------
            # 3. Append all tool results as one user message
            # -----------------------------------------------------
            working_messages.append(
                {
                    "role": "user",
                    "content": tool_results,
                }
            )

        # =========================================================
        # CASE 3: Unknown stop_reason
        # =========================================================
        else:
            raise UnexpectedStopReason(
                turn=turn_count,
                stop_reason=response.stop_reason,
            )