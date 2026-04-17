# ADR-005: Design approval is the only mandatory human gate; uses session-break pattern

## Status

Accepted (April 2026, v1)

## Context

Pre-v1 had no enforced human gates under autopilot. Every approval was
"ask when ambiguous" — useless under autopilot mode, where the agent
auto-responds to its own questions.

We considered four positions on human gates:

a. **No gates.** Pure autonomy. Maximises velocity, maximises blast
   radius of a bad plan.
b. **Gate every transition.** Maximises safety, kills velocity, pushes
   users to disable the system entirely.
c. **Gate at design plan, implementation plan, and phase review.** Three
   gates per phase. Manageable but interrupts flow.
d. **Gate only design plan approval.** One gate at the highest-leverage
   point. Implementation plan and phase review run autonomously with
   audit logging.

The empirical observation from Sentinel: a wrong design plan wastes the
entire phase. A suboptimal implementation plan or a missed strategic
review wastes a slice or two. The **design plan is uniquely high-leverage**.

A second question: how to actually *implement* a human gate. Options:

- **Modal approval** via `vscode_askQuestions`. Works in interactive
  sessions. Times out under Copilot CLI. Auto-responds under autopilot.
- **Session break.** The agent transitions to `Stage: blocked` with a
  specific `Blocked Kind`, the Stop hook allows session end, the human
  reviews the artifact, then runs `/resume` in a fresh session.

## Decision

Design plan approval is the **only mandatory human gate**, and it is
implemented as a **session break**, not a modal approval.

Mechanics:

1. After `design-critique` reaches `Design Status: approved`, the builder
   sets `Stage: blocked`, `Blocked Kind: awaiting-design-approval`, and
   `Blocked Reason: "Design approved — run /resume to advance."`
2. The Stop hook allows session end *because* `Blocked Kind` is set to a
   valid value.
3. The human reviews `roadmap/phases/phase-N-design.md`.
4. In a fresh session, the human runs `/resume`. The prompt routes on
   `Blocked Kind`:
   - `awaiting-design-approval` → advance to `implementation-planning`.
   - `awaiting-vision-update` → run `/vision-expand`.
   - `awaiting-human-decision` → present the recorded question to the
     human.
   - `error` → diagnose and unblock.
   - `vision-exhausted` → run `/vision-expand` for a new vision.

Implementation plan approval and phase review run **autonomously with
mandatory logging**: under autopilot the builder self-approves and
records the decision in the session log; under manual mode the prompt
asks the human.

## Consequences

### Positive
- Design errors are caught at the cheapest possible point.
- Session break is robust under autopilot, Copilot CLI, and interactive
  modes alike — there's no modal to time out or auto-respond to.
- The new session starts fresh, avoiding context saturation from a long
  planning session.
- The human always has artifacts to review (the design plan + critique
  rounds), not a one-line modal prompt.

### Negative
- Round-trips a session for every design approval. For a 1-day phase
  this is one extra session-start; for a 1-hour phase it doubles the
  number of sessions.
- The human must remember to run `/resume`. Mitigation: the
  `Blocked Reason` field always names the next action, and the
  `/resume` prompt is the single entry point for all unblock paths.

### Neutral
- The `Blocked Kind` vocabulary is a finite set enforced by the Stop
  hook (it refuses to allow stop with an unknown or empty Blocked Kind).
  This prevents an agent from declaring `Stage: blocked` with no
  explanation as a Stop-hook bypass.
- "Design = session break, rest = autonomous" was the riskiest decision
  of the v1 redesign. Reversal cost is low (re-enable a gate by editing
  one prompt + one hook check).
