# Prompt Files Reference

> Source: https://code.visualstudio.com/docs/copilot/customization/prompt-files
> Last verified: April 2026

## File Format

Prompt files use `.prompt.md` extension with optional YAML frontmatter + Markdown body.

## File Locations

| Scope | Path |
|-------|------|
| Workspace | `.github/prompts/` |
| User profile | `~/.copilot/prompts/` or VS Code user data |

Configure additional paths via `chat.promptFilesLocations` setting.

## Frontmatter Fields

```yaml
---
description: "One-line description shown in / autocomplete"
agent: agent              # Which agent runs this prompt (default: current agent)
tools:
  - search
  - edit
  - web
model: "Claude Sonnet 4.5 (copilot)"
---
```

### Field Details

| Field | Required | Description |
|-------|----------|-------------|
| `description` | No | Shown in `/` autocomplete menu. Important for discoverability. |
| `agent` | No | Agent to use. `agent` = default agent mode. |
| `tools` | No | Restricts tools. Omit to inherit from agent. Takes priority over agent's tool list. |
| `model` | No | Override the model for this prompt. |

## Body

The body contains the prompt instructions in Markdown.

### Input Variables

Use `${input:variableName}` for runtime user input. VS Code prompts the user to provide a value.

```markdown
Review the implementation plan at: **${input:planPath}**
```

Optional default: `${input:variableName:default value}`

### File References

Markdown links auto-attach referenced files as context:

```markdown
- [Project instructions](../../.github/copilot-instructions.md)
- [Architecture](../../docs/architecture/overview.md)
```

Paths are relative to the prompt file's location.

### Tool References

Reference agent tools in the body with `#tool:<tool-name>`:

```markdown
Use #tool:web/fetch to check the latest docs.
```

## Invocation

- Type `/` in chat to see available prompts
- Select a prompt from the autocomplete menu
- Optionally add context after the prompt name

## Best Practices

- Keep descriptions concise — they appear in autocomplete
- Use `agent: agent` for prompts that need full tool access
- Link to shared instruction files rather than duplicating content
- Use input variables for parameterization
- Don't add a `tools` list unless intentionally restricting

## Tool List Priority

When tools are specified in both a prompt file and the active custom agent:
1. Prompt file's `tools` take highest priority
2. Custom agent's `tools` come next
3. Default tools apply if neither specifies
