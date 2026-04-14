---
description: "Review UI changes against the project's DESIGN.md for visual consistency. Uses browser tools when available."
agent: agent
tools:
  - search
  - search/codebase
  - browser
---

# Design Review

Review recent UI changes for design consistency.

Read for context:
- [DESIGN.md](../../DESIGN.md)
- [Vision lock](../../docs/vision/VISION-LOCK.md)

## Task

Review design consistency for: **${input:scope:recent UI changes}**

## Review Checklist

### Color
- [ ] All colors match DESIGN.md palette tokens (no ad-hoc hex values)
- [ ] Contrast ratios meet WCAG AA (4.5:1 for text, 3:1 for large text)
- [ ] Semantic color usage is correct (error=red, success=green, etc.)

### Typography
- [ ] Font families match DESIGN.md specification
- [ ] Heading hierarchy is correct (no skipped levels)
- [ ] Font sizes follow the type scale
- [ ] Line heights and letter-spacing match the system

### Spacing & Layout
- [ ] Spacing uses the defined scale (no arbitrary pixel values)
- [ ] Grid alignment is maintained
- [ ] Consistent padding/margin patterns across similar components

### Components
- [ ] Buttons have all states: default, hover, focus, active, disabled
- [ ] Inputs have all states: default, focus, error, disabled
- [ ] Loading states exist for async operations
- [ ] Empty states exist for lists and data displays

### Motion
- [ ] Animations use the approved easing curves
- [ ] `prefers-reduced-motion` is respected
- [ ] No bounce/elastic easing

### Anti-Patterns
- [ ] No Inter/Roboto/Arial as display fonts
- [ ] No purple gradients on white backgrounds
- [ ] No gray text on colored backgrounds without contrast check
- [ ] No cards nested inside cards
- [ ] No missing component states

## Output

Report findings as:

| Severity | File | Finding | Recommendation |
|----------|------|---------|----------------|
| Critical/Major/Minor/Nit | path:line | description | fix |

Then rate overall design consistency: Consistent / Minor Drift / Significant Drift.

## Visual Verification

If browser tools are available (`workbench.browser.enableChatTools` enabled) and a dev server is running:

1. Navigate to pages affected by the changes
2. Take screenshots to capture rendered output
3. Verify colors, typography, spacing, and component states match DESIGN.md visually
4. Test interactive states (hover, focus, error) by clicking and hovering elements
5. Include screenshot evidence in findings where visual issues are detected

If browser tools are not available, perform all checks via code inspection only.
