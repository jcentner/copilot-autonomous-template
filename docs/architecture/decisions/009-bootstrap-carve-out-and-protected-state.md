# ADR-009: Bootstrap carve-out and `state.md` write-protection

## Status

Accepted (April 2026, v1)

## Context

ADR-007 establishes that the builder cannot edit the enforcement layer.
But bootstrap legitimately needs to:

- Copy catalog agents into `.github/agents/`.
- Copy catalog hooks into `.github/hooks/scripts/`.
- Initialise `roadmap/state.md` with the project's vision-phase fields.

These are one-time operations performed by `BOOTSTRAP.md` on the first
session. Without a carve-out, the v1 enforcement would block bootstrap
itself.

A naive carve-out — "skip enforcement when `Stage: bootstrap`" — has a
specific attack: an agent that wants to write the enforcement layer
could either:

a. Set `Stage: bootstrap` in `state.md` to re-enable the carve-out. If
   `state.md` is writable via `create_file`, this is trivial.
b. Delete `roadmap/state.md`. The carve-out also fires when state.md is
   absent (a fresh `copier copy` workspace before bootstrap has run).
   `rm roadmap/state.md` would unlock everything.

## Decision

The bootstrap carve-out is gated on:

```python
def _is_bootstrap_stage(cwd):
    if not _state_exists(cwd):
        return True              # fresh workspace
    return _get_stage_field(cwd, "Stage") == "bootstrap"
```

Both vectors above are closed independently:

1. **`roadmap/state.md` is in `PROTECTED_STATE_FILES`.** Writes via
   `create_file`, `replace_string_in_file`, `multi_replace_string_in_file`,
   or `edit_notebook_file` are denied unless bootstrap is active. The
   legitimate writers are:
   - `BOOTSTRAP.md` during bootstrap (carve-out applies).
   - `_state_io.update_state_field()`, called from agent helper scripts
     and hooks. These do not go through the file-edit tools, so they're
     naturally exempt.
   - `write-test-evidence.py`, which calls `update_state_field()`.

2. **`rm`/`mv`/`shred`/`unlink` on `roadmap/state.md` (or
   `roadmap/CURRENT-STATE.md`) is denied** by `tool-guardrails.py`'s
   terminal denylist, regardless of stage. The only way to legitimately
   reset state is `git checkout -- roadmap/state.md` or human action.

3. **`roadmap/CURRENT-STATE.md` is intentionally NOT in
   `PROTECTED_STATE_FILES`.** It is narrative — agents append to
   `## Context`, `## Proposed Workflow Improvements`, `## Vision Pivots`,
   and the `## Active Session` link throughout the lifecycle. Protecting
   it would break legitimate writes. The `rm`/`mv` denylist still
   prevents wholesale deletion.

4. **Path traversal is checked against the raw input** before
   `os.path.normpath` collapses intermediate `..` segments. A path like
   `src/foo/../../etc/passwd` is denied even though `normpath` would
   reduce it to `etc/passwd`.

5. **Absolute paths are denied when `cwd` is missing** from the hook
   payload — without `cwd`, the hook cannot resolve the path against
   workspace boundaries.

## Consequences

### Positive
- Bootstrap can do its job without disabling enforcement permanently.
- The two known escape vectors (forge `state.md`, delete `state.md`)
  are closed.
- The carve-out's trust boundary is auditable: it relies on the file
  state on disk, not on agent declaration.

### Negative
- During bootstrap the protection set is broad (everything except
  `state.md` itself is writable). This is the cost of a single trust
  boundary; bootstrap is rare and runs once per project.
- An agent that finds a novel path to mutate `state.md` (e.g., via a
  newly-added file-edit tool name not in `FILE_TOOLS`) would unlock
  the carve-out. Mitigation: `FILE_TOOLS` is the allowlist; new tools
  are denied by default.

### Neutral
- This ADR documents the fixes from CR-1 through CR-5 of the v1 code
  review (path-traversal regression, absolute-path-without-cwd,
  state-file write protection, terminal-delete denylist, `Phase=0`
  rejection in critique stages).
