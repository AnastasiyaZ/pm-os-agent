# Build Insights: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 4, what you learned building it

## Friction

> ⚠️ *Scaffolding — needs your voice. Factual raw material from the build below.*

- The starter shipped for OpenAI but the run target was Anthropic; porting the loop meant reworking the tool-call format, the system-message placement, and the token-accounting fields — small mismatches that would have silently broken cost tracking.
- The real gate on "running the agent" wasn't the code — it was environment plumbing: dependencies in a venv, a valid key, and later a github.com credential wall. _Your take: how much of shipping an agent is actually plumbing?_

## Learning

**I shipped at the lowest useful trust rung first, and made the climb conditional on evidence.** I chose to launch Cortex at **Supervised** — a human reviews every output before anything commits — so I could confirm it behaves as expected before widening its reach. Promotion to **Bounded-autonomous** comes only once that confidence is earned through evals, not on a schedule.

**I made my risk assumption explicit, because it's what justified the controls I chose.** I assumed Cortex is **one of several channels** feeding leadership, and that any information leak would stay **internal** — so a wrong call is recoverable, not catastrophic. That single assumption is what made a lighter-touch control set defensible instead of reckless.

> *Boundary condition (editorial note): this assumption is load-bearing — the light controls stop being defensible the moment Cortex becomes the sole channel to leadership or begins touching externally-sensitive material. Worth re-checking before any autonomy increase.*

## Aha moment

**Separating confidentiality into its own line item — instead of averaging it into "which context is relevant" — was what let me size its true impact.** It is the one place the agent could originate hard-to-reverse harm, and folding it into a broader "context" decision would have hidden that risk behind a comfortable average. The granularity of the decomposition is what made the real risk *visible* — and visible is the precondition for controllable.

## What you'd do differently

> ⚠️ *Scaffolding — needs your voice. Grounded candidates from real gaps found during the build below.*

- Build the **labeled eval harness early** — three fixtures prove the loop runs, but they can't prove a *rate*, and the rate is what gates every trust decision.
- Add a **wall-clock timeout** from day one (the current loop has none — safe only because the tools are local mock reads).
- Decide up front whether this agent should climb the Trust Ladder **at all** — a low-volume, high-visibility weekly update may be a deliberate forever-Supervised case.
