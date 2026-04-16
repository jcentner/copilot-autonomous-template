---
name: workflow-catalog
description: "Catalog of dormant workflow capabilities that can be activated on demand. Consult when hitting a capability gap: missing design guidance, shallow security review, vague requirements, CI failures, AI-slop code patterns, context window pressure. Lists available agents, skills, hooks, prompts, and patterns with activation triggers and instructions."
---

# Workflow Catalog Manifest

Available capabilities that can be activated by the autonomous builder or manually. Each item includes trigger conditions, dependencies, and activation instructions.

## Agents

> **Note:** `critic` and `product-owner` were promoted to **core agents** (shipped by default in `.github/agents/`). They are no longer catalog items — activation is automatic.

### designer

| Field | Value |
|-------|-------|
| Source | `catalog/agents/designer.agent.md` |
| Activates to | `.github/agents/designer.agent.md` |
| Trigger | Project has frontend/UI code (`*.tsx`, `*.vue`, `*.html`, `*.css`, `*.svelte`) or vision mentions design/UX/UI |
| Requires | `DESIGN.md` pattern (auto-install if missing) |
| Description | Establishes and enforces visual design system via DESIGN.md. Reviews UI changes for consistency. Uses `browser` tools for visual verification when available (requires `workbench.browser.enableChatTools`). |

### security-reviewer

| Field | Value |
|-------|-------|
| Source | `catalog/agents/security-reviewer.agent.md` |
| Activates to | `.github/agents/security-reviewer.agent.md` |
| Trigger | Project handles authentication, payments, PII, or external APIs. Grep for: `auth`, `login`, `password`, `token`, `secret`, `payment`, `stripe`, `oauth` |
| Requires | None |
| Description | Dedicated OWASP Top 10 review, secrets detection, auth/authz audit. Deeper than the generic reviewer's security checks. |

## Skills

### deep-interview

| Field | Value |
|-------|-------|
| Source | `catalog/skills/deep-interview/SKILL.md` |
| Activates to | `.github/skills/deep-interview/SKILL.md` |
| Trigger | New project (bootstrap), vague requirements, or user explicitly asks for requirements clarification |
| Description | Socratic requirements elicitation. Surfaces hidden assumptions through structured questioning with ambiguity gating. Uses `vscode_askQuestions` for interactive interview. |

### anti-slop

| Field | Value |
|-------|-------|
| Source | `catalog/skills/anti-slop/SKILL.md` |
| Activates to | `.github/skills/anti-slop/SKILL.md` |
| Trigger | Reviewer finds AI-generated code smells, or activated proactively after 10+ autonomous slices |
| Description | Detect and fix AI-generated code patterns: excessive comments, dead code, unnecessary abstractions, cargo-cult error handling, verbose variable names, commented-out code. |

### design-system

| Field | Value |
|-------|-------|
| Source | `catalog/skills/design-system/SKILL.md` |
| Activates to | `.github/skills/design-system/SKILL.md` |
| Trigger | Activated alongside designer agent |
| Description | Design system conventions: references Impeccable patterns, DESIGN.md format (Google Stitch), design anti-patterns, accessibility baselines. |

### ci-verification

| Field | Value |
|-------|-------|
| Source | `catalog/skills/ci-verification/SKILL.md` |
| Activates to | `.github/skills/ci-verification/SKILL.md` |
| Trigger | Project has CI pipeline (`.github/workflows/` directory exists) |
| Description | How to check CI status via `gh` CLI, interpret results, gate on pass/fail, handle flaky tests. |

## Hooks

> Note: `tool-guardrails` and `context-checkpoint` were promoted to core hooks
> (see `.github/hooks/scripts/tool-guardrails.py` and `context-pressure.py`).
> They are always active — no activation needed.

### ci-gate

| Field | Value |
|-------|-------|
| Source | `catalog/hooks/ci-gate.py` |
| Activates to | `.github/hooks/scripts/ci-gate.py` + reference in builder agent hooks |
| Trigger | Project has GitHub Actions workflows |
| Description | Stop hook enhancement: blocks session stop unless local tests have been verified as passing in the current slice. |

## Prompts

### clarify

| Field | Value |
|-------|-------|
| Source | `catalog/prompts/clarify.prompt.md` |
| Activates to | `.github/prompts/clarify.prompt.md` |
| Trigger | Ambiguous requirements, new features with unclear user expectations |
| Description | Structured requirements interview. Asks targeted questions about user goals, edge cases, error scenarios, and success criteria using interactive prompts. |

### design-review

| Field | Value |
|-------|-------|
| Source | `catalog/prompts/design-review.prompt.md` |
| Activates to | `.github/prompts/design-review.prompt.md` |
| Trigger | Activated alongside designer agent |
| Description | Review UI changes against the project's DESIGN.md for visual consistency, typography, color, spacing, and anti-patterns. Includes `browser` tools for visual verification when available. |

## Patterns

### DESIGN.md

| Field | Value |
|-------|-------|
| Source | `catalog/patterns/DESIGN.md.template` |
| Activates to | `DESIGN.md` (project root) |
| Trigger | Designer agent activation, or project has UI components |
| Description | Google Stitch format design system document. Skeleton that the designer agent populates with project-specific design tokens and guidelines. |

### commit-trailers

| Field | Value |
|-------|-------|
| Source | `catalog/patterns/commit-trailers.md` |
| Activates to | Referenced in `copilot-instructions.md` (builder appends the convention) |
| Trigger | Bootstrap or first session — always recommended |
| Description | Structured git commit trailers for decision context preservation: `Constraint:`, `Rejected:`, `Confidence:`, `Scope-risk:`, `Not-tested:`. |

## External Sources

When the catalog doesn't have what you need, these vetted external sources can be proposed for human-approved expansion:

| Source | What's Available | URL |
|--------|-----------------|-----|
| Impeccable | Design skills, anti-patterns, 18 audit/review commands | https://github.com/pbakaus/impeccable |
| agency-agents | 144 agent personality templates across 12 divisions | https://github.com/msitarzewski/agency-agents |
| awesome-design-md | 66 DESIGN.md files extracted from real brand websites | https://github.com/VoltAgent/awesome-design-md |
| anthropic/skills | Official community skills (frontend-design, doc-coauthoring) | https://github.com/anthropics/skills |
| oh-my-githubcopilot | Workflow patterns: ultraqa, deep-interview, ralph loops, MCP tools | https://github.com/jmstar85/oh-my-githubcopilot |

## Activation model

Catalog items are **activated manually by the human at bootstrap** (or at phase start). `BOOTSTRAP.md` prompts the human with a `vscode_askQuestions` picker listing every catalog item by type. The builder does not apply trigger heuristics autonomously — triggers in the tables above are advisory hints for the human picker.

Activation = copying the file from `.github/catalog/<type>/` to `.github/<type>/`. Deactivation is a plain delete.

## Changelog

- **2026-04 (v2 restructure)** — `critic` and `product-owner` promoted to core agents. `tool-guardrails` and `context-pressure` (née `context-checkpoint`) promoted to core hooks. Remaining catalog items: 2 agents, 4 skills, 1 hook, 2 prompts, 2 patterns.
