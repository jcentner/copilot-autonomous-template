# Subagents & Orchestration Reference

> Source: https://code.visualstudio.com/docs/copilot/agents/subagents
> Last verified: April 2026

## What Are Subagents

Subagents are independent AI agents that perform focused work in an isolated context and report results back to the main agent. They appear in chat as collapsible tool calls.

Key properties:
- **Context isolation**: Subagent gets a clean context with only the subtask
- **Synchronous execution**: Main agent waits for subagent result
- **Parallel capable**: Multiple subagents can run simultaneously
- **Summary return**: Only the final result is passed back (not all intermediate tool calls)

## Invocation

### Agent-initiated (typical)

The main agent decides when to spawn subagents. Ensure `runSubagent` (or `agent`) tool is enabled.

Hint subagent use by phrasing prompts to suggest isolated research or parallel analysis:
- "Research the best auth methods for this project"
- "Use the Plan agent to create an implementation plan"

### In prompt files

Include `agent` or `runSubagent` in tools:

```yaml
---
tools: ['agent', 'read', 'search', 'edit']
---
Run a subagent to research the feature, then update the docs.
```

## Custom Agents as Subagents (Experimental)

Subagents inherit the main session's agent by default. Use custom agents for specialized behavior.

### Control invocation

| Frontmatter | Effect |
|-------------|--------|
| `user-invocable: false` | Hidden from dropdown, still available as subagent |
| `disable-model-invocation: true` | Cannot be invoked as subagent (unless explicitly listed in parent's `agents`) |

### Restrict allowed subagents

In the parent agent's frontmatter:

```yaml
agents:
  - planner       # Only these agents can be subagents
  - reviewer
```

- `agents: ['*']` — allow all (default)
- `agents: []` — prevent subagent use
- Explicitly listing an agent in `agents` overrides `disable-model-invocation: true`

## Nested Subagents

By default, subagents cannot spawn further subagents.

Enable with: `chat.subagents.allowInvocationsFromSubagents` setting (default: `false`).

Max nesting depth: **5 levels**.

### Self-referential agents

An agent can list itself in its `agents` array for divide-and-conquer patterns:

```yaml
---
name: RecursiveProcessor
tools: ['agent', 'read', 'search']
agents: [RecursiveProcessor]
---
```

Requires `chat.subagents.allowInvocationsFromSubagents` to be enabled.

## Orchestration Patterns

### Coordinator and Worker

A coordinator agent delegates to specialized worker agents:

```yaml
---
name: Feature Builder
tools: ['agent', 'edit', 'search', 'read']
agents: ['Planner', 'Implementer', 'Reviewer']
---
1. Use Planner subagent to break down the feature
2. Use Implementer subagent to write code for each task
3. Use Reviewer subagent to check the implementation
4. Iterate until converged
```

Worker agents define their own tool access and can use faster/cheaper models:

```yaml
---
name: Planner
user-invocable: false
tools: ['read', 'search']
---
```

### Multi-perspective Review

Run multiple review perspectives as parallel subagents:

```yaml
---
name: Thorough Reviewer
tools: ['agent', 'read', 'search']
---
Run these subagents in parallel:
- Correctness reviewer
- Code quality reviewer
- Security reviewer
- Architecture reviewer
Then synthesize findings.
```

## What the User Sees

Subagent runs appear as collapsible tool calls showing:
- Custom agent name (if specified)
- Currently running tool
- Expandable for full details (all tool calls, prompt, result)
