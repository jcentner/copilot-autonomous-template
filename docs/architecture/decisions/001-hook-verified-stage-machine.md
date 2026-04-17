# ADR-001: Hook-verified stage machine replaces narrative checkpoints

## Status

Accepted (April 2026, v1)

## Context

The pre-v1 template (April 2026 internal) advertised a 9-step slice protocol enforced
by a Stop hook called `slice-gate.py`. In practice, that hook checked one
string in `CURRENT-STATE.md`:

```
**Phase Status**: Complete
```

If the agent set that string, the hook allowed stop. Nothing actually
verified that:

- A design plan had been written and approved.
- Tests had been run, much less passed.
- A reviewer had been invoked.
- Critical/Major findings had been resolved.
- The work had been committed.

Every other claim ("tests must pass before proceeding", "reviewer invoked
on changed files", "critic challenges plans") lived in prose instructions
inside agent or prompt markdown. LLMs follow the path of least resistance;
prose-only enforcement is effectively unenforced.

The Copilot hooks API exposes 8 lifecycle events
(`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`,
`PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`). The template
used exactly one (`Stop`). Everything else was advisory.

## Decision

Restructure the workflow as a **state machine** whose transitions are
**verified by hooks**, not by prose. The state is parsed from a
machine-readable file (`roadmap/state.md`, see ADR-002), and hooks at
`PreToolUse`, `PostToolUse`, `Stop`, and `SubagentStop` enforce that:

- Source-code edits are blocked outside the `executing` stage.
- Session stop is blocked when the current stage's gating fields are
  unsatisfied.
- Subagent return is blocked when expected artifacts are missing or
  verdict fields are not terminal.
- A small denylist of destructive operations is blocked unconditionally.

The stages are:

```
bootstrap → planning → design-critique → implementation-planning →
implementation-critique → executing → reviewing → cleanup →
(planning | complete | blocked)
```

`blocked` is a first-class stage with a required `Blocked Kind` field
(awaiting-design-approval, awaiting-vision-update, awaiting-human-decision,
error, vision-exhausted) so the agent cannot escape the Stop hook by
declaring an unexplained block.

## Consequences

### Positive
- Every advertised gate has a hook implementation that runs on the
  matching lifecycle event. The discrepancy between "what the docs say"
  and "what is enforced" is gone.
- The full enforcement layer is auditable in one directory
  (`.github/hooks/scripts/`) with stdlib-only Python — no runtime deps.
- Stage transitions are testable in isolation: each hook can be exercised
  with a JSON payload via `unittest`. The repo has 160+ tests covering
  the hooks.
- Failure modes are explicit. An unknown `Stage` value, an empty `Phase`,
  or a mismatched `Evidence For Slice` all cause the Stop / SubagentStop
  hook to block with a specific reason.

### Negative
- The hooks are now load-bearing. A bug in `session-gate.py` can wedge
  every Copilot session in the workspace. Mitigations: extensive unit
  tests, atomic file writes, fail-closed defaults, and a smoke test that
  exercises end-to-end via `copier copy`.
- More moving parts. v1 has 9 hook scripts plus a shared `_state_io.py`
  helper. New contributors must understand the lifecycle event model
  before changing them.
- Hooks add latency to every tool call. PreToolUse hooks run synchronously
  in front of `create_file`, `replace_string_in_file`, etc. We keep them
  to single-file reads of `state.md` plus a small regex set; in practice
  they add < 50 ms.

### Neutral
- The pre-v1 advisory protocol is still readable in `copilot-instructions.md`
  but it now ranks below Tier 1 enforcement (see ADR-010).
- `slice-gate.py` is removed; its name appears only in historical
  references (commit messages, ADRs).
