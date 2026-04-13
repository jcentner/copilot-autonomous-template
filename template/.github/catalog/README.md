# Workflow Catalog

This directory contains **dormant workflow capabilities** — pre-crafted agents, skills, hooks, prompts, and patterns that the autonomous builder can activate on demand.

## How It Works

1. The builder reads [MANIFEST.md](MANIFEST.md) to discover available capabilities
2. Each item has **trigger conditions** — project characteristics that indicate the item is needed
3. During bootstrap and at the start of each phase, the builder evaluates triggers and activates matching items
4. Activation = copy the file from `catalog/` to its target location + log the activation

## What's Here

| Directory | Contents | Activates to |
|-----------|----------|-------------|
| `agents/` | Pre-crafted agent definitions | `.github/agents/` |
| `skills/` | Pre-crafted skills with SKILL.md | `.github/skills/` |
| `hooks/` | Hook scripts and configs | `.github/hooks/` |
| `prompts/` | Prompt files | `.github/prompts/` |
| `patterns/` | Reusable file templates | Various locations (see MANIFEST) |

## Trust Model

- **Catalog items** are pre-vetted and can be activated autonomously by the builder
- **External sources** require human approval before fetching and installing
- Activated items are logged in `docs/reference/agent-improvement-log.md`
- Standards are never weakened during activation — only capabilities are added

## Manual Activation

You can also activate catalog items manually:

```bash
# Activate the designer agent
cp .github/catalog/agents/designer.agent.md .github/agents/

# Activate a skill
cp -r .github/catalog/skills/deep-interview .github/skills/

# Activate a hook
cp .github/catalog/hooks/tool-guardrails.json .github/hooks/
```
