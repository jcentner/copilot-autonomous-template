# copilot-autonomous-template — Copilot Instructions

You are working on **copilot-autonomous-template**, a [Copier](https://copier.readthedocs.io/) template that bootstraps an autonomous AI development workflow using GitHub Copilot.

This repo is NOT a runnable project. It is a template that generates `.github/` scaffolding (agents, prompts, instructions), documentation skeletons, and roadmap structure into other repos.

## Repository Layout

```
copier.yml                          # Copier config: variables, version, subdirectory
template/                           # Everything under here gets copied to the target
  README.md.jinja                   # Generated project README
  AGENTS.md.jinja                   # Cross-agent instructions (Copilot, Claude Code, etc.)
  .github/
    copilot-instructions.md.jinja   # Generated project-level Copilot instructions
    instructions/
      docs.instructions.md          # File-based instructions for *.md (no Jinja — copied as-is)
    agents/
      autonomous-builder.agent.md.jinja   # Stage orchestrator (with Stop hook)
      planner.agent.md.jinja              # Read-only research/planning subagent
      critic.agent.md.jinja               # Adversarial design/implementation review
      product-owner.agent.md.jinja        # User stories + strategic review
      reviewer.agent.md.jinja             # Per-slice code review + security
      tester.agent.md.jinja               # Test-from-spec subagent (isolation-enforced)
    hooks/
      scripts/
        _state_io.py                # Shared atomic read/write for state.md
        stage-gate.py               # PreToolUse: edits gated by Stage
        session-gate.py             # Stop hook: blocks premature stop, parses state.md
        tool-guardrails.py          # PreToolUse: destructive-command + protected-path denylist
        subagent-verdict-check.py   # SubagentStop: verifies critic/po/reviewer/planner wrote state
        tester-isolation.py         # PreToolUse (tester): blocks reads of source code
        evidence-tracker.py         # PostToolUse: per-session activity log
        context-pressure.py         # PostToolUse: context-window advisory
        write-test-evidence.py      # Agent helper: stamps Tests Pass + Evidence For Slice
        write-commit-evidence.py    # Agent helper: stamps Committed (refuses on dirty tree)
    prompts/
      PROMPT-GUIDE.md.jinja         # Human-facing usage guide
      design-plan.prompt.md.jinja
      implementation-plan.prompt.md.jinja
      implement.prompt.md.jinja
      code-review.prompt.md.jinja
      strategic-review.prompt.md.jinja
      phase-complete.prompt.md.jinja
      vision-expand.prompt.md.jinja
      resume.prompt.md.jinja        # Unblock routing on Blocked Kind
    skills/
      README.md                     # Stack skills convention (verbatim)
    catalog/                        # Dormant workflow capabilities (the storehouse)
      MANIFEST.md                   # Machine-readable index of all catalog items (also a skill)
      README.md                     # How the catalog works
      agents/                       # Pre-crafted agents: designer, product-owner, security-reviewer, critic
      skills/                       # Pre-crafted skills: deep-interview, anti-slop, design-system, ci-verification
      hooks/                        # Pre-crafted hooks: tool-guardrails, ci-gate, context-checkpoint
      prompts/                      # Pre-crafted prompts: clarify, design-review
      patterns/                     # Reusable patterns: DESIGN.md template, commit trailers
  docs/                             # Documentation skeleton (vision, architecture, reference)
    vision/
      VISION-LOCK.md.jinja          # Versioned vision lock (goals, outcomes, constraints)
      archive/                      # Archived vision versions
  roadmap/                          # Roadmap structure with checkpoint protocol
    state.md.jinja                  # Machine-readable workflow state (Stage, Phase, Slice Evidence, etc.)
    CURRENT-STATE.md.jinja          # Narrative state (Context, Proposed Improvements, Active Session link)
    sessions/                       # Per-session activity logs (one file per Copilot session)
```

Unit tests live under `tests/hooks/` (160 tests, stdlib `unittest`). End-to-end smoke test in `tests/smoke.sh`. Run with `make test-all`.

## How Copier Templating Works

- `copier.yml` defines template variables and settings. `_subdirectory: template` means only `template/` is copied.
- Files ending in `.jinja` are rendered through Jinja2 and the `.jinja` suffix is stripped in output.
- Files without `.jinja` are copied verbatim.
- Template variables available in Jinja: `project_name`, `project_slug`, `description`, `language`, `author`.
- Jinja syntax: `{{ variable }}`, `{% if %}`, `{% for %}`, filters like `| lower`.

## Key Conventions

- **Edit template files, not output files.** All generated content lives under `template/`. Changes to the template are tested by running `copier copy`.
- **Preserve Jinja expressions.** When editing `.jinja` files, keep `{{ project_name }}`, `{{ description }}`, `{{ language }}` etc. intact. These are replaced at generation time.
- **Agent files use `.agent.md` extension** with YAML frontmatter for `description`, `tools`, `agents` (subagents), `handoffs`, `hooks`, `model`, etc. Files in `.github/agents/` are auto-detected by VS Code.
- **Agent-scoped hooks** use `hooks:` in agent frontmatter to run commands at lifecycle events (e.g., Stop hook). Requires `chat.useCustomAgentHooks: true`.
- **Hook scripts** live in `.github/hooks/scripts/`. They receive JSON on stdin and return JSON on stdout to influence agent behavior.
- **Prompt files use `.prompt.md` extension** with YAML frontmatter (`description`, `agent`). Use `${input:variableName}` for runtime user input. Markdown links in prompt bodies auto-attach referenced files as context.
- **Instruction files use `.instructions.md` extension** with optional `applyTo` glob in frontmatter. Placed in `.github/instructions/`.
- **AGENTS.md** provides cross-agent instructions recognized by Copilot, Claude Code, and other AI agents.
- **Vision lock is a versioned living document.** Updated in place with changelog entries. Minor version bumps for within-scope changes; major version changes require human approval. Completed visions are archived to `docs/vision/archive/`.
- **Stack skills** are Agent Skills (`.github/skills/<name>/SKILL.md`) created by the autonomous builder for each technology in the stack. They ground agents in official docs.
- **No restrictive `tools` list** unless intentionally restricting (e.g., planner agent is read-only by design).
- **Subagent support**: agents can list allowed subagents in frontmatter `agents:` array. The autonomous-builder pre-lists both core (planner, reviewer, tester) and catalog (designer, product-owner, security-reviewer, critic) subagents. Catalog agents that don't exist as files are silently ignored until activated.
- **Handoffs**: agents define `handoffs:` in frontmatter to create transition buttons between agents (e.g., planner → implementation).
- **Workflow catalog** (`.github/catalog/`): Pre-vetted dormant capabilities the builder can activate on demand. MANIFEST.md is both the index and a skill (auto-discoverable by any agent). Catalog items are copied verbatim (no Jinja). Activation is autonomous for catalog items, human-approved for external sources.

## Validating Changes

Unit tests + smoke test:

```bash
make test-all          # Runs hook unit tests then smoke.sh
make test-hooks        # Just unit tests (fast, no copier copy)
```

Manual generation for inspection:

```bash
# Generate into a temp directory and inspect output
copier copy . /tmp/test-output --defaults \
  -d project_name="Test Project" \
  -d description="A test" \
  -d language="Python" \
  -d author="Test"

# Verify Jinja variables were substituted correctly
grep -r "project_name\|project_slug" /tmp/test-output  # should find no raw Jinja
grep -r "Test Project" /tmp/test-output                 # should find substituted values
```

## Design Principles

1. **The generated workflow must be self-contained.** A user should be able to open the generated repo in VS Code, select the autonomous-builder agent, and start working immediately.
2. **Manual and autonomous workflows coexist.** The prompt-based dev cycle (`/phase-plan` → `/implement` → `/code-review` → `/phase-complete`) works alongside the autonomous builder agent.
3. **Cross-session continuity via files.** `roadmap/CURRENT-STATE.md` is the checkpoint. No reliance on chat history or external state.
4. **Evidence-based, not speculative.** The vision lock must be grounded in shipped reality. Templates should not invent features or claims.
5. **Authority hierarchy.** Vision lock > ADRs > architecture docs > roadmap > open questions > instructions/prompts.

## What NOT to Do

- Don't add runtime code — this is purely a template repo.
- Don't hardcode project-specific values in `.jinja` files — use template variables.
- Don't add a `tools` list to agents/prompts unless intentionally restricting capabilities.
- Don't duplicate instructions across prompts — prompts link to `copilot-instructions.md` for shared context.

## Reviewing changes (mandatory doc-grounding)

This repo's product **is** GitHub Copilot customization. Any review of changes that touch agent / prompt / instruction / skill / hook files must be **grounded in the current Copilot docs**, not memory.

Before approving (or self-approving) any change to files under `template/.github/agents/`, `template/.github/prompts/`, `template/.github/instructions/`, `template/.github/skills/`, `template/.github/hooks/`, `template/.github/copilot-instructions.md.jinja`, or `template/AGENTS.md.jinja`:

1. **Consult the `copilot-customization-docs` skill** ([.github/skills/copilot-customization-docs/](.github/skills/copilot-customization-docs/)) for the relevant primitive (agents, prompts, instructions, hooks, subagents, permissions). The `references/` files there are version-stamped.
2. **If the skill's reference is older than ~3 months or the change touches a feature not covered, fetch the live doc** from the URLs listed in the skill (e.g., `https://code.visualstudio.com/docs/copilot/customization/custom-agents`). Cite the URL + retrieval date in the review or commit message.
3. **Validate frontmatter against the docs**, not against memory. Common things to check:
   - `tools:` values are real built-in tool sets / individual tools / `<server>/*` MCP names — not invented.
   - `agents:` declared subagents only work if the `agent` tool is included in `tools:` (per the docs verbatim).
   - Deprecated fields (e.g., `infer`) are not used.
   - Hook output JSON matches the schema for the hook event (`hookSpecificOutput` shape, `decision` / `permissionDecision` enum values, top-level `systemMessage` only where supported).
   - `applyTo` globs on `.instructions.md` use the documented syntax.
   - Stop hooks honor `stop_hook_active` to prevent infinite loops.
4. **Treat the smoke test as a must-pass, not an aspiration.** Frontmatter-scoped assertions (e.g., the researcher no-terminal check) must scan the YAML block, not the whole file body, because explanatory prose may legitimately mention denied tool names.

If a doc fetch reveals a Copilot feature change that affects shipped templates, add it to `## Proposed Workflow Improvements` in `roadmap/CURRENT-STATE.md` (or open a tech-debt entry) — do not silently retrofit the template without recording the source.

