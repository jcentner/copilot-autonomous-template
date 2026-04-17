# ADR-004: Bounded critique loops with iterative planner ↔ critic rounds

## Status

Accepted (April 2026, v1)

## Context

The pre-v1 workflow went directly from "phase plan" to "implement". The
critic agent existed in the catalog with a heuristic activation rule
("activate when phase has 5+ slices") that almost never fired. Plans
shipped to implementation without independent challenge.

Empirically (across 20+ autonomous sessions on the predecessor project,
Sentinel), the highest-leverage failure mode was **planning errors**:
missing edge cases, scope creep, infeasible test strategies, ambiguous
acceptance criteria. Catching these after a slice was implemented cost
days of rework. Catching them before any code was written cost minutes.

A naive solution — always run the critic — has its own failure mode:
infinite revision loops where the critic finds something to flag every
time, and the planner tries to address it without ever shipping.

## Decision

Make critique a **mandatory bounded loop** with two distinct stages and
explicit round caps:

1. **`design-critique`** stage (after `planning`):
   - product-owner adds user stories + acceptance criteria.
   - critic challenges assumptions, scope, feasibility.
   - critic emits a verdict: `approved`, `revise`, or `rethink`, plus a
     critique artifact at `roadmap/phases/phase-N-critique-design-RM.md`.
   - On `revise`/`rethink`: planner revises, re-enter critique, increment
     `Design Critique Rounds`.
   - **Cap: 3 rounds.** If still not approved, stage transitions to
     `blocked` with `Blocked Kind: awaiting-human-decision`.

2. **`implementation-critique`** stage (after `implementation-planning`):
   - Same loop but for the implementation plan.
   - **Cap: 2 rounds.** Lower because implementation plans are more
     mechanical; if the critic still objects after two rounds, the design
     itself is suspect (escalate).

The cap is **bounded** because LLMs are bad at recognising "good enough":
without a hard limit, critique loops would run until the context window
filled. The cap is **multi-round** because real planning errors often
need a back-and-forth, not a single pass.

`subagent-verdict-check.py` enforces that:
- The critic must write a terminal `Design Status` / `Implementation
  Status`, increment the `Rounds` counter, and produce the round's
  artifact file before returning.
- The planner (when invoked for a revision) must produce the
  corresponding plan file before returning.

## Consequences

### Positive
- Planning errors surface before code is written, in the cheapest
  possible context.
- The critique trail (`phase-N-critique-design-R1.md`,
  `-R2.md`, ...) is a durable record of what was challenged and what
  was changed in response. Useful for post-mortems.
- The cap prevents indefinite loops without human override.

### Negative
- For trivial phases (a single-slice typo fix), the critique stages add
  ceremony. Mitigation: the critic can return `approved` on round 1 with
  a one-line artifact saying "trivial change, no risks identified".
- Caps are arbitrary. We picked 3/2 from the Sentinel-era experience;
  these may need tuning per project. They live as constants in the
  prompts (not the hooks), so projects can override per-phase by editing
  the prompt or recording a waiver in `state.md`.

### Neutral
- The product-owner is invoked alongside the critic during
  `design-critique` (writes user stories), but is invoked again during
  `reviewing` for strategic validation. Two distinct modes for the same
  agent — see ADR-008.
