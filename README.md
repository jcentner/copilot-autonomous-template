# Copilot Autonomous Template

A [copier](https://copier.readthedocs.io/) template for bootstrapping an autonomous AI development workflow using GitHub Copilot.

> **v1.0.0 (April 2026)** — first tagged release. The workflow is a hook-verified stage machine: `bootstrap → planning → design-critique → implementation-planning → implementation-critique → executing → reviewing → cleanup`. Workflow state lives in `state.md` (machine), narrative in `CURRENT-STATE.md`, and per-tool activity in `roadmap/sessions/<session>.md`. See [CHANGELOG.md](CHANGELOG.md) and [docs/architecture/decisions/](docs/architecture/decisions/) (ADRs 001–010) for the design rationale.

## What you get

This template creates a complete `.github/` setup for autonomous development:

- **Autonomous builder agent** — stage orchestrator that dispatches subagents based on `Stage` in `roadmap/state.md`.
- **6 core subagents** — `planner`, `critic`, `product-owner`, `reviewer`, `tester`, plus `Explore` for read-only research.
- **Hook-enforced state machine** — `stage-gate` (edits gated by stage), `session-gate` (Stop backstop for terminal bypass), `tool-guardrails` (destructive-command denylist), `subagent-verdict-check` (SubagentStop state verification), `tester-isolation` (tester can't read implementation), `evidence-tracker`, `context-pressure`.
- **8 manual-override prompts** — `/design-plan`, `/implementation-plan`, `/implement`, `/code-review`, `/strategic-review`, `/phase-complete`, `/vision-expand`, `/resume`.
- **Workflow catalog** — dormant capabilities activated by the human at bootstrap (2 agents, 4 skills, 1 hook, 2 prompts, 2 patterns).
- **`AGENTS.md`** — cross-agent instructions recognized by Copilot, Claude Code, and other AI agents.
- **Documentation skeleton** — vision lock (versioned living document), ADRs, open questions, tech debt, glossary, phase wraps.
- **Roadmap structure** — checkpoint-based cross-session continuity with machine-readable fields hooks can parse.
- **Test suite** — 160 unit tests for hooks + smoke test for generated output (`make test-all`).

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
4. The repo includes a `BOOTSTRAP.md` that guides the first session — greenfield projects get an interactive brainstorm, existing projects get automatic vision synthesis
5. Select the **autonomous-builder** agent in Copilot Chat
6. The builder reads `BOOTSTRAP.md`, completes it, deletes it, and continues to implementation

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

A **Stop hook** (`session-gate.py`) enforces discipline: it parses `roadmap/state.md` and blocks stop unless the current stage's gating fields are satisfied (e.g., during `executing`: tests pass, reviewer invoked, no Critical/Major findings, committed). A `subagent-verdict-check.py` SubagentStop hook does the same for critic/product-owner/reviewer/planner returns. This prevents premature stopping and skipped reviews.

**Skills workflow**: During bootstrap (and whenever a new technology is adopted), the builder creates Agent Skills in `.github/skills/` that ground all agents in official documentation for each technology in the stack. These are auto-discovered by Copilot when relevant.

**Workflow catalog**: The template ships with a catalog of pre-vetted dormant capabilities in `.github/catalog/`. During bootstrap, the builder evaluates project characteristics against catalog trigger conditions and activates matching items by copying them into the appropriate `.github/` directories. For example, a project with a UI gets the designer agent and design-system skill; a project with CI gets the ci-gate hook. The catalog enables a lean default footprint that self-expands as project needs emerge. See `MANIFEST.md` for the full index.

**Vision lock**: A single versioned living document, updated in place with changelog entries. Minor version bumps for within-scope refinements (new constraints, priority shifts); major version changes (scope, goals) require human approval. When the vision is fully realized, the agent proposes new directions and, after human approval, archives the old vision and writes a new version.

Each session is stateless — all cross-session continuity comes from files in the repo and repository memory.

The manual prompts (`/design-plan` → `/implementation-plan` → `/implement` → `/code-review` → `/strategic-review` → `/phase-complete`) remain available as override tools for human-driven sessions. Use `/resume` to unblock a session waiting on design approval, vision update, or a human decision.

### Copilot CLI Support

The autonomous builder works with Copilot CLI for background execution:
- Worktree isolation keeps agent changes separate from your active work
- Custom agents are supported (experimental: `github.copilot.chat.cli.customAgents.enabled`)
- Sessions continue when VS Code closes

## Inspired By

This template extracts the autonomous development workflow from [Local Repo Sentinel](https://github.com/jakce/sentinel), where it was developed and battle-tested across 20+ autonomous sessions.
