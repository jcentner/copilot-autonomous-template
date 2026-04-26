# Changelog

All notable changes to `copilot-autonomous-template` will be documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] — 2026-04-25

Minor release. Installs a single design principle across the lifecycle:
**an agent must not produce an artifact whose subject it never directly
observed.** Six gaps closed at every boundary where a subagent commits
to a claim about a system (codebase, runtime, deployed surface).

> **Trigger:** wyoclear.com Phase 1 design plan proposed `build` slices
> over functionality already shipped in production (Joint Judiciary
> meeting videos, "Register to Testify" CTA, Floor Session Audio
> placeholder, BillStatusBadge column). Three of eight slices were
> already half-shipped; the planner authored without inspecting either
> the codebase or the deployed surface; the critic didn't catch it. A
> human discovered it post-critique by browsing the live site.

> **Mid-phase update note:** existing repos that `copier update` to
> v1.3.0 will see their next design plan refused by the critic until
> they add `## Existing Implementation`, their next implementation plan
> refused until each slice has `Codebase Anchors`, and their next built
> slice flagged by the reviewer if the commit body lacks a
> `Runtime check:` block. Either retro-fit the active plans or use
> `/scrap-phase` and re-strategize.

### Changed — Design plan contract (Block A)

- `/design-plan` prompt now requires a mandatory **Phase 0 — Reality
  Check** with two layers before slice authoring: **Layer A** (codebase
  inventory via `grep_search` + `read_file`, with `path:line` evidence
  or honest negative search) and **Layer B** (deployed/runnable surface
  inspection via browser/curl/CLI, with honest `n/a — <reason>`
  fallback when no runnable surface exists).
- Required new `## Existing Implementation` section in the plan
  structure summarizing both layers with implications for slices.
- Every slice now declares a `Kind`: `build | wire-up | augment |
  audit | drop`. Slices reference Reality Check findings; never
  propose `build` for code or UI Layer A/B showed exists.
- `planner.agent.md` mirrors the requirement in the `planning`
  responsibility and Rules section.

### Changed — Design critic dimensions (Block A)

- New **Reality grounding (check first)** dimension: critic must audit
  at least one slice itself with `grep_search` (and browser tools when
  available); undeclared shipped code/UI is **Blocking** regardless of
  how clean the rest of the plan reads.
- New **Slice Kind honesty** dimension: silent overlap of a `build`
  slice with shipped functionality → **Major**.

### Changed — Implementation plan contract (Block B)

- `/implementation-plan` prompt now requires a mandatory **Phase 0 —
  Codebase verification** before slice authoring.
- Each slice gets a required **Codebase Anchors (verified)** subsection:
  every `Files touched` path is confirmed (existing via `read_file`,
  new via `file_search` negative); every named function / class /
  route / table / endpoint the slice integrates with cites `path:line`.
- Slices carry forward the design plan's `Kind`; never silently upgrade
  `wire-up` / `augment` to `build`.
- `planner.agent.md` `implementation-planning` section + Rules updated.

### Changed — Implementation critic dimensions (Block C)

- New **Codebase grounding (check first)** dimension on
  `implementation-critique`: critic audits at least one slice's anchors
  with `grep_search`; missing/wrong/contradicted anchors → **Blocking**.
- New **Slice Kind continuity** dimension: silent upgrade of
  `wire-up` / `augment` → `build`, or implementation inventing slices
  the design never had → **Major**.

### Changed — Slice loop (Block D)

- New step **5b — Runtime check** in both `autonomous-builder.agent.md`
  "The slice loop" and the `/implement` prompt. For any slice with
  `Kind: build | wire-up | augment`, the builder must produce
  observation evidence the change works on the running surface (UI:
  dispatch catalog `designer`; API: `curl` + `jq`; CLI: invoke +
  capture stdout/stderr; library/audit/drop: honest
  `Runtime check: n/a — <reason ≥20 chars>`).
- The artifact (or honest `n/a`) goes in the commit body under a
  `Runtime check:` heading.
- Step numbers shifted: old 5 → 6 (reviewer), 6 → 7 (fix findings),
  7 → 8 (commit + commit-evidence), 8 → 9 (verify + advance).

### Changed — Reviewer dimensions (Block E)

- New review dimension #5 **Runtime evidence**: silent omission of the
  `Runtime check:` block on a `Kind: build | wire-up | augment` slice
  is a **Major** finding tagged `runtime-evidence: missing`. Honest
  `n/a — <reason ≥20 chars>` is acceptable; reviewer is consistency
  backstop, not runtime cop.
- Findings table example now includes a `runtime-evidence: missing`
  row alongside the existing `doc-sync: missing` row.
- Existing dimensions renumbered: Dependency security 5 → 6, Doc-sync
  6 → 7.

### Changed — Product-owner Review mode (Block F)

- "When browser tools are available, you **may** screenshot and
  navigate" replaced with **must** observe runnable surfaces (UI/API/
  CLI). Browser walkthroughs route through catalog `designer`; API/CLI
  probes via the autonomous-builder. Honest `Runtime observation: n/a`
  with reason allowed only when there is genuinely no runnable surface.
- Criteria marked `Met: Yes` based purely on code reading get
  downgraded to `Partial` with `evidence: code-only` until runtime
  observation is recorded.
- New Rules bullet: "Observe before judging."

### Backwards compatibility

- No state.md schema changes. No new vocab in `_state_io.py`. No new
  hook scripts. No removed prompts or helpers. All changes are contract
  guidance in agent + prompt files plus matching critic/reviewer review
  dimensions.
- All commits land green: `make test-all` (160 hook tests + smoke +
  contract-drift lint) passes after every block.

### Known limitations (deferred)

- **Slice Kind vocabulary doesn't fit refactor / infra phases
  cleanly.** `build | wire-up | augment | audit | drop` is
  user-facing-shaped. Pure refactor ("split God object") or pure
  CI/infra ("migrate to GitHub Actions") slices have no honest fit;
  current guidance is to pick the closest Kind and let `Layer B: n/a`
  + `Runtime check: n/a` carry the reality-check honesty downstream.
  A future minor may add `refactor` and/or `infra` to the vocab if
  this proves leaky in practice.
- **"Hand-waved" judgment in critic Reality grounding.** Block A's
  critic dimension treats `missing | hand-waved | contradicted` as
  Blocking. "Missing" and "contradicted" are objective; "hand-waved"
  is judgment-heavy and could cause inconsistent rounds across
  critic invocations. Not splitting now — the existing
  `evidence-status` convention (`present | needed | unmeasurable`)
  partially handles it. Revisit if rounds-budget exhaustion becomes
  a recurring failure mode.

## [1.2.4] — 2026-04-25

Patch release. Tooling-only: adds a contract-drift lint to catch the
class of bug v1.2.1 / v1.2.2 / v1.2.3 all patched. No template behavior
change; `copier update` is optional unless you also run the project's
smoke test.

### Added — `tests/contract_drift_lint.py`

Compares every documented value / reference in prompt + agent files
against the source-of-truth contract:

  - **A.** `agents:` frontmatter references resolve to a real agent file
    (template or catalog) or `Explore`.
  - **B.** Prompts that pin a non-builder agent and instruct subagent
    handoffs ("hand off to / dispatch / invoke X") — pinned agent must
    declare the `agent` tool and list X in its `agents:` whitelist.
    Catches the v1.2.3 planner bug.
  - **C.** `/<command>` slash-command references resolve to a real
    prompt or are in the catalog (path-aware: skips URLs, file paths,
    glob fragments).
  - **D.** `Next Prompt: /foo` values are in `VALID_NEXT_PROMPTS`.
    Catches the class of v1.2.1 routing bugs.
  - **E.** `Stage: foo` values are in `VALID_STAGES`.
  - **F.** `Blocked Kind: foo` values are in `VALID_BLOCKED_KINDS`.
  - **G.** `.github/hooks/scripts/<name>.py` references exist on disk.
    Catches the v1.2.2 helper-name drift class.

The lint reads the source of truth at lint time (parses `_state_io.py`
for the vocab sets, walks `.github/agents/` and `.github/prompts/` for
file existence). Adding a new stage / blocked kind / next prompt / hook
script automatically extends the lint with no manual update.

Negative-tested on all 6 detection categories: each produces a
non-zero exit and names the offending file + value.

### Wired into smoke

`tests/smoke.sh` runs `contract_drift_lint.py` against the generated
workspace as an additional check next to the existing state-writer
coverage lint. CI will fail any future PR that introduces a vocab,
helper-name, or subagent-permission drift in prompts or agents.

## [1.2.3] — 2026-04-25

Patch release. Fixes a missing primitive on the planner agent that
prevented it from dispatching the product-owner and critic subagents its
own prompts told it to hand off to.

### Fixed — Planner subagent dispatch
- `planner.agent.md.jinja` now declares `agent` in `tools:` and lists
  `product-owner` and `critic` in `agents:`. Without these, a human
  invoking `/design-plan` (which pins `agent: planner`) hit a dead end:
  the prompt body said "Hand off to product-owner / critic" but the
  planner had no way to dispatch them. The previous frontmatter comment
  conflated `handoffs:` (UI buttons humans press) with `agents:`
  (programmatic subagent dispatch from inside a prompt body) — only
  `handoffs:` carried the stage-bypass risk that motivated the
  restriction.
- The SubagentStop verdict-trailer hooks on product-owner and critic
  still fire regardless of dispatcher, so the critique-gate guarantees
  documented in ADR-001/ADR-003 are unchanged.

### Documented — Subagent vs. autonomous-builder context
- `/design-plan` and `/implementation-plan` Handoff sections now note
  that nested subagent invocation is off by default
  (`chat.subagents.allowInvocationsFromSubagents`), so when the planner
  runs **as a subagent of autonomous-builder** the Handoff section is
  inert — the builder owns the `planning → design-critique` and
  `implementation-planning → implementation-critique` transitions and
  dispatches product-owner / critic itself. Act on Handoff only when a
  human invoked the planner directly.

### Why we are not enabling nested subagent invocation
Evaluated the trade-off and kept the default. Enabling it would let the
planner-as-subagent dispatch critic from inside `Stage: planning`, which
bypasses `record-verdict.py`'s round-budget counter (it runs on builder-
driven `design-critique` transitions, not on nested critic calls). The
asymmetry is a documentation gap, not a functional bug — the builder
already handles the dispatches it needs.

## [1.2.2] — 2026-04-25

Patch release. Fixes a `tool-guardrails.py` denial that blocked `/design-plan`
(and several other prompts) from stamping `state.md` because no sanctioned
CLI helper existed for the field — the agent's only remaining path was a
`python3 -c "from _state_io..."` one-liner, which the guardrail correctly
denied. The fix splits state writes into two sanctioned paths: helpers
where they earn their keep (cross-field invariants or the bootstrap-forging
threat model), and a line-shape carve-out for the rest. No state.md schema
changes; no new stages, blocked kinds, or hook events. Generated repos can
pull this via `copier update` without migration steps.

### Added — Sanctioned helpers for fields that need invariants
- `write-stage.py` — sole writer of `Stage` / `Blocked Kind` / `Blocked
  Reason` / `Next Prompt`. Enforces the `Stage=blocked ⇒ Blocked Kind`
  invariant and is the gate against forging `Stage: bootstrap` to unlock
  the enforcement-layer carve-out (ADR-009).
- `write-phase.py` — atomic `Phase` / `Phase Title` writes with optional
  `--reset-evidence` that resets all 17 slice/review/commit/plan fields
  in one transaction (one missed field would corrupt downstream hook reads).
- `write-plan-evidence.py` — `design-plan` / `design-status` / `impl-plan`
  / `impl-status` / `slice-total` subcommands. Validates plan-file
  existence and status vocabulary.
- `_state_io.update_state_fields(cwd, {field: value, ...})` library
  function for atomic multi-field writes (used by `write-stage.py` and
  `write-phase.py`).

### Added — Line-shape carve-out in `tool-guardrails.py`
- `replace_string_in_file` and `multi_replace_string_in_file` against
  `roadmap/state.md` are now allowed when every (oldString, newString)
  pair matches `^- **Field**: value$` line shape, the field name is
  unchanged between old and new, and the field is NOT in
  `{Stage, Blocked Kind, Blocked Reason}`. `create_file` against
  `state.md` is still denied unconditionally outside `bootstrap`.
- This covers `Active Slice`, `Reviewer Invoked`, `Review Verdict`,
  `Critical Findings`, `Major Findings`, `Strategic Review`, `Merge Mode`,
  and the slice-evidence reset fields. These are data the hooks read,
  not enforcement-layer fields, and ceremony around them was making the
  workflow brittle without raising the security bar.

### Changed — Callers updated to use sanctioned helpers
- `planner.agent.md.jinja`, `design-plan.prompt.md.jinja`,
  `implementation-plan.prompt.md.jinja` now call `write-plan-evidence.py`
  for all plan-status writes.
- `phase-complete.prompt.md.jinja`, `resume.prompt.md.jinja`,
  `vision-expand.prompt.md.jinja`, `strategize.prompt.md.jinja`,
  `autonomous-builder.agent.md.jinja`, `product-owner.agent.md.jinja`
  now call `write-stage.py` / `write-phase.py` for stage and phase
  transitions instead of inline edits.
- `implement.prompt.md.jinja` and `autonomous-builder.agent.md.jinja`
  slice-loop now use line-shape edits for `Active Slice` and the
  per-slice evidence reset.
- `AGENTS.md.jinja` ships a "State writers" table documenting the split
  (helpers vs. carve-out) so agents have one place to look up which
  fields take which path.

### Added — Smoke lint
- `tests/smoke.sh` scans every prompt and agent file for instruction-
  shaped phrases ("Set/Update/Clear `Field`") and asserts the file
  references the owning helper for fields in `FIELD_TO_HELPER`. Catches
  prose drift where a prompt tells an agent to write a field but doesn't
  point it at the sanctioned helper.

### Tests
- 265 hook unit tests pass (8 new tests in `test_tool_guardrails.py`
  cover the line-shape carve-out: safe-field allow, Stage/Blocked Kind
  deny, multi-line deny, field-rename deny, multi_replace allow/deny).
- `tests/smoke.sh` passes including the new state-writer coverage lint.

### Migration
- `copier update` then accept the new helpers and prose. No state.md
  schema changes; in-flight phases continue without intervention. If you
  had local prompts/agents calling `python3 -c "from _state_io..."` for
  state writes, replace them with the matching helper or a line-shape
  `replace_string_in_file` per the new `AGENTS.md` table.

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
