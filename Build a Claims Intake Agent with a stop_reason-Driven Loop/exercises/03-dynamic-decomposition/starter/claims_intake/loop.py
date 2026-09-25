import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from claims_intake.budget import BudgetExceeded


class UnexpectedStopReason(Exception):
    """Raised when the model stops for an unexpected reason."""

    pass


@dataclass
class AgentState:
    """State maintained by the agent loop."""

    messages: list[dict[str, Any]]
    turn_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    response: Any = None


def run_agent_loop(
    client,
    model: str,
    system: str,
    tools: list,
    messages: list[dict[str, Any]],
    tool_executor: Callable[[str, dict[str, Any]], Any],
    budget,
    tracer,
) -> AgentState:
    """
    Run the agent loop until the model returns end_turn.

    The loop:
    - Calls the model.
    - Tracks turns.
    - Tracks input/output tokens.
    - Records tracing information.
    - Stops on end_turn.
    - Executes all tool_use blocks.
    - Sends all tool results in one user message.
    - Raises on unexpected stop reasons.
    - Enforces token and wall-clock budgets.
    """

    state = AgentState(
        messages=messages,
        turn_count=0,
        total_input_tokens=0,
        total_output_tokens=0,
        response=None,
    )

    while True:

        # =========================================================
        # 1. Check wall-clock budget
        # =========================================================
        if hasattr(budget, "_start"):
            elapsed = time.monotonic() - budget._start

            if elapsed > budget.max_wall_clock_s:
                raise BudgetExceeded(
                    "Maximum wall-clock budget exceeded"
                )

        # =========================================================
        # 2. Call the model
        # =========================================================
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=state.messages,
        )

        state.response = response

        # Each model response is one turn.
        state.turn_count += 1

        # =========================================================
        # 3. Read usage information
        # =========================================================
        usage = getattr(response, "usage", None)

        input_tokens = 0
        output_tokens = 0

        if usage is not None:
            input_tokens = getattr(
                usage,
                "input_tokens",
                0,
            )

            output_tokens = getattr(
                usage,
                "output_tokens",
                0,
            )

        state.total_input_tokens += input_tokens
        state.total_output_tokens += output_tokens

        # =========================================================
        # 4. Update budget
        # =========================================================
        if hasattr(budget, "input_tokens_used"):
            budget.input_tokens_used += input_tokens

            if budget.input_tokens_used > budget.max_input_tokens:
                raise BudgetExceeded(
                    "Maximum input token budget exceeded"
                )

        if hasattr(budget, "output_tokens_used"):
            budget.output_tokens_used += output_tokens

        # =========================================================
        # 5. Get stop reason
        # =========================================================
        stop_reason = getattr(
            response,
            "stop_reason",
            None,
        )

        # =========================================================
        # 6. Collect tool calls for tracing
        # =========================================================
        tool_calls = []

        for content_block in getattr(
            response,
            "content",
            [],
        ):
            if getattr(
                content_block,
                "type",
                None,
            ) == "tool_use":

                tool_calls.append(
                    {
                        "id": getattr(
                            content_block,
                            "id",
                            None,
                        ),
                        "name": getattr(
                            content_block,
                            "name",
                            None,
                        ),
                        "input": getattr(
                            content_block,
                            "input",
                            {},
                        ),
                    }
                )

        # =========================================================
        # 7. Record tracer event
        # =========================================================
        if tracer is not None and hasattr(tracer, "events"):

            event = {
                "turn": state.turn_count,
                "stop_reason": stop_reason,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

            # The tests expect tool_calls for tool_use turns.
            if tool_calls:
                event["tool_calls"] = tool_calls

            tracer.events.append(event)

        # =========================================================
        # 8. Add assistant response to message history
        # =========================================================
        state.messages.append(
            {
                "role": "assistant",
                "content": response.content,
            }
        )

        # =========================================================
        # 9. Normal completion
        # =========================================================
        if stop_reason == "end_turn":
            return state

        # =========================================================
        # 10. Unexpected stop reason
        # =========================================================
        if stop_reason != "tool_use":
            raise UnexpectedStopReason(
                f"Unexpected stop_reason: {stop_reason}"
            )

        # =========================================================
        # 11. Execute ALL tool calls
        # =========================================================
        tool_results = []

        for content_block in getattr(
            response,
            "content",
            [],
        ):

            if getattr(
                content_block,
                "type",
                None,
            ) != "tool_use":
                continue

            tool_name = content_block.name
            tool_input = content_block.input
            tool_use_id = content_block.id

            result = tool_executor(
                tool_name,
                tool_input,
            )

            if isinstance(result, str):
                result_content = result
            else:
                result_content = json.dumps(result)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_content,
                }
            )

        # =========================================================
        # 12. Send ALL tool results in ONE user message
        # =========================================================
        if tool_results:
            state.messages.append(
                {
                    "role": "user",
                    "content": tool_results,
                }
            )


# Test compatibility
run = run_agent_loop