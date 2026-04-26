# ADR-012: Slice loop owned by `slice-runner` subagent, not the orchestrator

## Status

Accepted (April 2026, v1)

## Context

Through v1.3, the autonomous-builder agent file was 262 lines. About 80 of
those were a 9-step inline "slice loop" the orchestrator was supposed to
execute on every slice during `Stage: executing`: invoke tester, implement,
run tests, runtime check, invoke reviewer, fix findings, commit, stamp
evidence, advance Active Slice. The same loop was duplicated in
`.github/prompts/implement.prompt.md`, with a header note saying "if the
two ever disagree, the builder agent is authoritative" — i.e., we'd
already accepted that the duplication would drift.

Empirically (April 2026, on the wyoclear v1.3 work), the orchestrator
behaved less like a coordinator and more like an everything-agent. It
would lose the plot mid-loop, eyeball verdicts instead of running
`record-verdict.py`, and try to write fields the helpers were supposed to
own. The hooks caught those drifts, which made the agent feel "blocked"
when it was really being routed back from a wrong move.

The VS Code subagents docs document a "Coordinator and worker pattern"
where the coordinator's body is **a few lines of high-level steps**, each
one a subagent dispatch. Our orchestrator was nowhere near that shape.

## Decision

Extract the entire 9-step slice loop into a new subagent at
[.github/agents/slice-runner.agent.md](../../template/.github/agents/slice-runner.agent.md.jinja).
The orchestrator's `executing` behavior becomes:

1. While `Active Slice <= Slice Total`: dispatch `slice-runner` with the
   slice number.
2. After the final slice: `write-stage.py reviewing --next-prompt
   /strategic-review`.

`slice-runner` owns: tester dispatch, implementation, runtime check,
reviewer dispatch, fix-and-recommit, commit + evidence stamping,
slice-evidence reset, error recovery, escalation to `Stage: blocked` on
unrecoverable failure or `needs-rework` verdict.

`slice-runner` is `user-invocable: false` — it is only meaningful when
dispatched by the orchestrator (or by `/implement` as a manual override).

The `/implement` prompt becomes a thin wrapper that dispatches
`slice-runner`. It explicitly forbids re-implementing any of the 9 steps
inline.

## Consequences

### Positive

- Orchestrator's per-slice context drops from ~10–30k tokens (the loop's
  own tool calls + tester + reviewer activity inline) to a
  single subagent-call summary. Real win for long phases.
- Single source of truth for the slice contract. The `/implement` prompt
  no longer maintains a parallel copy.
- Existing per-subagent verification (`subagent-verdict-check.py
  reviewer` / `tester-isolation.py` / `write-commit-evidence.py`) still
  fires unchanged — `slice-runner` dispatches those subagents with the
  same machinery the orchestrator used to.

### Negative

- **Requires `chat.subagents.allowInvocationsFromSubagents: true`.**
  Default is `false`. Without it, every slice fails at the
  tester/reviewer dispatch (depth 2). BOOTSTRAP.md Step 4.5 prompts the
  human; an executing session with the setting off will produce a
  consistent failure mode, not silent corruption.
- Nesting depth used: 2 (orchestrator → slice-runner → tester/reviewer).
  Well within VS Code's documented max of 5, but constrains future
  sub-delegations from `tester` or `reviewer`.
- No `subagent-verdict-check.py slice-runner` rule yet. The contract is
  enforced in aggregate by existing hooks: `tester-isolation` /
  `subagent-verdict-check.py reviewer` (during the dispatched
  sub-subagents), `write-commit-evidence.py` (refuses dirty tree), and
  `session-gate.py` (refuses Stop with incomplete Slice Evidence). If
  drift emerges (e.g., slice-runner returning without advancing
  `Active Slice` and the orchestrator silently looping forever), add a
  dedicated check at that point. Speculative addition was deliberately
  declined.

### Neutral

- Orchestrator file shrinks by ~80 lines. Not the main goal — the main
  goal was real coordination — but a useful side effect.
- Branch-hygiene table, blocked-kind vocabulary, and stage dispatch table
  remain in the orchestrator. Those are coordination concerns, not slice
  execution. Further extraction (e.g., critique stages → dedicated
  subagents) is a separate decision.

## Alternatives considered

1. **Extract stage runbooks into prompt files.** Initial proposal, but
   the live VS Code docs ([prompt-files](https://code.visualstudio.com/docs/copilot/customization/prompt-files),
   retrieved 2026-04-26) state prompts are "invoked manually in chat" —
   there is no documented mechanism for an agent's reasoning loop to
   invoke a prompt and resume. Subagents are the only documented
   delegation primitive that returns control to the caller.
2. **Slim the orchestrator without adding a subagent** (delete duplicated
   prose only). Saves ~30 lines, doesn't address the underlying
   "agent does too much directly" problem, and doesn't reclaim per-slice
   context. Rejected as cosmetic.
3. **Split slice-runner into "mechanical-only" + leave tester/reviewer on
   the orchestrator.** Avoids the nesting setting requirement, but
   captures almost no context win — the heaviest per-slice activity is
   tester (writes test files) and reviewer (reads/searches widely).
   Rejected.

## References

- [Subagents (VS Code docs)](https://code.visualstudio.com/docs/copilot/agents/subagents) — Coordinator/worker pattern, nested subagents, `chat.subagents.allowInvocationsFromSubagents` setting.
- [ADR-003](003-agents-write-state-hooks-verify.md) — reviewer is the sole writer of `Review Verdict` etc.; slice-runner inherits this contract for the dispatched reviewer.
- [ADR-008](008-promote-critic-product-owner-to-core.md) — precedent for promoting workflow capabilities from catalog to core.
