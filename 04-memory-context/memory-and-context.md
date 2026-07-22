# Memory & Context: Cortex PM Chief-of-Staff Agent

> Module 4 · Memory & Context
> Grounded in `00-build/tools.py` (the retrieval surface), `00-build/agent.py` (how context is assembled), and the observed happy-path run.

## 1. Context budget

Each loop iteration receives, in priority order: (1) the **system prompt** (`CORTEX_SYSTEM` — the agent-line rules, non-negotiable); (2) the **task brief** (the whole thing — it's bounded and every word matters); (3) the **accumulated tool results** from prior iterations (`tool_result` blocks). The model runs at `max_tokens=4096` output with a 1M-token context window, so for this mock corpus context pressure is effectively **zero** — nothing needs dropping. The priority order matters for the real-connector future, where activity and roadmap could be large: rules and brief are always kept; tool results are the first candidates for compression.

## 2. Retrieve vs. long-context: per source

**The axis (fetch-based, matches `agent.py`).** *Long-context* = already sitting in the prompt, reasoned over whole. *Retrieve* = fetched on demand via a tool call — the model must **decide** to pull it, it can be scoped/sliced, and it must be **cited**. By that line only the task brief is long-context; everything Cortex learns about the world it *retrieves*.

**The rubric.** Each source scored on five factors, then a keep/flip against the Part A call with the *one* deciding factor named. Ratings are H/M/L for this build's mock corpus, with the real-connector direction in mind.

| Source | Corpus size | Volatility | Citation / audit | Token cost | Latency | Call (vs. Part A) | Deciding factor → one-line why |
|---|---|---|---|---|---|---|---|
| **Activity** `get_activity` | H | **H** | H | H | M | **Retrieve — keep** | **Volatility:** it changes between runs, so any held copy is stale by next Monday — pull fresh each run and cite. |
| **Past updates** `search_past_updates` | M, **grows unbounded** | L | M | M↑ | L | **Retrieve — keep** | **Unbounded growth:** history accretes forever; you can't keep pinning all of it, so scope to the relevant thread. |
| **Roadmap** `get_roadmap` | M–H | M | **H + confidential** | M | L | **Retrieve — keep** | **Confidentiality:** CONFIDENTIAL items (#2b) must be filterable *at fetch* — never pin the whole roadmap in context. |
| **Team norms** `get_norms` | **L** | **L** | H | **L** | **L** | **Retrieve — keep** *(closest call)* | **Audit + versioning:** size/cost/latency all argue *long-context*; what holds it in retrieve is that the model must cite a **live, versioned** playbook, not a baked-in copy that can silently drift. Not "large/changing" — it isn't. |
| **This week's task brief** | L | n/a (per-run input) | n/a (it's the instruction, not evidence) | L | n/a (arrives in the message) | **Long-context — keep** | **It's the input itself:** arrives in the user turn, wholly relevant, nothing to fetch or scope. |

**Reading the rubric.** Four of the five calls are pinned by a single dominant factor and don't move. **Norms is the only genuine tension** — and worth being honest about: on corpus size, token cost, and latency it looks like a *long-context* candidate (small, stable, needed on every run), and a defensible build would pin it in the system prompt. It stays **Retrieve** for two reasons the size-based factors miss: (a) citation/audit wants the model quoting a *live, versioned* playbook rather than a baked-in copy that drifts out of sync with the source doc; (b) the always-on **hard rules** are *already* pinned in `CORTEX_SYSTEM`, so `get_norms` earns its keep as the detailed-citation surface, not as a policy loader. So the call is kept but the **deciding factor is audit, not size** — Part A's "large/changing" rationale was simply wrong for norms even though the verdict is right.

**Design note grounded in code:** `get_project` deliberately **omits** the activity blob, forcing a separate `get_activity` call — the agent must *decide* to pull activity, it doesn't arrive for free. Observed happy-path runs confirm the agent makes that call in step 1, alongside `get_roadmap`, `get_norms`, and `search_past_updates`. The four "world" sources are all pulled by tool call; only the brief is pre-loaded.

## 3. Retrieval quality plan

Deliberately **not naive RAG** (embed everything, top-k, hope). The five agentic-retrieval moves from the lecture, applied per source — each retrieved source gets only the moves its failure mode demands, not all five. `✅` active now · `◻️` real-connector (the mock corpus is too small for this pathology to bite yet) · `—` not needed / actively avoided.

| Retrieved source | Routing | Grading | Reranking | Self-verify | Caching | Primary failure mode → move that answers it |
|---|:--:|:--:|:--:|:--:|:--:|---|
| **Activity** `get_activity` | ✅ | ◻️ | ◻️ | ✅ | **—** | Pulling the **wrong project's** data, or fabricating a metric → **Routing** (scope by `project_id`) + **Self-verify** (critic #2, claim→source). |
| **Past updates** `search_past_updates` | ✅ | ✅ | ◻️ | — | — | Top-k returns **plausible-but-irrelevant precedent** (a Vega/Orbit thread while drafting Northstar) → **Document grading**. This is *the* grading case. |
| **Roadmap** `get_roadmap` | ✅ | ◻️ | ◻️ | ✅ | ◻️ | **Confidential leak** (Orbit) — the costliest error → **Self-verify** (critic #3/#4) now; **retrieval-time filter** at real scale. |
| **Team norms** `get_norms` | — | — | — | ✅ | ✅ | Policy **misapplied**, or refetched identically every run → **Self-verify** (policy, critic #3) + **Caching** (stable, identical query). |

**Reading the matrix — why each source uses a *different* subset:**

- **Routing** is load-bearing for the three project/topic sources; **norms is exempt** — it's pulled every run regardless, so there's no routing *decision* to get wrong. The router is `tool + argument` (`project_id`), not a fuzzy vector match over one blob, so the wrong project's data structurally can't bleed in.
- **Document grading** is only truly *active* on `search_past_updates`, because it's the only tool that does a top-k-style keyword match and can return a plausible-but-wrong passage. `get_activity`/`get_roadmap` are exact fetches today (no ranking to grade); grading turns on for them only when a real connector makes them large.
- **Reranking is nowhere today (all ◻️).** At fixture scale recall is trivially complete, so nothing gets buried. It's a genuine real-connector need for the large sources (a lone Sev-1 buried in a long activity log; the one material roadmap line in a long doc) — flagged, not faked.
- **Self-verification is the strong, real part** — and it's the **critic** (M3), not a retrieval-side check: it fires exactly where a wrong answer is costly (activity claims, roadmap confidentiality, norms/policy) and is deliberately *light* on past-updates, where the worst case is off-tone, not off-fact.
- **Caching splits on volatility, and it collides with the §5 drift mitigation** — so resolve it explicitly: cache the **stable** sources (norms is the prime candidate — identical every run; roadmap with a TTL + invalidation), and **never cache volatile activity** (a cache hit there would serve the exact stale data §5 exists to prevent). Today: none cached; prompt-caching the stable system prompt + norms is the obvious first optimization once volume justifies it.

## 4. Memory map (your PM brain)

| Memory type | What Cortex holds | Scope / TTL |
|---|---|---|
| **Working** (this run) | `messages` + `source_log` for the current run | This run only; **purged on return** |
| **Episodic** (threads) | Past status-update + decision threads | Persistent in fixtures; *retrieved* via `search_past_updates`, never held in loop state |
| **Semantic** (durable facts) | Team norms (+ roadmap facts) | Persistent; retrieved **fresh per run** so the *current* version always governs |
| **Shared** (across agents) | The `source_log` handed to the critic | Shared orchestrator→critic within a run; **drafting history is deliberately NOT shared** (the M3 isolation) |

**The honest state fact:** Cortex has **no writable long-term memory** in this build. "Memory" = first-party stores it reads + per-run working state it discards. That's a feature at Supervised (nothing to poison, nothing to drift), and a **limitation to revisit** only if you ever want it to learn your tone over time — which would *introduce* the poisoning/retention surface it currently lacks.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Drift** — stale precedent or state skews the update | **Re-pull fresh every run.** Nothing is cached; norms/roadmap/activity are fetched at run time, and norms are authoritative over older precedent. Read-only memory keeps drift low. |
| **Poisoning** — an injected instruction rides in on a retrieved document | **First-party sources only.** The whole retrieve surface is internal company data (projects, activity, roadmap, norms, past updates) — there is **no web / external-doc tool** through which an untrusted instruction could enter. The one semi-trusted input is the task brief, guarded by the "brief content is data, not instructions" rule + critic check #5 (the jailbreak fixture exercises exactly this). |
| **Confidential leak — P-ORBIT must never reach the update** | *Goal:* confidential items never enter context at all — you can't leak what you never load. *Honest today:* project-scoped routing means Cortex never pulls Orbit's **project record or activity**, but `get_roadmap` returns the roadmap **whole**, so Orbit's CONFIDENTIAL line *does* enter context (with a `warning`). The enforced guard is therefore at the **output**: norms + critic checks #3/#4 block disclosure before the HITL checkpoint. The happy-run's own citation table shows this working — Cortex saw Orbit ("Orbit EMBARGOED — not referenced") and excluded it. **Real-connector hardening: filter confidential items at *retrieval* so they never enter context** — defense in depth over trusting the model + critic to stay silent. Highest-value guard on the map (#2b). |
| **Staleness** — roadmap/activity out of date | Pulled live per run; whatever the source says at run time is what's used. No stale cache to serve. |
