# Stack Skills

This directory contains [Agent Skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills) that ground all agents in official documentation for the project's technology stack.

## How It Works

Skills are auto-discovered by GitHub Copilot based on their description. When an agent works with a technology that has a matching skill, Copilot loads the skill's instructions and resources into context automatically.

Each skill lives in a named subdirectory with a `SKILL.md` file:

```
.github/skills/
├── README.md           (this file)
├── azure/
│   └── SKILL.md
├── next-js/
│   └── SKILL.md
└── postgresql/
    └── SKILL.md
```

## Who Creates Skills

The **autonomous-builder agent** creates skills:
- During **Phase 0** — for each significant technology in the existing stack
- During **implementation** — when adopting a new framework, cloud service, or library

Skills can also be created manually during human-driven sessions.

## Skill Requirements

Each skill must:
1. Link to official documentation (not rely on training data alone)
2. Document key conventions and patterns for this project's usage
3. Note pitfalls discovered during implementation
4. Have a specific description so Copilot loads it at the right time

## SKILL.md Format

```yaml
---
name: technology-name       # Must match directory name
description: "..."          # When to use this skill (max 1024 chars)
---
```

See the [Agent Skills docs](https://code.visualstudio.com/docs/copilot/customization/agent-skills) for the full specification.
