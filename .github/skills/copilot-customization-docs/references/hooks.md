# Hooks Reference

> Source: https://code.visualstudio.com/docs/copilot/customization/hooks
> Last verified: April 2026

Hooks execute shell commands at agent lifecycle points with guaranteed outcomes. Unlike instructions (which guide), hooks **enforce**.

## Hook Lifecycle Events

| Event | When | Use Case |
|-------|------|----------|
| `SessionStart` | User submits first prompt | Initialize resources, inject project context |
| `UserPromptSubmit` | User submits a prompt | Audit requests, inject system context |
| `PreToolUse` | Before agent invokes any tool | Block dangerous operations, require approval |
| `PostToolUse` | After tool completes | Run formatters, log results, validate changes |
| `PreCompact` | Before context compaction | Export important context before truncation |
| `SubagentStart` | Subagent spawned | Track nested usage, initialize resources |
| `SubagentStop` | Subagent completes | Aggregate results, block premature completion |
| `Stop` | Agent session ends | Generate reports, enforce completion criteria |

## File Locations

| Scope | Path |
|-------|------|
| Workspace | `.github/hooks/*.json` |
| Workspace (Claude) | `.claude/settings.json`, `.claude/settings.local.json` |
| User | `~/.copilot/hooks/`, `~/.claude/settings.json` |
| Agent-scoped | `hooks:` field in `.agent.md` frontmatter (requires `chat.useCustomAgentHooks`) |

## Hook Configuration Format

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "command": "npx prettier --write \"$TOOL_INPUT_FILE_PATH\""
      }
    ]
  }
}
```

### Command Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | string | Must be `"command"` |
| `command` | string | Default command (cross-platform) |
| `windows` | string | Windows-specific override |
| `linux` | string | Linux-specific override |
| `osx` | string | macOS-specific override |
| `cwd` | string | Working directory (relative to repo root) |
| `env` | object | Additional environment variables |
| `timeout` | number | Timeout in seconds (default: 30) |

## Agent-Scoped Hooks (Preview)

Define hooks directly in custom agent frontmatter. Only runs when that agent is active.

```yaml
---
name: "Strict Builder"
hooks:
  Stop:
    - type: command
      command: "python3 .github/hooks/scripts/check-completion.py"
---
```

Requires `chat.useCustomAgentHooks: true`.

## Hook I/O

### Input (JSON on stdin)

Every hook receives:
```json
{
  "timestamp": "2026-02-09T10:30:00.000Z",
  "cwd": "/path/to/workspace",
  "sessionId": "session-id",
  "hookEventName": "Stop"
}
```

Additional fields vary by event type.

### Output (JSON on stdout)

```json
{
  "continue": true,
  "stopReason": "Security policy violation",
  "systemMessage": "Warning shown to user"
}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — parse stdout as JSON |
| 2 | Blocking error — stop processing, show error to model |
| Other | Non-blocking warning — show warning, continue |

## Key Event Details

### Stop Hook

Input includes `stop_hook_active` (boolean). **Always check this to prevent infinite loops.**

Output:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "decision": "block",
    "reason": "Run test suite before finishing."
  }
}
```

### PreToolUse Hook

Output controls tool execution:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Blocked by policy",
    "updatedInput": {},
    "additionalContext": "Extra info for the model"
  }
}
```

`permissionDecision`: `"allow"`, `"deny"`, or `"ask"`. Most restrictive wins when multiple hooks fire.

### PostToolUse Hook

Can inject context or block further processing:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Lint errors found in edited file"
  }
}
```
