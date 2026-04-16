# Phase C — Pipeline Prompts

> Goal: Align prompts with the new stage pipeline. Rename, expand, add, and wire wrap summaries.
> Depends on: Phase A (state structure), Phase B (agent roles).

## Exit criteria

- [ ] `phase-plan.prompt.md.jinja` renamed to `design-plan.prompt.md.jinja`, body expanded
- [ ] New `strategic-review.prompt.md.jinja` exists
- [ ] `phase-complete.prompt.md.jinja` enhanced to generate wrap summary
- [ ] `docs/wraps/README.md` + template exist in generated output
- [ ] All prompts reference machine-readable CURRENT-STATE fields (no prose-only state)
- [ ] `PROMPT-GUIDE.md.jinja` updated with new prompt inventory
- [ ] `copier copy` smoke test produces all prompts discoverable in VS Code slash-command picker

## Work items

### C1. Rename + expand phase-plan → design-plan

- `git mv template/.github/prompts/phase-plan.prompt.md.jinja template/.github/prompts/design-plan.prompt.md.jinja`
- Rewrite body. Required sections the prompt must produce in `roadmap/phases/phase-N-design.md`:
  1. **User Stories** — as user, I want, so that (populated by product-owner handoff or inline if product-owner not yet invoked)
  2. **Acceptance Criteria** — measurable outcomes per story
  3. **Non-Goals** — explicit exclusions
  4. **Risks** — what could go wrong, mitigation
  5. **ADR Candidates** — decisions requiring capture in `docs/architecture/decisions/`
  6. **Test Strategy** — what gets tested at what layer
  7. **Slice Breakdown** — ordered list of slices with file-level hints
- Prompt frontmatter: `agent: planner`.
- Prompt body must instruct: update CURRENT-STATE `Design Plan:` field to the new file path and set `Design Status: draft`.
- Update all references to the old prompt name across template files.

### C2. Keep + tighten implementation-plan prompt

File: `template/.github/prompts/implementation-plan.prompt.md.jinja`

- Add top-of-prompt requirement: the referenced design plan must exist and CURRENT-STATE `Design Status` must be `approved` before running.
- Output location: `roadmap/phases/phase-N-implementation.md`.
- Must update CURRENT-STATE `Implementation Plan:` and `Implementation Status: draft`.

### C3. Keep /implement prompt minimal

File: `template/.github/prompts/implement.prompt.md.jinja`

- Remove the "ask when ambiguous" prose that conflicts with autopilot (acknowledged inconsistency in the proposal).
- Add explicit instruction: pull slice N from the implementation plan, run the slice loop per the builder's executing-stage protocol.
- Update Slice Evidence fields after each step.

### C4. Tighten /code-review to code focus

File: `template/.github/prompts/code-review.prompt.md.jinja`

- Remove any strategic/product questions — those move to `/strategic-review`.
- Output must set CURRENT-STATE `Reviewer Invoked: yes`, `Review Verdict: <verdict>`, `Critical Findings: N`, `Major Findings: N`.

### C5. Add /strategic-review

File: `template/.github/prompts/strategic-review.prompt.md.jinja` (new)

- Frontmatter: `description`, `agent: product-owner` (fallback to planner if product-owner not invoked).
- Body: compare implementation results to design plan.
  - Were acceptance criteria met?
  - Did any test results invalidate a design assumption?
  - Are there newly-discovered constraints that warrant vision update?
- Output: set CURRENT-STATE `Strategic Review: pass | replan | n/a` with 1-line rationale appended to Session Log.

### C6. Enhance /phase-complete with wrap summary

File: `template/.github/prompts/phase-complete.prompt.md.jinja`

- Body runs the cleanup checklist in order:
  1. Verify acceptance criteria against design plan
  2. Record ADRs in `docs/architecture/decisions/`
  3. Update open questions, tech debt, glossary
  4. Sync docs (README, architecture, instructions)
  5. **Write wrap summary to `docs/wraps/phase-N-wrap.md`** using the template (C7)
  6. Save context notes to `/memories/repo/`
  7. Check all boxes in CURRENT-STATE Completion Checklist
  8. Increment Phase, set Stage=`planning`, reset Slice Evidence fields
- Hook-verified: session-gate blocks stop in `cleanup` stage until the Completion Checklist is fully checked.

### C7. Add wrap summary scaffold

New files in template:

- `template/docs/wraps/README.md` — explains the directory, links to format.
- `template/docs/wraps/.gitkeep` OR a starter `TEMPLATE.md` with the format from the proposal:

  ```markdown
  # Phase N: [Title]

  - **Design plan**: link
  - **Implementation plan**: link
  - **Slices completed**: N/M
  - **Key decisions**: ...
  - **What went well**: ...
  - **What surprised us**: ...
  - **Deferred to future phases**: ...
  ```

### C8. Update PROMPT-GUIDE

File: `template/.github/prompts/PROMPT-GUIDE.md.jinja`

- Replace prompt table with new inventory:
  - `/vision-expand`
  - `/design-plan` (was `/phase-plan`)
  - `/implementation-plan`
  - `/implement`
  - `/code-review`
  - `/strategic-review` (new)
  - `/phase-complete`
- Describe when to invoke each manually vs let the builder drive it.
- Note: prompts are now **human override entry points**. The builder orchestrates autonomously.

### C9. Update all cross-references

Grep for old prompt names and update:
```bash
grep -rln "phase-plan" template/ --include="*.jinja" --include="*.md"
```
Replace references in:
- `AGENTS.md.jinja`
- `BOOTSTRAP.md.jinja`
- `copilot-instructions.md.jinja`
- `autonomous-builder.agent.md.jinja`
- `planner.agent.md.jinja`
- any instruction files

### C10. Smoke test

- Run `copier copy`.
- Verify VS Code command palette lists all 7 prompts.
- Open `/design-plan` and verify it renders with the expanded sections.
- Open `/strategic-review` and verify frontmatter + body.
- Verify `docs/wraps/README.md` exists and is readable.

## Risks

- Renaming `phase-plan` → `design-plan` is a breaking change for anyone mid-stream. Mitigation: since this is a template (not an installed tool), only affects new generations. Note the rename in README/changelog for template users.
- Prompt bodies duplicating content from `copilot-instructions.md`. Mitigation: prompts link to the instructions file for shared context per template convention.

## Out of scope

- Removing self-modification from builder → Phase D.
- Catalog bootstrap-time selection UX → Phase D.
- BOOTSTRAP.md slimming → Phase D.
