# Copilot Autonomous Template

A [copier](https://copier.readthedocs.io/) template for bootstrapping an autonomous AI development workflow using GitHub Copilot.

## What You Get

This template creates a complete `.github/` setup for autonomous development:

- **Autonomous builder agent** — a build loop that plans, implements, tests, and checkpoints
- **Reviewer subagent** — code review with restricted read-only tools + handoff to fix
- **Planner subagent** — research and planning with read-only tools + handoff to implement
- **7 dev-cycle prompts** — manual workflow: plan → implement → review → complete
- **Documentation skeleton** — vision lock, ADRs, open questions, tech debt, glossary
- **Roadmap structure** — checkpoint-based cross-session continuity
- **Prompt guide** — how to use the workflow (for humans)

## Usage

### New project

```bash
pip install copier
copier copy gh:YOUR_USER/copilot-autonomous-template my-new-project
```

### Existing repo

```bash
cd existing-repo
copier copy gh:YOUR_USER/copilot-autonomous-template .
```

### Update (pull template improvements)

```bash
copier update
```

## After Generation

1. Open the repo in VS Code
2. Review and customize `.github/copilot-instructions.md` for your project
3. Write your initial vision in `docs/vision/VISION-LOCK.md`
4. Select the **autonomous-builder** agent in Copilot Chat
5. Tell it to start Phase 0 (vision baseline)

## Template Variables

| Variable | Description |
|----------|-------------|
| `project_name` | Human-readable name (e.g., "My Cool Tool") |
| `project_slug` | URL-safe slug (auto-derived) |
| `description` | One-line project description |
| `language` | Primary language: Python, TypeScript, Go, Rust, or Mixed |
| `author` | Your name or team |

## How It Works

The autonomous builder agent runs a continuous loop:

1. **Discover** — reads checkpoint file, vision lock, and repo state
2. **Plan** — identifies the next highest-leverage slice of work
3. **Implement** — writes code, tests, and docs
4. **Validate** — runs tests and reviews via subagents
5. **Checkpoint** — commits and updates durable state for the next session

Each session is stateless — all cross-session continuity comes from files in the repo and repository memory.

The manual dev cycle (`/phase-plan` → `/implement` → `/code-review` → `/phase-complete`) remains available for human-driven sessions.

## Inspired By

This template extracts the autonomous development workflow from [Local Repo Sentinel](https://github.com/jakce/sentinel), where it was developed and battle-tested across 20+ autonomous sessions.
