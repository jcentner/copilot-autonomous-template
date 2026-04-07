# Copilot Autonomous Template

A [copier](https://copier.readthedocs.io/) template for bootstrapping an autonomous AI development workflow using GitHub Copilot.

## What You Get

This template creates a complete `.github/` setup for autonomous development:

- **Autonomous builder agent** — a build loop that plans, implements, tests, reviews, and checkpoints
- **Reviewer subagent** — code review + security with restricted read-only tools + handoff to fix
- **Planner subagent** — research and planning with read-only tools + handoff to implement
- **Tester subagent** — writes tests from specs before seeing implementation (context isolation)
- **Stop hook** — deterministic enforcement that prevents premature stopping and skipped reviews
- **Stack skills scaffold** — auto-created skills that ground agents in official docs for each technology
- **5 manual override prompts** — plan, detail, implement, review, complete
- **AGENTS.md** — cross-agent instructions (works with Copilot, Claude Code, etc.)
- **Documentation skeleton** — vision lock (versioned living document), ADRs, open questions, tech debt, glossary
- **Roadmap structure** — checkpoint-based cross-session continuity with machine-readable status
- **Prompt guide** — how to use the workflow (for humans)

## Usage

### New project

```bash
pip install copier
copier copy gh:jcentner/copilot-autonomous-template my-new-project
```

### Existing repo

```bash
cd existing-repo
copier copy gh:jcentner/copilot-autonomous-template .
```

### Update (pull template improvements)

```bash
copier update
```

## After Generation

1. Open the repo in VS Code
2. Review and customize `.github/copilot-instructions.md` for your project
3. Enable recommended settings:
   - `chat.useCustomAgentHooks`: `true` (enables Stop hook)
   - `chat.autopilot.enabled`: `true` (for autonomous sessions)
   - `chat.agent.sandbox`: `true` (safety)
4. The autonomous builder synthesizes your initial vision into `docs/vision/VISION-LOCK.md`
5. Select the **autonomous-builder** agent in Copilot Chat
6. Tell it to start Phase 0 (vision baseline + stack skills)

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

1. **Orient** — reads checkpoint file, vision lock, and repo state
2. **Plan** — identifies the next highest-leverage slice of work
3. **Implement** — writes code
4. **Test** — runs tests (optionally uses tester subagent to write tests from spec first)
5. **Review** — invokes reviewer subagent for code review + security
6. **Fix** — addresses Critical/Major findings
7. **Commit** — atomic commit with conventional message
8. **Checkpoint** — updates durable state for the next session or slice

A **Stop hook** (`slice-gate.py`) enforces discipline: the agent cannot stop until the phase is marked complete or explicitly blocked. This prevents premature stopping and skipped reviews.

**Skills workflow**: During Phase 0 (and whenever a new technology is adopted), the builder creates Agent Skills in `.github/skills/` that ground all agents in official documentation for each technology in the stack. These are auto-discovered by Copilot when relevant.

**Vision lock**: A single versioned living document, updated in place with changelog entries. Minor version bumps for within-scope refinements (new constraints, priority shifts); major version changes (scope, goals) require human approval. When the vision is fully realized, the agent proposes new directions and, after human approval, archives the old vision and writes a new version.

Each session is stateless — all cross-session continuity comes from files in the repo and repository memory.

The manual prompts (`/phase-plan` → `/implement` → `/code-review` → `/phase-complete`) remain available as override tools for human-driven sessions.

### Copilot CLI Support

The autonomous builder works with Copilot CLI for background execution:
- Worktree isolation keeps agent changes separate from your active work
- Custom agents are supported (experimental: `github.copilot.chat.cli.customAgents.enabled`)
- Sessions continue when VS Code closes

## Inspired By

This template extracts the autonomous development workflow from [Local Repo Sentinel](https://github.com/jakce/sentinel), where it was developed and battle-tested across 20+ autonomous sessions.
