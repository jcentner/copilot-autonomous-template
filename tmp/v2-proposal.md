# Autonomous Workflow Template v2 — Unified Proposal

> Written: April 15, 2026
> Status: Draft — awaiting decisions on open questions before implementation

---

## Diagnosis

Both analyses converge on the same core problem: **you have a stage-model problem, not a capabilities problem.** The right ideas exist (planning, critique, review, cleanup) but they live in prose instructions, optional catalog items, and unchecked narrative state. The single enforcement point — `slice-gate.py` — checks one string (`**Phase Status**: Complete`) and claims to enforce a 9-step slice protocol that it cannot actually verify.

The hook API is far more capable than the template uses. You have 8 lifecycle events available (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, SubagentStart, SubagentStop, Stop). The template uses exactly one (Stop), and that one only checks a status string.

### What's actually enforced today vs. what's claimed

| Claim | Reality |
|-------|---------|
| "Stop hook prevents skipped reviews" | Hook checks `**Phase Status**` line only. Never verifies review happened. |
| "Tests must pass before proceeding" | Prose instruction. No verification. |
| "Reviewer invoked on changed files" | Prose instruction. No verification. |
| "Phase plan → implementation plan → implement" | Autonomous builder goes straight to "identify the next highest-leverage change." No required link to an approved plan. |
| "Tool guardrails block dangerous operations" | Catalog item. Not active by default. |
| "Context checkpoint prevents saturation" | Catalog item. Not active by default. |
| "Critic challenges plans before coding" | Catalog item. Heuristic activation ("5+ slices"). |
| "Product-owner validates user perspective" | Catalog item. Heuristic activation. |

### Internal inconsistencies

- `implement.prompt.md.jinja` says "ask when ambiguous" — but autopilot mode auto-responds to questions, making this useless
- `copilot-instructions.md.jinja` says "all external actions require explicit human approval" — but the builder runs under autopilot where nothing requires approval
- Tester is described as writing tests "before seeing the implementation" but its frontmatter has no tool restrictions preventing it from reading implementation files
- The builder can self-modify its own instructions, prompts, and agents — but hooks enforce rules the builder might weaken

---

## Design Principles for v2

1. **If a rule can't be checked mechanically, stop describing it as enforced.** Move it to "guidelines" or make it checkable.
2. **Mandatory state before optional features.** Machine-readable workflow state before catalog expansion. Safety hooks before self-improvement.
3. **Subagents for independent judgment, hooks for deterministic policy.** Critique quality comes from context isolation. Stage transitions come from hooks parsing state.
4. **Autonomy inside approved bounds.** The builder executes freely within an approved plan. It cannot advance to a new stage without evidence that the current stage is complete.
5. **Prompts own human approvals. Subagents own independent analysis. Hooks own deterministic gates.**

---

## The Workflow State Machine

Replace narrative `CURRENT-STATE.md` with machine-readable workflow state. Hooks parse this. The builder updates it. Humans can read it.

### CURRENT-STATE.md structure

```markdown
# Project State

## Workflow State
- **Stage**: planning | design-critique | implementation-planning | implementation-critique | executing | reviewing | cleanup | blocked | complete
- **Phase**: 1
- **Phase Title**: Core Data Pipeline
- **Design Plan**: roadmap/phases/phase-1-design.md
- **Design Status**: draft | in-critique | approved | waived
- **Design Critique Rounds**: 0
- **Implementation Plan**: roadmap/phases/phase-1-implementation.md
- **Implementation Status**: draft | in-critique | approved | waived
- **Implementation Critique Rounds**: 0
- **Active Slice**: 3
- **Slice Total**: 8

## Slice Evidence
- **Tests Written**: yes | no | n/a
- **Tests Pass**: yes | no | n/a
- **Reviewer Invoked**: yes | no
- **Review Verdict**: pass | needs-fixes | needs-rework | pending
- **Critical Findings**: 0
- **Major Findings**: 0
- **Strategic Review**: pass | replan | pending | n/a
- **Committed**: yes | no

## Phase Completion Checklist
- [ ] All acceptance criteria verified
- [ ] ADRs recorded for new decisions
- [ ] Open questions resolved or flagged
- [ ] Tech debt documented
- [ ] Docs synced (README, architecture, instructions)
- [ ] Wrap summary written
- [ ] Context notes saved to /memories/repo/
- [ ] CURRENT-STATE updated for next phase

## Waivers
(Human-approved exceptions to the normal flow)

## Session Log
- [timestamp] Stage transition: planning → design-critique
- [timestamp] Design critique round 1: verdict = revise (3 blocking, 2 major)
- [timestamp] Design critique round 2: verdict = approve
- ...

## Context
(Narrative: what was done, what's next, what's blocked, key decisions)
```

Every field in **Workflow State** and **Slice Evidence** is parseable by hooks. The **Context** section remains narrative for humans and future sessions.

---

## The Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: DESIGN PLANNING                                          │
│                                                                     │
│  Planner creates design plan (user stories, acceptance criteria,    │
│  non-goals, risks, ADR candidates, test strategy)                  │
│                                                                     │
│  Human approval gate: "Approve design plan?"                        │
├─────────────────────────────────────────────────────────────────────┤
│  STAGE 2: DESIGN CRITIQUE (iterative, max 3 rounds)                │
│                                                                     │
│  Product-owner reviews user stories + acceptance criteria           │
│  Critic challenges assumptions, scope, feasibility                  │
│     ↓                                                               │
│  If verdict = revise → planner revises → re-critique                │
│  If verdict = approve → advance                                     │
│  If 3 rounds without approval → escalate to human                   │
│                                                                     │
│  Hook: SubagentStop on critic/product-owner verifies saved verdict  │
├─────────────────────────────────────────────────────────────────────┤
│  STAGE 3: IMPLEMENTATION PLANNING                                   │
│                                                                     │
│  Planner creates file-by-file implementation plan from approved     │
│  design. Tester reviews test strategy.                              │
│                                                                     │
│  Human approval gate: "Approve implementation plan?"                │
├─────────────────────────────────────────────────────────────────────┤
│  STAGE 4: IMPLEMENTATION CRITIQUE (iterative, max 2 rounds)        │
│                                                                     │
│  Critic reviews: feasibility, ordering, gaps, scope risk            │
│  Tester reviews: test coverage, strategy gaps                       │
│     ↓                                                               │
│  If verdict = revise → planner revises → re-critique                │
│  If verdict = approve → advance                                     │
│                                                                     │
│  Hook: SubagentStop on critic verifies saved verdict                │
├─────────────────────────────────────────────────────────────────────┤
│  STAGE 5: SLICE EXECUTION                                           │
│                                                                     │
│  For each slice in the implementation plan:                         │
│    1. Tester writes tests from spec (subagent)                      │
│    2. Builder implements                                            │
│    3. Builder runs tests                                            │
│    4. Builder runs post-implementation checks                       │
│    5. Reviewer reviews code (subagent)                              │
│    6. Builder fixes Critical/Major                                  │
│    7. Builder commits                                               │
│    8. Builder updates slice evidence in CURRENT-STATE               │
│                                                                     │
│  Hook: PreToolUse blocks code edits if Design Status ≠ approved     │
│  Hook: PostToolUse tracks test runs and file modifications          │
│  Hook: Stop checks slice evidence before allowing session end       │
├─────────────────────────────────────────────────────────────────────┤
│  STAGE 6: PHASE REVIEW                                              │
│                                                                     │
│  Code review: reviewer (quality, security, conventions)             │
│  Strategic review: planner or product-owner                         │
│    - Did this achieve the design plan's goals?                      │
│    - Do test results invalidate any planning assumptions?           │
│    - Verdict: accept | replan | propose vision update               │
│                                                                     │
│  Human confirmation gate: "Accept phase results?"                   │
├─────────────────────────────────────────────────────────────────────┤
│  STAGE 7: CLEANUP                                                   │
│                                                                     │
│  Phase-complete process:                                            │
│    - Verify acceptance criteria                                     │
│    - Record ADRs                                                    │
│    - Update open questions, tech debt, glossary                     │
│    - Sync docs (README, architecture, instructions)                 │
│    - Write wrap summary to docs/wraps/                              │
│    - Update CURRENT-STATE for next phase                            │
│    - Save context notes to /memories/repo/                          │
│                                                                     │
│  Hook: Stop verifies completion checklist before allowing session   │
│  end                                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Hook Architecture

### Core hooks (always active — `.github/hooks/`)

| Hook | Event | File | What It Does |
|------|-------|------|-------------|
| **Stage gate** | PreToolUse | `stage-gate.py` | Blocks code-editing tools (`create_file`, `replace_string_in_file`, `edit_notebook_file`, `run_in_terminal`) if `Stage` is not `executing` and the target file is source code (not plans/docs/state). Prevents coding before plans are approved. |
| **Tool guardrails** | PreToolUse | `tool-guardrails.py` | Blocks `git push --force`, `git reset --hard`, deletion of critical files, writes to `node_modules/`, path traversal. Always active, not a catalog item. |
| **Evidence tracker** | PostToolUse | `evidence-tracker.py` | After terminal commands containing `test`/`pytest`/`vitest`/etc., records test results. After subagent invocations, records review/critique verdicts. Writes evidence to CURRENT-STATE.md Slice Evidence section. |
| **Context pressure** | PostToolUse | `context-pressure.py` | Tracks accumulated tool I/O. When threshold exceeded, injects advisory to checkpoint and wrap up. Always active, not a catalog item. |
| **Session checkpoint** | Stop | `session-gate.py` | Replaces current `slice-gate.py`. Parses CURRENT-STATE.md machine-readable fields. Blocks stop if: (a) Stage is `executing` and Slice Evidence has unchecked items, (b) Stage is `cleanup` and completion checklist has unchecked items, (c) Stage is `reviewing` and strategic review is pending. Allows stop if Phase Status is `complete` or `blocked`. |

### Agent-scoped hooks

| Agent | Event | What It Does |
|-------|-------|-------------|
| **critic** | SubagentStop | Verifies the critic wrote a verdict file or updated Design/Implementation Status in CURRENT-STATE. Blocks stop if no verdict artifact exists. |
| **product-owner** | SubagentStop | Verifies user stories and acceptance criteria were written to the design plan. Blocks stop if artifact is missing. |
| **reviewer** | SubagentStop | Verifies review findings table was produced and Review Verdict was set. Blocks stop if no review artifact. |

### Conditional hooks (activated at bootstrap or phase start)

| Hook | Event | Trigger | File |
|------|-------|---------|------|
| **CI gate** | Stop | `.github/workflows/` exists | `ci-gate.py` |

---

## Core Agents (not catalog — always present)

### 1. `autonomous-builder` — Orchestrator

The builder's role simplifies significantly. It becomes a **stage orchestrator**, not a do-everything agent. Its job:

1. Read CURRENT-STATE.md, determine current stage
2. Execute the appropriate stage protocol
3. Delegate to subagents for all independent judgment (planning, critique, review, testing)
4. Update workflow state after each stage transition
5. Use `vscode_askQuestions` for human approval gates

The builder **does not**:
- Self-modify workflow instructions (removed)
- Auto-activate catalog items based on heuristics (removed)
- Contain detailed vision expansion protocol (use `/vision-expand`)
- Contain detailed bootstrap protocol (keep BOOTSTRAP.md but slimmed)

**Subagents:** planner, critic, product-owner, reviewer, tester, Explore

### 2. `planner` — Research, Design, and Planning

Expanded from current role. Still read-only. Now responsible for:
- Creating **design plans** (not just "phase plans") that include user stories, acceptance criteria, non-goals, risks, ADR candidates, and test strategy
- Creating implementation plans from approved designs
- Revising plans based on critique feedback
- Running strategic reviews after implementation ("did we build the right thing?")

### 3. `critic` — Adversarial Plan Review

**Promoted from catalog to core.** This is the most important change. The critic is what gives you the iterative back-and-forth before code is written.

- Reviews design plans: challenges assumptions, identifies scope risks, missing edge cases
- Reviews implementation plans: challenges feasibility, ordering, testing gaps
- **Produces a verdict**: approve / revise / rethink
- **SubagentStop hook** ensures verdict is recorded before the critic finishes
- Max 3 rounds on design, 2 rounds on implementation, then escalate to human

### 4. `product-owner` — User Perspective and Strategic Validation

**Promoted from catalog to core.** This is what ensures you're building the right thing.

- During design: writes user stories, maps user journeys, validates acceptance criteria
- During review: strategic validation — does the implementation actually achieve what the design intended?
- **SubagentStop hook** ensures artifacts are saved

### 5. `reviewer` — Code Quality and Security

Tightened to focus on code, not strategy. Code quality, architecture compliance, security, doc-sync checklist. No change to core function, but strategic review is now the product-owner's job.

### 6. `tester` — Test-from-Spec

Restrict tools to prevent reading implementation:
```yaml
tools:
  - search
  - search/codebase
  - edit
  - run_in_terminal
```
Remove `read` access to implementation directories (or instruct against it — tool restrictions are the real enforcement; instructions are backup).

### Catalog agents (conditional — human-chosen at bootstrap/phase start)

| Agent | When to activate |
|-------|-----------------|
| `designer` | Frontend/UI code exists |
| `security-reviewer` | Auth, payments, PII handling |

These are activated at bootstrap or phase start via human decision, not autonomous heuristics. Present options via `vscode_askQuestions`: "Your project has frontend code. Activate the designer agent? [Yes / No / Later]"

---

## What Gets Cut

| Item | Why |
|------|-----|
| **Autonomous catalog activation heuristics** | Fragile, burns context evaluating rules. Replace with human-choice at bootstrap/phase start. |
| **Vision expansion mode in builder** | 30+ lines for a rare event. `/vision-expand` prompt handles it better. Builder just sets `Blocked: run /vision-expand` and stops. |
| **Self-modification permission** | Unreliable. Builder can *propose* improvements to CURRENT-STATE under `## Proposed Workflow Improvements`. Humans execute them. |
| **"Improve the development system" section** | Corollary of above. Remove from builder. Keep the improvement log as a place humans record changes. |
| **Excessive context links** | Each agent gets 2-3 mandatory reads. Others are "consult on demand" without path listings. Trust Explore subagent. |
| **Catalog auto-evaluate triggers table** | Remove the phase-trigger heuristic matrix from builder. Replace with one-time evaluation at bootstrap. |
| **Tool guardrails as catalog item** | Promote to always-on core hook. |
| **Context checkpoint as catalog item** | Promote to always-on core hook. |

---

## What Gets Added

| Item | Why |
|------|-----|
| **Machine-readable CURRENT-STATE.md** | Hooks can parse and enforce state. Enables real stage gating. |
| **Stage gate hook (PreToolUse)** | Blocks code edits before plans are approved. The single most impactful enforcement. |
| **Evidence tracker hook (PostToolUse)** | Records test results and review verdicts automatically. |
| **SubagentStop hooks** | Enforce that critic/product-owner/reviewer produce artifacts before completing. |
| **Design plan (expanded phase plan)** | Includes user stories, acceptance criteria, ADR candidates, test strategy. Not just features + deps. |
| **Iterative critique loop** | Design plan → critique → revise → re-critique. Max 3 rounds. Explicit and bounded. |
| **Strategic review** | Post-implementation: did we achieve the design? What assumptions were wrong? |
| **Wrap summaries** | `docs/wraps/` — self-contained phase summary for cross-session context. Proven in wyoclear. |
| **Human decision gates** | `vscode_askQuestions` at plan approval and post-review. Lightweight, one question each. |
| **Session gate hook** | Replaces slice-gate.py. Parses machine-readable state, checks slice evidence + completion checklist. |

---

## Revised Prompt Surface

The prompts shift from being the primary workflow to being **human override entry points** and **approval artifacts**. The autonomous builder drives the stage pipeline; prompts are for when you want manual control.

| Prompt | Role | Change |
|--------|------|--------|
| `/vision-expand` | Interactive vision brainstorm | Keep as-is. Builder defers to it. |
| `/design-plan` | Create design plan (renamed from phase-plan) | Expanded: user stories, acceptance criteria, non-goals, risks, ADR candidates, test strategy |
| `/implementation-plan` | Create implementation plan | Mostly unchanged. References approved design plan. |
| `/implement` | Execute implementation plan | Unchanged. |
| `/code-review` | Code quality review | Tightened to code focus. |
| `/strategic-review` | Post-implementation plan-vs-reality check | **New.** Evaluates whether implementation achieved design intent. |
| `/phase-complete` | Cleanup and wrap-up | Enhanced: generates wrap summary, enforced by hook. |
| `/PROMPT-GUIDE` | Guide to all prompts and agents | Updated to reflect new flow. |

---

## The Enforcement Reality Check

### What's actually enforced (deterministic, hook-verified)

- Cannot edit source code before design plan is approved (PreToolUse stage gate)
- Cannot stop session with incomplete slice evidence (Stop hook)
- Cannot stop session with incomplete phase checklist (Stop hook)
- Cannot complete critique without producing a verdict artifact (SubagentStop)
- Cannot complete review without producing findings (SubagentStop)
- Cannot use `git push --force` or delete critical files (PreToolUse guardrails)

### What's strongly guided (instruction-level, not mechanically verified)

- Quality of critique (hook verifies artifact exists, not quality)
- Test coverage adequacy (hook verifies tests ran, not coverage)
- Strategic review depth (hook verifies review happened, not thoroughness)
- Doc-sync completeness (hook verifies checklist is checked, not content accuracy)

### What's advisory (pure instructions, no verification)

- Code style and conventions
- Commit message format
- When to use subagents vs. do things inline
- Error recovery strategy

The template should clearly distinguish these tiers rather than claiming everything is "enforced."

---

## Implementation Sequence

### Phase A — State Machine and Core Hooks

1. Redesign `CURRENT-STATE.md.jinja` with machine-readable workflow state
2. Write `stage-gate.py` (PreToolUse — blocks code edits before plan approval)
3. Write `session-gate.py` (Stop — replaces slice-gate.py, parses full state)
4. Promote `tool-guardrails.py` from catalog to core hook (move to `.github/hooks/scripts/`)
5. Promote `context-pressure.py` from catalog to core hook
6. Write `evidence-tracker.py` (PostToolUse — records test/review evidence)

### Phase B — Core Agent Restructure

1. Promote critic to core agent (move from catalog to `.github/agents/`), add SubagentStop hook
2. Promote product-owner to core agent, add SubagentStop hook
3. Add SubagentStop hook to reviewer
4. Rewrite `autonomous-builder.agent.md.jinja` as stage orchestrator
5. Expand planner to handle design plans + strategic reviews
6. Restrict tester tools

### Phase C — Pipeline Prompts

1. Rename/expand `phase-plan` → `design-plan` with user stories, acceptance criteria, ADR candidates, test strategy
2. Add `/strategic-review` prompt
3. Enhance `/phase-complete` to produce wrap summary
4. Update all prompts to reference machine-readable state
5. Add wrap summary template to `docs/wraps/`

### Phase D — Cleanup

1. Remove vision expansion mode from builder (defer to `/vision-expand`)
2. Remove self-modification permission from builder
3. Remove catalog auto-activation heuristics (replace with bootstrap-time human choice)
4. Slim context links in all agents
5. Update `PROMPT-GUIDE`, `AGENTS.md`, `copilot-instructions.md`, `BOOTSTRAP.md`
6. Update `MANIFEST.md` to reflect promotions and new catalog boundary
7. Reconcile autopilot vs. manual inconsistencies in instructions

---

## Open Questions + Recommendations

### OQ-1: Tester tool restriction

**Question:** The tester's "don't read implementation" promise can be partially enforced by removing `read` from its tools list — but this also prevents it from reading test utilities, framework configs, and existing test patterns.

**Options:**
- (a) Restrict tools and accept the tester can't read existing test patterns (purer isolation, but may write tests that don't match project conventions)
- (b) Use instruction-level rule only, accept it's not mechanically enforced (pragmatic, but the tester could look at implementation)
- (c) Use a PreToolUse hook on the tester that blocks reads to `src/` but allows reads to `tests/`, `__tests__/`, `*.test.*`, `*.spec.*` (best of both worlds, more hook complexity)

**Recommendation:** Option (c). The hook can be simple — check if `tool_name` is a read tool and the path matches implementation directories. The tester needs to read test patterns but not implementation code.

### OQ-2: Bootstrap pattern

**Question:** The parallel analysis suggests dropping the self-deleting BOOTSTRAP.md. The current pattern has merit (keeps builder lean after first session) but adds branching logic to the builder.

**Options:**
- (a) Keep self-deleting BOOTSTRAP.md, slim it significantly
- (b) Move bootstrap logic into a dedicated `bootstrap.agent.md` that is only used for first session, then `user-invocable: false` after
- (c) Move bootstrap into the builder's SessionStart hook (inject bootstrap context on first session only)
- (d) Make bootstrap a prompt (`/bootstrap`) that the user explicitly runs

**Recommendation:** Option (a) with significant slimming. The self-deleting pattern is elegant — the builder checks for BOOTSTRAP.md, follows it, deletes it, never thinks about it again. But the current BOOTSTRAP.md is too long (140+ lines). Slim it to: detect project type → interview or synthesize → write vision + phase 1 design → delete self. Move the catalog evaluation to a separate step the builder does after bootstrap.

### OQ-3: Human gate implementation under autopilot

**Question:** The design proposes `vscode_askQuestions` at plan approval and post-review. Under full autopilot, these get auto-responded. This undermines the approval model.

**Options:**
- (a) Accept that autopilot skips gates (autonomy-first). The builder decides on its own. Hooks still enforce artifacts exist.
- (b) Use `Blocked` status to force a session break at gates (safety-first). The builder sets `Stage: blocked` with reason, the Stop hook allows it, and the human must restart a new session to continue.
- (c) Make it configurable: check for a `## Gate Policy` field in CURRENT-STATE. Values: `autonomous` (gates are self-approved with logged reasoning), `interactive` (gates use vscode_askQuestions), `strict` (gates block the session).
- (d) Hybrid: design plan approval is always a session break (too important to auto-approve), but slice-level reviews are autonomous.

**Recommendation:** Option (d). The design plan is the highest-leverage approval point — getting it wrong wastes an entire phase of work. Force a session break there. Implementation plan approval and phase review can be autonomous with logged reasoning under autopilot, or interactive under manual mode. This gives you the "autonomy inside approved bounds" model: once the design is human-approved, the builder can execute autonomously within it.

### OQ-4: Catalog boundary after promotions

**Question:** With critic and product-owner promoted to core, the catalog shrinks to designer, security-reviewer, and the skills/patterns. Is that enough to justify the catalog infrastructure (MANIFEST.md, activation protocol, catalog/ directory tree)?

**Options:**
- (a) Keep catalog as-is, just smaller. The infrastructure is already built and works.
- (b) Collapse catalog into a simpler `optional/` directory with a README. No MANIFEST.md, no activation protocol. Just "copy this file to .github/agents/ if you want it."
- (c) Remove catalog entirely. Ship designer and security-reviewer as commented-out agents in `.github/agents/` with a note saying "uncomment if needed."
- (d) Keep catalog but make MANIFEST.md a skill (already is) and remove the activation protocol from the builder. Activation is manual only.

**Recommendation:** Option (d). The catalog infrastructure is lightweight and the MANIFEST.md-as-skill pattern is clever — any agent can discover available capabilities by reading it. But remove the builder's autonomous activation protocol. Catalog items are activated by humans (at bootstrap via `vscode_askQuestions` or manually later). This eliminates the fragile heuristic matching while preserving discoverability.

### OQ-5: Stage gate granularity for PreToolUse

**Question:** The stage gate hook needs to distinguish "source code edits" from "plan/doc/state edits." The builder legitimately needs to edit CURRENT-STATE.md, plan docs, and roadmap files during non-executing stages. How to draw the line?

**Options:**
- (a) Allowlist approach: during non-executing stages, only allow edits to files matching `roadmap/**`, `docs/**`, `CURRENT-STATE.md`, `.github/**`. Block everything else.
- (b) Blocklist approach: during non-executing stages, block edits to files matching `src/**`, `app/**`, `lib/**`, `tests/**`, `*.py` (non-hook), `*.ts`, `*.js`, etc. Allow everything else.
- (c) Convention-based: the template establishes that source code lives under `src/` (or a configured path). The hook reads a `source_root` config from CURRENT-STATE.md or copilot-instructions.md.

**Recommendation:** Option (c) with fallback to (a). Add a `- **Source Root**: src/` field to Workflow State. The stage gate allows edits only outside the source root during planning stages. Default to `src/` if not specified. This is the most template-friendly approach — different projects have different layouts, and a configurable source root handles that without hardcoding.

### OQ-6: Handling the first phase (no prior state)

**Question:** On the very first phase after bootstrap, there's no prior implementation to strategically review, no existing patterns for the tester to read, and the design plan is being created from a fresh vision. Should the stage pipeline have a "first phase" mode that skips or simplifies certain stages?

**Options:**
- (a) No special handling. The full pipeline runs even for phase 1. Critique may be shallow but the practice is still valuable.
- (b) Phase 1 uses a simplified pipeline: design plan → critique (1 round) → implementation plan → execute → review → cleanup. Skip implementation critique and strategic review.
- (c) Phase 1 gets a `first_phase: true` flag in Workflow State. Hooks are more lenient (e.g., strategic review is `n/a` by default).

**Recommendation:** Option (a). The pipeline shouldn't have special modes — that's complexity without proportional benefit. The critique may be lighter on phase 1, but running it establishes the habit and catches issues even on a fresh codebase. The product-owner's user stories are arguably *most* valuable on phase 1 when there's no existing code to ground decisions.

### OQ-7: Wrap summary placement and format

**Question:** Wrap summaries are proven valuable in wyoclear. Where should they live and what's the minimum viable format for the template?

**Options:**
- (a) `docs/wraps/phase-N-wrap.md` — dedicated directory, one file per phase (wyoclear pattern)
- (b) Appended to the phase design plan as a final section
- (c) Written to `/memories/repo/` as session notes (leverages existing memory system)

**Recommendation:** Option (a). Wraps are distinct from plans (they summarize *what actually happened* vs. *what was planned*) and distinct from session notes (they're phase-level, not session-level). The dedicated directory makes them easy to find and list. The template should include a `docs/wraps/README.md` explaining the format.

---

## Revised Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                    CORE AGENTS (always present)                     │
│                                                                    │
│  autonomous-builder  planner  critic  product-owner  reviewer      │
│  tester  Explore                                                   │
├────────────────────────────────────────────────────────────────────┤
│                    CATALOG AGENTS (human-chosen)                    │
│                                                                    │
│  designer  security-reviewer                                       │
├────────────────────────────────────────────────────────────────────┤
│                    CORE HOOKS (always active)                       │
│                                                                    │
│  PreToolUse:  stage-gate.py, tool-guardrails.py                    │
│  PostToolUse: evidence-tracker.py, context-pressure.py             │
│  Stop:        session-gate.py                                      │
│                                                                    │
│  Agent-scoped SubagentStop: critic, product-owner, reviewer        │
├────────────────────────────────────────────────────────────────────┤
│                    PROMPTS (human overrides)                        │
│                                                                    │
│  /vision-expand  /design-plan  /implementation-plan  /implement    │
│  /code-review  /strategic-review  /phase-complete                  │
├────────────────────────────────────────────────────────────────────┤
│                    STATE (machine-readable)                         │
│                                                                    │
│  CURRENT-STATE.md (workflow state + slice evidence + checklist)     │
│  roadmap/phases/ (design plans + implementation plans)              │
│  docs/wraps/ (phase wrap summaries)                                │
└────────────────────────────────────────────────────────────────────┘
```

---

## Enforcement Tiers (be honest about these in docs)

### Tier 1: Deterministic (hook-verified)

- Cannot edit source code before design plan is approved (PreToolUse stage gate)
- Cannot stop session with incomplete slice evidence (Stop hook)
- Cannot stop session with incomplete phase checklist (Stop hook)
- Cannot complete critique without producing a verdict artifact (SubagentStop)
- Cannot complete review without producing findings (SubagentStop)
- Cannot use `git push --force` or delete critical files (PreToolUse guardrails)

### Tier 2: Strongly guided (instruction-level, artifact-verified)

- Quality of critique (hook verifies artifact exists, not quality)
- Test coverage adequacy (hook verifies tests ran, not coverage)
- Strategic review depth (hook verifies review happened, not thoroughness)
- Doc-sync completeness (hook verifies checklist is checked, not content accuracy)

### Tier 3: Advisory (pure instructions, no verification)

- Code style and conventions
- Commit message format
- When to use subagents vs. do things inline
- Error recovery strategy (bounded retries, tech debt recording)
