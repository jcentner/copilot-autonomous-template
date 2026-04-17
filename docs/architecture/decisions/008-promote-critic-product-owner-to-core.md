# ADR-008: Promote critic and product-owner from catalog to core

## Status

Accepted (April 2026, v1)

## Context

Pre-v1 had `critic` and `product-owner` as catalog agents activated by
heuristic ("5+ slices in this phase → activate critic"). The heuristic
almost never fired; the catalog activation step itself was advisory and
often skipped.

Both agents address failure modes that are **universal**, not
project-specific:

- The critic catches planning errors (scope creep, infeasibility, missing
  edge cases). Every plan benefits from adversarial review.
- The product-owner writes user stories and acceptance criteria, then
  validates that what was built achieves what was designed. Every phase
  benefits from "did we build the right thing?"

The catalog model is appropriate for **conditional capabilities**:
`designer` only matters with a UI, `security-reviewer` only matters with
auth/PII/payments. Critic and product-owner are not conditional.

## Decision

Promote `critic` and `product-owner` from `.github/catalog/agents/` to
`.github/agents/`. They are core agents shipped in every generated
project. Their lifecycle hooks (`subagent-verdict-check.py` for both)
are core hooks.

The critic operates in two modes selected by `Stage`:

- `design-critique`: review the design plan; emit `Design Status` and
  the round artifact `phase-N-critique-design-RM.md`.
- `implementation-critique`: review the implementation plan; emit
  `Implementation Status` and `phase-N-critique-implementation-RM.md`.

The product-owner operates in two modes:

- **Design mode** (during `design-critique`): write user stories and
  acceptance criteria into the design plan. Emits no verdict — the
  critic owns the verdict for the design stage.
- **Review mode** (during `reviewing`): strategic validation. Emits
  `Strategic Review` (`pass`, `replan`, or `n/a`) and
  `phase-N-strategic-review.md`.

Catalog still exists for genuinely-conditional agents (`designer`,
`security-reviewer`).

## Consequences

### Positive
- Every phase gets adversarial planning review and user-story validation
  by default. The most-leverage failure modes are addressed without
  configuration.
- The SubagentStop hook can hard-require these agents because they're
  always present.

### Negative
- The default footprint is larger. Projects that genuinely don't want
  these agents must explicitly waive them per-phase (`Design Status:
  waived`, `Strategic Review: n/a`).
- Two agents in two modes each is more cognitive load than two agents
  in one mode. The prompt for each agent has to dispatch on `Stage`.

### Neutral
- The `reviewer` agent stays focused on **code quality** (architecture,
  security, conventions, doc-sync). Strategic review is the
  product-owner's job. This split was muddled in pre-v1; v1 makes it
  explicit.
- The catalog still owns `designer` and `security-reviewer`, plus four
  skills (deep-interview, anti-slop, design-system, ci-verification),
  one hook (ci-gate), two prompts, and two patterns.
