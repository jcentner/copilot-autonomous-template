---
description: "Structured requirements interview — surfaces hidden assumptions and clarifies ambiguous requirements before building."
agent: agent
---

# Requirements Clarification

Before building, let's make sure the requirements are clear.

Read for context:
- [Vision lock](../../docs/vision/VISION-LOCK.md)
- [Current state](../../roadmap/CURRENT-STATE.md)
- [Open questions](../../docs/reference/open-questions.md)

## Task

Clarify requirements for: **${input:feature:the next feature or phase}**

## Interview Protocol

### Round 1 — Understand the User
Ask 3-5 questions about:
- Who uses this feature? (persona, technical level, frequency)
- What problem does it solve? (pain point, current workaround)
- Where does it fit in the user's workflow?

### Round 2 — Define Success
Ask 3-5 questions about:
- What does "done" look like? (specific, observable outcomes)
- What's the minimum viable version?
- What would make this fail? (deal-breakers)

### Round 3 — Surface Assumptions
Challenge with:
- "You mentioned X — does that mean Y, or something else?"
- "What happens when [edge case]?"
- "Is [assumption] always true?"

### Round 4 — Scope and Prioritize
- Which requirements are must-have vs. nice-to-have?
- What's explicitly out of scope?
- Are there dependencies?

## Output

Write a requirements summary to the current phase plan or `roadmap/CURRENT-STATE.md`:

```markdown
## Requirements: [Feature Name]

### Context
[Who, what, where, when]

### Success Criteria
1. [Testable criterion]

### Assumptions
- [Assumption] — confidence: high/medium/low

### Out of Scope
- [Exclusion]

### Open Questions
- [Remaining unknowns]
```
