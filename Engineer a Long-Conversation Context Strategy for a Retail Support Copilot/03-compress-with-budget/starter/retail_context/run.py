import json
from retail_context import tokens

def _build(run_dir, transcript, assembled, baseline_tokens, compression_api_stats):
    # Assemble the budget dictionary
    assembled_tokens = sum(assembled.section_tokens().values())
    
    reduction_pct = (
        round(((baseline_tokens - assembled_tokens) / baseline_tokens) * 100, 2)
        if baseline_tokens > 0 else 0.0
    )

    budget = {
        "token_counter_methodology": tokens.methodology(),
        "baseline_tokens": baseline_tokens,
        "assembled_tokens": assembled_tokens,
        "reduction_pct": reduction_pct,
        "per_section_tokens": assembled.section_tokens(),
        "compression_api": compression_api_stats,
    }

    # Write out to run_dir / "budget.json"
    budget_path = run_dir / "budget.json"
    with open(budget_path, "w") as f:
        json.dump(budget, f, indent=2)