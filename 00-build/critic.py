"""Independent validator (M3). A separate model call that never saw the drafting
context, so it can't inherit the draft's blind spots. Returns a pass/fail verdict.
The revision cap that stops a critic<->drafter loop lives in `agent.py`.
"""

from __future__ import annotations

import json

from prompts import CRITIC_SYSTEM


def review(client, model: str, proposed_output: str, source_data: str) -> dict:
    """Return {"verdict": "pass"|"fail", "reasons": ["..."], "_usage": {...}} for a proposed output."""
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=CRITIC_SYSTEM,
        messages=[
            {"role": "user", "content":
                f"SOURCE DATA Cortex used:\n{source_data}\n\n"
                f"CORTEX PROPOSED OUTPUT:\n{proposed_output}\n\n"
                "Respond as strict JSON: {\"verdict\": \"pass\" | \"fail\", \"reasons\": [\"...\"]}."},
        ],
    )
    usage = resp.usage
    raw = resp.content[0].text if resp.content else ""
    try:
        verdict = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        verdict = {"verdict": "fail", "reasons": ["critic returned unparseable output"]}
    verdict["_usage"] = {"input": usage.input_tokens, "output": usage.output_tokens}
    return verdict
