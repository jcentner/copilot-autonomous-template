# Session Logs

One Markdown file per agent session. Created automatically by the
`evidence-tracker.py` PostToolUse hook on the first tool call of a session.

## Why per-session files

- **Append-only**: each PostToolUse appends one line. POSIX `O_APPEND` writes
  smaller than `PIPE_BUF` (4 KiB on Linux) are atomic, so concurrent appends
  from parallel hook invocations cannot interleave-corrupt.
- **Bounded**: a single session log grows with one session's tool count, not
  the project's lifetime. The previous design wrote every tool call into
  `CURRENT-STATE.md`, which grew unbounded across phases.
- **Hooks never re-read these files**: they are an audit trail, not workflow
  state. State lives in `../state.md`.

## File naming

`<sessionId>.md` when Copilot supplies a session id, otherwise
`nosid-<short-hash>.md` derived from `(cwd, ppid)` so independent windows on
the same repo get distinct files.

## Rotation

These files are not rotated automatically. Treat them as build artifacts:
either commit them (small repos) or add `roadmap/sessions/` to `.gitignore`
(busy repos). The default `.gitignore` keeps them tracked for traceability.

## What's logged

One line per tool call with format:

```
- [ISO8601] tool_name: short summary
```

The `evidence-tracker.py` hook writes these. Agents do **not** append to
these files manually — agent-significant transitions are already captured by
state-field changes in `../state.md` and by artifact files written under
`../phases/`.
