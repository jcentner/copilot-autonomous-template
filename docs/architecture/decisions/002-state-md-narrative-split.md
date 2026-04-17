# ADR-002: Split workflow state into `state.md`, `CURRENT-STATE.md`, and `sessions/`

## Status

Accepted (April 2026, v1)

## Context

The pre-v1 template kept everything in one `roadmap/CURRENT-STATE.md`:

- Machine fields (Stage, Phase, slice counters).
- Narrative context (what the agent did, what's blocked, decisions in flight).
- A growing per-session activity log appended after each tool call.

This forced every parser (every hook) to read a long Markdown file and
regex-extract fields from it, while every narrative update had to avoid
breaking the field syntax. Concurrent writes (PostToolUse hooks running
in parallel from independent tool calls) corrupted the file in practice.

A SQLite-backed approach was considered and rejected: it would make the
state opaque to humans, complicate `copier update`, and break the
"open the file in any editor" expectation that makes the workflow
debuggable.

## Decision

Split the single file into three artifacts with distinct ownership and
mutation patterns:

| File | Purpose | Writers | Read pattern |
|---|---|---|---|
| `roadmap/state.md` | Machine-readable workflow state. Fixed schema of `- **Field**: value` lines plus a `## Phase Completion Checklist` section. | Agents (via prompts) and hooks (via `_state_io.update_state_field`, atomic temp+rename). | Every hook on every relevant event. Parsed by regex. |
| `roadmap/CURRENT-STATE.md` | Narrative state. Free-form Markdown sections: `## Context`, `## Proposed Workflow Improvements`, `## Vision Pivots`, `## Active Session` link. | Agents only. Append-style edits. | Humans, occasional planner reads. |
| `roadmap/sessions/<sessionId>.md` | Per-session activity log, one line per tool call. | `evidence-tracker.py` only, via POSIX `O_APPEND` writes. | Diagnostic / audit. |

`_state_io.py` centralises:
- Atomic field updates (`tempfile.mkstemp` + `os.replace` — POSIX atomic
  rename within a filesystem).
- Append-only session log writes (`O_APPEND` for atomicity of writes
  smaller than `PIPE_BUF` = 4 KiB on Linux).
- The `## Active Session` link update in `CURRENT-STATE.md`.

`state.md` ships the canonical vocabulary inside an HTML comment block at
the top, so an agent reading it learns the valid values for every field
without consulting the hooks.

## Consequences

### Positive
- Hooks parse a small, stable file. Adding a new field requires updating
  only `state.md.jinja` and the hook(s) that read it.
- Narrative edits to `CURRENT-STATE.md` cannot accidentally break a
  machine field.
- Session logs grow without bounding the parsed-state file. Old sessions
  can be archived or pruned independently.
- Concurrent PostToolUse writes are now safe: each writes to its own
  session log via `O_APPEND`, and field updates use atomic rename.

### Negative
- Three files instead of one. Contributors must learn which file owns
  what.
- The pre-v1 narrative `CURRENT-STATE.md` no longer exists in its old
  form. Existing downstream projects that adopted the template before
  v1 will need a one-time migration (split their fields into
  `state.md`).

### Neutral
- `BOOTSTRAP.md` writes both `state.md` and `CURRENT-STATE.md` during
  bootstrap, so a fresh `copier copy` produces a coherent initial state.
- The `sessions/` directory is checked in via a `.gitkeep`; its contents
  are not (per generated `.gitignore` patterns the user can add).
