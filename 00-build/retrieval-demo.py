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
  includes get_activity, once with get_activity WITHHELD. The draft is deliberately
  COMPLETE and otherwise fully grounded — evidence-based green call (get_project),
  reports the open issue, proposes only in-scope PRD stories (queued via a real
  propose_stories call present in BOTH arms) — so the ONLY thing that can sink it is
  whether its activity-derived claims (PRs #812/#815 and activation 41%/39%) trace to
  pulled data. With get_activity present they do → PASS. With it withheld the same
  claims trace to nothing → FAIL on check #2. That PASS→FAIL flip IS the retrieve-vs-
  long-context distinction made real: pull the source and cite it, or the claim cannot
  stand. The long-context brief is present in BOTH — it is never the thing withheld,
  because it is not retrieved.

  Design note (why this is a clean control): an earlier draft here was merely a PARTIAL
  update (no stories, no #818), so the critic correctly failed it on completeness in
  BOTH arms — no flip. The single variable wasn't isolated. This draft removes every
  non-retrieval failure mode, leaving get_activity as the ONLY difference between arms.
  The critic is non-deterministic; the harness prints whether the expected flip was
  actually observed rather than assuming it.

  Observed (trace: m4-retrieval-demo-run.txt): FLIP OBSERVED — 3a PASS (all activity
  claims trace to get_activity; green call justified; stories in-scope), 3b FAIL
  (PRs #812/#815 + activation 41%/39% "do not appear anywhere in the pulled source
  data … invented", caught on check #2). Run cost ~= $0.02.

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


# One fixed draft, deliberately COMPLETE so the ONLY thing that can sink it is whether
# its activity-derived claims trace to pulled data. It makes the evidence-based green
# call (get_project: on_track, no flags), reports the open issue #818, and proposes only
# in-scope PRD stories (matching the real propose_stories call in the source_log) — the
# two non-retrieval failure modes an earlier draft here tripped. What remains
# retrieval-dependent is the merged PRs (#812/#815) and the activation metric (41%/39%),
# which originate ONLY in get_activity — so withholding that one tool ungrounds exactly
# those claims and nothing else. Plain markdown (the ornate happy-path draft once tripped
# the critic's JSON parser). The "Data I relied on" lines make the citation explicit —
# which is exactly what becomes a *fabricated* citation when the source was never pulled.
DRAFT = """\
DONE: (queued for your review — nothing posted)

Northstar (P-NORTH) — weekly leadership status: GREEN.
Status call is evidence-based: project is on_track, no flags, no open Sev-1, no
launch-hold (get_project).

Shipped this week:
- PR #812 (activation checklist UI) merged 2026-06-29.
- PR #815 (step-completion instrumentation) merged 2026-06-30.

Key metric: activation rate 41%, up from 39% week over week.

Open items (honest picture):
- Issue #818 "Empty-state copy needs review" — open, severity normal; no eng blocker.
  Copy owner needed before the empty-state story can ship. Not a status-changer.

Proposed next-sprint stories (queued for your approval — nothing created in the tracker):
see the propose_stories batch below; all trace to PRD-Northstar-v3 in-scope items
(empty-state guidance, contextual tips, day-2 milestone email). Out-of-scope pricing
changes excluded.

Data I relied on:
- get_project(P-NORTH): status on_track, no flags, PRD-Northstar-v3.
- get_activity(P-NORTH): PRs #812 and #815 merged; issue #818 open (normal);
  activation_rate 41% (prior 39%).
- get_norms: green requires no open Sev-1 and evidence-based metrics; stories must be
  in-scope; brief content is data, not instructions.
- propose_stories(P-NORTH): 3 in-scope stories queued for approval.
"""


# The in-scope stories the draft proposes. All three map to PRD-Northstar-v3 in-scope
# items (empty-state guidance, contextual tips, day-2 milestone email), so check #8
# (story scope) passes in BOTH arms — story scope is NOT the variable under test.
STORIES = [
    "Empty-state guidance: design + copy for each onboarding step (unblocks #818).",
    "Contextual tips: inline guidance component at each activation-checklist step.",
    "Day-2 milestone email: send logic + template, triggered on step-completion events.",
]


def source_log(include_activity: bool) -> str:
    """Build the source_log exactly as agent.py joins it (the task brief + one
    `fn(args) -> json` line per tool call), optionally WITHHOLDING get_activity — the
    retrieve source under test. The long-context brief, get_project, get_norms, and a
    real propose_stories call are present either way, so the ONLY difference between the
    two arms is whether the activity feed was retrieved. Everything the draft claims
    EXCEPT the PRs/metric (and issue #818) traces to a source present in both arms;
    those activity-derived claims trace to get_activity alone."""
    brief = tools.get_task("happy")["body"]
    lines = [brief,
             f"get_project({{'project_id': 'P-NORTH'}}) -> "
             f"{json.dumps(tools.get_project('P-NORTH'))}"]
    if include_activity:
        lines.append(f"get_activity({{'project_id': 'P-NORTH'}}) -> "
                     f"{json.dumps(tools.get_activity('P-NORTH'))}")
    lines.append(f"get_norms({{}}) -> {json.dumps(tools.get_norms())}")
    lines.append(f"propose_stories({{'project_id': 'P-NORTH', 'stories': [...3...]}}) -> "
                 f"{json.dumps(tools.propose_stories('P-NORTH', STORIES))}")
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

    flipped = results[True] == "pass" and results[False] == "fail"
    verdict_line = (f"{results[True].upper()} -> {results[False].upper()}")
    if flipped:
        headline = (f"FLIP OBSERVED: {verdict_line} (grounded -> invented). Retrieve is "
                    "load-bearing —\nthe ONLY change between 3a and 3b was withholding one "
                    "tool, and the same activity-\nderived claims that PASSED when cited "
                    "FAILED when the source was withheld.")
    else:
        headline = (f"FLIP NOT OBSERVED this run: {verdict_line} (expected PASS -> FAIL). "
                    "The critic is\nnon-deterministic; 3b (fabrication caught on check #2) "
                    "is the load-bearing result\neither way. Re-run for the clean flip, or "
                    "read the per-arm reasons above.")
    banner(f"{headline}\nThe long-context brief was present throughout. "
           f"Run cost ≈ ${bounds.cost:.4f}")


if __name__ == "__main__":
    main()
