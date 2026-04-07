# Instructions Reference

> Source: https://code.visualstudio.com/docs/copilot/customization/custom-instructions
> Last verified: April 2026

## Types of Instructions

### Always-on Instructions

Automatically included in every chat request.

| File | Location | Notes |
|------|----------|-------|
| `copilot-instructions.md` | `.github/` | Primary project-wide instructions |
| `AGENTS.md` | Root or subfolders | Multi-agent compatible (works with Claude Code, etc.) |
| `CLAUDE.md` | Root, `.claude/`, or `~/` | Claude Code compatibility |

### File-based Instructions

Applied dynamically based on `applyTo` glob patterns or semantic `description` matching.

| File | Location |
|------|----------|
| `*.instructions.md` | `.github/instructions/` (recursive) |
| `*.instructions.md` | `.claude/rules/` (Claude format) |

## copilot-instructions.md

Single file at `.github/copilot-instructions.md`. Applied to all chat requests in the workspace.

Use for:
- Coding style and naming conventions
- Technology stack declarations
- Architectural patterns
- Security requirements and error handling
- Documentation standards

## .instructions.md Files

### Frontmatter

```yaml
---
name: "Python Standards"               # Display name (defaults to filename)
description: "Coding conventions for Python files"  # Shown on hover
applyTo: "**/*.py"                     # Glob pattern for auto-apply
---
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Display name in UI |
| `description` | No | Shown on hover; also used for semantic matching |
| `applyTo` | No | Glob pattern. If omitted, not auto-applied (manual attach only) |

### Glob Pattern Examples

| Pattern | Matches |
|---------|---------|
| `*` | All files in current directory |
| `**` or `**/*` | All files recursively |
| `**/*.py` | All Python files recursively |
| `src/**/*.py` | Python files under `src/` recursively |
| `**/*.ts,**/*.tsx` | Multiple patterns (comma-separated) |
| `**/subdir/**/*.py` | Python files under any `subdir/` at any depth |

### File Locations

| Scope | Path |
|-------|------|
| Workspace | `.github/instructions/` (default, recursive) |
| Workspace (Claude) | `.claude/rules/` |
| User profile | `~/.copilot/instructions/` or VS Code user data |

Configure via `chat.instructionsFilesLocations` setting.

## AGENTS.md

Always-on instructions in `AGENTS.md` at workspace root. Enable with `chat.useAgentsMdFile` setting.

### Nested AGENTS.md (experimental)

Enable `chat.useNestedAgentsMdFiles` for subfolder-level AGENTS.md files. Each subfolder can have its own AGENTS.md that applies to files in that subtree.

## CLAUDE.md

Enable with `chat.useClaudeMdFile` setting. Searched in:

| Location | Path |
|----------|------|
| Workspace root | `CLAUDE.md` |
| .claude folder | `.claude/CLAUDE.md` |
| User home | `~/.claude/CLAUDE.md` |
| Local variant | `CLAUDE.local.md` (not committed) |

Claude `.claude/rules/` instructions use `paths` property instead of `applyTo`.

## Instruction Priority

When multiple instruction types exist (highest priority first):

1. Personal instructions (user-level)
2. Repository instructions (`copilot-instructions.md` or `AGENTS.md`)
3. Organization instructions

## Tips for Effective Instructions

- Keep short and self-contained
- Include reasoning behind rules (helps AI handle edge cases)
- Show preferred/avoided patterns with code examples
- Focus on non-obvious rules (skip what linters enforce)
- Use multiple `.instructions.md` files for language/framework-specific rules
- Reference instruction files in prompts and agents via Markdown links
