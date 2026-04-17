---
description: "Template-aware code review for the copilot-autonomous-template repo. Reviews edits to the Copier template (agents, prompts, instructions, skills, hooks, catalog, state schema) for convention compliance, ADR fidelity, and Jinja correctness."
---

# Template Review

You are reviewing changes to the **copilot-autonomous-template** meta-repo. This is not a generated project — it is the Copier template that bootstraps generated projects. The `reviewer` and `critic` agents under `template/.github/agents/` are *artifacts*, not reviewers of this repo. **You** are the reviewer.

Operate with the latitude appropriate for a thorough review: read what you need, run validation commands, consult docs. Be specific and critical; honest feedback beats validation. Subagents (e.g. `Explore`) are fine for parallel reads.

## Required reads

Before writing any finding:

- The diff or files in scope (see Input).
- [Copilot instructions](../copilot-instructions.md) — repo conventions.
- [Template conventions skill](../skills/template-conventions/SKILL.md) — the rule set you are enforcing.
- [Copilot customization docs skill](../skills/copilot-customization-docs/SKILL.md) — only if the change touches frontmatter/syntax for agents/prompts/skills/instructions/hooks.

Consult on demand: relevant ADRs in [docs/architecture/decisions/](../../docs/architecture/decisions/), the [README](../../README.md), and any template file the change interacts with.

## Input

Review scope (file paths, glob, or git ref range; default = unstaged + staged changes): **${input:scope:current uncommitted changes}**

If the scope is "current uncommitted changes" or empty, run `git status` and `git diff HEAD` to discover the scope, then expand to staged-but-uncommitted with `git diff --cached`.

## Review dimensions

Cover each that applies. Skip with a one-line note when not applicable.

### 1. Template hygiene
- All edits live under `template/`, `tests/`, `docs/`, `.github/skills/`, `.github/prompts/`, top-level config, or `CHANGELOG.md`. Anything else needs justification.
- No edits to throwaway generated output (e.g. `/tmp/...`).
- `.jinja` files preserve `{{ project_name }}` / `{{ description }}` / `{{ language }}` / `{{ author }}` / `{{ project_slug }}` where they belong; no hardcoded substitutions.
- New files under `template/.github/catalog/**` are **not** `.jinja` (catalog is verbatim).

### 2. Frontmatter contracts
For each touched agent / prompt / instruction / skill file:
- Required fields present; optional fields valid per the customization-docs skill.
- `agents:` references resolve (or are intentional dormant catalog references).
- `hooks:` paths point to scripts that exist at `template/.github/hooks/scripts/<name>.py`.
- `handoffs[].agent` names a real agent or `agent`.
- Subagent agents include the `SubagentStop` verdict-check hook.
- No `tools:` restriction unless the role demands it.

### 3. State schema integrity
If `state.md.jinja`, `_state_io.py`, any hook script, or any agent that writes state was touched:
- Field names match across **all four**: `state.md.jinja`, parser/`_state_io.py`, the agent prose that documents writes, and `tests/hooks/`.
- Vocabulary values still match the documented enums (Stage, Status, Verdict, etc.).
- A rename in one place without the others is a Critical finding.

### 4. Hook contract
For new or modified hook scripts:
- Stdlib only. Stdin JSON in, stdout JSON out. Graceful on missing/malformed `state.md`.
- Companion `tests/hooks/test_<name>.py` exists and exercises the new behavior.
- `make test-hooks` passes.

### 5. ADR fidelity
- The change does not contradict ADRs 001, 003, 006, 007, 009, 010 (see template-conventions skill for the short list). If it does, a superseding ADR is required, not a patch.
- New design decisions of comparable weight have an ADR draft.

### 6. Convention drift
- Conventions introduced in one of the six agent files (`autonomous-builder`, `planner`, `critic`, `product-owner`, `reviewer`, `tester`) are mirrored in the others where applicable: Required reads section, output artifact path scheme, verdict format, state-update block.
- README counts ("6 core subagents", "8 manual prompts", "ADRs 001–010") match reality after the change.
- The repo file tree in [.github/copilot-instructions.md](../copilot-instructions.md) matches reality if directories were added/removed.

### 7. Validation evidence
- `make test-all` was run and passed (or you run it now). Paste the tail (~10 lines) into the artifact.
- For Jinja-touching edits, a manual `copier copy` to a temp dir was performed; `grep -rn "{{\\|}}"` on the output is empty.

### 8. Doc-sync
- Change touched user-visible behavior → README updated.
- Change touched workflow semantics → relevant prompt/agent description and `PROMPT-GUIDE.md` updated.
- New convention → captured in the template-conventions skill so it persists.

## Output artifact

Write the review to `roadmap/reviews/template-review-<YYYYMMDD-HHMM>.md` (create the directory if missing). If the review is short and there are no Critical/Major findings, posting it inline in the chat is also acceptable — but state that explicitly so the human can decide whether to persist it.

Use this format:

```markdown
# Template Review — <date>

**Scope**: <files / refs reviewed>
**Validation**: `make test-all` <pass|fail>; copier-render <pass|fail|n/a>

## Findings

| Severity | File | Finding | Recommendation |
|----------|------|---------|----------------|
| Critical | path:line | ... | ... |
| Major    | path:line | ... | ... |
| Minor    | path:line | ... | ... |
| Nit      | path:line | ... | ... |

## Verdict

Verdict: pass | needs-fixes | needs-rework
Critical: <n>  Major: <n>
```

Verdict rules (mirroring the generated `reviewer` agent for consistency):
- `pass` — zero Critical, zero Major.
- `needs-fixes` — zero Critical, ≥1 Major.
- `needs-rework` — ≥1 Critical, or ADR violation, or systemic problem.

## Rules

- Do not modify the files under review. You report; the human or a follow-up session fixes.
- Cite file paths with line numbers on every finding.
- Be specific. "Could be cleaner" is not a finding; "the `Stage` field is read but not written here, breaking the pipeline at line 42" is.
- Distinguish blockers (Critical/Major) from preferences (Minor/Nit). Do not pad with Nits.
- If the scope is genuinely small and clean, a `pass` with one-paragraph rationale is the right answer. Don't manufacture findings.
- If you find a class of mistake worth catching automatically, propose a unit test or a hook in the verdict commentary — but don't write it as part of the review itself.
