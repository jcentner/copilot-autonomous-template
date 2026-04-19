# ADR-011: Strategy stage and three-gate human approval

## Status

Accepted (April 2026, v1.2)

## Context

Real use of v1.1 in [WyoClear](https://github.com/jakce/wyoclear) bootstrap revealed three friction points:

1. **Planner-led unilateral phase selection.** After bootstrap, the autonomous-builder advanced straight from `planning` into `design-critique` using whatever phase the planner had produced — no checkpoint where a human said "yes, *this* is the next phase to work on." Strategic context (open questions, tech debt, deferred items in wraps, externally-detected systems) was available but not consulted at a deliberate moment.
2. **Commits-to-main risk.** Nothing in the workflow refused a `git commit` on the default branch. The autonomous loop could (and on first dogfood did) commit the entire bootstrap directly to `main` instead of a feature branch.
3. **Verdict transcription friction.** The critic agent was responsible for writing both its findings artifact AND mutating `Design Critique Rounds` / `Design Status` / `Stage` / `Blocked Kind` / `Next Prompt` in `state.md`. Two failure modes followed: (a) state mutations diverged from the artifact (artifact said "approve", state field still said `in-critique`), and (b) double-increments when the critic *and* the orchestrator both touched the rounds counter.

In parallel, the researcher capability — previously suggested as a catalog item — surfaced as a real need: design-plan claims about external systems were going un-grounded, and the only way to ground them was an ad-hoc `fetch_webpage` call that left no durable artifact for the next session.

## Decision

Five coupled changes for v1.2.0:

### 1. New `strategy` stage and `/strategize` prompt

Insert `strategy` between `bootstrap` and `planning` (and as the loop-back target from `cleanup`, replacing the old direct loop to `planning`). The `/strategize` prompt:

- Reads vision + open questions + tech debt + recent CURRENT-STATE.md context (including any "detected external systems" line written during bootstrap).
- Produces ≥3 ranked candidate phases, including at least one not present in `docs/plans/`.
- Presents candidates via `vscode_askQuestions` with a "save and let me think" escape.
- Writes a timestamped artifact at `roadmap/strategy-YYYYMMDD-HHMMSSZ.md` (lex-sortable so `sorted(glob)[-1]` is canonical).

Stage sequence becomes:

```
bootstrap → strategy → planning → design-critique → [GATE]
       → implementation-planning → implementation-critique → executing
       → reviewing → cleanup → [GATE] → strategy (loop)
```

### 2. Three hook-enforced human-approval gates

All three are realised as `Stage: blocked` + a specific `Blocked Kind`. The session-gate Stop hook holds the gate regardless of autopilot setting:

- **Strategy approval** — only when the human chose "save and let me think". Inline approval (the default path) advances same-session. `Blocked Kind: awaiting-strategy-approval`.
- **Design approval** — always required (preserves [ADR-005](005-design-approval-as-session-break.md)'s session-break invariant). `Blocked Kind: awaiting-design-approval`.
- **Merge approval** — always required after `cleanup`. The agent never executes the merge — `/merge-phase` only prepares commands or a PR URL. `Blocked Kind: awaiting-merge-approval`.

Reconciles with [ADR-005](005-design-approval-as-session-break.md): design approval remains a hard session break; the new strategy gate is the human's choice (inline or session-break); the new merge gate is mandatory.

### 3. Researcher promoted to core (no terminal access)

Researcher is now a core agent (alongside planner / critic / reviewer / product-owner / tester), not a catalog item. Its toolset deliberately **excludes terminal access** (`run_in_terminal`, `send_to_terminal`) to close the prompt-injection-via-fetched-content → shell-execution attack surface. Output is `docs/reference/<topic>.md` with mandatory ISO8601-dated citations.

Verification is **caller-side**, not hook-enforced: per [ADR-010](010-three-tier-enforcement-honesty.md), a presence-only SubagentStop check that can't tell which `<topic>.md` corresponds to *this* invocation would be enforcement theatre. The orchestrator reads the researcher's handoff message and confirms the file path.

### 4. `record-verdict.py` is the sole writer of critique-rounds + verdict mutations

The critic agent **does not write `state.md`** anymore. After it returns, the orchestrator runs `python3 .github/hooks/scripts/record-verdict.py {design|impl} R<n>`, which:

- Parses a single `^VERDICT: (approve|revise|rethink)$` trailer line from the round artifact.
- Refuses missing / ambiguous / lowercase trailers.
- Refuses round arguments that don't follow the current counter (`R<current+1>` only).
- Refuses over-cap rounds (3 design / 2 impl per [ADR-004](004-stage-pipeline-and-critique-loops.md)).
- Asymmetric mutations: design-approve goes to `awaiting-design-approval` (human gate); impl-approve advances directly to `executing` (no gate).

The critic SubagentStop hook now verifies only artifact presence + trailer well-formedness — not state fields, which are stale-by-design at the moment the critic returns.

### 5. Universal `Next Prompt` surfacing + branch-gate

- New `Next Prompt` machine field in `state.md`, written by every Stage transition. The Stop hook surfaces it (top-level `systemMessage` per Copilot hooks docs) on every session end so the human always knows the next slash-command to run.
- New `Merge Mode` field (`cli` | `pr`), picked at bootstrap via `vscode_askQuestions` with no default.
- New `branch-gate.py` PreToolUse hook refuses `git commit` on denylisted branches (default: `main`, `master`, `trunk`, `prod`, `release/*`). Bootstrap stage exempt. Config at `.github/hooks/config/branch-policy.json`.
- New `evidence-status: present | needed | unmeasurable` finding tag in critic prompt; paired with `evidence-gathering` skill describing the audit patterns (live API call, schema dump, dependency inventory). Critic may not issue `approve` while any finding is tagged `needed`.
- New `/scrap-phase` prompt (refuses on dirty tree; archives artifacts under `roadmap/phases/_archived/`; **leaves `Phase` unchanged** — the burned number is reused by the next pick).
- New `/catalog-review` prompt (re-presents catalog picker mid-flight; activation only — never deactivates).

## Authority hierarchy interaction

This ADR adds no new authority-hierarchy rules. The vision lock remains highest authority; the new gates are workflow steps that respect it.

## Consequences

### Positive

- **Strategic intent is now an explicit, dated artifact** (`roadmap/strategy-*.md`), not an implicit byproduct of whatever the planner produced first.
- **Three deliberate human checkpoints** survive autopilot. Users can run autopilot during design-critique through executing without losing strategy / design / merge oversight.
- **Direct-to-main commits are prevented at the tool-call layer**, not just by convention.
- **Verdict recording is single-writer.** No more split-brain between critic state writes and orchestrator state writes; `record-verdict.py` either succeeds atomically or refuses with a parseable error.
- **External-system grounding has a durable home** (`docs/reference/`) that the next strategize round can cite.
- **Honest enforcement vocabulary** — researcher's caller-side verification is documented as such in `copilot-instructions.md` and AGENTS.md, not falsely advertised as hook-enforced.

### Negative

- **More state-machine vocabulary** — three new `Blocked Kind` values, two new state fields (`Next Prompt`, `Merge Mode`), one new Stage value. Documented in `state.md` comment block; smoke test asserts presence.
- **Phase-number reuse on scrap** is a sharp edge: a scrapped Phase 1 becomes a new Phase 1, not Phase 2. This is intentional (no merge happened, so git history doesn't have the burned number) but easy to misremember. Documented in the `/scrap-phase` prompt itself and in the dispatch table.
- **`Merge Mode: n/a` on `copier update`** of v1.1 projects requires a manual one-time edit; `/merge-phase` refuses to run until it's set. CHANGELOG calls this out.
- **More prompts** to discover (`/strategize`, `/research`, `/scrap-phase`, `/catalog-review`, `/merge-phase`). Mitigated by the universal `Next Prompt` surfacing — the user is told what to run next.

### Neutral

- The researcher-as-core decision means existing in-flight projects on `copier update` see a new agent appear in `.github/agents/`. This is additive; no removal happens.
- `evidence-status` finding tags are advisory until a future version teaches `record-verdict.py` to scan for unresolved `needed` findings. v1.2 relies on the critic's good faith (Tier 2 per [ADR-010](010-three-tier-enforcement-honesty.md)).

## References

- [ADR-003](003-agents-write-state-hooks-verify.md) — agents write state, hooks verify. Block 3 narrows this for the critic: the critic now writes the artifact only, and `record-verdict.py` (a CLI orchestrator-side, not a SubagentStop hook) writes the state. Hooks still verify.
- [ADR-004](004-stage-pipeline-and-critique-loops.md) — round caps (3 design / 2 impl) enforced by `record-verdict.py`.
- [ADR-005](005-design-approval-as-session-break.md) — design-approval session-break invariant preserved; strategy approval is a softer cousin (inline or session-break by human choice).
- [ADR-009](009-bootstrap-carve-out-and-protected-state.md) — bootstrap stage remains exempt from `branch-gate.py` and `stage-gate.py` per the same carve-out logic.
- [ADR-010](010-three-tier-enforcement-honesty.md) — researcher's caller-side verification is documented as Tier 2 (artifact-verified, no hook), not falsely advertised as Tier 1.
