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
      autonomous-builder.agent.md.jinja   # Main autonomous build loop agent (with Stop hook)
      planner.agent.md.jinja              # Read-only research/planning subagent
      reviewer.agent.md.jinja             # Code review + security subagent with handoff
      tester.agent.md.jinja               # Test-from-spec subagent (hidden from picker)
    hooks/
      scripts/
        slice-gate.py               # Stop hook: enforces review + prevents premature stopping
    prompts/
      PROMPT-GUIDE.md.jinja         # Human-facing usage guide
      phase-plan.prompt.md.jinja    # Plan a new development phase
      implementation-plan.prompt.md.jinja  # File-by-file implementation checklist
      implement.prompt.md.jinja     # Execute an implementation plan
      code-review.prompt.md.jinja   # Code review + security audit
      phase-complete.prompt.md.jinja      # Complete a phase, update docs
    skills/
      README.md                     # Stack skills convention (verbatim)
  docs/                             # Documentation skeleton (vision, architecture, reference)
    vision/
      VISION-LOCK.md.jinja          # Immutable vision lock (goals, outcomes, constraints)
      revisions/
        README.md                   # Vision revision format and rules (verbatim)
      archive/                      # Archived vision versions
  roadmap/                          # Roadmap structure with checkpoint protocol
```

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
- **Vision lock is immutable.** Once written, it is never edited directly. Minor refinements go in `docs/vision/revisions/`. A completed vision is archived and replaced with a new version.
- **Stack skills** are Agent Skills (`.github/skills/<name>/SKILL.md`) created by the autonomous builder for each technology in the stack. They ground agents in official docs.
- **No restrictive `tools` list** unless intentionally restricting (e.g., planner agent is read-only by design).
- **Subagent support**: agents can list allowed subagents in frontmatter `agents:` array. The autonomous-builder uses planner, reviewer, tester, and Explore as subagents.
- **Handoffs**: agents define `handoffs:` in frontmatter to create transition buttons between agents (e.g., planner → implementation).

## Validating Changes

There is no build step or test suite. To validate:

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
