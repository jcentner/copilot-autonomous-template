# Custom Agents Reference

> Source: https://code.visualstudio.com/docs/copilot/customization/custom-agents
> Last verified: April 2026

## File Format

Custom agent files use `.agent.md` extension with optional YAML frontmatter + Markdown body.

VS Code also detects any `.md` files in `.github/agents/` as custom agents.

## File Locations

| Scope | Path |
|-------|------|
| Workspace | `.github/agents/` |
| Workspace (Claude format) | `.claude/agents/` |
| User profile | `~/.copilot/agents/` or VS Code user data |

Configure additional paths via `chat.agentFilesLocations` setting.

## Frontmatter Fields

```yaml
---
description: "Brief description shown as placeholder text in chat input"
name: "Agent name (defaults to filename if omitted)"
argument-hint: "Hint text shown in chat input to guide user interaction"
tools:
  - search           # Built-in tool set (includes search/codebase, search/textSearch, etc.)
  - web              # Built-in tool set (includes web/fetch)
  - search/codebase  # Individual built-in tool
  - myServer/*       # All tools from an MCP server
agents:
  - planner          # Allowed subagent names
  - reviewer
  - '*'              # Or allow all agents
  - []               # Or prevent any subagent use
model: "Claude Sonnet 4.5 (copilot)"   # Single model or prioritized array
user-invocable: true           # Show in agents dropdown (default: true)
disable-model-invocation: false # Prevent subagent invocation (default: false)
target: vscode                 # vscode or github-copilot
handoffs:
  - label: "Start Implementation"
    agent: implementation
    prompt: "Now implement the plan above."
    send: false         # Auto-submit prompt (default: false)
    model: "GPT-5.2 (copilot)"  # Optional model override
hooks:                   # Preview — requires chat.useCustomAgentHooks
  PreToolUse:
    - command: "echo pre-tool"
mcp-servers: []          # For target: github-copilot agents
---
```

### Field Details

| Field | Required | Description |
|-------|----------|-------------|
| `description` | No | Shown as placeholder text. Critical for discovery when used as subagent. |
| `name` | No | Display name. Defaults to filename. |
| `tools` | No | Restricts available tools. Omit to inherit all tools. |
| `agents` | No | Restricts which subagents can be used. `*` = all, `[]` = none. |
| `model` | No | String or array (tried in order until one is available). |
| `user-invocable` | No | Set `false` to hide from dropdown (subagent-only). |
| `disable-model-invocation` | No | Set `true` to prevent other agents from invoking this as subagent. |
| `handoffs` | No | Transition buttons shown after response completes. |
| `hooks` | No | Preview. Scoped hook commands that only run when this agent is active. |
| `target` | No | `vscode` (local) or `github-copilot` (cloud). |

### Deprecated Fields

| Field | Replacement |
|-------|-------------|
| `infer` | Use `user-invocable` + `disable-model-invocation` instead |

## Body

The body contains instructions in Markdown. These are prepended to every user prompt when the agent is active.

- Reference files with Markdown links (auto-attached as context)
- Reference tools with `#tool:<tool-name>` syntax (e.g., `#tool:web/fetch`)

## Handoffs

Handoffs create guided sequential workflows between agents. After a response completes, handoff buttons appear as next-step suggestions.

```yaml
handoffs:
  - label: "Button text"
    agent: target-agent-name
    prompt: "Pre-filled prompt for target agent"
    send: false    # true = auto-submit
    model: "optional model override"
```

## Subagent Configuration

Agents can be used as subagents by other agents. Control this with:

- `agents: ['planner', 'reviewer']` — whitelist specific subagents
- `agents: ['*']` — allow all (default)
- `agents: []` — prevent subagent use
- `user-invocable: false` — hide from picker, still available as subagent
- `disable-model-invocation: true` — prevent subagent invocation (overridden if explicitly listed in another agent's `agents` array)

## Claude Agent Format

Files in `.claude/agents/` use plain `.md` with Claude-specific frontmatter:

```yaml
---
name: "Agent name (required)"
description: "What the agent does"
tools: "Read, Grep, Glob, Bash"         # Comma-separated string
disallowedTools: "Write, Edit"           # Comma-separated string
---
```

VS Code maps Claude tool names to corresponding VS Code tools.

## Tool List Priority

When `tools` appears in both a custom agent and a prompt file, the prompt file's tools take precedence.
