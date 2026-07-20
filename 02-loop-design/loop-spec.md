# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.
> Grounded in the live loop at `00-build/agent.py` and the observed happy-path run (`00-build/happy-run.txt`).

## 1. Trigger & loop type

**Type: goal loop. Triggers: cron + hook.** These are two different axes — the trigger answers *when it fires*; "goal vs. fixed pipeline" answers *how it runs once fired* — so both belong in the answer, on different lines. It is not "hook+cron instead of goal."

> **Justification (≤2 sentences):** A weekly leadership update is a scheduled deliverable, so a **cron (Monday 9:00am)** owns it, while a **hook** on inbound tasks / new-PRD versions handles event-driven work like story proposals; the same daily cron also runs a morning **sweep** as a reliability backstop, re-checking for any inbound task a dropped hook event missed (idempotent, so it never re-processes work the hook already handled). It is a *goal* loop rather than a fixed pipeline because "done" is defined by an independent validator passing, not by a fixed step count — the agent chooses which tools to call to get there.

- **Cron — primary for the weekly update.** The status update is due every week regardless of whether anyone asks, so the cron *owns* it. Cron here is not a safety net; it is why the single most important artifact ships on time.
- **Hook — primary for event-driven work.** Story proposals and ad-hoc briefs make sense *when* a PRD lands or a PM drops a request, so a hook on an inbound task / new-PRD version triggers those.
- **Daily-sweep cron — secondary, reliability backstop.** The same daily cron re-checks for any inbound task a dropped hook event missed. This is a bonus, not cron's reason to exist, and it carries a real requirement: it must be **idempotent** — dedupe against already-processed tasks so it never re-queues stories or regenerates an update the hook already produced.
- **Not heartbeat.** Heartbeat suits latency-sensitive, continuously-changing state (poll every few minutes, react fast). Cortex is the opposite — low-volume, days of slack — so a tight poll would burn cost for zero benefit. Correctly excluded.

Once triggered, the inner loop iterates (pull → draft → validate → revise) until the definition of done is met or a bound trips — no hard-coded step order. The observed run confirms this: the model batched 5 reads, drafted, then submitted to the critic on its own initiative.

**Honesty note:** none of these triggers exist in `agent.py` today — the code is a single manual `run(which)` invoked by hand (`python agent.py happy`). The trigger design is spec-level intent; the scheduler is not built.

## 2. Goal / definition of done

**Outcome the loop owns:** a leadership status update *grounded in real pulled activity*, plus (when asked) a backlog proposal *queued* for review — with **nothing posted, committed, or created**.

**What says "done":** the independent critic (M3) returns `verdict: "pass"` on the drafted output, which is then surfaced at the HITL checkpoint. Done is never "the model stopped talking" — it is "an independent check that never saw the drafting context confirmed the output is grounded, norm-compliant, leak-free, and commits nothing." On the happy path this fired on the first critique (a few cents, well under the $0.50 cap).

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | Critic returns `verdict: "pass"` | HITL checkpoint: update + any queued stories surfaced for human review; loop returns; nothing posted |
| **Give up / stuck** | `MAX_REVISIONS=2` exhausted (critic keeps rejecting), or `MAX_ITERATIONS=8` reached, or `COST_CAP_USD=0.50` hit | Halt instead of spinning; escalate to a human with what was tried. `REVISION CAP` / `MAX ITERATIONS` / `BOUND TRIPPED` banner |
| **Escalate to human** | Required data missing (`project_not_found`), jailbreak detected, an unconfirmed date / Sev-1 / over-cap batch (`batch_exceeds_queue_cap`) would be required | Emit `ESCALATE:` with what was tried; commit nothing, fabricate nothing (from agent-line-map #7–#8) |

The key design property: **all three stop conditions are enforced outside the model.** The agent never decides it has looped enough — a counter, a cap, or a missing-data error decides for it.

### Self-validation (required, because this is a goal loop)

A goal loop needs something other than the model's own say-so to decide "done" — otherwise it stops whenever it *feels* finished. That something is the independent critic (`critic.py`): a **separate model call** with **context isolation** — it sees only the `source_log` + the proposed output, never the drafting conversation — returning strict JSON `{verdict, reasons}` against six checks: correct project + real activity, every claim traceable, norms compliance, nothing posted/committed/created, jailbreak refused, and bound-trips treated as *correct*. It **fails closed**: an unparseable critic response scores `fail`, never `pass`. This is what makes "done" mean *validated*, not merely *stopped*.

## 4. State

**Per-run, purged each run:** the message list (`messages`) and the `source_log` that the critic later audits. Nothing carries between runs in the current build — each weekly update starts clean.

**Scope guard:** because state is per-run and per-project (the task brief names one project), there is no cross-project bleed. The confidential-leak risk (agent-line map #2b) comes not from state but from the roadmap *read* within a run — mitigated by norms + the critic, not by state scoping. Persistent memory (past updates, decisions, norms) lives in fixtures and is *retrieved*, not held in loop state — see M4.

## 5. The five things every loop needs

Two components are always-on and locked today (**connectors, state**). Of the three that scale with autonomy, Cortex already needs one — the **critic subagent** was load-bearing from day one — so it is locked too; **skills** and **work tree** are genuinely *not needed yet* and get a one-line reason, to be fleshed out as later modules add autonomy.

| Component | Status | For Cortex |
|---|---|---|
| **Plugins / connectors** (tools & access) | 🔒 **Locked** | **5** model-callable read tools (`get_project`, `get_activity`, `search_past_updates`, `get_roadmap`, `get_norms`) + **1** queue-only tool (`propose_stories`) = 6 tools the model can call. (`get_task` is in `tools.py` but *not* in `TOOL_SCHEMAS` — the harness calls it to load the brief, so it's infrastructure, not a model connector.) All read-only or queue-only over `fixtures/`; **no world-acting tool exists** — read + draft/queue only, never send. This is the **M1 agent line made real.** |
| **State tracking** | 🔒 **Locked** | **Per-run only.** *Within* a run, across iterations: the `messages` list, the `source_log` the critic audits, the `step` and `revisions` counters, and `Bounds.cost`. **Scope:** per-run, per-project (the brief names one project). **Cross-run retention: zero** — each weekly update starts clean; there is no persistent "which threads handled / where in the approval" state, because the HITL checkpoint *ends* the run and approval happens out-of-band. (Contrast the lecture's "retained 30 days" — Cortex deliberately retains nothing yet.) |
| **Subagents** (delegated / validation) | 🔒 **Locked** *(exception to the "defer" default)* | The independent critic (`critic.review`) — a separate model call with its own system prompt that **never sees the drafting messages**, and **fails closed**. Not deferred: needed from day one because a drafter can't grade its own homework. Full topology → `03-orchestration/orchestration-map.md`. |
| **Skills** (reusable capabilities) | ◻️ **Not needed yet** | Cortex has exactly one task shape (weekly update + story proposal), expressed inline in `CORTEX_SYSTEM` — there is no library of reusable, composable capabilities to factor out until it handles multiple task types. |
| **Work tree** (isolated workspace per run) | ◻️ **Not needed yet** | Cortex runs one task per invocation, single-threaded, with state purged each run — so there is no concurrent second thread to isolate. The per-run freshness (new client + new `Bounds()`) already gives the single-threaded version of the guarantee; a real work tree earns its keep only once runs overlap (several projects in flight at once). |

## 6. Context plan

Each iteration the model receives: the system prompt (`CORTEX_SYSTEM`), the task brief, and the accumulated tool results (`tool_result` blocks) from prior iterations. Ground truth is **pulled deliberately** — `get_project` intentionally omits the activity blob, forcing a separate `get_activity` call (a teachable retrieve step). The critic receives a *different* context: only the `source_log` + the proposed output, never the drafting conversation — deliberate **context isolation** so it can't inherit the draft's blind spots. Full retrieve-vs-long-context analysis → M4 `memory-and-context.md`.

## 7. Hand-off to bounds & evals

Bounds enforced this loop, specified in `05-bounds-evals/bounds-and-evals.md`: `MAX_ITERATIONS=8`, `MAX_REVISIONS=2`, `COST_CAP_USD=0.50`, `MAX_QUEUE_ITEMS=10`, read-only permissions, HITL at every above-the-line decision. Known gap: no wall-clock timeout yet (safe with local mock tools; required before a live connector).

## Link to live loop

`00-build/agent.py` — `run(which="happy")`. Captured trace: `00-build/happy-run.txt`.
