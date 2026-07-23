# Build Insights: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 4, what you learned building it

## Friction

**The hard part wasn't the code — it was the design under uncertainty.** Building an agent gets complicated fast the moment it touches many data sources and many tasks that carry *different levels of confidentiality and sensitivity*. Each new source and each new task widens the blast radius, so the real work is up front and conceptual: **defining the bounds, anticipating the failure modes, and engineering so a confused or adversarial run cannot make an irreversible mistake.** Writing the loop is an afternoon; deciding what the loop must *never* do is the project.

Two concrete frictions made that tangible:

- **Provider port, with a silent-failure trap.** The starter shipped for OpenAI but my run target was Anthropic. Porting meant reworking the tool-call format, the system-message placement, and the token-accounting fields — small mismatches, except the token-accounting one would have *silently* broken cost tracking. And cost tracking isn't a nicety here; it's one of the safety bounds (`COST_CAP_USD`). A quiet break in a bound is worse than a loud crash.
- **Plumbing, not reasoning, was the real gate.** What actually blocked "run the agent" wasn't agent design — it was environment plumbing: dependencies in a venv, a valid key, and later a github.com credential wall. My honest estimate: for a first agent, well over half the elapsed time to a working run went to plumbing and configuration, not to the interesting design decisions. Worth planning for — the clever part is a smaller slice of the work than it looks.

## Learning

**I shipped at the lowest useful trust rung first, and made the climb conditional on evidence.** I chose to launch Cortex at **Supervised** — a human reviews every output before anything commits — so I could confirm it behaves as expected before widening its reach. Promotion to **Bounded-autonomous** comes only once that confidence is earned through evals, not on a schedule.

**I made my risk assumption explicit, because it's what justified the controls I chose.** I assumed Cortex is **one of several channels** feeding leadership, and that any information leak would stay **internal** — so a wrong call is recoverable, not catastrophic. That single assumption is what made a lighter-touch control set defensible instead of reckless.

> *Boundary condition (editorial note): this assumption is load-bearing — the light controls stop being defensible the moment Cortex becomes the sole channel to leadership or begins touching externally-sensitive material. Worth re-checking before any autonomy increase.*

**Start small, then widen — scope is the control you have most leverage over.** The most useful design decision I made was to build a *small* agent first: few tasks, few data sources, all reads local. That is what kept the agent controllable while I was still learning how it behaved — a narrow surface means fewer failure modes to anticipate and a blast radius small enough to reason about completely. The plan is to *expand deliberately* from there — more data sources, then more sensitive and higher-stakes tasks — each expansion earned by evidence, not assumed. This isn't just a build tactic; it's the same logic as the Trust Ladder (`governance-and-strategy.md`): widen reach only after the smaller version has proven it behaves. Confidentiality was the case that proved the point — the moment tasks vary in sensitivity, you can no longer treat "what data can it touch" as one undifferentiated decision.

## Aha moment

**Separating confidentiality into its own line item — instead of averaging it into "which context is relevant" — was what let me size its true impact.** It is the one place the agent could originate hard-to-reverse harm, and folding it into a broader "context" decision would have hidden that risk behind a comfortable average. The granularity of the decomposition is what made the real risk *visible* — and visible is the precondition for controllable.

## What you'd do differently

- **Build the labeled eval harness early.** Three fixtures prove the loop *runs*, but they can't prove a *rate* — and the rate (critic false-pass, leak rate) is what gates every trust decision. I treated it as M5→M6 work; it should have been there from the first real run so the thresholds were measured, not estimated.
- **Add a wall-clock timeout from day one.** The current loop has none — it's safe only because the tools are local mock reads. That dormant risk becomes live the instant a real connector can hang, and "add it later" is exactly the kind of thing that gets skipped under deadline. Cheap to add early, easy to forget late.
- **Treat monitoring as a first-class feature, not an afterthought.** Once an agent runs unattended, being able to *see it's healthy without reading logs* — outcome per run, cost vs. cap, escalation rate, leak events — matters as much as the loop itself. I specced this properly only at M6 (`governance-and-strategy.md`); a blind agent in production is an incident waiting to happen, and I'd wire the instrumentation in alongside the first bound next time, not after.
- **Stress-test adversarially, and keep doing it as the threat model grows.** The jailbreak fixture (`00-build/m5-jailbreak-run.txt`) was the highest-signal test I built — a pasted "SYSTEM OVERRIDE" that Cortex refused *structurally* (no publish tool to satisfy it). But one injection fixture isn't a security posture. As agents touch more real, sensitive data, the cyber-security surface — prompt injection, data exfiltration, credential misuse — grows faster than the feature surface, so adversarial stress-testing has to be continuous and expanding, not a one-time checkbox. I'd invest in a larger red-team suite well before granting any write access or widening data scope.
- **Decide up front whether this agent should climb the Trust Ladder at all.** A low-volume, high-visibility weekly update may be a deliberate *forever-Supervised* case. Naming that as a real option early — rather than assuming every agent is on a path to autonomy — is a stronger governance stance than defaulting to a climb and then arguing your way out of it.
