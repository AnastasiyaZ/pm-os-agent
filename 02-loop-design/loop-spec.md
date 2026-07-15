# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.
> Grounded in the live loop at `00-build/agent.py` and the observed happy-path run (`00-build/happy-run.txt`).

## 1. Trigger & loop type

**Chosen type: goal loop**, wrapped by a **cron** trigger.

A Monday-morning cron fires the weekly leadership update; a **hook** on a new PRD version is the natural second trigger for the story-proposal path. The inner loop itself is a *goal* loop: it iterates (pull → draft → validate → revise) until an explicit definition of done is met or a bound trips — it is not a fixed pipeline. This matches the observed run: the model chose to batch 5 reads, then draft, then submit to the critic, with no hard-coded step order.

## 2. Goal / definition of done

**Outcome the loop owns:** a leadership status update *grounded in real pulled activity*, plus (when asked) a backlog proposal *queued* for review — with **nothing posted, committed, or created**.

**Validation that says "done":** the independent critic (M3) returns `verdict: "pass"` on the drafted output. Done is not "the model stopped talking" — it's "an independent check that never saw the drafting context confirmed the output is grounded, norm-compliant, leak-free, and commits nothing." On the happy path this fired on the first critique (3 loop iterations, ≈ $0.066).

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | Critic returns `pass` | HITL checkpoint: update + any queued stories surfaced for human review; loop returns; nothing posted |
| **Stuck / give up** | `MAX_REVISIONS=2` exhausted (critic keeps rejecting), or `MAX_ITERATIONS=8` reached, or `project_not_found` on required data | Escalate to a human with what was tried; loop halts. `ESCALATE:` output per the system prompt |
| **Escalate to human** | Jailbreak detected, unconfirmed date demanded, batch > queue cap, or cost cap hit | HITL checkpoint / escalation (from agent-line-map #7–#8); machinery trips outside the model |

The key design property: **all three stop conditions are enforced outside the model.** The agent never decides it has looped enough — a counter, a cap, or a missing-data error decides for it.

## 4. State

**Per-run, purged each run:** the message list (`messages`) and the `source_log` that the critic later audits. Nothing carries between runs in the current build — each weekly update starts clean.

**Scope guard:** because state is per-run and per-project (the task brief names one project), there is no cross-project bleed. The confidential-leak risk (agent-line map #2b) comes not from state but from the roadmap *read* within a run — mitigated by norms + the critic, not by state scoping. Persistent memory (past updates, decisions, norms) lives in fixtures and is *retrieved*, not held in loop state — see M4.

## 5. The five things every loop needs

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run) | The per-run `messages` + `source_log`; a fresh `anthropic.Anthropic()` client and `Bounds()` object per `run()`. No shared mutable state across runs. |
| **Skills** (reusable capabilities) | Draft-a-status-update and propose-backlog-stories, expressed in `CORTEX_SYSTEM` + the `propose_stories` tool. |
| **Plugins / connectors** (tools & access) | 6 read tools (`get_project`, `get_activity`, `search_past_updates`, `get_roadmap`, `get_norms`) + 1 queue-only tool (`propose_stories`). All read-only over `fixtures/`; **no world-acting tool exists.** |
| **Subagents** (delegated / validation) | The independent critic (`critic.review`) — a separate model call with its own system prompt that never sees the drafting messages. Full topology → `03-orchestration/orchestration-map.md`. |
| **State tracking** | `Bounds` (running cost), the iteration counter (`step`), and the `revisions` counter — the three that trip the stop conditions. |

## 6. Context plan

Each iteration the model receives: the system prompt (`CORTEX_SYSTEM`), the task brief, and the accumulated tool results (`tool_result` blocks) from prior iterations. Ground truth is **pulled deliberately** — `get_project` intentionally omits the activity blob, forcing a separate `get_activity` call (a teachable retrieve step). The critic receives a *different* context: only the `source_log` + the proposed output, never the drafting conversation — deliberate **context isolation** so it can't inherit the draft's blind spots. Full retrieve-vs-long-context analysis → M4 `memory-and-context.md`.

## 7. Hand-off to bounds & evals

Bounds enforced this loop, specified in `05-bounds-evals/bounds-and-evals.md`: `MAX_ITERATIONS=8`, `MAX_REVISIONS=2`, `COST_CAP_USD=0.50`, `MAX_QUEUE_ITEMS=10`, read-only permissions, HITL at every above-the-line decision. Known gap: no wall-clock timeout yet (safe with local mock tools; required before a live connector).

## Link to live loop

`00-build/agent.py` — `run(which="happy")`. Captured trace: `00-build/happy-run.txt`.
