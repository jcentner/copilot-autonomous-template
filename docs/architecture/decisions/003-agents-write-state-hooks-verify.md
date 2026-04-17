# ADR-003: Agents write state, hooks verify state

## Status

Accepted (April 2026, v1)

## Context

A natural design instinct is to have hooks **derive** workflow state from
observed tool calls — e.g., a PostToolUse hook scans `run_in_terminal`
output for "tests passed" and stamps `Tests Pass: yes` automatically.

We tried this in pre-v1's `evidence-tracker.py`. It led to:

- Brittle pattern-matching against test runner output (every framework
  has different exit messages, colorized output, paginated tail, etc.).
- Race conditions: the hook runs *after* the tool call but before the
  agent has interpreted the result. The agent might re-run, retry, or
  decide the failure is acceptable. The hook had no way to know.
- Silent disagreement: the agent's narrative said "tests pass" while the
  hook stamped `Tests Pass: no` because it saw a stderr line. There was
  no resolution rule.

The agent has the full context — it knows whether the test run is the
real one or an exploratory one, whether the failure is the slice it's
working on, etc. The hook does not.

## Decision

Establish the architectural principle:

> **Agents write workflow state. Hooks verify workflow state.**

Concretely:

1. **State writes** are performed by:
   - Agents (via prompts that explicitly instruct field updates).
   - The hook-internal helper `write-test-evidence.py` (an agent-invoked
     CLI utility, not a hook), which the agent runs after deciding the
     test result is final.
   - `_state_io.update_state_field()`, called from agent helper scripts.

2. **State verification** is performed by hooks:
   - `session-gate.py` (Stop): blocks stop when the current stage's
     gating fields aren't terminal.
   - `subagent-verdict-check.py` (SubagentStop): blocks subagent return
     when expected fields/artifacts are missing.
   - `stage-gate.py` (PreToolUse): denies edits to non-allowlisted paths
     based on `Stage`.

3. **Hooks may log** (via `evidence-tracker.py` writing to
   `roadmap/sessions/<id>.md`), but logging is observation, not state
   mutation. The session log is auditable history; it is not a source of
   truth for any gate.

`subagent-verdict-check.py` ties this together for subagent invocations:
the subagent's prompt tells it which fields to write before returning,
and the SubagentStop hook refuses to let it return until those fields
match the terminal vocabulary. The hook never tries to infer the verdict
from the subagent's output.

## Consequences

### Positive
- The state is always intentional. A field has a value because an agent
  decided to write it, not because a regex caught a substring.
- Hook code is simpler and more robust. `subagent-verdict-check.py` checks
  field membership against a fixed vocabulary; that's it.
- Disagreements are impossible by construction. The agent's claim and the
  recorded state are the same write.

### Negative
- Agents must remember to write state. If a prompt forgets to instruct a
  field update, the hook can block but cannot help recover. Mitigation:
  prompts list the exact fields to update in a numbered checklist;
  reviews of new prompts focus on this.
- The agent can lie. `Tests Pass: yes` written without running tests
  satisfies the hook. This is a Tier 1 vs Tier 2 distinction (ADR-010):
  the hook enforces *that* the field is set, not *that* the underlying
  reality matches.

### Neutral
- This shaped Bug-C's fix: `Evidence For Slice` binds the recorded
  evidence to the active slice number. If the agent increments
  `Active Slice` without re-running `write-test-evidence.py`, the Stop
  hook catches the staleness — still pure verification, no inference.
