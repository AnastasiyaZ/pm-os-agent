# Bounds, Trust & Autonomy Strategy: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 5, how you'd ship it and widen trust over time
> Carries the climb path from `01-agent-line/agent-line-map.md` and the eval gates from `05-bounds-evals/bounds-and-evals.md`.

## Autonomy Dial by segment

Autonomy is a product decision per user, not one global setting. The same Cortex build serves both by moving *where the human sits*, not by changing the tools.

| Segment | Desired autonomy | Why |
|---|---|---|
| Cautious PM ("Tesla driver") | **Supervised** | Wants to read every leadership update before it goes out; the critic is a helper, the PM is the gate |
| High-trust team lead ("Waymo passenger") | **Bounded-autonomous** | Happy to let the weekly update assemble and the backlog proposal queue itself; spot-checks rather than reviews each |
| **Never any segment** | — | **#8 (post company-wide) stays human for everyone.** A weekly leadership update is low-volume, high-visibility — removing the human gate saves minutes and risks reputation. This gate does not move. |

## Trust Ladder

- **Current rung: Supervised.** Cortex drafts the update and *queues* a backlog proposal; a human reviews at the HITL checkpoint before anything commits. There is no publish tool, so it *structurally cannot* climb past this on its own.
- **Target next rung: Bounded-autonomous.** The human stops being the *inline gate* and becomes an *out-of-line auditor* — spot-checking rather than reviewing every output. This single transfer is the entire risk of the promotion.

**Eval gate to reach Bounded-autonomous** (from M5; the climb is gated on evidence, not calendar):

| Gate | Threshold | Why it's required at Bounded but not Supervised |
|---|---|---|
| Labeled eval harness exists | ≥ 24 labeled known-bad cases | Three fixtures demo the loop; they can't certify a *rate*. No rate = no warrant to remove the human. |
| Critic false-pass rate | ≤ 5% (tighter for date-promises) | At Supervised the human catches a false-pass; at Bounded the critic **is** the gate. |
| Confidentiality leak rate | **0** on seeded embargoed tasks + a dedicated pre-publish scan | The human currently catches leaks inline; remove them and #2b needs its own control. |
| Escalation-correctness | 100% on missing-data + cost-cap cases | The machinery must provably fail safe when unsupervised. |

**The design consequence:** the two controls I *declined* at Supervised — a second independent critic, and a structural confidentiality wall — are declined **only because the human is the inline gate**. Both flip to "required" the moment we climb. The climb checklist and the declined-controls list are the same list.

**Should this agent climb at all? (the honest counterargument.)** Autonomy pays off on high-volume, low-latency-tolerance work where human review is the bottleneck. A weekly exec update is the opposite: one a week, days of slack, high visibility, review costs ~2 minutes against a ~$0.07 run. A defensible strategy is to **keep Cortex at Supervised for exec updates indefinitely** and spend the autonomy budget on higher-volume fleet tasks (activity triage, first-draft grooming). "We deliberately chose not to promote this agent" is a stronger governance answer than a climb-by-calendar.

- **Incident record so far:** none in production (not yet deployed). Build-time near-miss: a credential-materialization attempt was correctly blocked by the harness (logged in `06-autonomy/build-insights.md`).

## Deployment plan

- **Runtime:** self-hosted script today (`00-build/agent.py`), triggered manually or by a Monday cron. For production, a managed-agent platform or serverless function on a schedule — the loop is small and stateless per run, so serverless fits. No standing compute needed.
- **Operator / on-call owner:** the PM who owns the update (you) at Supervised; a named eng owner once it runs unattended at Bounded.
- **Rollback:** kill the schedule / process. Because Cortex writes nothing and posts nothing, "off" is instant and clean — there is no partial state to unwind. This is a direct benefit of the no-write-tool design.
- **Monitoring:** per-run cost vs the $0.50 cap; critic pass/fail rate; escalation rate; and (once live) leak-rate and false-pass on sampled traces. Alert on any confidential-leak event (should be 0) and on escalation-rate spikes (signals data-source drift).

## ROI metrics (beyond adoption & tokens)

| Metric | Target |
|---|---|
| Task completion rate (grounded update queued, no leak, no fabrication) | ≥ 95% of runs reach a clean HITL checkpoint |
| Time saved | ~30–45 min of PM assembly per weekly update → ~2 min review; ≈ 90% reduction |
| Cost-to-serve | ≤ $0.10 / run (happy path ≈ $0.066; cap $0.50) |
| Trust incidents (leaks, false-greens, bad dates reaching a human unflagged) | **0** — any incident pauses autonomy expansion |

## Widen-autonomy decision rule

**Turn the dial from Supervised → Bounded-autonomous only when, over a rolling 30-day / ≥ 50-run window:** (1) the labeled harness exists and is green, (2) critic false-pass ≤ 5%, (3) confidentiality leak rate = 0 with the dedicated scan live, and (4) zero trust incidents. Miss any one → stay at Supervised. **#8 (company-wide post) never crosses the line short of full autonomy, regardless of these metrics.** Stated in advance so the decision is evidence-driven, not vibes-driven.
