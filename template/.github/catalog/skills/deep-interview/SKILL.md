---
name: deep-interview
description: "Socratic requirements elicitation. Use when requirements are vague, when starting a new project or phase, or when the user asks to clarify what should be built. Surfaces hidden assumptions through structured questioning."
---

# Deep Interview

Structured requirements clarification through Socratic questioning. Use this skill to surface hidden assumptions, clarify ambiguous requirements, and ensure you understand what needs to be built before you build it.

## When to Use

- Bootstrap: Understanding an existing project's intent
- New phase planning: Clarifying what features should do
- Ambiguous user requests: "Build me a dashboard" (what kind? for whom? showing what?)
- After discovering conflicting requirements in docs

## Interview Protocol

### Round 1 — Understand the User

Ask about:
- **Who** uses this? (persona, technical level, frequency of use)
- **What** problem does it solve? (pain point, current workaround)
- **Where** does it fit? (standalone, part of a flow, integration point)
- **When** is it used? (triggers, frequency, urgency)

### Round 2 — Define Success

Ask about:
- **What does "done" look like?** (specific observable outcomes)
- **What's the minimum viable version?** (smallest useful increment)
- **What would delight the user?** (beyond functional — experience quality)
- **What would make this fail?** (deal-breakers, must-not-happen scenarios)

### Round 3 — Surface Assumptions

Challenge with:
- "You mentioned [X] — does that mean [Y], or is there a different intent?"
- "What happens when [edge case]?"
- "Is [assumption] always true, or are there exceptions?"
- "Who else is affected by this besides the primary user?"

### Round 4 — Prioritize and Scope

Clarify:
- Which requirements are must-have vs. nice-to-have?
- What's explicitly out of scope?
- Are there dependencies on other work?
- What constraints exist (performance, compatibility, accessibility)?

## Ambiguity Gating

After each round, assess ambiguity:

- **High ambiguity** (50%+ questions have unclear answers): Ask more questions. Do not proceed to planning.
- **Medium ambiguity** (25-50%): Note the gaps. Proceed to planning but flag assumptions explicitly.
- **Low ambiguity** (<25%): Requirements are sufficiently clear. Proceed.

## Output Format

```markdown
## Requirements Summary

### Context
[Who, what, where, when — summarized from interview]

### Success Criteria
1. [Specific, testable criterion]
2. [Specific, testable criterion]

### Assumptions (to verify)
- [Assumption] — confidence: high/medium/low
- [Assumption] — confidence: high/medium/low

### Out of Scope
- [Explicit exclusion]

### Open Questions
- [Question that still needs an answer]

### Ambiguity Level: [High/Medium/Low]
```

## Tips

- Use `vscode_askQuestions` for interactive interviews when the user is present
- Don't ask more than 5 questions per round — respect attention
- Frame questions as multiple-choice when possible (easier to answer than open-ended)
- Record the interview output in `roadmap/` or the relevant phase plan
