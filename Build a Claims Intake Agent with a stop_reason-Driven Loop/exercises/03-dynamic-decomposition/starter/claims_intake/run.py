from pathlib import Path
from typing import Any, Dict
from claims_intake.client import get_client
from claims_intake.loop import run_agent_loop
from claims_intake.session import ClaimSession
from claims_intake.system_prompt import SYSTEM_PROMPT


def _run_one(
    fixture: Dict[str, Any],
    runs_dir: Path,
) -> Dict[str, Any]:
    client = get_client()

    session = ClaimSession(
        claim_id=fixture["claim_id"],
        runs_dir=runs_dir,
        clarification_responses=fixture.get("clarification_responses", {}),
    )

    # Seed initial user message with claim description
    session.messages.append({
        "role": "user",
        "content": f"Initial Claim Submission:\n{fixture['description']}"
    })

    run_agent_loop(session, client, system_prompt=SYSTEM_PROMPT)

    return session.to_summary_dict()