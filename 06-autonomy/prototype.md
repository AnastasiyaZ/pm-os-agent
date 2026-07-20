# Prototype: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 1, the working agent demo

## What it does

Cortex takes one PM task brief — "assemble this week's leadership status update for Northstar, and propose next sprint's stories" — and runs a transparent, bounded loop: it pulls the project, its recent engineering activity, past updates for tone, the roadmap, and team norms; drafts a grounded status update; queues a capped batch of backlog stories for approval; submits the draft to an independent critic; and stops at a human-in-the-loop checkpoint with **nothing posted, committed, or created.** In the captured happy-path run it batched 5 read calls, queued a batch of backlog stories that hit the 10-item cap — the cap held and the overflow was flagged for sprint planning rather than expanded past the limit — passed the critic on the first try, and finished for ≈ **$0.080** — about 16% of the $0.50 cost cap.

## How you built it

- **Coding agent:** Claude Code (directed the OpenAI→Anthropic port of the starter, verified the model ID/pricing, ran the fixture, and wrote up the deliverables).
- **Model + bounds:** `claude-sonnet-4-6` ($3/$15 per 1M in/out); `MAX_ITERATIONS=8`, `MAX_REVISIONS=2`, `COST_CAP_USD=0.50`, `MAX_QUEUE_ITEMS=10`. Bounds enforced outside the model in `agent.py` / `tools.py`.
- **Repo / config:** `00-build/` — `agent.py` (loop), `critic.py` (validator), `tools.py` (7 tools, no publish tool), `prompts.py` (agent + critic system prompts), `fixtures/` (mock data).
- **Live link:** _[optional]_

## Screenshots (required, collected M2 to M6)

Real screenshots of *your* Cortex running. These are the `00-build/CORTEX-ANATOMY.md` set and they are required, a link alone is not enough.

| # | Screenshot | What it shows | From | Status |
|---|---|---|---|---|
| 1 | _[img]_ | happy-path run: a real drafted update + the HITL checkpoint (queued, not posted) | M2 | ✅ **captured** — `00-build/happy-run.txt` |
| 2 | _[img]_ | the critic rejecting a bad draft (revise/block) | M3 | ⏳ needs a seeded-bad run |
| 3 | _[img]_ | a grounded update citing pulled activity + a caught hallucination | M4 | ⏳ partial — happy run shows the citation table mapping claims to source tools |
| 4 | _[img]_ | jailbreak refused + escalated | M5 | ⏳ run `agent.py jailbreak` |
| 5 | _[img]_ | an iteration/cost/queue bound halting a runaway | M5 | ⏳ run `agent.py missing-data` or force the queue cap |
| 6 | _[img]_ | end-to-end run | M6 | ⏳ |

**Evidence captured so far:** the happy-path trace (`00-build/happy-run.txt`) covers screenshot #1 in full — the 5 tool pulls, the `queued_for_approval` story batch (at the 10-item cap), the drafted update with a citation table mapping each claim to the source tool it came from, the critic's `pass` verdict with its per-claim reasons, and the HITL checkpoint banner stating nothing was posted.

## How to run it

```bash
cd 00-build
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
# add ANTHROPIC_API_KEY to .env (copy from .env.example)
./.venv/bin/python agent.py happy          # happy path (this is the captured run)
./.venv/bin/python agent.py missing-data   # the stuck/escalate case
./.venv/bin/python agent.py jailbreak       # the prompt-injection refusal case
```

Each run prints the full trace to the terminal; pipe through `| tee happy-run.txt` to save it.
