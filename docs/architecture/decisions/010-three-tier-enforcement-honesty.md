# ADR-010: Three-tier enforcement vocabulary

## Status

Accepted (April 2026, v1)

## Context

Pre-v1 used the word "enforced" loosely. Prose instructions, catalog
items, and a single Stop hook were all described with the same verbs
("must", "required", "blocked"). This created two problems:

1. **Users trusted unenforceable claims.** "Reviewer must be invoked on
   changed files" sounded like a hard rule, but no hook checked it. Users
   were surprised when the agent skipped the reviewer.
2. **Engineers couldn't tell which rules were load-bearing.** When
   refactoring an agent prompt, it was unclear whether removing a
   "must" sentence would break enforcement or just remove a guideline.

## Decision

Adopt a three-tier vocabulary, used consistently in `copilot-instructions.md`,
`AGENTS.md`, and prompt frontmatter:

### Tier 1 — Deterministic (hook-verified)

Rules a hook can mechanically check. Failure to comply produces a hook
denial with a specific reason.

Examples:
- Cannot edit source code outside `executing` stage (PreToolUse
  `stage-gate.py`).
- Cannot stop session with incomplete Slice Evidence (Stop
  `session-gate.py`).
- Cannot return from critic without writing a verdict and an artifact
  (SubagentStop `subagent-verdict-check.py`).
- Cannot `git push --force` or delete `roadmap/state.md` (PreToolUse
  `tool-guardrails.py`).

These rules are **the contract**. Documentation must accurately describe
what the hook checks; if the doc and the hook disagree, the hook is
right.

### Tier 2 — Strongly guided (instruction-level, artifact-verified)

Rules where a hook verifies that an artifact exists or a field is set,
but cannot verify the **quality** of the artifact.

Examples:
- Critique quality (the hook verifies the critique file exists, not
  whether the critique is rigorous).
- Test coverage adequacy (the hook verifies `Tests Pass: yes`, not what
  the tests cover).
- Strategic-review thoroughness (the hook verifies `Strategic Review`
  is terminal, not whether it was actually thorough).
- Doc-sync completeness (the hook verifies the checklist box is checked,
  not whether the docs are accurate).

These rules rely on the agent's good faith. They are bounded by Tier 1
gates (a Tier 2 lie still has to satisfy Tier 1 enforcement to ship).

### Tier 3 — Advisory (pure instructions)

Rules that exist only as guidance in agent prompts. No hook enforcement,
no artifact requirement.

Examples:
- Code style and conventions.
- Commit message format.
- When to use subagents vs. inline tools.
- Error recovery strategy.

These are **suggestions**. An agent that ignores them won't be blocked
by any hook.

## Consequences

### Positive
- Documentation can honestly describe what each rule guarantees.
- Engineers reviewing changes can identify which tier a rule belongs to
  and choose the right enforcement mechanism.
- Users have a calibrated expectation: Tier 1 is mechanical, Tier 2 needs
  a culture of agent diligence, Tier 3 is taste.

### Negative
- Three tiers is more vocabulary to teach.
- Some rules are at a tier boundary (e.g., "the reviewer must be invoked
  on every slice" — Tier 1 enforced by `session-gate.py`'s
  `Reviewer Invoked: yes` check, but Tier 2 for "the reviewer must
  actually look at the diff").

### Neutral
- The tier label is most visible in the generated project's
  `.github/copilot-instructions.md`. Agents reading it learn which
  promises they can rely on.
- Future ADRs that introduce new rules should declare the tier in their
  Decision section.
