# Phase D — Cleanup, Slimming, and Reconciliation

> Goal: Remove what the v2 proposal cuts, slim bloated files, and reconcile inconsistencies.
> Depends on: Phases A, B, C.

## Exit criteria

- [ ] Builder no longer contains vision expansion detailed protocol, self-modification permission, or catalog auto-activation heuristics
- [ ] BOOTSTRAP.md slimmed to ~50 lines
- [ ] Every agent file has ≤ 3 mandatory "read first" links; everything else is "consult on demand"
- [ ] `MANIFEST.md` reflects final catalog boundary (2 agents, 4 skills, 0 hooks moved to core, 2 prompts, 2 patterns)
- [ ] `PROMPT-GUIDE`, `AGENTS.md`, `copilot-instructions.md` reconciled — no autopilot/manual contradictions
- [ ] Catalog activation happens at bootstrap via `vscode_askQuestions`, not heuristics
- [ ] End-to-end smoke test: generated project, bootstrap a fake project, reach executing stage, run a slice, complete phase

## Work items

### D1. Strip vision expansion from builder

File: `template/.github/agents/autonomous-builder.agent.md.jinja`

- Remove the "Vision expansion mode" section entirely.
- In the stage dispatch table, the `complete` row reads only: `Set Stage=blocked with reason "Run /vision-expand to propose next directions." Stop.`

### D2. Remove self-modification permission

- Remove any language in `autonomous-builder.agent.md.jinja` or `copilot-instructions.md.jinja` that permits the agent to edit its own instructions, prompts, or hook scripts during a phase.
- Add a new section to CURRENT-STATE structure (update `CURRENT-STATE.md.jinja` if missed in Phase A): `## Proposed Workflow Improvements` — builder writes suggestions here; humans apply them manually.
- Update the agent improvement log reference (`template/docs/reference/agent-improvement-log.md`) with a note: "Entries added here by humans after reviewing Proposed Workflow Improvements in CURRENT-STATE."

### D3. Remove catalog auto-activation heuristics

- Remove the trigger heuristic table from the builder (any table like "bootstrap → tool-guardrails; 5+ slices → critic").
- Replace the "Workflow catalog" dormant references in the builder with a one-liner: "Catalog items are activated manually by the human at bootstrap or phase start. See `.github/catalog/MANIFEST.md`."
- Ensure the builder does not read MANIFEST.md autonomously during a phase — only at bootstrap.

### D4. Slim BOOTSTRAP.md to ~50 lines

File: `template/BOOTSTRAP.md.jinja`

Target structure:

1. **Purpose** (2 lines): first-session bootstrap, self-deletes on completion.
2. **Detect project type** (3 lines): greenfield (empty repo) vs existing (has source).
3. **Delegate interview** (3 lines): invoke planner subagent with prompt "Run a deep-interview for {{ project_name }} and produce VISION-LOCK draft + phase 1 design plan."
4. **Write outputs** (4 lines): planner returns → builder writes `docs/vision/VISION-LOCK.md` + `roadmap/phases/phase-1-design.md`.
5. **Catalog selection** (6 lines): `vscode_askQuestions` with options for designer, security-reviewer, ci-gate, and any other catalog items applicable to detected project type.
6. **Finalize** (4 lines): set CURRENT-STATE Stage=`design-critique`, append Session Log entry, delete BOOTSTRAP.md.

Cut from current version:
- The 4-round inline interview protocol (planner owns it now)
- Stack skills creation loop (moved into phase 1 executing stage — builder creates stack skills per adopted technology during implementation)
- Any catalog evaluation heuristics

### D5. Slim agent context links

For each of `autonomous-builder`, `planner`, `critic`, `product-owner`, `reviewer`, `tester`:

- Keep 2–3 mandatory "read first" links (typically: CURRENT-STATE, VISION-LOCK, and one role-specific artifact).
- Move everything else to a single "Consult on demand via Explore subagent" bullet.
- Remove exhaustive path listings.

### D6. Reconcile autopilot vs manual

Files to audit:
- `template/.github/copilot-instructions.md.jinja`
- `template/AGENTS.md.jinja`
- `template/.github/prompts/implement.prompt.md.jinja`

Remove contradictions:
- Drop "all external actions require explicit human approval" under autopilot. Replace with: "Under autopilot, the builder self-approves plan advancement and logs rationale to Session Log. Tool-guardrails and stage-gate hooks remain hard constraints regardless of mode."
- Drop "ask when ambiguous" — replace with: "Under autopilot, make a best-faith choice and log rationale. Under manual mode, use vscode_askQuestions."
- Clarify the single hard human gate under autopilot: **design plan approval** (OQ-3 decision).

### D7. Final MANIFEST update

File: `template/.github/catalog/MANIFEST.md`

Verify final state matches proposal tally:
- Agents: `designer`, `security-reviewer` (2)
- Skills: `anti-slop`, `ci-verification`, `deep-interview`, `design-system` (4)
- Hooks: `ci-gate` (1 remaining — `tool-guardrails` and `context-checkpoint` promoted)
- Prompts: `clarify`, `design-review` (2)
- Patterns: `DESIGN.md`, `commit-trailers` (2)

Add a dated changelog entry at bottom noting v2 promotions.

### D8. Update copilot-instructions.md.jinja

- Add section: "Workflow state is machine-readable. CURRENT-STATE.md fields are parsed by hooks. Do not paraphrase field values — use the exact vocabulary (`approved`, `pending`, `pass`, etc.)."
- Add: **Three enforcement tiers** summary from the proposal so users know what's actually enforced vs advisory. Include honest notes about known bypass paths:
  - **Tier 1 (hook-enforced):** stage-gate blocks *direct tool edits* to source outside allowlist during non-executing stages. `run_in_terminal` can technically bypass this (e.g., `echo ... > src/x.py`). **Backstop:** `session-gate.py` runs `git diff --name-only HEAD` at session end and blocks stop if source files changed during a non-executing stage. Terminal-based source edits are therefore detected at session end, not per-command.
  - **Tier 1 (hook-enforced):** tool-guardrails blocks destructive commands (`git push --force`, `rm -rf` on critical paths, etc.) but is a denylist — novel destructive patterns can slip through.
  - **Tier 1 (hook-enforced):** SubagentStop verifies subagents wrote their verdicts to CURRENT-STATE. Cannot verify verdict *quality*, only that a terminal value exists.
  - **Tier 2 (artifact-verified, quality not checked):** critique depth, test coverage, strategic review thoroughness, doc-sync accuracy.
  - **Tier 3 (advisory only):** code style, commit format, subagent-vs-inline choices, error recovery strategy.
- State clearly: "Don't describe a rule as enforced if hooks can't check it."

### D9. Update AGENTS.md.jinja

- Document the 6 core agents + 2 catalog agents.
- Document the stage pipeline at a glance.
- Point to PROMPT-GUIDE for prompts and to MANIFEST for catalog.

### D10. End-to-end smoke test

```bash
copier copy . /tmp/v2-e2e --defaults \
  -d project_name="E2E" -d description="e2e" -d language="Python" -d author="Test" \
  --force
cd /tmp/v2-e2e
git init && git add -A && git commit -m "initial"
```

Open in VS Code. Select autonomous-builder. Walk through:

1. Bootstrap runs, planner interviews, vision lock + phase 1 design produced, BOOTSTRAP.md deleted.
2. Design-critique stage runs: product-owner writes stories, critic reviews.
3. Design approval → Stage=blocked → session ends (OQ-3 in action).
4. New session: approve → implementation-planning → implementation-critique → executing.
5. One slice: tester writes tests, builder implements, reviewer reviews, commit.
6. Verify session-gate blocks an early `stop` during executing with unmet Slice Evidence.
7. Phase-complete runs, wrap summary appears at `docs/wraps/phase-1-wrap.md`.
8. Stage transitions to `planning` for phase 2.

Record any friction in `notes.md` for follow-up.

### D11. Update repo README

File: `/home/jakce/copilot-autonomous-template/README.md`

- Note v2 changes at top.
- Link to `tmp/v2-proposal.md` and the four phase plans while they exist; remove `tmp/` references once merged.

## Risks

- Slimming too aggressively may remove context agents rely on. Mitigation: keep cut content in `tmp/archive-v1/` during Phase D until e2e smoke passes.
- Autopilot reconciliation may surface deeper prose inconsistencies not yet catalogued. Mitigation: do a grep pass for "approval", "autopilot", "ask", "manual" across all template files and resolve each hit explicitly.
- E2E test is manual and lengthy. Mitigation: scope the smoke test to "fake" phase 1 content — no real implementation required to exercise the pipeline.

## Out of scope

- Adding new catalog items not mentioned in the proposal.
- Documentation polish beyond the reconciliation items listed here.
- Changing the `copier.yml` variable schema.
