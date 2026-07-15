# Build Insights: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 4, what you learned building it
>
> ⚠️ **This deliverable is your reflection — it must be in your voice.** Below is *factual scaffolding* from the build session (things that verifiably happened), provided as raw material. Replace the prompts with your own words before submitting; a grader wants your judgment, not a transcript.

## Friction

_Where did the build fight you? (Loop stop conditions? Context budget? The validator? Bounds?)_

Factual events from the build you can draw on:
- **The starter shipped for OpenAI; the run target was Anthropic.** Porting `agent.py` + `critic.py` meant swapping `chat.completions` → `messages`, `tool` role → `tool_result` blocks, `system` message → top-level `system=`, and the token-field names (`prompt_tokens`/`completion_tokens` → `input_tokens`/`output_tokens`). Every one of those is a place the cost accounting or the loop would silently break if missed.
- **Dependencies + credentials were the real gate, not the code.** The agent wouldn't run until deps were installed in a venv and a valid key was present; the push later hit a github.com credential wall (gh was authed to the corporate GHE only). _Your take: how much of "building an agent" is actually plumbing?_
- **A credential-materialization attempt was blocked by the harness** — a safety guardrail refused to print even a masked secret. _Your take on that as a governance signal._

## Learning

_The two or three things you now understand about shipping agents that you didn't before the course._

Candidate threads (make them yours):
- **The agent line is enforced in infrastructure, not in the prompt.** The single most load-bearing safety property of Cortex is a *tool that doesn't exist* (no `post_update`). A prompt saying "don't post" is a request; a missing tool is a wall.
- **Independence is contextual, not architectural.** The critic catches things because it never saw the drafting conversation — not because it's a smarter model. Cheap to build, and it's the difference between grading your own homework and a second reader.
- **Bounds are what make "stop" trustworthy.** The agent never *decides* it's done looping; a counter or a cap decides. That's what lets you sleep at night when it runs unattended.

## Aha moment

_The single insight that changed how you'd design your next agent._

Candidate (yours to confirm or reject): **the controls you *decline* to build are as much a design decision as the ones you add** — and they're only safe because of *where the human currently sits*. The moment the human moves from inline gate to out-of-line auditor, the declined controls become required. Autonomy isn't a slider on the agent; it's a statement about where the human is standing.

## What you'd do differently

_If you rebuilt Cortex from scratch, what changes?_

Grounded candidates (from real gaps found this build):
- Add a **wall-clock timeout** from day one (the current loop has none — safe only because tools are local mock reads).
- Fix the **cost cap's one-iteration overshoot** (checked at loop top, so a big call can exceed $0.50 before the next check).
- Build the **labeled eval harness** before writing more features — three fixtures prove the loop works but can't prove a *rate*, and the rate is what gates every trust decision.
- Decide up front whether this agent should climb the Trust Ladder **at all** — a low-volume, high-visibility weekly update may be a deliberate forever-Supervised case.
