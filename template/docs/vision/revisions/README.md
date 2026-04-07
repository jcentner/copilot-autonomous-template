# Vision Revisions

Minor refinements to the vision lock are tracked here as sequentially numbered revision files. These supplement the vision lock — they do not replace it.

## When to Create a Revision

- A scope clarification is needed (something in the vision was ambiguous)
- A priority shift is discovered during implementation
- A new constraint is learned that affects vision goals
- A non-goal needs to be added based on stakeholder feedback

## When NOT to Create a Revision

- Implementation details (these belong in ADRs or architecture docs)
- Bug fixes or technical changes (these belong in tech debt or commit history)
- The vision is fully realized (this triggers a new vision version, not a revision)

## Format

Name files sequentially: `revision-001.md`, `revision-002.md`, etc.

```markdown
# Vision Revision VR-NNN

**Date**: YYYY-MM-DD
**Vision Version**: v1
**Phase**: Phase N — [title]
**Type**: Clarification | Priority Shift | Constraint | Scope Refinement | Non-Goal Addition

## Summary

One-paragraph description of the refinement.

## Rationale

Why this refinement is needed. What evidence or learning prompted it.

## Impact on Vision Goals

How this affects the "Where We're Going" goals, if at all.
```

## Rules

- Revisions are append-only — never edit or delete a revision file
- Each revision references the vision version it applies to
- When a new vision version is created (v2, v3, ...), accumulated revisions are moved to `docs/vision/archive/v{N}-revisions/`
