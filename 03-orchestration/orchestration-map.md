# Orchestration Map: Cortex PM Chief-of-Staff Agent

> Module 3 · Orchestration & Subagents, ★ Deliverable 3
>
> Builds on the M2 Loop Spec. Only split one agent into a team when there's a real reason, coordination has a cost.

## 1. Why split? (or why not)

Run the default-to-simple check. Cortex is **one orchestrator + exactly one subagent (the critic)** — and that split earns its keep for one reason only: **independent validation.**

The critic is not a second worker for parallelism or context-window relief. It exists to break a specific failure mode: a drafter grading its own homework can't see its own blind spots. So the critic is a separate model call with its own system prompt (`CRITIC_SYSTEM`) that **never sees the drafting conversation** — only the source data and the proposed output. That context isolation is the entire value; it's why a false-green or a smuggled confidential item has a second, uncontaminated chance of being caught.

**What we did NOT split, and why:** the read tools (`get_project`, `get_activity`, `get_roadmap`, …) are *not* subagents — they're plain function calls the orchestrator makes directly. No research subagent, no separate GitHub/Jira reader agent. The corpus is small, the calls are cheap and read-only, and splitting them would add coordination cost for zero benefit. This is the default-to-simple check passing: **one agent, one validator, no fleet.**

## 2. Topology

**Pattern:** single agent + one validation subagent (sequential gate).

```
  task brief
      │
      ▼
┌─────────────────────┐   direct function calls (not subagents)
│  Cortex             │──▶ get_project · get_activity · search_past_updates
│  (orchestrator +    │    get_roadmap · get_norms          [read-only]
│   drafter)          │──▶ propose_stories                  [queue-only, cap 10]
└─────────────────────┘
      │ proposed output (text, no tool call)
      ▼
┌─────────────────────┐
│  Critic (subagent)  │  separate model call · own system prompt
│  context-ISOLATED   │  sees: source_log + proposed output ONLY
└─────────────────────┘
      │
   pass ──────────────▶ HITL checkpoint → queued for human  (nothing posted)
   fail ──▶ revise (≤ MAX_REVISIONS=2) ──▶ then ESCALATE to human
```

## 3. Roster

| Agent / subagent | Responsibility | Runs which Loop Spec |
|---|---|---|
| **Cortex** (chief-of-staff) | Orchestrates: reads task, pulls context, drafts the update, queues story proposals | M2 goal loop |
| **Critic / Validator** | Independently checks the draft before it can advance to a human | Validation loop (`critic.review`) |
| ~~Research subagent~~ | *Not used* — no external/market research in scope | — |
| ~~GitHub/Jira reader~~ | *Not a subagent* — collapsed into direct read-tool calls | — |

## 4. Communication & hand-offs

Plain in-process function calls — no MCP/A2A protocol (unnecessary at this scale; note it here so the choice is explicit, not accidental). What passes between the parts:

- **Orchestrator → tools:** structured args (`project_id`, `query`, `stories`); tools return JSON.
- **Orchestrator → critic:** two strings — the `source_log` (every tool call + result, joined) and the `proposed_output`. Deliberately **not** the message history, that isolation is the point.
- **Critic → orchestrator:** strict JSON `{"verdict": "pass"|"fail", "reasons": [...]}` plus a `_usage` block for cost tracking. On unparseable output the critic **fails closed** (`verdict: fail`) — a safe default.

## 5. The validator

- **What the critic checks** (6 checks in `CRITIC_SYSTEM`): (1) correct project + real activity; (2) every claim/metric/date traceable to pulled data; (3) norms compliance — no unconfirmed date, no launch gate marked, no CONFIDENTIAL item in a company-wide update; (4) posts/commits/creates nothing, leaks nothing; (5) if jailbroken, refused + escalated; (6) if a bound tripped (e.g. `batch_exceeds_queue_cap`), escalation is the *correct* response and must pass.
- **Fail action:** `agent.py` feeds the critic's reasons back to the drafter for revision, up to `MAX_REVISIONS=2`; on the 3rd fail it escalates to a human instead of looping. Fail-closed on parse error.
- **The known limitation (carried to M5/M6):** this is a **single** validator running the **same model** as the drafter. Its independence is *contextual*, not *architectural*. At the Supervised rung that's acceptable — the human is the real gate. At Bounded-autonomous the critic *becomes* the gate, so a second independent check (or a different model) is the specific control that must be added before climbing. See `01-agent-line/agent-line-map.md` and `06-autonomy/governance-and-strategy.md`.

## 6. State: shared vs isolated

| State | Shared or isolated | Why |
|---|---|---|
| Task brief + `source_log` | Shared (orchestrator → critic) | The critic must audit against the same ground truth |
| Drafting message history | **Isolated** (critic never sees it) | Prevents the critic inheriting the draft's rationalizations — the core design choice |
| `Bounds` (cost), counters | Orchestrator only | Bounds are enforced outside both model calls |

## 7. Cost & latency budget

Coordination price is one extra model call per completed run (the critic). On the happy path: total is **a few cents** including critic spend — well under the $0.50 cap, a small fraction of the run. Latency is one added round-trip at the end. Cheap enough that the independent-validation benefit clearly wins — but note the cost roughly **triples** if the draft bounces the full `MAX_REVISIONS=2` (each revision = another drafter call + another critic call). That range, not the happy-path floor, is what the $0.50 cap in M5 must cover.
