# Permissions & Autopilot Reference

> Source: https://code.visualstudio.com/docs/copilot/agents/overview
> Last verified: April 2026

## Permission Levels

The permissions picker in the Chat view controls how much autonomy agents have for tool calls and terminal commands.

| Level | Behavior |
|-------|----------|
| **Default Approvals** | Uses per-setting approvals. By default, only read-only and safe tools auto-approve. |
| **Bypass Approvals** | Auto-approves all tool calls without confirmation dialogs. Agent may still ask clarifying questions. |
| **Autopilot** (Preview) | Auto-approves all tool calls, auto-responds to agent questions, agent works autonomously until task is complete. |

## Autopilot Mode

Autopilot is the fully autonomous mode. The agent:
- Auto-approves all tool calls (file edits, terminal commands, etc.)
- Auto-responds to any clarifying questions
- Continues working until the task is complete or it gets stuck

### Implications for agent design

When an agent runs under Autopilot:
- **Cannot rely on human answers** — questions get auto-responded, not answered by a human
- **Must make evidence-based decisions** — instead of asking, decide and record the decision
- **Should checkpoint frequently** — write state to files in case the session ends
- **Context window is finite** — use subagents for research to keep main context clean

### Recommended settings for Autopilot

| Setting | Value | Purpose |
|---------|-------|---------|
| `chat.autopilot.enabled` | `true` | Enable autopilot (on by default) |
| `chat.agent.sandbox` | `true` | Restrict file writes to workspace directory |

## Agent Types

Agents run in different environments:

| Type | Where | How | Use Case |
|------|-------|-----|----------|
| **Local** | Your machine, VS Code | Interactive in editor | Brainstorming, iteration, editor context |
| **Copilot CLI** | Your machine, background | Autonomous via CLI | Well-defined tasks, Git worktree isolation |
| **Cloud** | GitHub infrastructure | Remote, PR-based | Pull requests, team collaboration |
| **Third-party** | Varies | Anthropic/OpenAI SDK | Specific AI provider |

### Local agent built-in modes

| Agent | Role |
|-------|------|
| **Agent** | Autonomous — plans, implements, runs commands, invokes tools |
| **Plan** | Creates structured implementation plans, hands off to Agent |
| **Ask** | Answers questions without making file changes |

## Handoffs Between Agent Types

You can hand off sessions between agent types:
- Local → Copilot CLI: Select from session type dropdown
- Copilot CLI → Cloud: Use `/delegate` command
- Local → Cloud: Select from session type dropdown

Full conversation history carries over. Original session is archived.

## Relevant Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `chat.agent.enabled` | org-managed | Master switch for agents |
| `chat.autopilot.enabled` | `true` | Enable autopilot permission level |
| `chat.agent.sandbox` | `false` | Restrict writes to workspace |
| `chat.subagents.allowInvocationsFromSubagents` | `false` | Allow nested subagents |
| `chat.useAgentsMdFile` | configurable | Enable AGENTS.md support |
| `chat.useClaudeMdFile` | configurable | Enable CLAUDE.md support |
| `chat.useNestedAgentsMdFiles` | experimental | Subfolder AGENTS.md files |
| `chat.useCustomAgentHooks` | experimental | Agent-scoped hooks |
| `chat.useCustomizationsInParentRepositories` | `false` | Monorepo: discover from parent repo root |
| `github.copilot.chat.organizationCustomAgents.enabled` | `false` | Org-level custom agents |
| `github.copilot.chat.organizationInstructions.enabled` | `false` | Org-level instructions |
