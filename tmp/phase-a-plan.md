# Phase A — State Machine and Core Hooks

> Goal: Replace narrative state with machine-readable state and install the enforcement hooks that make stage gating real.
> Prerequisite for all other phases.

## Exit criteria

- [ ] `CURRENT-STATE.md.jinja` has machine-readable Workflow State, Slice Evidence, Completion Checklist, Waivers, Session Log, Context sections
- [ ] Five core hooks installed under `template/.github/hooks/scripts/`: `stage-gate.py`, `session-gate.py`, `evidence-tracker.py`, `context-pressure.py`, `tool-guardrails.py`
- [ ] `slice-gate.py` deleted (superseded by `session-gate.py`)
- [ ] `tool-guardrails.py` and `context-checkpoint.py` removed from `template/.github/catalog/hooks/`
- [ ] Hook registrations added to `autonomous-builder.agent.md.jinja` frontmatter (PreToolUse, PostToolUse, Stop)
- [ ] `copier copy` smoke test produces a project where all hooks parse and execute on a dummy stdin payload
- [ ] MANIFEST.md updated to reflect catalog removals
- [ ] Tier 1 hook unit tests + Tier 2 generation smoke test passing (see A10)

## Work items

### A1. Redesign CURRENT-STATE.md.jinja

File: `template/roadmap/CURRENT-STATE.md.jinja`

Replace the entire body with the structure defined in the v2 proposal "CURRENT-STATE.md structure" section. Initial values for a freshly generated template:

- `Stage`: `bootstrap`
- `Phase`: `0`
- `Phase Title`: `Bootstrap`
- `Design Plan`: `n/a`
- `Design Status`: `n/a`
- `Design Critique Rounds`: `0`
- `Implementation Plan`: `n/a`
- `Implementation Status`: `n/a`
- `Implementation Critique Rounds`: `0`
- `Active Slice`: `n/a`
- `Slice Total`: `n/a`
- All Slice Evidence fields: `n/a`
- Completion Checklist: unchecked
- Waivers: empty
- Session Log: empty
- Context: short narrative referencing `BOOTSTRAP.md`

Add a `Source Root` field under Workflow State (default `src/`). This field is consumed by the tester PreToolUse hook (Phase B) and may be used by the stage gate allowlist later.

Stage vocabulary (enforced by hooks, document at top of file as a comment):
`bootstrap | planning | design-critique | implementation-planning | implementation-critique | executing | reviewing | cleanup | blocked | complete`

### A2. Write `stage-gate.py` (PreToolUse)

File: `template/.github/hooks/scripts/stage-gate.py`

Behavior:
1. Read `roadmap/CURRENT-STATE.md`, parse `Stage:` field.
2. If `Stage == executing` or `Stage == bootstrap` or `Stage == cleanup` → allow.
3. Otherwise, inspect the tool call:
   - Extract target path from `create_file`, `replace_string_in_file`, `multi_replace_string_in_file`, `edit_notebook_file` payloads.
   - For `run_in_terminal`, allow unconditionally at this layer. Terminal-based bypass (e.g. `echo ... > src/foo.py`) is caught by the session-gate git-diff backstop (see A3).
   - If target path matches allowlist (`roadmap/**`, `docs/**`, `.github/**`) → allow.
   - Otherwise → deny with a reason pointing to current stage and advising plan approval.
4. If CURRENT-STATE.md is missing → allow (bootstrap edge case).

Edge cases to handle:
- Paths may be absolute or workspace-relative — normalize before matching.
- Glob matching uses `fnmatch` with `**` expansion via manual path-component check.

Return schema per Copilot hook API (verified against [hooks docs](https://code.visualstudio.com/docs/copilot/customization/hooks)):
```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow" | "deny" | "ask", "permissionDecisionReason": "..."}}
```
Note: PreToolUse uses `permissionDecision` + `permissionDecisionReason`, not `decision` + `reason`. Most restrictive wins when multiple PreToolUse hooks fire.

### A3. Write `session-gate.py` (Stop)

File: `template/.github/hooks/scripts/session-gate.py`

Replaces `slice-gate.py`. Parses machine-readable fields and blocks stop when:

- `Stage == executing`:
  - Any Slice Evidence field still `pending` or `no` for the active slice (except `n/a`)
  - `Reviewer Invoked == no`
  - `Review Verdict == pending` or `needs-fixes` or `needs-rework`
  - `Critical Findings > 0` or `Major Findings > 0`
  - `Committed == no`
- `Stage == reviewing`:
  - `Strategic Review == pending` (but accept `n/a`)
- `Stage == cleanup`:
  - Any Completion Checklist item unchecked
- `Stage == design-critique` or `Stage == implementation-critique`:
  - Corresponding `Design Status` / `Implementation Status` is `in-critique`

Allow stop when:
- `Stage == blocked` (session break — expected under OQ-3)
- `Stage == complete`
- `stop_hook_active == true` (loop prevention)

Block message must tell the agent exactly which field is unsatisfied and what value is required.
**Terminal-bypass backstop.** In addition to the field checks, when `Stage` is one of `planning | design-critique | implementation-planning | implementation-critique | reviewing`:

- Run `git diff --name-only HEAD` (wrapped in a try/except — missing git or unborn HEAD → skip this check).
- If any changed path falls outside the allowlist (`roadmap/**`, `docs/**`, `.github/**`), block stop with reason: "Source files modified during non-executing stage: <paths>. Revert with `git checkout -- <path>`, stash the changes, or advance Stage to `executing` (requires approved plans)."
- This closes the terminal-write bypass of stage-gate (e.g. `echo ... > src/foo.py`). It catches the bypass at session end rather than per-command, which is acceptable because uncommitted source changes during non-executing stages are the real concern.

Stop return schema:
```json
{"hookSpecificOutput": {"hookEventName": "Stop", "decision": "block", "reason": "..."}}
```
### A4. Write `evidence-tracker.py` (PostToolUse) — logger only

File: `template/.github/hooks/scripts/evidence-tracker.py`

**Scope decision:** This hook is a *pure logger*. It does not parse subagent verdicts. Verdict recording is the responsibility of the critic/product-owner/reviewer subagents themselves — they write directly to CURRENT-STATE fields before returning. Phase B's `subagent-verdict-check.py` (SubagentStop) verifies the write happened.

Why: PostToolUse cannot reliably determine *which* CURRENT-STATE field corresponds to a given subagent invocation (design vs implementation critique, etc.) without re-parsing state, and free-form prose verdict extraction is brittle. The docs also note PostToolUse hooks can inject `additionalContext` but cannot rewrite tool output, making parsed-result feedback one-way.

Behavior:
1. Inspect the tool call payload (`tool_name`, `tool_input`, optional `tool_response`).
2. If `run_in_terminal` and command matches `/\b(pytest|jest|vitest|go test|cargo test|npm test|yarn test|pnpm test)\b/`:
   - Parse exit code from `tool_response` if present.
   - Update `Tests Written: yes` and `Tests Pass: yes|no` in CURRENT-STATE.md via single-line `str_replace`.
3. Always append a line to Session Log: `- [ISO8601 timestamp] <event summary>` (tool name + short outcome).
4. Never modify Design Status / Implementation Status / Review Verdict / Strategic Review — those are owned by the agents.

Must be idempotent — re-running the same test twice should not corrupt state. Uses string-anchored `str_replace` on a single line rather than rewriting the full file.

Graceful degradation: if parsing fails, log `- [ts] evidence-tracker: unable to parse <tool>` to Session Log and exit 0 without modifying state fields.

Return schema:
```json
{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "optional note to model"}}
```

### A5. Promote `tool-guardrails.py` to core

Source: `template/.github/catalog/hooks/tool-guardrails.py` (+ `.json`)
Destination: `template/.github/hooks/scripts/tool-guardrails.py`

- Move file, delete catalog copy (and `tool-guardrails.json` if no longer referenced there).
- Verify its rules cover: `git push --force`, `git push -f`, `git reset --hard`, `rm -rf` on `.git`/`roadmap`/`docs/vision`, writes to `node_modules/`, path traversal containing `..`.
- Update MANIFEST.md to remove the tool-guardrails catalog entry.
- Update any prose in catalog README referencing its dormant status.

### A6. Promote `context-pressure.py` (née `context-checkpoint.py`) to core

Source: `template/.github/catalog/hooks/context-checkpoint.py`
Destination: `template/.github/hooks/scripts/context-pressure.py` (renamed)

- Move + rename. Update any internal docstrings.
- Update MANIFEST.md to remove catalog entry.
- Verify it still functions as a PostToolUse advisory (does not block; injects recommendation).

### A7. Delete `slice-gate.py`

File: `template/.github/hooks/scripts/slice-gate.py` → delete after session-gate.py is wired in.

### A8. Wire hooks into autonomous-builder frontmatter

File: `template/.github/agents/autonomous-builder.agent.md.jinja`

Replace the single `Stop` hook with:

```yaml
hooks:
  PreToolUse:
    - type: command
      command: "python3 .github/hooks/scripts/stage-gate.py"
    - type: command
      command: "python3 .github/hooks/scripts/tool-guardrails.py"
  PostToolUse:
    - type: command
      command: "python3 .github/hooks/scripts/evidence-tracker.py"
    - type: command
      command: "python3 .github/hooks/scripts/context-pressure.py"
  Stop:
    - type: command
      command: "python3 .github/hooks/scripts/session-gate.py"
```

Agent-scoped SubagentStop hooks on critic, product-owner, reviewer belong to Phase B (those agents are promoted/expanded there).

### A9. Smoke test

After changes, run:

```bash
copier copy . /tmp/v2-smoke --defaults \
  -d project_name="Smoke" -d description="smoke" -d language="Python" -d author="Test" \
  --force
```

Then manually pipe minimal JSON into each hook script and verify exit 0 + well-formed JSON on stdout:

```bash
cd /tmp/v2-smoke
echo '{"cwd":".","tool_name":"create_file","tool_input":{"filePath":"src/x.py"}}' \
  | python3 .github/hooks/scripts/stage-gate.py
```

Expected: `deny` (Stage is `bootstrap`, but wait — bootstrap allows everything; switch `Stage:` to `planning` manually and retest for a deny).

### A10. Testing infrastructure

Create `tests/` at repo root (not inside `template/` — these test the template itself, not generated output).

**Tier 1 — Hook unit tests.**
- `tests/hooks/test_stage_gate.py`
- `tests/hooks/test_session_gate.py`
- `tests/hooks/test_evidence_tracker.py`
- `tests/hooks/test_tool_guardrails.py`
- `tests/hooks/test_context_pressure.py`

Each test uses stdlib `unittest` + `subprocess.run` to pipe fixture JSON into the script and assert exit code + parsed stdout JSON. Minimum ~10 fixtures per hook covering representative stages and tool payloads. Fixtures live under `tests/hooks/fixtures/<hook>/*.json`.

**Tier 2 — Generation smoke test.**
- `tests/smoke.sh`: runs `copier copy . $TMP --defaults -d project_name=Smoke ...`, greps for expected files (all 5 core hooks, 6 core agents, 7 prompts, CURRENT-STATE structure markers), pipes a representative payload through each hook in the generated project. Exits non-zero on any mismatch.

**Tier 3 — Manual e2e.** Stays as Phase D's D10 walkthrough.

Add a top-level `Makefile` or `justfile` with `test-hooks`, `test-smoke`, `test-all` targets. Document in root README.

## Risks

- Hook parsing is fragile if users hand-edit CURRENT-STATE.md with different casing/whitespace. Mitigation: `session-gate.py` must match case-insensitively, trim whitespace, and emit a clear error if a required field is missing entirely.
- `evidence-tracker.py` writing to CURRENT-STATE.md races with the builder writing to the same file. Mitigation: always append to Session Log at end-of-file, use single-line `str_replace` for field updates, document the race in the hook docstring.
- `run_in_terminal` is not gated by `stage-gate.py`. This is a known bypass. Mitigation: `session-gate.py`'s git-diff backstop (see A3) catches terminal-based edits to source during non-executing stages at session end. Documented honestly in the enforcement-tier section (Phase D).

## Out of scope (deferred to later phases)

- Removing self-modification permission from builder (Phase D)
- Rewriting the builder as a stage orchestrator (Phase B)
- SubagentStop hooks on critic/product-owner (Phase B)
- Prompt renames (Phase C)
