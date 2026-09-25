import os

import anthropic


def get_client() -> anthropic.Anthropic:
    """Initialize and return the Anthropic client."""

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set."
        )

    base_url = os.getenv("ANTHROPIC_BASE_URL")

    kwargs = {
        "api_key": api_key,
    }

    if base_url:
        kwargs["base_url"] = base_url

    return anthropic.Anthropic(**kwargs)