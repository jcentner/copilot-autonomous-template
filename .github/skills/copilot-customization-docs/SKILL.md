---
name: copilot-customization-docs
description: "**REFERENCE SKILL** — GitHub Copilot AI customization features: custom agents (.agent.md), prompt files (.prompt.md), instruction files (.instructions.md), subagents, handoffs, autopilot mode, skills (SKILL.md), hooks, AGENTS.md, copilot-instructions.md, agent permissions. USE FOR: checking current syntax and frontmatter fields for agent/prompt/instruction files; verifying subagent configuration; understanding autopilot vs bypass-approvals vs default permission levels; updating template files to match latest Copilot features; checking if new Copilot features have been added. DO NOT USE FOR: general coding; MCP server setup; VS Code extension APIs."
---

# GitHub Copilot Customization Reference

Comprehensive reference for the VS Code Copilot customization primitives that this template generates. Use this skill when editing `.agent.md`, `.prompt.md`, `.instructions.md`, or `copilot-instructions.md` template files, or when checking whether the template aligns with the latest Copilot features.

## When to Use

- Editing or creating agent, prompt, instruction, or skill template files
- Verifying frontmatter syntax/fields are current
- Checking if new Copilot customization features have been added
- Understanding how subagents, handoffs, or autopilot work
- Reviewing whether the template's generated files match latest VS Code conventions

## Checking for Updates

The Copilot customization surface evolves. When in doubt about whether a feature is current:

1. **Fetch the canonical docs** — the official pages are the source of truth:
   - [Custom instructions](https://code.visualstudio.com/docs/copilot/customization/custom-instructions)
   - [Custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
   - [Prompt files](https://code.visualstudio.com/docs/copilot/customization/prompt-files)
   - [Agent skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
   - [Subagents](https://code.visualstudio.com/docs/copilot/agents/subagents)
   - [Agents overview](https://code.visualstudio.com/docs/copilot/agents/overview)
   - [Hooks](https://code.visualstudio.com/docs/copilot/customization/hooks)
   - [Customization overview](https://code.visualstudio.com/docs/copilot/copilot-customization)
   - [GitHub repo instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
2. **Compare against reference files** in this skill's [references/](./references/) folder
3. **Look for new primitives** — VS Code adds new customization types periodically (e.g., hooks, skills, agent plugins were all added over time)

## Quick Reference: Customization Primitives

| Primitive | File Pattern | Location | Applied |
|-----------|-------------|----------|---------|
| Workspace instructions | `copilot-instructions.md` | `.github/` | Always-on, all requests |
| AGENTS.md | `AGENTS.md` | Root or subfolders | Always-on, multi-agent compat |
| File instructions | `*.instructions.md` | `.github/instructions/` | When `applyTo` glob matches |
| Prompt files | `*.prompt.md` | `.github/prompts/` | On `/` slash command |
| Custom agents | `*.agent.md` | `.github/agents/` | When selected in agent picker |
| Skills | `SKILL.md` in named folder | `.github/skills/<name>/` | On-demand, via `/` or auto |
| Hooks | `*.json` | `.github/hooks/` | At agent lifecycle events |

## Detailed References

- [Custom agents reference](./references/agents.md) — frontmatter fields, subagent config, handoffs
- [Prompt files reference](./references/prompts.md) — frontmatter, input variables, tool lists
- [Instructions reference](./references/instructions.md) — applyTo patterns, always-on vs file-based
- [Subagents & orchestration reference](./references/subagents.md) — nesting, coordinator patterns, autopilot
- [Permissions & autopilot reference](./references/permissions.md) — permission levels, autopilot mode, settings
- [Hooks reference](./references/hooks.md) — Stop hooks, PreToolUse, PostToolUse, lifecycle events
