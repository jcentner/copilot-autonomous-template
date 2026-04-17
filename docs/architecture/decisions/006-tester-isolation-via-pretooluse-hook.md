# ADR-006: Tester source-isolation via PreToolUse hook

## Status

Accepted (April 2026, v1)

## Context

The tester subagent's value is writing tests **from the spec**, before
seeing the implementation. Tests written after reading the implementation
mirror its bugs and miss edge cases the implementation forgot.

Pre-v1 attempted to enforce this via prose: the tester's instructions
said "do not read implementation code." LLMs ignore prose constraints
when reading is the easiest path to a working test.

Three options were considered:

a. **Strip all read tools.** Maximum safety. Breaks legitimate reads of
   test framework config, existing test helpers, package manifests.
b. **Instruction-only.** What pre-v1 did. Effectively unenforced.
c. **PreToolUse hook gating reads by path.** Allow reads to test files
   and config, deny reads to source.

## Decision

Implement option (c): a `tester-isolation.py` PreToolUse hook scoped to
the tester agent (via `hooks:` in its frontmatter).

Policy:

1. **Semantic search is denied entirely.** `semantic_search` and
   `search/codebase` return source content in their results and cannot
   be path-gated.
2. **`read_file` under `Source Root`** is denied unless the path matches
   a test or config glob.
3. **`grep_search` / `file_search`** without `includePattern`, or with an
   `includePattern` that could reach non-test files under `Source Root`,
   is denied.
4. Everything else is allowed.

`Source Root`, `Test Path Globs`, and `Config File Globs` come from
`state.md`, with sensible defaults that cover Python, TS/JS, Go, Rust,
and common monorepo layouts.

The glob-intersection check uses **path-segment-anchored** matching, not
substring matching. `src/pretests/**` is denied even though `tests/**`
is a substring, because the test-glob tail (`/tests/**`) does not align
to a path-segment boundary in `src/pretests/**`.

## Consequences

### Positive
- The tester literally cannot read implementation code under the
  configured Source Root. Bias-free test authoring is mechanically
  enforced.
- Collocated tests work (`src/foo/__tests__/`, `src/**/*.test.ts`).
- Per-project overrides are a state-file edit, not a hook-script edit.

### Negative
- The hook is per-agent, which requires `chat.useCustomAgentHooks: true`
  to be enabled in VS Code. Without that setting, the tester is
  effectively unconstrained.
- A tester reading config files can still indirectly observe
  implementation choices ("the project uses framework X, so the
  implementation must look like Y"). Acceptable — tests *should* be
  framework-aware.
- The hook must agree with the agent's prompt about what's a test vs.
  what's source. A misconfigured `Source Root` either over-restricts
  (legitimate test reads denied) or under-restricts (source reads
  allowed). This is a configuration burden, not a correctness one.

### Neutral
- The tester has no `handoffs:` in its frontmatter; it returns to its
  caller automatically. This is intentional — chaining the tester to
  another agent (e.g., directly to the reviewer) would defeat the
  bias-free isolation that justifies its existence.
