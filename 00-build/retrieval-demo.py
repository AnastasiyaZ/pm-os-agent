"""M4 retrieve-vs-long-context demo — makes the two context paths real and testable
using the shipping 00-build tools.

THE DISTINCTION (from the M4 lecture), grounded in THIS build:

  LONG-CONTEXT source — the incoming task brief. agent.py includes it WHOLE as the
    first user message every run (agent.py:110-112). It is never fetched by a tool and
    never narrowed; the model reasons over all of it. There is exactly one.

  RETRIEVE sources — get_activity / get_norms (and get_project / get_roadmap /
    search_past_updates). Cortex must CALL the tool to pull a slice of a large or
    changing corpus, and every claim in the update must trace back to what came back
    (CORTEX_SYSTEM: "show the data you relied on"; critic check #2: every claim
    traceable to pulled data). The citation is not decoration — it is load-bearing.

THE PROOF (agent.py's M4 task: "withhold one source, show the hallucination caught"):
  We feed the REAL critic ONE fixed draft twice — once against a source_log that
  includes get_activity, once with get_activity WITHHELD. The same "activation rate
  41%" claim flips from grounded (pass) to invented (fail). That flip IS the
  retrieve-vs-long-context distinction made real: pull the source and cite it, or the
  claim cannot stand. The long-context brief is present in BOTH — it is never the
  thing withheld, because it is not retrieved.

Nothing here reimplements the loop or the validator: critic.review(), the real tools,
and the real cost accounting are imported from the shipping build. Only the source_log
is varied — which is the whole point.

Run:  ./.venv/bin/python retrieval-demo.py
"""

from __future__ import annotations

import json

import anthropic

import tools
from agent import MODEL, PRICE_IN, PRICE_OUT, Bounds, banner
from critic import review


# One fixed draft. Deliberately PLAIN markdown (the ornate happy-path draft once tripped
# the critic's JSON parser). Every factual claim here — the two merged PRs and the
# activation metric — originates in get_activity, so withholding that ONE tool ungrounds
# all of them. The "Data I relied on" lines make the citation explicit, which is exactly
# what turns into a *fabricated* citation when the source was never retrieved.
DRAFT = """\
DONE: (queued for your review — nothing posted)

Northstar (P-NORTH) — weekly leadership status: GREEN.
- Shipped this week: PR #812 (activation checklist UI) and PR #815 (step-completion
  instrumentation).
- Activation rate rose to 41%, up from 39% week over week.
- No open Sev-1s and no launch-hold flags.

Data I relied on:
- get_activity(P-NORTH): PRs #812 and #815 merged; activation_rate 41% (prior 39%).
- get_norms: green requires no open Sev-1 and evidence-based metrics.
"""


def source_log(include_activity: bool) -> str:
    """Build the source_log exactly as agent.py joins it (the task brief + one
    `fn(args) -> json` line per tool call), optionally WITHHOLDING get_activity — the
    retrieve source under test. The long-context brief is present either way."""
    brief = tools.get_task("happy")["body"]
    lines = [brief,
             f"get_project({{'project_id': 'P-NORTH'}}) -> "
             f"{json.dumps(tools.get_project('P-NORTH'))}"]
    if include_activity:
        lines.append(f"get_activity({{'project_id': 'P-NORTH'}}) -> "
                     f"{json.dumps(tools.get_activity('P-NORTH'))}")
    lines.append(f"get_norms({{}}) -> {json.dumps(tools.get_norms())}")
    return "\n".join(lines)


def main() -> None:
    client = anthropic.Anthropic()
    bounds = Bounds()

    # ---- 1. LONG-CONTEXT source: the task brief, whole, every run -------------------
    banner("1. LONG-CONTEXT SOURCE — the task brief (included WHOLE every run)")
    brief = tools.get_task("happy")["body"]
    print("agent.py puts this verbatim in the first user message (agent.py:110-112).")
    print("It is NOT fetched by a tool and NOT narrowed — the one long-context input:\n")
    print(brief.rstrip())

    # ---- 2. RETRIEVE sources: call the tool, narrow the corpus ----------------------
    banner("2. RETRIEVE SOURCES — get_activity narrows a large/changing corpus")
    known = tools.get_project("__list_projects__").get("known_projects", [])
    act = tools.get_activity("P-NORTH")
    print(f"The activity corpus spans {len(known)} projects {known}.")
    print(f"get_activity('P-NORTH') NARROWS to ONE project's activity "
          f"({len(act['activity'])} items) — that is the retrieve move:\n")
    print(json.dumps(act, indent=2))
    print("\nThe '41% / prior 39%' metric Cortex cites lives ONLY here — pulled, not "
          "pre-loaded.\nget_norms() is a retrieve source too (fetched on demand + cited), "
          "though it is bounded:\nit returns the whole playbook rather than narrowing "
          "(see memory-and-context.md §2).")

    # ---- 3. THE PROOF: withhold get_activity, watch the same claim get caught -------
    banner("3. PROOF — same draft judged by the REAL critic, WITH vs. WITHOUT get_activity")
    print("One fixed draft claims 'activation rate 41%' + PRs #812/#815. We change ONLY\n"
          "whether get_activity was retrieved, then let the real critic judge. The\n"
          "long-context brief is identical in both runs — it is never withheld.\n")

    results = {}
    for include in (True, False):
        tag = ("WITH get_activity (retrieved + cited)" if include
               else "WITHOUT get_activity (source WITHHELD)")
        banner(f"3{'a' if include else 'b'}. {tag}")
        verdict = review(client, MODEL, DRAFT, source_log(include))
        bounds.cost += (verdict["_usage"]["input"] * PRICE_IN
                        + verdict["_usage"]["output"] * PRICE_OUT) / 1_000_000
        print(json.dumps({k: v for k, v in verdict.items() if k != "_usage"}, indent=2))
        expect = ("PASS — every claim traces to pulled data" if include
                  else "FAIL — metric + PRs trace to NOTHING (invented; caught by check #2)")
        print(f"\n   expected:    {expect}")
        print(f"   critic said: {verdict['verdict'].upper()}")
        results[include] = verdict["verdict"]

    banner("Retrieve is load-bearing. The ONLY change between 3a and 3b was withholding "
           f"one tool,\nand the same claim flipped "
           f"{results[True].upper()} -> {results[False].upper()} "
           f"(grounded -> invented).\nThe long-context brief was present throughout. "
           f"Run cost ≈ ${bounds.cost:.4f}")


if __name__ == "__main__":
    main()
