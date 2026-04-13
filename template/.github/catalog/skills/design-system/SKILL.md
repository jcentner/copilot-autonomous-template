---
name: design-system
description: "Design system conventions and references. Use when working with UI code, styling, component design, or visual consistency. References Impeccable patterns, DESIGN.md format, and design anti-patterns."
---

# Design System Skill

Conventions and references for maintaining visual design consistency. This skill is auto-loaded when working with UI code and ensures all agents reference the project's design system.

## Project Design System

The project's design system is defined in `DESIGN.md` at the project root. This is the single source of truth for visual decisions. All UI code must conform to it.

If `DESIGN.md` doesn't exist, invoke the **designer** agent to create it before writing UI code.

## DESIGN.md Format (Google Stitch)

The standard format for DESIGN.md files, as defined by [Google Stitch](https://stitch.withgoogle.com/docs/design-md/format/):

```markdown
# [Project Name] Design System

## Visual Theme & Atmosphere
[Mood, density, design philosophy — one paragraph]

## Color Palette
| Token | Hex | Role |
|-------|-----|------|
| primary | #XXXXXX | Main brand color, CTAs |
| primary-light | #XXXXXX | Hover states, backgrounds |
| accent | #XXXXXX | Highlights, active states |
| surface | #XXXXXX | Card/panel backgrounds |
| surface-alt | #XXXXXX | Alternate surface for contrast |
| text-primary | #XXXXXX | Main body text |
| text-secondary | #XXXXXX | Supporting text, captions |
| error | #XXXXXX | Error states, destructive actions |
| success | #XXXXXX | Success confirmations |
| warning | #XXXXXX | Warning states |

## Typography
| Level | Font | Size | Weight | Line Height |
|-------|------|------|--------|-------------|
| h1 | ... | ... | ... | ... |
| h2 | ... | ... | ... | ... |
| body | ... | ... | ... | ... |
| caption | ... | ... | ... | ... |
| code | ... | ... | ... | ... |

## Component Patterns
[Buttons, cards, inputs, navigation — with states]

## Layout & Spacing
[Grid, spacing scale, whitespace philosophy]

## Motion & Animation
[Easing, durations, reduced-motion]

## Do's and Don'ts
[Project-specific guardrails]
```

## Design Anti-Patterns

These are patterns to avoid in all UI work:

### Typography
- Do NOT use Inter, Roboto, Arial, or system-ui as the primary display font
- Do NOT skip heading levels (h1 → h3)
- Do NOT use more than 2-3 font families
- Do check that body text line-length stays under 75 characters

### Color
- Do NOT use purple gradients on white (AI-slop marker)
- Do NOT use gray text on colored backgrounds without checking contrast
- Do NOT use pure black (#000000) or pure gray — always tint neutrals
- Do use OKLCH or HSL for color manipulation, not hex math

### Layout
- Do NOT nest cards inside cards inside cards
- Do NOT use identical section layouts throughout — vary rhythm
- Do NOT ignore mobile layouts — design mobile-first
- Do use the spacing scale consistently (no arbitrary pixel values)

### Motion
- Do NOT use bounce/elastic easing (feels dated)
- Do NOT animate everything — pick high-impact moments
- Do support `prefers-reduced-motion`
- Do use cubic-bezier with intention

### Components
- Do NOT ship buttons without hover/focus/disabled states
- Do NOT ship inputs without error/focus states
- Do NOT forget loading states for async operations
- Do NOT forget empty states for lists/tables

## References

- [Impeccable](https://impeccable.style/) — 18 design commands, anti-pattern detection
- [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) — 66 real-world DESIGN.md examples
- [Google Stitch](https://stitch.withgoogle.com/docs/design-md/format/) — DESIGN.md format specification
- [Anthropic frontend-design skill](https://github.com/anthropics/skills/tree/main/skills/frontend-design) — creative direction guidelines
