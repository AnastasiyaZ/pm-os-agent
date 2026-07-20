# Agent Line Map: Cortex PM Chief-of-Staff Agent

> Module 1 · The Agent Line
> Scored against the happy-path run (`python agent.py happy`, run cost a few cents, critic verdict *pass*). Every unit below maps to an observed point in that trace or a line in `agent.py` / `critic.py`.

## The agent in one sentence

Cortex turns raw project state (activity, roadmap, past updates, norms) into a **drafted** leadership status update and a **queued** backlog proposal for a human to clear — it drafts and judges below the line, everything that *commits* stays above it, and it *stops* on machinery, not on the model deciding it's done.

## How to read the scores (polarity — the axes don't point the same way)

- **Reversibility** — High = *good* (easy to undo).
- **Blast radius** — High = *bad* (more damage before someone catches it).
- **Measurability** — High = *good* (we can tell after the fact whether it was right).

An ideal below-the-line decision reads **H · L · H**. The danger cells are **Low reversibility, High blast, or Low measurability** — that is where controls have to sit.

## The workflow, decision by decision

Below the line there are **three different kinds** of "decision," and conflating them is the classic M1 error: **generative judgment** (the agent drafts/decides), **automated control** (an independent check), and **machinery bound** (deterministic code that trips outside the model). Only #8 is above the line — human authority.

| # | Decision / action | Reversibility | Blast radius | Measurability | Above / Below | HITL? |
|---|---|---|---|---|---|---|
| 1 | Pull project state + recent GitHub/Jira activity | H | L | H | Below | · |
| 2 | Decide which past updates / context are relevant | H | L | M | Below | · |
| 2b | **Confidentiality judgment** (shareable vs. embargoed) | L raw / H realized | M | H | Below *(for now)* | spot-check |
| 3 | Classify status / flag at-risk (green / yellow / red) | H | M | M | Below | review |
| 4 | Draft at a chosen commitment level (**the date-promise**) | H ‡ | H | H | Below | review |
| 5 | Propose the story batch (count, justification, queue) | H | L | M | Below | required |
| 6 | Independent critic pass / fail verdict | M | M | H | Below · **control** | n/a |
| 7 | Revise-or-escalate (revision cap, cost cap, max iters) | H | L | H | **Machinery** | n/a |
| 8 | Post / approve a company-wide update | L | H | H | **Above** | required |

‡ #4 reversibility is High *only while it is a draft*; it collapses to Low the instant it is posted — its reversibility is contingent on the gates downstream (#6, #8) holding.

## Justification, line by line

1. **Pull state / activity** — Read-only and re-runnable, so a wrong pull costs nothing and is verifiable against source; nothing to gate.
2. **Relevant context / precedent** — Worst case is an ugly-but-harmless draft the human sees before it commits, so judgment stays with the agent.
2b. **Confidentiality** — The one below-line call that is *raw*-irreversible (you cannot unleak), which earns it its own row; Supervised human review makes the *realized* risk recoverable, so it stays below the line **for now**.
3. **Status classification** — A false-green is independently caught by dashboards and standups (status is one of several channels), so blast stays Med and no dedicated check is warranted.
4. **Date-promise / commitment level** — Highest-blast generative act (a committed date propagates into others' planning), but it is still a draft with the critic *and* the human behind it, so two gates justify keeping it below.
5. **Propose story batch** — Queue-only and capped at 10; it structurally *cannot* create tracker items, so the worst case is a few junk stories a human rejects.
6. **Critic verdict** — Advisory at Supervised (the human is the real gate), so a false-pass is recoverable — which is exactly why it is a check, not the final authority.
7. **Revise-or-escalate** — A deterministic bound that fails safe (halts / escalates, commits nothing) regardless of rung, so it is machinery outside the model, not a judgment.
8. **Post / approve company-wide** — The only irreversible, widest-audience commitment, so it must stay human — and by design no publish tool exists to tempt otherwise.

## Design decisions (and the ones I deliberately declined)

M5 will ask you to defend not just the bounds you added but the ones you *chose not to*. All four are conditional on the **Supervised** rung.

| Decision | Verdict | One-line justification |
|---|---|---|
| Split confidentiality into its own row (#2b) | **Do** | Averaging it into #2 hid the single worst irreversible failure the agent can *originate*; splitting it surfaces the risk at zero cost. |
| Reframe the HITL checkpoint as *advisory*, not "validated ✓" | **Do** | At Supervised the human is the gate, so a badge that invites rubber-stamping — not the critic itself — is the real failure mode. |
| Add a second independent critic | **Don't** *(yet)* | Redundant with the inline human at Supervised and doubles critic cost; justifying a bound you *declined* is stronger calibration than adding it reflexively. |
| Add a structural confidentiality wall | **Don't** *(yet)* | The leak severity here is internal-and-recoverable, making a wall over-engineering; reserve that pattern for MNPI or external-facing updates. |

## What changes at Bounded-autonomous (the climb gate)

The planned climb to **Bounded-autonomous** is a single event: the human stops being the *inline gate* and becomes an *out-of-line auditor*. Every control I declined above is safe **only because** the human occupies the inline seat — so both "Don't"s flip to "Do" on the climb. The climb is gated on **evidence, not calendar**:

- A **labeled eval harness** (the three fixtures demo the loop; they cannot certify a *rate* — that needs a few dozen labeled cases). This is itself the M5 trajectory-evals deliverable.
- **Critic false-pass rate** below threshold (starting bar ≈ ≤5% on seeded known-bad drafts — *low confidence on the exact number*; it should be tighter for the High-blast date-promise mode than for a recoverable leak).
- **Confidentiality leak rate = 0** on tasks seeded with embargoed items, backed by a dedicated pre-publish confidentiality scan (#2b moves above the line or gains its own gate).
- **#8 (company-wide post) stays human even at Bounded** — a weekly leadership update is low-volume and high-visibility, exactly the artifact where removing the human gate saves little and exposes much.

## Agent anatomy

- **Model:** `claude-sonnet-4-6` (env-default, ~$3 / $15 per 1M in/out). **No frontier escalation** — drafter and critic run the *same* model; the critic's independence comes from **context isolation** (it never sees the drafting messages), not a bigger model.
- **Tools:** `get_project` · `get_activity` · `search_past_updates` · `get_roadmap` · `get_norms` (all **read-only**) + `propose_stories` (**capped at 10, queue-only, creates nothing**). **There is no publish/write tool — by design.**
- **Memory:** the roadmap, team norms, and past updates are the persistent "PM brain," retrieved per run via tools; nothing is written back. The per-run message loop is purged each run.
- **Loop:** observed shape is read → draft → independent critic → revise (≤2) → HITL checkpoint. Full spec in `02-loop-design/loop-spec.md`.
- **Bounds:** `MAX_ITERATIONS=8` · `MAX_REVISIONS=2` · `COST_CAP_USD=0.50` · `MAX_QUEUE_ITEMS=10`, all enforced **outside the model**. Justification in `05-bounds-evals/bounds-and-evals.md`.
- **Evals:** three fixtures today (happy / missing-data / jailbreak) exercise the loop; a labeled harness for *rates* is the climb prerequisite. See `05-bounds-evals/bounds-and-evals.md`.

## The golden rule, applied

- **#8 Post / approve company-wide** stays human because it fails the cheap-to-undo test on the axis that matters most: **reversibility is Low** (you cannot un-send to leadership) and **blast is High** (widest audience, real commitments). It is highly measurable after the fact — but the measurement arrives too late to prevent the harm, which is precisely why the gate must be *before* the act, not after.

## Hardest call

**#2b, confidentiality.** It is the only decision on the map that is *raw*-irreversible — you cannot unleak an embargoed roadmap item — yet I placed it **below** the line. The resolution: at the Supervised rung the human review is an inline gate that makes the *realized* risk recoverable, and the leak severity here is internal-and-recoverable rather than market-moving. That placement is explicitly **conditional**: it is the first unit that moves above the line the moment the leak severity rises (MNPI / external reach) or the human leaves the inline seat at Bounded-autonomous. I'm flagging it as the map's most fragile call rather than hiding it in an averaged score — which is exactly what the starter decomposition did.
