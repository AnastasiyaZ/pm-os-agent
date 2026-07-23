# Bounds, Trust & Autonomy Strategy: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 5, how you'd ship it and widen trust over time
> Carries the climb path from `01-agent-line/agent-line-map.md` and the eval gates from `05-bounds-evals/bounds-and-evals.md`.

## Autonomy Dial by segment

Autonomy is a product decision per user, not one global setting. The same Cortex build serves all three segments by moving *where the human sits* — how much of the drafting they delegate and how closely they check it — not by changing the tools.

| Segment | Desired autonomy | Why |
|---|---|---|
| **Seasoned PM** — months of clean Supervised traces | **Bounded-autonomous** for routine status updates | Has watched Cortex assemble the weekly update and queue the backlog batch correctly across dozens of runs, with a near-zero override rate. Lets the draft assemble and the story batch queue themselves, then **spot-checks** rather than reading every one — still performs the company-wide post by hand, so what she hands over is the *review*, not the *send*. |
| **New eng lead** — owns story-prep, no track record yet | **Supervised**; approves every story-prep action | Approves each queued backlog batch and status draft at the HITL checkpoint before anything is used. This is Cortex's default rung — it acts, a human approves each action. |
| **Exec stakeholder** — uses Cortex for their own prep, doesn't operate the loop | **Assisted**; acts manually | Treats Cortex's output as suggestions, not a delegate: reads the drafted update / talking points and writes the version they'll actually use, in their own voice. Wants a second opinion, not hands-off assembly. |

**Invariant across every segment:** #8 (post company-wide) stays human for *everyone*, regardless of rung — there is no publish tool to move above the line, and a weekly leadership update is low-volume, high-visibility (removing the gate saves minutes and risks reputation). Promotion — e.g. the seasoned PM from Supervised → Bounded — is gated on the M5 eval gate below (override rate < 2% for 2 weeks, critic false-pass ≤ 2%), **not on elapsed time**. The "months of clean traces" matter only because they *produce* that evidence, never as a calendar milestone on their own.

## Trust Ladder

- **Current rung: Supervised.** Cortex drafts the update and *queues* a backlog proposal; a human reviews at the HITL checkpoint before anything commits. There is no publish tool, so it *structurally cannot* climb past this on its own.
- **Target next rung: Bounded-autonomous.** The human stops being the *inline gate* and becomes an *out-of-line auditor* — spot-checking rather than reviewing every output. This single transfer is the entire risk of the promotion.

**Eval gate to reach Bounded-autonomous** (from M5; the climb is gated on evidence, not calendar):

| Gate | Threshold | Why it's required at Bounded but not Supervised |
|---|---|---|
| Labeled eval harness exists | ≥ 24 labeled known-bad cases | Three fixtures demo the loop; they can't certify a *rate*. No rate = no warrant to remove the human. |
| Tool-call accuracy | ≥ 98% on the replay set (up from the ≥ 95% Supervised bar) | The Supervised human catches arg/tool errors inline; at Bounded no one does. |
| Critic false-pass rate | ≤ 2% overall, **≤ 1% on the High-blast date-promise / false-green subset** | At Supervised the human catches a false-pass; at Bounded the critic **is** the gate, so a false-green on a Sev-1 earns the tighter bar. |
| Confidentiality leak rate | **0** across the seeded-embargo set **and** ≥ 200 sampled production traces, backed by a dedicated pre-publish scan | The human currently catches leaks inline; remove them and #2b needs its own control. |
| Escalation-correctness | 100% on the missing-data + cost-cap cases | The machinery must provably fail safe when unsupervised. |
| Human-override rate | < 2% for 2 consecutive weeks of Supervised traces | Evidence the inline gate is already rubber-stamping — the precondition for loosening it to a spot-check. |

**The design consequence:** the two controls I *declined* at Supervised — a second independent critic, and a structural confidentiality wall — are declined **only because the human is the inline gate**. Both flip to "required" the moment we climb. The climb checklist and the declined-controls list are the same list.

**Should this agent climb at all? (the honest counterargument.)** Autonomy pays off on high-volume, low-latency-tolerance work where human review is the bottleneck. A weekly exec update is the opposite: one a week, days of slack, high visibility, review costs ~2 minutes against a run that costs a few cents. A defensible strategy is to **keep Cortex at Supervised for exec updates indefinitely** and spend the autonomy budget on higher-volume fleet tasks (activity triage, first-draft grooming). "We deliberately chose not to promote this agent" is a stronger governance answer than a climb-by-calendar.

- **Incident record so far:** none in production (not yet deployed). Build-time near-miss: a credential-materialization attempt was correctly blocked by the harness (logged in `06-autonomy/build-insights.md`).

## Deployment plan

A prototype handoff is a link; an **operator handoff is four concrete things** — runtime, on-call owner, rollback, monitoring — plus the runbook that says how to operate, pause, and recover. All four below are calibrated to the current rung (**Supervised**); the piece that changes on the climb to Bounded is called out in each.

### Runtime

- **Today:** local `python 00-build/agent.py [fixture]` against the Anthropic API. Model is `CORTEX_MODEL` (default `claude-sonnet-4-6`), auth is `ANTHROPIC_API_KEY` from a gitignored `.env`. Triggered by hand.
- **Production target: a GitHub Actions scheduled workflow in this same repo.** The loop is small, stateless per run, and fires once a week — that profile does not justify standing compute or a new cloud account. A cron in the repo the code already lives in is the lowest-plumbing path (and per `build-insights.md`, shipping an agent is *mostly* plumbing). Concretely: a `schedule:` cron for Monday morning + `workflow_dispatch` for manual/replay runs; `ANTHROPIC_API_KEY` as an encrypted repo/environment secret (never committed); the bounds pinned as workflow env (`CORTEX_COST_CAP_USD=0.50`, `CORTEX_MAX_ITERATIONS=8`, …) so the caps travel *with* the deploy; the full run trace uploaded as a workflow artifact (that artifact is the monitoring substrate); a `concurrency:` group so a manual re-run can't overlap a scheduled one.
- **Honest status — this is a plan, not a shipped pipeline.** No `.github/workflows/` exists yet. Two caveats when it does: (1) GitHub Actions cron is UTC and best-effort — it can lag minutes under load. Fine for a weekly job with days of slack; not for anything latency-sensitive. (2) The cron is the *trivial* part. A real Monday run needs live GitHub/Jira/Slack **read** connectors, and the moment those land they activate the two dormant M5 bounds (wall-clock **timeout** and **JIT/expiring tokens**) and become the single largest blast-radius item on the map. So "deploy the cron" ≠ "ship it"; **"ship the connector safely" is the actual milestone**, and it is gated on the M5 bounds work, not on the workflow YAML.

### On-call owner

*Named owner + escalation path — not "the team."*

- **Supervised (today):** primary owner is the PM who owns the update — **you**. There is no unattended failure that pages anyone, because nothing posts: a failed run just means no draft is waiting Monday, which the PM notices at review. **On-call burden ≈ 0, by design** — a direct dividend of the no-write-tool posture.
- **Secondary (machinery):** a **named eng owner** of `agent.py` for pipeline failures — bad key, connector down, dependency break. A named person, not a rota-less "the team."
- **Bounded (future) — the pager gets real, so the role splits:** **eng on-call** owns the machinery (bound trips, connector failures, the pre-publish leak scan) and the **PM owner** becomes the content auditor (spot-checks the now-unattended output). "Who decides at 2am" only becomes a live question here, and the answer is pre-agreed: **eng halts the machinery, PM adjudicates content** — nobody improvises. The escalation the *agent* raises (revision cap, missing data, cost cap) always terminates at the human owner; the machinery escalates, it never decides to proceed.

### Rollback

The lecture's three rollback levers, mapped to controls Cortex actually has — fastest first:

1. **Off (RTO ≈ immediate):** `gh workflow disable "<name>"` or delete the schedule. Because Cortex writes nothing and posts nothing, "off" is instant and there is **no partial state to unwind**.
2. **Revert version:** prompts and bounds are code in this repo, so "known-good" is a git tag/SHA. A bad prompt or bound change rolls back in **one commit** (or by pinning the workflow to the prior SHA).
3. **Disable a tool:** drop a tool from `tools.TOOLS` — e.g. remove `propose_stories` and Cortex degrades to **draft-only** (queues nothing) while still producing the update. Graceful and partial, not all-or-nothing.
4. **Drop the dial a rung:** Bounded → Supervised = re-insert the human inline gate (stop auto-accepting, require review every run). Supervised → Assisted = stop the cron, revert to manual suggest-only.

**What rollback does *not* cover, stated plainly:** if a human already approved and posted a bad update at the checkpoint, that post is a *human* action outside Cortex — rolling back the agent does not recall it; that is a comms correction, not an agent rollback. Cortex's rollback is clean *precisely because* the irreversible step lives with the human, not the agent.

### Runbook (operate · pause · recover · replay)

| Need | Do this |
|---|---|
| **Operate** (run now) | `workflow_dispatch` (Actions → Run workflow), or `python 00-build/agent.py happy` locally |
| **Pause** | `gh workflow disable "<name>"` (or toggle in the Actions UI) — no run fires; nothing to unwind |
| **Recover from a tripped bound** | Read the trace banner: `REVISION CAP hit` → self-contradictory brief, fix the brief; `MAX ITERATIONS reached` → loop didn't converge, inspect fixture/connector; `BOUND TRIPPED, cost cap` → raise `CORTEX_COST_CAP_USD` only if the run is legitimate, else investigate. The run **already escalated safely** — recovery is diagnosis, not damage control. |
| **Recover from a bad output** | It was *queued, not posted* — discard the draft at the checkpoint. No rollback needed. |
| **Replay a failed run** | Re-run the exact fixture: `python 00-build/agent.py <fixture>`. The six captured traces in `00-build/` are deterministic replays for regression. |

*This is the operator guide; `00-build/RUNBOOK.md` is the **build** guide (how to construct Cortex), not how to operate it.*

### Monitoring

Goal (lecture): **see it's healthy without watching logs.** Live eval pass %, escalation rate, cost-to-serve, incidents.

- **What each run emits:** outcome (checkpoint-reached / escalated / bound-tripped) · cost/run vs the $0.50 cap · iterations used (of 8) · revisions used (of 2) · critic verdict + which checks fired · escalation reason · *(live)* pre-publish leak-scan result · *(live)* tool-call latency vs the 30 s/120 s timeout.
- **"Healthy without watching logs" mechanism:** GitHub Actions job status (green/red) + a one-line job-summary per run + a Slack alert on the red conditions + a **weekly rollup** of the ROI metrics below. Nobody opens a log unless an alert fires.
- **Page-worthy (alert):** any confidential-leak event (expected **0**) · escalation-rate **spike** (signals data-source drift / connector rot) · cost/run **> cap** · an **unexpected** bound trip.
- **Log-and-rollup (not page):** normal escalations, revisions within cap, expected cost variance.
- **This is the online arm of the M5 eval lifecycle** (`05-bounds-evals` §4, production traces): sampled runs score leak-rate, critic false-pass, escalation-correctness, and cost/run against the §3B thresholds, and failures feed the seeded known-bad set — the climb prerequisite. **Monitoring and evals are the same instrument, read live.**

## ROI metrics (beyond adoption & tokens)

Adoption says people clicked it; tokens say it ran. Neither says it was *worth* running — and for this agent the token bill is a rounding error next to the human gate. Three pillars: **outcome**, **fully-loaded cost-to-serve**, **trust incidents**.

**1. Outcome metrics** — measured against a **shadow-mode baseline**, not asserted. *Baseline method:* before trusting any "time saved" figure, run Cortex in **shadow** (Trust-Ladder rung 1 — it drafts, the PM ignores it and assembles by hand as usual) for ~4 weeks, recording (a) PM wall-clock to assemble the update manually and (b) whether the ignored draft *would* have been accepted. That converts the estimates below into a measured delta.

| Outcome metric | How measured | Target | Confidence |
|---|---|---|---|
| Draft-accepted-without-substantive-edit rate | % of weekly runs where the PM ships Cortex's draft with ≤ trivial edits | ≥ 90% | moderate — ties to the < 2% human-override climb gate |
| Time saved vs shadow baseline | PM hand-assembly time − ~2 min review, from the shadow weeks | ~30–45 min/wk → ~2 min (~0.5 hr/wk saved) | moderate — pending shadow measurement |
| Content-error rate (caught at review) | % of drafts with a factual/tone error the human fixes | trend ↓; expected > 0 early | low |
| Task completion (clean checkpoint: grounded, no leak, no fabrication) | % of runs reaching a clean HITL checkpoint | ≥ 95% | high on the binary parts |

*"End-to-end completion" is a Bounded metric — at Supervised Cortex never completes end to end by design; a human always closes. The honest Supervised outcome is "draft accepted without edit," not "threads completed autonomously."*

**2. Cost-to-serve (fully loaded — the part everyone gets wrong).** The lecture's definition is model + tools + retries + **human review**, per *completed* task — not raw tokens. Do that arithmetic and the headline flips:

| Component | Per run |
|---|---|
| Model + tools (happy path) | **~$0.05** (observed this session: $0.0420 / $0.0576; 2-revision worst legit run ~$0.15–0.18; hard cap $0.50) |
| Human review (~2 min at Director/Sr-PM fully-loaded ~$150–250/hr) | **~$5–8** |
| **Fully-loaded cost-to-serve** | **~$5–8 / run — ~97–99% of it human review** |

The load-bearing conclusion: **at Supervised, Cortex's cost-to-serve is almost entirely the human gate; the model is effectively free.** That is exactly why token/adoption dashboards mislead here, and it reframes the climb: the *only* material cost lever is reducing human-review time — i.e. climbing to Bounded. Which sharpens the counterargument already in this doc — **2 min/week is a trivial cost, so the exec-update use case may not justify the climb at all**; spend the autonomy budget on higher-volume fleet work (activity triage, first-draft grooming) where review minutes actually accumulate. *Confidence: comp figures moderate (public ranges); the conclusion that review dwarfs tokens is **high** — it holds across any plausible PM comp.*

**3. Trust incidents (the metric that gates the ladder).** Count + severity of out-of-bounds actions or errors that **escaped the gate**: a confidential leak reaching a human unflagged, a false-green on a Sev-1, a committed date that shouldn't have been, any attempt to act beyond read-only.

| | |
|---|---|
| Target | **0.** Any incident pauses autonomy expansion (see the widen-autonomy rule below). |
| Severity weighting | A leak or false-green on a High-blast item is a hard stop; a recoverable tone slip is logged, not a stop. |

This is the one ROI metric that is a **gate, not a trend** — you don't average it and you don't trade it against time saved.

**The honest ROI story** (the lecture's one-liner, filled with defensible illustrative numbers — every figure except the observed model cost and the 0-incident gate is a target pending shadow + live runs):

> *"In shadow and early Supervised, Cortex produced a leadership-ready weekly update accepted with no substantive edit in **~90%** of weeks, saving the PM **~30–45 min/week (~0.5 hr)** at a fully-loaded cost-to-serve of **~$5–8/run** — **~$0.05–0.18** of it model + tools, the rest the ~2-min human review — with **0** trust incidents."*

## Widen-autonomy decision rule

**Turn the dial from Supervised → Bounded-autonomous only when, over a rolling 30-day / ≥ 50-run window:** (1) the labeled harness exists and is green, (2) tool-call accuracy ≥ 98%, (3) critic false-pass ≤ 2% overall and ≤ 1% on the date-promise / false-green subset, (4) confidentiality leak rate = 0 with the dedicated scan live, (5) escalation-correctness = 100% on the missing-data + cost-cap cases, (6) human-override < 2% for 2 consecutive weeks, and (7) zero trust incidents. Miss any one → stay at Supervised. **#8 (company-wide post) never crosses the line short of full autonomy, regardless of these metrics.** Stated in advance so the decision is evidence-driven, not vibes-driven.
