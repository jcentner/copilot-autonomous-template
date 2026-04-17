---
name: template-conventions
description: "Conventions and invariants for editing the copilot-autonomous-template repo itself: Copier/Jinja rules, frontmatter contracts for agents/prompts/instructions/skills, the catalog vs. core split, hook-script contract, the canonical state.md schema, and ADR-derived design invariants. USE FOR: reviewing template edits, validating PRs, creating new agents/prompts/skills/hooks under template/, or auditing whether a change respects the design rules. DO NOT USE FOR: reviewing code in repos generated *by* this template (those have their own reviewer agent)."
---

# Template Conventions — copilot-autonomous-template

This skill captures the rules a reviewer or editor needs to keep changes to **this meta-repo** correct. The repo is a Copier template; mistakes here propagate to every generated project.

## Always-true invariants

1. **Edit `template/`, never the rendered output.** Anything outside `template/`, `tests/`, `docs/`, top-level config files, and this skill folder is generally not the target of changes. Generated files (e.g. `/tmp/test-output/...`) are throwaway.
2. **Don't add runtime code.** This is a pure template repo. No `src/`, no app code.
3. **Don't hardcode project-specific values in `.jinja`.** Use `{{ project_name }}`, `{{ project_slug }}`, `{{ description }}`, `{{ language }}`, `{{ author }}`.
4. **No restrictive `tools` list on agents/prompts unless intentional.** Restrictions exist only on `planner` (read-only by design), `critic`, `reviewer`, `product-owner`, `tester` — and each restriction is justified by its role.
5. **Authority hierarchy** (in generated projects): vision lock > ADRs > architecture docs > roadmap > open questions > instructions/prompts. Changes that invert this are wrong.

## Copier / Jinja rules

- Files with `.jinja` suffix are rendered through Jinja2; suffix is stripped on output.
- Files **without** `.jinja` are copied verbatim — this matters for the catalog.
- After any non-trivial edit, run `make test-all`. For Jinja-only edits, also do a manual generation:

  ```bash
  copier copy . /tmp/tcheck --defaults \
    -d project_name="Test Project" -d description="A test" \
    -d language="Python" -d author="Test"
  grep -rn "{{\|}}" /tmp/tcheck   # should be empty (no unrendered Jinja)
  grep -rn "Test Project" /tmp/tcheck   # should find substitutions
  ```

## Catalog vs. core split

Path | Rendered? | Notes
--- | --- | ---
`template/.github/agents/`, `prompts/`, `skills/`, `hooks/scripts/` | **Yes** (`.jinja` allowed) | Always-on capabilities of the generated repo
`template/.github/catalog/**` | **No — copied verbatim** | Dormant items activated by the builder. **Do not add `.jinja` here.** They get activated via plain `cp`, so any unrendered Jinja would ship to users as-is.
`template/.github/instructions/` | Mixed | `docs.instructions.md` is verbatim by current convention

When adding a catalog item:
- Use literal text only; no `{{ }}`/`{% %}`.
- Add a row to [MANIFEST.md](../../template/.github/catalog/MANIFEST.md) with trigger conditions and target path.
- The builder activates by `cp` — verify the source path in MANIFEST resolves.

## Frontmatter contracts

### Agents (`*.agent.md` / `*.agent.md.jinja`)

Required: `description`. Common optional fields: `tools`, `agents` (subagent allow-list), `handoffs`, `hooks`, `model`, `user-invocable`.

- `agents:` may list both core agents and catalog agents that don't yet exist as files — VS Code silently ignores unknown ones until activated. This is intentional.
- `hooks:` paths must point to a script that actually exists at `.github/hooks/scripts/<name>.py`. Mismatch → silent breakage at runtime.
- `handoffs[].agent` must name a real agent (or `agent` for the calling agent).
- Subagent agents (`critic`, `reviewer`, `product-owner`, `planner`, `tester`) all carry a `SubagentStop` hook that runs `subagent-verdict-check.py <name>`. Adding a new subagent without this hook will let it return without writing required state — a silent contract break.

### Prompts (`*.prompt.md` / `*.prompt.md.jinja`)

- Frontmatter: `description`, optionally `agent` (defaults to active agent).
- Use `${input:varName:default}` for runtime input.
- Markdown links in the body auto-attach files as context — prefer linking to shared docs over duplicating content.
- Don't add a `tools` list unless the prompt must restrict capability beyond the agent it dispatches to.

### Instructions (`*.instructions.md`)

- Optional `applyTo:` glob in frontmatter. Without it, instruction is always-on for the agent.
- One responsibility per file; prefer additive over rewriting `copilot-instructions.md`.

### Skills (`SKILL.md` in a named folder)

- Frontmatter: `name`, `description`. The `description` is what Copilot uses to decide auto-discovery — write it like a search query: include both **what's covered** and **when to use / not use**.
- Folder name must equal `name`.
- Long-form references go in `references/` siblings; the SKILL.md itself stays scannable.

## Hook-script contract

Located at `template/.github/hooks/scripts/`.

- Stdlib only. No third-party deps. Python 3.10+.
- Read JSON from stdin, write JSON to stdout. Exit code 0 even when blocking; the JSON `decision` field carries the verdict.
- Side effects (state writes) go through `_state_io.py` for atomicity.
- Every script has a corresponding `tests/hooks/test_<name>.py` using stdlib `unittest`. **No new hook ships without tests.**
- Hooks must tolerate missing/malformed `state.md` gracefully — they run before the file may exist (e.g. bootstrap).

## Canonical `state.md` schema

Hook scripts parse these field names verbatim. Renaming any field requires updating the parser, the agent that writes it, and the tests in lockstep. Source of truth: [template/roadmap/state.md.jinja](../../template/roadmap/state.md.jinja).

Workflow State block: `Stage`, `Blocked Kind`, `Phase`, `Phase Title`, `Source Root`, `Test Path Globs`, `Config File Globs`, `Design Plan`, `Design Status`, `Design Critique Rounds`, `Implementation Plan`, `Implementation Status`, `Implementation Critique Rounds`, `Active Slice`, `Slice Total`, `Blocked Reason`.

Slice Evidence block: `Evidence For Slice`, `Tests Written`, `Tests Pass`, `Reviewer Invoked`, `Review Verdict`, `Critical Findings`, `Major Findings`, `Strategic Review`, `Committed`.

Vocabularies (also verbatim — see header comment in the file):
- Stage: `bootstrap | planning | design-critique | implementation-planning | implementation-critique | executing | reviewing | cleanup | blocked | complete`
- Blocked Kind: `awaiting-design-approval | awaiting-vision-update | awaiting-human-decision | error | vision-exhausted | n/a`
- Status: `n/a | draft | in-critique | approved | revise | rethink | waived`
- Slice Evidence values: `yes | no | pending | n/a`
- Review Verdict: `pending | pass | needs-fixes | needs-rework | n/a`
- Strategic Review: `pending | pass | replan | n/a`

## ADR-derived invariants

These are non-negotiable design rules. Any change that contradicts one needs a superseding ADR, not a patch.

- **ADR 001** — workflow is a hook-verified stage machine. Agents propose; hooks verify.
- **ADR 003** — agents *write* `state.md`; hooks *verify*. Don't shift verification into agents.
- **ADR 006** — tester subagent cannot read source code. The `tester-isolation.py` PreToolUse hook enforces this. Don't relax the deny-list.
- **ADR 007** — self-modification ban. Agents in generated repos must not edit their own definition files mid-session.
- **ADR 009** — bootstrap carve-out exists so the very first session can write to otherwise-protected paths. Preserve it.
- **ADR 010** — three-tier honesty (verdicts must be `pass | needs-fixes | needs-rework`, never silently softened).

Index: [docs/architecture/decisions/](../../docs/architecture/decisions/).

## Common mistakes to flag in review

1. New `.jinja` file under `template/.github/catalog/`.
2. New subagent agent without `SubagentStop` hook entry.
3. Hook script added without a `tests/hooks/test_*.py` companion.
4. State-field rename in one place but not in `_state_io.py` / parsers / tests.
5. Hardcoded project name, language, or author string in a `.jinja`.
6. Restrictive `tools:` list added to a generic agent/prompt with no justification.
7. README counts drift (e.g. "6 core subagents", "ADRs 001–010", "8 manual prompts") not updated when those numbers change.
8. New convention introduced in one agent file but not propagated to the others (Required reads, output artifact paths, verdict format).
9. Edits to generated/output files instead of `template/` sources.
10. Linking to external docs without first checking [copilot-customization-docs](../copilot-customization-docs/SKILL.md) for the canonical URL.

## When in doubt

- Read the relevant ADR before changing a design rule.
- Run `make test-all`. If it doesn't fail and a real bug ships anyway, that's a missing test — add it.
- Compare the change to the corresponding pattern in another agent/prompt; consistency is a feature here.
