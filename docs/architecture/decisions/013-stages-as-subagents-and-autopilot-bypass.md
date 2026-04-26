# ADR-013: Stage protocols are subagents; the orchestrator is a dispatch table

## Status

Accepted (April 2026, v1)

Extends and generalizes [ADR-012](012-slice-loop-as-subagent.md) (slice loop) and supersedes the strategy-stage portion of [ADR-011](011-strategy-stage-and-three-gate-approval.md) (the bits about how strategy execution lives in `/strategize` are now incorrect: the prompt is a thin wrapper; the strategist subagent owns the protocol).

## Context

After ADR-012 extracted the slice loop into the `slice-runner` subagent, the autonomous-builder file dropped from 262 to ~200 lines but still re-implemented two stage protocols inline:

- **Strategy** (`Stage: strategy`) — read open questions / tech debt / wraps / context, rank candidates, produce ≥3, ask via `vscode_askQuestions` or pick under autopilot, write timestamped artifact, cut phase branch, stamp state. ~30 lines of orchestrator prose, with a parallel copy in `/strategize`.
- **Cleanup** (`Stage: cleanup`) — acceptance criteria, ADRs, open questions / tech debt / glossary, doc-sync resolution, wrap summary, repo memory, vision check, hand-off to merge gate. ~30 lines of orchestrator prose, with a parallel copy in `/phase-complete`.

The pattern was identical to the slice-loop case ADR-012 fixed:

1. Inline protocol in the orchestrator → orchestrator turns into "everything-agent."
2. Parallel copy in a prompt for human override → drift inevitable.
3. The orchestrator's reasoning loop carries the protocol's full token cost on every iteration, even when the protocol is a one-shot at one stage boundary.

A second pain point surfaced empirically: the orchestrator was constantly being told "switch to phase branch" or "switch to strategy branch" because branch transitions lived in prose ("run `git checkout -b phase/N-...`") instead of a helper. Different prompts had different incantations (some pulled, some didn't, some refused to switch off `phase/*` first, none refused on dirty trees), and the orchestrator routinely picked the wrong one.

A third pain point: the v1 design treated **all** human gates as session-breaks under autopilot. In practice the strategy-pick and design-approval gates are soft (the reviewer is in the loop later anyway) while merge is hard (autopilot can't `git push`). Bundling them at the same severity meant heads-down sessions kept stopping for things the human didn't actually want to gate.

## Decision

### 1. One subagent per stage

Each `Stage` value gets exactly one owning subagent. The orchestrator's body becomes a **dispatch table**: a 13-row table mapping `Stage` to subagent + on-return action. No stage protocol prose lives in the orchestrator.

| Stage | Subagent | Pre-existing? |
|-------|----------|--------------|
| `bootstrap` | (BOOTSTRAP.md, no agent) | yes |
| `strategy` | `strategist` | **new (this ADR)** |
| `planning` | `planner` (planning mode) | yes |
| `design-critique` | `product-owner` + `critic` | yes |
| `implementation-planning` | `planner` (impl mode) | yes |
| `implementation-critique` | `critic` | yes |
| `executing` | `slice-runner` | ADR-012 |
| `reviewing` | `product-owner` (review mode) | yes |
| `cleanup` | `phase-completer` | **new (this ADR)** |
| `blocked` / `complete` | (no agent — stop) | yes |

The corresponding prompts (`/strategize`, `/design-plan`, `/implementation-plan`, `/implement`, `/code-review`, `/strategic-review`, `/phase-complete`) all become thin dispatch wrappers (≤120 lines, smoke-enforced). The protocol lives in exactly one place: the subagent file.

### 2. Branch transitions are a helper, not prose

`.github/hooks/scripts/cut-branch.py` centralizes every workflow branch transition with subcommands `strategy [--pull]` and `phase --number N --title "..."`. The helper:

- refuses to run on a dirty tree (exit 3),
- switches off any current `phase/*` branch to trunk before cutting (avoids carrying scrapped commits forward),
- is idempotent (re-checks-out an existing branch instead of failing),
- is the sole git-checkout site referenced by BOOTSTRAP, the strategist subagent, and the resume prompt.

The orchestrator never runs `git checkout` for workflow branches. Smoke asserts BOOTSTRAP.md and resume.prompt.md both reference `cut-branch.py` and contain no inline `git checkout -b phase/...` / `strategy/...` commands.

### 3. Two-tier autopilot with `Autopilot` field in `state.md`

Add a new `Autopilot: on|off` field to `roadmap/state.md` (default `off`). It is a workflow-level switch, separate from VS Code's per-tool `chat.autopilot.enabled`:

| Switch | Lives in | Controls |
|--------|----------|----------|
| `chat.autopilot.enabled` | VS Code settings | Whether tool calls auto-confirm. |
| `Autopilot` field | `roadmap/state.md` | Whether the orchestrator pauses at the **soft** human gates. |

Soft gates (bypassed under `Autopilot: on`):

- **Strategy candidate pick** — strategist skips `vscode_askQuestions`, picks the top-ranked candidate, records rationale in artifact + `## Context`.
- **Design-plan approval** — `record-verdict.py design <round> approve` checks `is_autopilot()` and routes straight to `Stage: implementation-planning` instead of `blocked + awaiting-design-approval`.

Hard gates (always pause):

- **Merge approval** (`awaiting-merge-approval`) — autopilot cannot run `git push` / `gh pr create`.
- All escalation blocks: `awaiting-vision-update`, `awaiting-human-decision`, `error`, `vision-exhausted`.

The `Autopilot` field is **not** in `STATE_HELPER_REQUIRED_FIELDS`. It's flipped via direct line-shape edit; the line-shape carve-out in `tool-guardrails.py` allows it. `is_autopilot()` in `_state_io.py` reads the field and returns `True` only on exact `"on"` (fail-closed).

This amends ADR-005 (design-approval as session break) — the gate is now conditional on `Autopilot: off`. Under `Autopilot: on`, the design-approval session break is consciously removed; the strategic review at end-of-phase remains the human's quality backstop.

## Consequences

### Positive

- Orchestrator drops to a true coordinator (~290 lines, almost all of it the dispatch table + cross-cutting concerns + non-negotiable rules — no stage-protocol prose).
- Each stage's protocol has a single source of truth. Drift between prompt and orchestrator is structurally impossible (the prompt dispatches the same subagent).
- Per-stage context: each stage's subagent runs in its own isolated context window, so the orchestrator's loop carries only summaries between stages.
- Branch friction goes to zero: helper handles all four workflow branch transitions consistently.
- Heads-down sessions actually stay heads-down. Soft gates collapse; the merge gate still fires.
- Easier to evolve. A new stage = a new subagent + one row in the dispatch table; no surgical edits to the orchestrator's prose.

### Negative

- More agent files (10 core agents now, up from 7). Cognitive load when reading the codebase, but each file is small and single-purpose.
- Nesting depth: orchestrator → slice-runner → tester/reviewer is depth 2. `chat.subagents.allowInvocationsFromSubagents: true` is required (BOOTSTRAP prompts for it). Other branches stay at depth 1.
- The autopilot-bypass of design-approval changes risk profile. A genuinely bad design plan now reaches `executing` if the human had `Autopilot: on`. Mitigation: the critic round must already pass before the bypass kicks in; the strategic review can still set `Strategic Review: replan` and bounce the phase.

### Neutral

- ADR-005 stays accepted but is amended in scope: the design-approval gate is conditional on `Autopilot: off`, not unconditional.
- ADR-011's strategy-stage section is partially superseded — the strategy stage still exists with the same purpose, but execution moved from `/strategize` into the strategist subagent.

## Alternatives considered

- **Keep all stage protocols inline in the orchestrator and just slim the prose**: rejected. Same root cause as ADR-012 (everything-agent + drift between prompt and agent).
- **One mega-subagent that handles every non-executing stage**: rejected. Defeats per-stage isolated context; one bug in one stage's protocol contaminates all others' agent files.
- **Make `/strategize` callable as a subagent**: rejected. Per the [VS Code prompt-files docs](https://code.visualstudio.com/docs/copilot/customization/prompt-files), prompts are "invoked manually in chat" — there is no documented mechanism for an agent to invoke a prompt file as a callable. Subagents are the only documented agent-callable delegation primitive.
- **A `/autopilot on|off` slash-command instead of a state-md field**: rejected. Slash-commands are user-only invocations; the orchestrator can't run them. A state field is readable by every hook and helper without ceremony, and the line-shape carve-out already handles direct edits safely.

## How we'll know it worked

- Empirical signal during the next phase: zero "switch to phase branch" or "switch to strategy branch" prompts from the human. If branch friction returns, the helper has a gap.
- The orchestrator's per-session token budget for non-executing stages should drop. Each stage handoff carries a subagent summary, not the full protocol.
- A heads-down session with `Autopilot: on` should run from strategy through cleanup with exactly one stop: the merge gate. If it stops anywhere else, either there's a real escalation (legitimate) or a soft gate slipped through (bug).

## References

- [VS Code custom agents docs](https://code.visualstudio.com/docs/copilot/customization/custom-agents) — agent file format, subagent invocation contract.
- [VS Code subagents docs](https://code.visualstudio.com/docs/copilot/agents/subagents) — coordinator/worker pattern; `chat.subagents.allowInvocationsFromSubagents` for nesting beyond depth 1.
- [VS Code prompt-files docs](https://code.visualstudio.com/docs/copilot/customization/prompt-files) — confirms prompts are user-invoked only.
- ADR-012 — slice-loop extraction (the precedent).
- ADR-005 — amended; design-approval gate now conditional on `Autopilot: off`.
- ADR-011 — strategy-stage execution moved from `/strategize` into `strategist` subagent.
