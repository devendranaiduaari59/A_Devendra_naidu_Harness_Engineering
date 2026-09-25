You are condensing a resolved customer-support conversation segment into a tight
factual summary that will be placed in the *middle* of a longer context window. ...

# Required structure

Produce a Markdown block with exactly this format:

    **Outcome.** <one sentence stating what was resolved, in past tense>

    **Key facts.**
    - <bullet 1 — a specific, decision-relevant fact>
    - <bullet 2>
    - ...

    **Resolution.** <one sentence stating the final state at segment close>

Rules:
- "Outcome" sentence is past tense and concrete.
- "Key facts" list must be 3-6 bullets. Each bullet is a specific fact...
- Preserve every numeric value, ID, and status code verbatim from the source.
- Total length: ≤ 500 tokens. Aim for ~300 tokens.
- Output ONLY the Markdown block above. No preamble, no postscript, no code fences.