from __future__ import annotations

import os
from functools import lru_cache
import anthropic

_CHARS_PER_TOKEN = 3.8

def count(text: str) -> int:
    """Canonical token counting for the retail_context project."""
    if not text:
        return 0

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        client = anthropic.Anthropic(
            api_key=api_key,
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
        )
        response = client.messages.count_tokens(
            model="claude-3-5-haiku-20241022",
            messages=[{"role": "user", "content": text}],
        )
        return response.input_tokens

    # Fallback heuristic calculation
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def methodology() -> str:
    """Returns a string naming the path actually in use."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic_messages_count_tokens"
    return "heuristic_len_div_3_8"