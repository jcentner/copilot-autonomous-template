# Changelog

All notable changes to `copilot-autonomous-template` will be documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-04-17

First tagged release. The template is restructured around a hook-verified
stage machine. See [docs/architecture/decisions/](docs/architecture/decisions/)
for the design rationale (ADRs 001–010).

### Added
- **Workflow state machine** with explicit stages: `bootstrap → planning →
  design-critique → implementation-planning → implementation-critique →
  executing → reviewing → cleanup → (planning | complete | blocked)`.
- **`roadmap/state.md`** — machine-readable workflow state. Hooks parse
  this file. Vocabulary documented inline at the top of the file.
- **`roadmap/CURRENT-STATE.md`** — narrative state (`## Context`,
  `## Proposed Workflow Improvements`, `## Vision Pivots`,
  `## Active Session`).
- **`roadmap/sessions/<sessionId>.md`** — per-session activity log,
  one line per tool call (POSIX `O_APPEND`, atomic).
- **`_state_io.py`** — shared atomic state I/O for all hooks (temp + rename).
- **`stage-gate.py`** (PreToolUse) — denies edits to non-allowlisted
  paths outside `executing` stage. Iterates every entry in
  `multi_replace_string_in_file` to prevent batch-smuggle bypass.
- **`session-gate.py`** (Stop) — replaces `slice-gate.py`. Parses
  `state.md` and blocks stop on per-stage gating fields. Includes a
  git-diff backstop that detects terminal-edit bypass during
  non-executing stages.
- **`subagent-verdict-check.py`** (SubagentStop) — verifies that critic,
  product-owner, reviewer, and planner subagents wrote their expected
  fields and artifacts before returning.
- **`tester-isolation.py`** (PreToolUse, tester-scoped) — denies the
  tester reads of source code under `Source Root`. Uses path-segment-
  anchored glob matching to avoid substring false positives.
- **`tool-guardrails.py`** (PreToolUse) — destructive-command denylist
  promoted from catalog to core. Adds enforcement-layer write
  protection (`.github/agents/**`, `.github/hooks/scripts/**`,
  `.github/instructions/**`, `copilot-instructions.md`, `AGENTS.md`,
  `roadmap/state.md`) with a bootstrap carve-out, terminal-delete
  protection for state files, and raw-input path-traversal check.
- **`evidence-tracker.py`** (PostToolUse) — pure logger that appends to
  the per-session log. Does not infer state.
- **`context-pressure.py`** (PostToolUse) — context-window advisory
  promoted from catalog to core.
- **`write-test-evidence.py`** — agent-invoked CLI helper that stamps
  `Tests Written`, `Tests Pass`, and `Evidence For Slice` atomically.
- **`write-commit-evidence.py`** — agent-invoked CLI helper that stamps
  `Committed` after `git commit`. Refuses to mark `Committed: yes` when
  the working tree is dirty (ignoring `roadmap/sessions/`,
  `roadmap/state.md`, and `__pycache__/`), preventing the field from
  becoming a lie.
- **Product-owner `n/a — <reason>` opt-out** — phases with no
  user-facing surface (refactors, infra, build/CI, internal tooling)
  may declare `n/a — <≥20-char justification>` in the User Stories
  section. `subagent-verdict-check` accepts this as terminal; bare
  `n/a` or trivial reasons are still rejected.
- **Core agents** — `critic` and `product-owner` promoted from catalog
  to core with SubagentStop verification. `tester` agent gains a
  PreToolUse isolation hook. `planner` gains a SubagentStop check.
- **Prompts** — `/design-plan` (replaces `/phase-plan` with user
  stories, acceptance criteria, ADR candidates), `/strategic-review`,
  `/resume` (unblock routing on `Blocked Kind`).
- **`Blocked Kind` vocabulary** — `awaiting-design-approval`,
  `awaiting-vision-update`, `awaiting-human-decision`, `error`,
  `vision-exhausted`. Stop hook refuses to allow stop with an empty or
  unknown Blocked Kind.
- **Test suite** — 160 unit tests under `tests/hooks/` (stdlib
  `unittest`) plus end-to-end smoke test in `tests/smoke.sh`.
  `make test-all` runs both.
- **ADRs 001–010** under [docs/architecture/decisions/](docs/architecture/decisions/)
  recording the major design decisions.

### Changed
- **`autonomous-builder.agent.md`** rewritten as a thin **stage
  orchestrator**. All independent judgment is delegated to subagents.
- **`planner`** expanded to handle design plans (user stories,
  acceptance criteria, non-goals, risks, ADR candidates, test strategy)
  and strategic review fallback.
- **`reviewer`** scoped to code quality and security; strategic review
  is now the product-owner's job.
- **Tester** must always be invoked (no "skip on N+ files" loophole).
- **`PROMPT-GUIDE.md`**, **`AGENTS.md`**, **`copilot-instructions.md`**,
  **`BOOTSTRAP.md`** rewritten to reflect the stage machine and the
  three-tier enforcement vocabulary (deterministic / strongly-guided /
  advisory).
- Catalog activation is now **human-only at bootstrap** (no autonomous
  heuristics). Catalog still ships designer, security-reviewer, four
  skills, ci-gate, two prompts, two patterns.

### Removed
- **`slice-gate.py`** — superseded by `session-gate.py` +
  `subagent-verdict-check.py`.
- **Builder self-modification permission.** The builder can no longer
  edit its own instructions, agents, hooks, or scoped instructions.
  Improvements are recorded in `## Proposed Workflow Improvements` for
  human action via `copier update`.
- **Autonomous catalog-activation heuristics.** The "5+ slices →
  activate critic" pattern is gone; critic and product-owner are core.
- **Vision-expansion mode in the builder.** The builder defers to the
  `/vision-expand` prompt.

### Fixed (during v1 implementation)
- Path traversal regression in `tool-guardrails.py` (`os.path.normpath`
  collapsed `..` segments before the check ran).
- `multi_replace_string_in_file` smuggle: stage-gate and tool-guardrails
  now iterate every replacement entry.
- Tester-isolation substring false positives (`pretests/`, `latest/`,
  `contest_data/` were being treated as test directories).
- `Phase` field coerced to `int`; non-numeric or `Phase: 0` in critique
  stages fail closed.
- Stale slice evidence detection via `Evidence For Slice` field bound
  to the active slice number.
- Terminal `rm`/`mv` of `roadmap/state.md` denied (would otherwise
  unlock the bootstrap carve-out).

[1.0.0]: https://github.com/jcentner/copilot-autonomous-template/releases/tag/v1.0.0
