# Phase B — Core Agent Restructure

> Goal: Promote critic and product-owner to core, restrict tester, wire SubagentStop enforcement, and rewrite the builder as a stage orchestrator.
> Depends on: Phase A (needs machine-readable state for orchestrator logic).

## Exit criteria

- [ ] `template/.github/agents/` contains 6 core agents: `autonomous-builder`, `planner`, `critic`, `product-owner`, `reviewer`, `tester`
- [ ] `template/.github/catalog/agents/` contains only `designer` and `security-reviewer`
- [ ] `critic`, `product-owner`, `reviewer` each have SubagentStop hooks
- [ ] Tester has PreToolUse hook (`tester-isolation.py`) blocking reads to Source Root non-test files
- [ ] Planner role expanded to handle design plans + strategic reviews
- [ ] Builder `.agent.md.jinja` rewritten as stage orchestrator (< 200 lines body)
- [ ] MANIFEST.md updated
- [ ] `copier copy` smoke test produces a project with all 6 core agents discoverable

## Work items

### B1. Promote critic to core

Source: `template/.github/catalog/agents/critic.agent.md`
Destination: `template/.github/agents/critic.agent.md.jinja`

- Move, rename with `.jinja` extension (uses `{{ project_name }}` in description).
- Rewrite body for the iterative design/implementation critique role:
  - Input: a plan file path (design or implementation)
  - Output: verdict file at `roadmap/phases/phase-N-critique-R.md` (R = round number) containing findings table + `Verdict: approve | revise | rethink`
  - Must update `Design Status` / `Implementation Status` and `Design Critique Rounds` / `Implementation Critique Rounds` in CURRENT-STATE.md
  - Escalate to human if round count hits max (3 for design, 2 for implementation)
- Frontmatter gains:
  ```yaml
  hooks:
    SubagentStop:
      - type: command
        command: "python3 .github/hooks/scripts/subagent-verdict-check.py critic"
  ```

### B2. Promote product-owner to core

Source: `template/.github/catalog/agents/product-owner.agent.md`
Destination: `template/.github/agents/product-owner.agent.md.jinja`

- Move + rename.
- Rewrite body for two modes:
  - Design phase: write user stories + acceptance criteria into the design plan
  - Review phase: strategic validation — did the implementation achieve design intent? emits `Strategic Review: pass|replan`
- Add SubagentStop hook (same pattern as critic).

### B3. Add SubagentStop to reviewer

File: `template/.github/agents/reviewer.agent.md.jinja`

- Add frontmatter hook matching critic/product-owner pattern.
- Tighten body to code focus only (quality, architecture, security, doc-sync). Move any strategic language to product-owner's purview.
- Ensure the review output format includes a `Review Verdict:` line that evidence-tracker.py can parse.

### B4. Write `subagent-verdict-check.py` — state-write verifier

File: `template/.github/hooks/scripts/subagent-verdict-check.py`

**Architecture note:** agents write state, hooks verify state wrote. The critic/product-owner/reviewer agent instructions explicitly require updating the relevant CURRENT-STATE field before returning. This hook verifies the write happened — it does not parse prose or subagent output.

- Takes one CLI arg: subagent name (`critic` | `product-owner` | `reviewer`).
- Reads CURRENT-STATE.md before-state from a sidecar (see below) and after-state live, or — simpler — just checks the current field values are valid terminal values, not `pending` or `in-critique`:
  - `critic`: current `Stage` determines which status to check. If `Stage == design-critique` → `Design Status` must be `approved`, `revise`, or `rethink` (not `in-critique` or `draft`). Same for `implementation-critique` → `Implementation Status`. Also `Design Critique Rounds` / `Implementation Critique Rounds` must be > 0.
  - `product-owner`: depending on stage, either the design plan file must contain a `## User Stories` section with at least one `- As a ...` bullet (filesystem check), OR `Strategic Review` field is `pass`/`replan`/`n/a` (not `pending`).
  - `reviewer`: `Review Verdict` is `pass`/`needs-fixes`/`needs-rework` (not `pending`), AND `Reviewer Invoked: yes`, AND `Critical Findings` and `Major Findings` are numeric (not blank).
- If verification fails, block SubagentStop with a reason string naming the exact field that must be written before returning.
- Allow if `stop_hook_active` is true (loop prevention).

Return schema (per Copilot docs):
```json
{"hookSpecificOutput": {"hookEventName": "SubagentStop", "decision": "block", "reason": "..."}}
```

No sidecar diffing needed — checking "is the field a terminal value?" is simpler and sufficient, because every critique round / review starts by setting the field back to `pending` or `in-critique`.

### B5. Restrict tester via hybrid isolation (tool list + PreToolUse hook)

Decision OQ-1: hook approach, refined after review.

**Why hybrid:** `semantic_search` returns source content in results — a PreToolUse hook can deny the call but cannot sanitize results. The only reliable way to prevent semantic_search leakage is to remove the tool from the tester's available tool list. `grep_search`/`file_search`/`read_file` can be gated by path because they accept explicit path/pattern arguments.

**Tester agent frontmatter:** explicitly list allowed tools, excluding `search/codebase` (semantic_search).
```yaml
tools:
  - edit                    # create_file, replace_string_in_file, etc.
  - run_in_terminal
  - search/textSearch       # grep_search
  - search/fileSearch       # file_search
  - search/readFile         # read_file
  # NOTE: search/codebase (semantic_search) intentionally omitted.
  # Semantic search returns source content in results and cannot be path-gated.
hooks:
  PreToolUse:
    - type: command
      command: "python3 .github/hooks/scripts/tester-isolation.py"
```

Verify exact tool IDs against [custom agents docs](https://code.visualstudio.com/docs/copilot/customization/custom-agents) during implementation — the tool-set names may need adjustment.

**File:** `template/.github/hooks/scripts/tester-isolation.py`

Behavior:
- Reads `Source Root` from CURRENT-STATE.md (default `src/`).
- On `read_file`: extract `filePath`. Allow if it matches: `**/test*/**`, `**/tests/**`, `**/*.test.*`, `**/*.spec.*`, `**/__tests__/**`, `*.config.*`, `package.json`, `tsconfig*.json`, `pyproject.toml`, `setup.cfg`, `Cargo.toml`, `go.mod`. Allow if path does not begin with Source Root. Otherwise deny.
- On `grep_search` / `file_search`: require `includePattern` to be present and match one of the allowlist patterns above. Deny unscoped searches (no `includePattern`) or searches whose `includePattern` could reach into Source Root non-test files.
- Deny message: "tester cannot read implementation files — write tests from the spec and existing test helpers only. Allowed locations: tests/, *.test.*, *.spec.*, __tests__/, config files."

Return schema: same PreToolUse `permissionDecision` format as stage-gate (see Phase A A2).

### B6. Expand planner role

File: `template/.github/agents/planner.agent.md.jinja`

Add responsibilities to the body (keep read-only):
- Produce **design plans** at `roadmap/phases/phase-N-design.md` with sections: User Stories (filled by product-owner later or by planner with product-owner handoff), Acceptance Criteria, Non-Goals, Risks, ADR Candidates, Test Strategy
- Produce **implementation plans** at `roadmap/phases/phase-N-implementation.md` from approved designs
- Revise plans based on critic/product-owner feedback
- Run **strategic reviews** post-implementation: compare results to design, emit verdict

Add a handoff to critic via frontmatter `handoffs:` list pointing at review flow.

### B7. Rewrite autonomous-builder as stage orchestrator

File: `template/.github/agents/autonomous-builder.agent.md.jinja`

Target: body under 200 lines. Structure:

1. **Role statement** (3 lines): orchestrator, not do-everything.
2. **Required reads** (3 bullets): CURRENT-STATE, VISION-LOCK, `/memories/repo/`.
3. **Stage dispatch table**:

   | Stage | Action |
   |-------|--------|
   | `bootstrap` | Read `BOOTSTRAP.md` if present; follow its protocol; delete on completion. |
   | `planning` | Invoke planner to produce design plan. Request human approval via `vscode_askQuestions`. On approve → `design-critique`. |
   | `design-critique` | Invoke product-owner (user stories) then critic. If verdict=revise → planner revises → re-critique (max 3 rounds). If approve → set `blocked`, write blocked reason = "Design approved — start new session for implementation planning." |
   | `implementation-planning` | Invoke planner for implementation plan + tester for strategy review. Autopilot self-approves with Session Log entry. Manual mode asks human. → `implementation-critique`. |
   | `implementation-critique` | Critic reviews implementation plan (max 2 rounds). → `executing`. |
   | `executing` | Run slice loop (see below). |
   | `reviewing` | Invoke reviewer (code) + product-owner or planner (strategic). Autopilot self-approves. → `cleanup`. |
   | `cleanup` | Run phase-complete protocol. Checklist must be satisfied before session-gate allows stop. On complete → increment Phase, set Stage=`planning`. |
   | `blocked` | Stop immediately. |
   | `complete` | Enter vision expansion protocol via `/vision-expand` prompt. |

4. **Slice loop** (executing stage):
   - For each slice 1..N:
     1. Invoke tester to write tests (from spec only).
     2. Implement.
     3. Run tests.
     4. Run post-implementation checks.
     5. Invoke reviewer.
     6. Fix Critical/Major.
     7. Commit.
     8. Update Slice Evidence fields in CURRENT-STATE.
   - After slice N, set Stage=`reviewing`.

5. **Error recovery** (unchanged from current builder — keep the 2-attempt bounded retry + tech-debt recording).

6. **Subagents** block:
   ```
   planner, critic, product-owner, reviewer, tester, Explore
   ```
   Plus catalog: `designer`, `security-reviewer` (listed — silently ignored if not activated).

Remove:
- Vision expansion detailed protocol (defer to `/vision-expand` prompt — builder just sets `blocked` with reason "run /vision-expand").
- Self-modification section (Phase D).
- Catalog auto-activation heuristics (Phase D).
- Post-implementation checks detail block — link to a new `.github/instructions/post-impl-checks.instructions.md` instead.

### B8. Update catalog MANIFEST.md

File: `template/.github/catalog/MANIFEST.md`

- Remove `critic` and `product-owner` rows from catalog agents table.
- Add note at top: "critic and product-owner are now core agents — see `.github/agents/`."
- Retain `designer`, `security-reviewer` entries.

### B9. Smoke test

- Run `copier copy`.
- Open generated project in VS Code, verify agent picker lists all 6 core agents.
- Manually set `Stage: planning` in CURRENT-STATE, attempt to `create_file` in `src/` via a test script — verify stage-gate denies.
- Simulate a critic subagent completion without writing a verdict — verify subagent-verdict-check blocks.

## Risks

- Builder rewrite is the largest single change. Mitigation: keep the previous builder content archived in `tmp/builder-v1.md` during the rewrite for reference.
- SubagentStop verdict detection is heuristic (string matching on artifacts). Mitigation: subagents write to a known path and known field; heuristic failure shows up as a visible block, not silent pass.
- Tester isolation hook may be too aggressive for monorepos with co-located tests. Mitigation: the `**/*.test.*` / `**/*.spec.*` allowlist covers the common co-located patterns. Users can add patterns to the hook if needed.

## Out of scope

- Prompt renames and new `/strategic-review` prompt → Phase C.
- Removing catalog auto-activation from builder → partially in B7 (rewrite drops it), formally closed in Phase D.
- Wrap summary infrastructure → Phase C.
