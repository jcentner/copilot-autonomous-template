# Changelog

All notable changes to `copilot-autonomous-template` will be documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] — 2026-04-22

Patch release. Fixes workflow contradictions discovered while running v1.2.0
in a real project (the `executing → reviewing` transition cued the wrong
slash-command, which led to a full audit of every stage transition,
resume-routing branch, and subagent handoff). No state.md schema changes;
no new stages, blocked kinds, or hooks. Generated repos can pull this via
`copier update` without migration steps.

### Fixed — Stage routing
- **`executing → reviewing`** now writes `Next Prompt: /strategic-review`
  (was `/code-review`, which dispatched the per-slice reviewer that had
  already run on every slice). `/strategic-review` added to
  `VALID_NEXT_PROMPTS` (was missing entirely, so any agent writing the
  correct value would have been rejected by the validator).
- **`/resume awaiting-design-approval`** Approve and Revise branches now
  set `Next Prompt` (`/implementation-plan` and `/design-plan`
  respectively). Previously left the stale `/resume` cue from
  `record-verdict.py`, looping the human back into the resume prompt
  whose precondition then refused.
- **`/vision-expand`** now routes through `Stage: strategy` +
  `Next Prompt: /strategize` instead of jumping straight to `planning`,
  so the new vision's first phase actually goes through the strategy
  approval gate and gets a proper `Phase Title`.
- **`/scrap-phase`** now writes `Next Prompt: /resume` (was
  `/strategize`), matching every other blocked-exit path.
- **`/merge-phase`** now writes `Next Prompt: /resume` (was `n/a`), so
  the Stop hook surfaces the next slash-command instead of leaving the
  human to find it from `stage-recommendations`.
- **`/strategize` Phase E** now checks out `main` first if currently on
  a `phase/*` branch, preventing scrapped commits from being carried
  into the next phase branch when the post-scrap path runs through
  `/resume → /strategize`.

### Fixed — Critic agent contract
- Removed the invalid `escalate` verdict from the critic agent doc
  (only `approve | revise | rethink` are accepted by `record-verdict.py`
  and `subagent-verdict-check.py`). Removed the contradictory
  instruction telling the critic to write `Blocked Reason` directly
  while the same file's "Do NOT write state.md" section forbade it.
  Over-cap escalation continues to flow through `record-verdict.py`'s
  refusal of the increment.

### Fixed — Sole-writer principle (ADR-003)
- Slice-loop step 8 in the autonomous-builder agent and step 9 in
  `/implement` now tell the orchestrator to **verify** the reviewer
  wrote `Reviewer Invoked / Review Verdict / Critical Findings /
  Major Findings`, not overwrite them. Reviewer remains the sole
  writer per ADR-003.
- Removed `handoffs:` blocks from the planner and product-owner agents.
  Both routed to the critic from a stage where
  `subagent-verdict-check.py critic` does not enforce the
  verdict-trailer requirement, silently degrading the critique gate.
- Strategic review `replan` verdict now sets the full block transition
  (`Stage: blocked`, `Blocked Kind: awaiting-human-decision`,
  `Blocked Reason`, `Next Prompt: /resume`) inside `/strategic-review`
  and the product-owner agent doc, instead of deferring to "the builder."
  `session-gate` only blocks stop on `Strategic Review: pending`, so the
  prior approach allowed stop at `Stage: reviewing` with no resume cue.

### Fixed — Schema and field discipline
- Initial `Phase Title` shipped in `state.md.jinja` is now
  `Strategy Pending` (was `Bootstrap`), matching the autonomous-builder's
  `Phase` value rules.
- `Slice Total` is now written by `/implementation-plan` and the planner
  agent's `implementation-planning` responsibilities. Previously stayed
  `n/a` permanently despite being in the schema and the reviewer's
  required reads.
- `/implement` prompt now pins `agent: autonomous-builder`. Without the
  pin, running `/implement` from a non-builder agent silently lacked
  the slice loop's subagent and hook wiring.
- Tester agent dropped `search/codebase` from `tools:` —
  `tester-isolation.py` denies it unconditionally; advertising it
  invited futile attempts.

### Hardened — Stop hook
- `Stage: complete` no longer allows stop unconditionally. The
  autonomous-builder's stage table mandates flipping to
  `Stage: blocked` + `Blocked Kind: vision-exhausted` +
  `Next Prompt: /vision-expand`; `session-gate.py` now enforces the
  flip so a forgetful agent can't silently dead-end the workflow.
- `executing` stop now also checks `Tests Written` (in addition to
  `Tests Pass`), closing the gap where the field was reset/written
  by helpers but never gated.

### Docs / cosmetic
- Promoted "Browser tools" subsection in `copilot-instructions.md.jinja`
  from "(optional)" to "(preferred)".

## [1.2.0] — 2026-04-19

Additive on top of v1.1.0. No breaking changes; all v1.1 state.md fields and
stage values remain valid. See
[ADR-011](docs/architecture/decisions/011-strategy-stage-and-three-gate-approval.md)
for the design rationale.

### Added — Block 1 (foundation)
- **`strategy` stage** between `bootstrap` and `planning` (and as the loop-back
  target from `cleanup`). New `Blocked Kind` values:
  `awaiting-strategy-approval`, `awaiting-merge-approval`,
  `scrapped-by-human`. Vocab updated in `_state_io.VALID_STAGES` /
  `VALID_BLOCKED_KINDS` and in `state.md.jinja`.
- **`Next Prompt` machine field** in `state.md`, written by every Stage
  transition. Surfaced by `session-gate.py` (Stop hook, top-level
  `systemMessage` per Copilot hooks docs) on every session end.
- **`Merge Mode` machine field** (`cli` | `pr`). Picked at bootstrap via
  `vscode_askQuestions` with no pre-selection. `/merge-phase` refuses to
  run while it is `n/a`.
- **`branch-gate.py`** (PreToolUse) — refuses `git commit` on denylisted
  branches (default: `main`, `master`, `trunk`, `prod`, `release/*`).
  Bootstrap exempt. Config at `.github/hooks/config/branch-policy.json`.
- **`stage-recommendations.json`** — per-stage prompts/skills surfaced by
  the Stop hook so `Next Prompt` is never opaque. Smoke test asserts every
  referenced `/prompt` resolves to a real `.prompt.md.jinja`.
- **`stage-gate.STAGE_PATH_DENYLIST`** — `strategy` stage cannot write to
  `roadmap/phases/`.
- **BOOTSTRAP.md** rewritten: no `phase-1-design.md`; new Step 3.5 detects
  external systems (greps package manifests for `*-client`/`*-sdk`/`-api`
  deps) so `/strategize` can recommend `/research`. New Step 4 asks Merge
  Mode. Final stage flip is `Stage: strategy`, not `design-critique`.
- **`/resume`** extended with three new Blocked-Kind branches:
  `awaiting-strategy-approval`, `awaiting-merge-approval` (this branch
  increments `Phase` and resets all Phase-scoped fields after merge
  verification), `scrapped-by-human`.

### Added — Block 2 (researcher + strategize + merge)
- **`researcher` core agent** at `.github/agents/researcher.agent.md` —
  produces `docs/reference/<topic>.md` from cited public sources. **NO
  terminal access** — closes prompt-injection-via-fetched-content →
  shell-execution attack surface. Verified caller-side per
  [ADR-010](docs/architecture/decisions/010-three-tier-enforcement-honesty.md);
  no SubagentStop hook (a presence-only check would be enforcement
  theatre).
- **`/strategize`** prompt — reads vision + open questions + tech debt +
  recent context; produces ≥3 ranked candidates including at least one
  outside `docs/plans/`; presents via `vscode_askQuestions` with a "save
  and let me think" escape; writes a timestamped artifact at
  `roadmap/strategy-YYYYMMDD-HHMMSSZ.md` (lex-sortable).
- **`/research <topic>`** prompt — standalone dispatcher to the researcher
  subagent.
- **`/merge-phase`** prompt — branches on `Merge Mode`. Verifies tests +
  reviewer + doc-sync + clean tree; prints commands or PR URL; sets
  `Blocked Kind: awaiting-merge-approval`. Agent never executes the
  merge.
- **Reviewer agent extended** with `doc-sync: missing` finding tag —
  warning per-slice (does not fail review verdict); blocker at
  `/merge-phase` (refuses until cleared).

### Added — Block 3 (verdict / scrap / evidence / catalog-review)
- **`record-verdict.py`** — sole writer of `Design Critique Rounds` /
  `Implementation Critique Rounds` and the verdict-driven mutations.
  Parses `^VERDICT: (approve|revise|rethink)$` trailer (case-sensitive,
  exact). Refuses missing / ambiguous / lowercase trailers and
  out-of-order or over-cap rounds (caps 3 design / 2 impl per
  [ADR-004](docs/architecture/decisions/004-stage-pipeline-and-critique-loops.md)).
  Asymmetric mutations: `design approve` → `awaiting-design-approval`
  human gate; `impl approve` → `executing` directly.
- **`/scrap-phase`** prompt — refuses on dirty tree (override:
  `--force`); archives `roadmap/phases/phase-N-*` to
  `roadmap/phases/_archived/phase-N-<ISO>-scrapped/`; resets all
  Phase-scoped fields; **leaves `Phase` unchanged** (the burned number
  is reused by the next strategize pick); refuses to suggest deleting
  any phase branch that exists on `origin`.
- **`/catalog-review`** prompt — re-presents the catalog picker; copies
  selected items from `.github/catalog/<type>/` to `.github/<type>/`;
  skips already-activated items; **never overwrites; never
  deactivates** (alignment with operational safety).
- **`evidence-gathering` skill** at
  `.github/skills/evidence-gathering/SKILL.md` — audit patterns for
  satisfying `evidence-status: needed` critic findings (live API audit,
  schema dump, file/dependency inventory, race-condition audit,
  performance probe, external-system grounding via researcher).
- **Critic agent updated** to (a) mandate the `^VERDICT:` trailer; (b)
  tag every finding with `evidence-status: present | needed |
  unmeasurable`; (c) refuse `approve` while any `needed` finding is
  open; (d) NOT write `state.md` — `record-verdict.py` is sole writer
  per Decision #21.
- **`subagent-verdict-check.py` critic check rewritten** — verifies
  artifact presence + parseable VERDICT trailer only. Old
  state-field/rounds checks removed (those fields are stale-by-design
  at the moment the critic returns).

### Changed
- **Autonomous-builder dispatch table** — new `strategy` row; new
  `awaiting-strategy-approval` and `awaiting-merge-approval` Blocked
  Kinds; explicit `Next Prompt` for every transition; `cleanup` no
  longer loops to `planning` — it sets `awaiting-merge-approval`.
  Researcher and `branch-gate.py` registered. New "Branch hygiene"
  section documents the `strategy/<date>` ↔ `phase/N-<theme>` branch
  cuts so `branch-gate.py` and `/merge-phase` stay happy.
- **`/phase-complete` Step 9 rewritten** — no longer increments
  `Phase`, resets Slice Evidence, or sets `Stage: planning`. Now hands
  off to the merge gate by setting `Stage: blocked` / `Blocked Kind:
  awaiting-merge-approval` / `Next Prompt: /merge-phase`. The previous
  behavior would have silently bypassed the merge approval gate (the
  marquee v1.2 feature) and wiped the `Review Verdict` / `doc-sync:
  missing` rows that `/merge-phase` scans before approving the merge.
  Phase increment + Phase-scoped resets now live exclusively in
  `/resume awaiting-merge-approval`. Smoke test asserts
  `/phase-complete` does not contain the v1.1-era instructions.
- **`BOOTSTRAP.md` Step 5 added** — cuts a `strategy/<UTC-date>` branch
  before flipping `Stage: strategy` so the next session's first commit
  doesn't fight `branch-gate.py`.
- **`/strategize` and `/resume`** — explicit `git checkout -b
  phase/<N>-<kebab>` instructions on inline pick / strategy resume;
  `/resume awaiting-merge-approval` cuts a fresh strategy branch off
  updated `main` before mutating state.
- **`/strategize` autopilot warning** — surfaces a one-line note when
  autopilot may be on, since `vscode_askQuestions` auto-answer
  degrades the strategy gate.
- **AGENTS.md core-agents table** — researcher row added.
- **Catalog MANIFEST preamble** — notes that researcher is core in v1.2+.

### Migration notes
- Existing in-flight v1.1 projects continue working. State.md vocab
  additions don't invalidate existing values.
- After `copier update`:
  - `Merge Mode` defaults to `n/a` and must be set manually (or by the
    next strategize → merge cycle's `/merge-phase` prompt, which will
    refuse with a clear message until set).
  - Run `/catalog-review` to inspect the picker; researcher is now core,
    not catalog, so it will already be present.
  - The new `branch-gate.py` denylists `main`, `master`, `trunk`, `prod`
    — projects on trunk-based development must edit
    `.github/hooks/config/branch-policy.json` to remove `main` from the
    denylist.
  - **`Stage: planning` carry-overs need a strategy artifact stub.**
    `session-gate.py` now blocks Stop in `planning` when no
    `roadmap/strategy-*.md` exists. v1.1 projects mid-flight in
    `planning` should `touch
    roadmap/strategy-grandfathered-from-v1.1.md` (one-line content:
    "Phase chosen pre-v1.2; no strategize artifact recorded.") to clear
    the gate. Future phases will write real timestamped artifacts.
  - **`/phase-complete` now hands off to the merge gate** instead of
    incrementing Phase + setting `Stage: planning`. v1.1 projects that
    have a half-completed `cleanup` in flight should re-run
    `/phase-complete` after `copier update` — Step 9 is now a state
    handoff (`Stage: blocked` / `Blocked Kind:
    awaiting-merge-approval`), not a Phase increment.
  - `/merge-phase` only supports GitHub for v1.2 (CLI or PR via `gh` /
    compare URL). GitLab / Bitbucket are v1.3+ candidates.

### Fixed
- **`subagent-verdict-check.py` SubagentStop output schema.** Previously
  the hook emitted `{"hookSpecificOutput": {"hookEventName":
  "SubagentStop", "decision": "block", "reason": ...}}` (the Stop hook
  shape). VS Code's hooks docs specify SubagentStop output is **top-level**
  `{"decision": "block", "reason": ...}`, with no `hookSpecificOutput`
  wrapper — VS Code silently ignored the wrapped form, meaning the
  critic / product-owner / reviewer / planner SubagentStop verifiers
  never actually blocked. Latent since v1.0.0; v1.2 makes the verifier
  load-bearing (researcher is now core; ADR-011 hangs the design on
  "agents write state, hooks verify state wrote"), so shipping the bug
  forward would be enforcement theatre per ADR-010. Test helpers and
  smoke assertions updated to match.

## [1.1.0] — 2026-04-17

Backward-compatible additions on top of v1.0.0.

### Added
- **`write-commit-evidence.py`** — agent-invoked CLI helper that stamps
  `Committed` after `git commit`. Refuses to mark `Committed: yes` when
  the working tree is dirty (ignoring `roadmap/sessions/`,
  `roadmap/state.md`, and `__pycache__/`), preventing the field from
  becoming a lie. Required step in the autonomous-builder and
  `/implement` per-slice loop.
- **Product-owner `n/a — <reason>` opt-out** — phases with no
  user-facing surface (refactors, infra, build/CI, internal tooling)
  may declare `n/a — <≥20-char justification>` in the User Stories
  section. `subagent-verdict-check` accepts this as terminal; bare
  `n/a` or trivial reasons are still rejected.
- **Template-aware review skill and prompt** for the meta-repo
  (`copilot-autonomous-template` itself).

### Fixed
- **Bootstrap stage-flip ordering**, and `BOOTSTRAP.md` is now in the
  bootstrap-stage allowlist.
- **`subagent-verdict-check` story scoping** — the `As a ...` check now
  runs against the User Stories section body only, not the entire plan
  text, so a story phrase elsewhere in the doc no longer satisfies the
  gate.

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
