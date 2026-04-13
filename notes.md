# Template Improvement Notes — April 2026

Research and analysis for making the autonomous template more reliable, consistent, parallel-capable, and proactive.

---

## 1. CI / Code Review Hooks — Preventing "Ship Broken Code" Drift

### Problem observed
Sentinel autonomous dev frequently forgot to check CI tests and pushed code that failed GitHub CI. The current template has a Stop hook (`slice-gate.py`) that blocks premature stopping, but **no enforcement for CI verification or code review completion before pushing**.

### Current state
- `slice-gate.py`: Checks `CURRENT-STATE.md` for phase status. Blocks stop unless phase is `Complete` or `Blocked`.
- Reviewer agent: Manual invocation as subagent. Builder *should* call it, but nothing enforces this.
- Test running: Builder instructions say "run tests — do not proceed if tests fail" but this is advisory only.
- No pre-push hook. No CI status check.

### What OMG does differently (relevant pieces)
- **Pre/post tool-use hooks** (`chat.useCustomAgentHooks: true`): Block modifications to `node_modules/`, prevent `.env` edits, stop deletion of critical config files, prevent `git push --force` and `git reset --hard`, path traversal sanitization.
- **Post-tool-use tracking**: Logs tool usage, tracks file modifications for phase awareness, monitors test results.
- **ultraqa skill**: QA cycling — test, verify, fix, repeat until green.

### Proposed changes

#### A. Add a `pre-push` hook script (`.github/hooks/scripts/ci-gate.py`)
Before allowing `git push`, verify:
1. Tests were run locally and passed (check for recent test output or a sentinel file).
2. Reviewer was invoked (check for a `.review-done` marker or git trailer in the last commit).
3. Optional: If GH Actions is configured, wait for CI status check on the branch.

**Implementation approach**: This would be a Stop hook enhancement or a separate hook. Since Copilot hooks currently support `Stop`, `onFileCreate`, `onFileEdit`, etc., the most practical approach is:
- Enhance `slice-gate.py` to also check for evidence of test runs and review completion
- Add `tests_passed` and `review_completed` markers to `CURRENT-STATE.md` per-slice
- Make the builder update these markers as it completes each step

#### B. Make the slice loop machine-checkable
Currently the slice protocol is prose instructions. Proposal:

Add a **slice checklist** section to `CURRENT-STATE.md`:
```markdown
### Current Slice Checklist
- [ ] Tests written/updated
- [ ] Tests pass locally
- [ ] Post-implementation checks run
- [ ] Reviewer invoked (findings: X critical, Y major)
- [ ] Critical/Major findings fixed
- [ ] CI pipeline status: pending/pass/fail
- [ ] Committed
```

The Stop hook (`slice-gate.py`) parses this checklist and blocks stop if any required items are unchecked.

#### C. Add tool guardrail hooks (stretch goal)
Pre-tool-use hooks from OMG for safety:
- Block `git push --force` / `git reset --hard`
- Block deletion of critical files (`package.json`, `.gitignore`, config files)
- Block writes to `node_modules/`, `.env`

**VS Code hook types available**: `Stop`, `onFileCreate`, `onFileEdit`, `onTerminalCommand` (if available). Need to check current Copilot hook support for pre-terminal-command hooks.

#### D. Priority
- **P0**: Enhance slice-gate.py to verify test + review evidence
- **P1**: Slice checklist in CURRENT-STATE.md
- **P2**: Tool guardrail hooks (depends on Copilot hook API expansion)

---

## 2. Evaluation: oh-my-githubcopilot (OMG)

**Repo**: https://github.com/jmstar85/oh-my-githubcopilot  
**Stats**: 28 agents, 22 skills, 15 MCP tools, 53 stars, built in 6 days

### Architecture comparison

| Feature | Our Template | OMG |
|---------|-------------|-----|
| Agents | 4 (builder, planner, reviewer, tester) | 28 (20 core + 8 language reviewers) |
| Skills | Template for stack skills | 22 workflow + analysis skills |
| Hooks | Stop hook only | Pre/post tool-use hooks + Stop-equivalent |
| State | File-based (CURRENT-STATE.md) | MCP server + file-based (.omc/) |
| Context management | Subagents + manual | Context pressure protocol + checkpointing |
| Workflow modes | Single build loop | autopilot, ralph loops, ultrawork parallel, team swarm |

### Ideas worth adopting

#### HIGH VALUE — Should adopt
1. **Context preservation protocol** — OMG tracks context pressure (accumulated tool I/O bytes) and advises checkpoint when threshold exceeded (default 400KB). This directly addresses "more reliable over long sessions."
   - **Our approach**: Add a context management section to the autonomous builder. Track approximate token usage. When context is filling up, checkpoint current state to files and consider starting a fresh conversation.
   - Can be advisory (instructions-based) without needing an MCP server.

2. **Interactive decision gates** (`vscode_askQuestions`) — OMG's skills fire structured multiple-choice prompts at key decision points (spec confirmation, plan approval, QA stuck recovery). This prevents the "you don't know what you don't know" problem by creating mandatory human checkpoints.
   - **Our approach**: Add decision gate prompts at key points:
     - After Phase 0 vision synthesis → "Does this vision look right?"
     - After phase planning → "Approve this plan?"
     - When blocked → structured options (skip, defer, escalate)
   - This is a Copilot-native feature (`vscode_askQuestions` tool) — no MCP needed.

3. **RALPLAN consensus planning** — Planner/Architect/Critic loop. 22% of design decisions were revised at planning stage before code was written. Directly addresses "implementing before having a solid idea."
   - **Our approach**: Enhance the planner subagent or add a `critic` role. Before implementation plans are finalized, run a Planner → Planner-as-Critic review pass that specifically challenges assumptions.

4. **deep-interview / Socratic requirements clarification** — Before building, surface hidden assumptions through structured questioning. Ambiguity gating prevents proceeding until clarity threshold is met.
   - **Our approach**: Add a `requirements` or `clarify` prompt/skill that the builder invokes when starting a new feature. Uses `vscode_askQuestions` to interview the user about edge cases, user expectations, error scenarios.

5. **Commit protocol with trailers** — `Constraint:`, `Rejected:`, `Confidence:`, `Scope-risk:`, `Not-tested:`. Preserves decision context in git history.
   - **Our approach**: Add this to the autonomous builder's commit format spec. Low effort, high value for cross-session continuity.

#### MEDIUM VALUE — Consider adopting
6. **Language-specific reviewer agents** — 8 language specialists with embedded style rules. Higher-quality reviews than a generic reviewer.
   - **Our approach**: Since this is a template, we can't predict the language. But we could add a `language-reviewer.agent.md.jinja` that adapts based on `{{ language }}` template variable, or have the `reviewer` agent consult language-specific stack skills.

7. **ultraqa skill** — QA cycling: test → verify → fix → repeat until green. Prevents the "tests fail but I'll fix it later" drift.
   - **Our approach**: Add a `verify` prompt or skill that runs tests in a loop until they pass, with a bounded retry limit.

8. **ai-slop-cleaner** — Detect and fix AI-generated code smells. Addresses a real problem with autonomous dev.
   - **Our approach**: Add anti-patterns to the reviewer agent's checklist. E.g., "Check for: excessive comments on obvious code, unnecessary abstractions, dead code, overly verbose error handling, commented-out code."

#### LOWER VALUE or DIFFERENT APPROACH
9. **MCP server for state** — Adds significant complexity. Our file-based approach is simpler and sufficient. MCP might be worth it for very complex multi-agent workflows, but not for a template.

10. **28 agents** — Too many for a general-purpose template. Cognitive overhead. Our approach of 4-6 focused agents + skills is better for a starting point. Users can add domain-specific agents as needed.

---

## 3. Sub-Agent Expansion — PM / Product Agent

### Problem observed
Sentinel implemented features before having a solid understanding of how users would actually use them. Gap between vision (strategic) and implementation (tactical) — no one advocating for the user experience at the feature level.

### Current agent roles
- **autonomous-builder**: Does everything — plans, implements, tests, reviews, checkpoints
- **planner**: Read-only research and analysis
- **reviewer**: Code review after implementation
- **tester**: Write tests from specs before implementation

### Gap analysis
There's no agent that:
- Writes user stories with acceptance criteria before implementation
- Maps user journeys for features
- Questions whether a feature makes sense from a user's perspective
- Validates that implementation matches user expectations
- Checks for UX consistency across features

### Proposed: `product-owner` agent

**Why "product-owner" not "PM"**: The agent acts as a proxy product owner — writes stories, defines acceptance criteria, validates features against user needs. It's not doing market research or roadmap prioritization (that's higher-level human work).

```yaml
---
description: "Product owner agent — writes user stories, defines acceptance criteria, validates features against user needs."
tools:
  - search
  - codebase
  - web
handoffs:
  - label: Plan Implementation
    agent: agent  
    prompt: "/implementation-plan"
    send: false
---
```

**Role in the build loop**:
1. Before the planner creates an implementation plan, the product-owner writes user stories for the features in the current phase
2. Each story includes: user type, action, benefit, acceptance criteria, edge cases
3. The autonomous builder references these stories when implementing
4. The reviewer checks implementation against acceptance criteria
5. Product-owner can be re-invoked when implementation reveals ambiguity

**Integration with existing workflow**:
- Phase planning prompt → product-owner writes stories → implementation plan references stories
- Builder checks stories before each slice
- Reviewer validates against acceptance criteria

### Alternative: Expand the planner
Instead of a new agent, enhance the planner to include a "product thinking" phase:
- Before outputting an implementation plan, the planner must first write user stories
- Add a "user perspective" section to every implementation plan

**Recommendation**: Start with expanding the planner (less complexity), add a dedicated product-owner agent if the expanded planner proves insufficient. The planner already has read-only tools and web access — it just needs stronger product-thinking instructions.

### Also from agency-agents worth considering:
- **Workflow Architect**: "Map every path through a system before code is written" — this is exactly the gap. Could be folded into the planner's responsibilities.
- **Codebase Onboarding Engineer**: Helps understand unfamiliar repos. Useful for Phase 0 when the builder encounters an existing codebase. Could be a skill rather than a separate agent.

---

## 4. Design Agent / Design Consistency

### Problem observed
UI/design inconsistency across features in Sentinel. No design system established, no one reviewing visual consistency, no shared design tokens.

### Resources evaluated

#### Anthropic's frontend-design skill
- Focuses on "bold aesthetic direction" — avoiding generic AI aesthetics
- Design Thinking phase: purpose, tone, constraints, differentiation
- Aesthetics guidelines: typography, color, motion, spatial composition, backgrounds
- Anti-patterns: overused fonts (Inter, Roboto), cliched purple gradients, predictable layouts
- **Limitation**: One-shot creativity guidance, not design system enforcement

#### Impeccable (pbakaus)
- Builds on Anthropic's skill with deeper expertise
- 7 domain-specific references: typography, color-and-contrast, spatial-design, motion-design, interaction-design, responsive-design, ux-writing
- 18 steering commands: /audit, /critique, /polish, /normalize, /distill, /animate, etc.
- Curated anti-patterns
- CLI for detecting anti-patterns without AI
- **Key insight**: The `/teach` command gathers design context once and saves to config. This is the "establish a design theme early" pattern.
- **Key insight**: `/normalize` aligns code with design system. This is the "stick to it/review against it" pattern.

#### awesome-design-md (VoltAgent / Google Stitch)
- DESIGN.md: Plain-text design system document that AI agents read to generate consistent UI
- Follows Google Stitch format: Visual Theme, Color Palette, Typography, Components, Layout, Depth, Do's and Don'ts, Responsive, Agent Prompt Guide
- 66 pre-made DESIGN.md files from real brands
- **Key insight**: `DESIGN.md` is to design what `AGENTS.md` is to development. A single file that grounds all agents in the visual identity.

### Proposed approach: DESIGN.md + designer agent

#### Step 1: Add DESIGN.md to the template scaffold
Add `template/DESIGN.md.jinja` — a skeleton DESIGN.md that the designer agent populates in Phase 0 or Phase 1.

```
# {{ project_name }} Design System

## Visual Theme & Atmosphere
<!-- Describe mood, density, design philosophy -->

## Color Palette
<!-- Primary, secondary, accent, neutral, semantic colors with hex values -->

## Typography
<!-- Font families, hierarchy, sizes, weights -->

## Component Patterns
<!-- Buttons, cards, inputs, navigation — with states -->

## Layout & Spacing
<!-- Grid system, spacing scale, whitespace philosophy -->

## Motion & Animation
<!-- Easing curves, transition patterns, reduced-motion support -->

## Do's and Don'ts
<!-- Design guardrails specific to this project -->
```

#### Step 2: Create `designer` agent

```yaml
---
description: "Design system agent — establishes visual identity, reviews UI consistency, maintains DESIGN.md."
tools:
  - search
  - codebase
  - web
handoffs:
  - label: Fix Design Issues
    agent: agent
    prompt: "Fix the design inconsistencies identified in the review above."
    send: false
---
```

**Responsibilities**:
1. **Phase 0/1**: Establish the project's design system in `DESIGN.md`, informed by the vision and any existing visual assets
2. **During implementation**: Review UI changes against `DESIGN.md`
3. **When invoked directly**: Run audit/normalize/polish workflows (Impeccable-style commands)
4. **Maintain**: Keep `DESIGN.md` updated as the design evolves

**Grounding**: The designer agent's instructions should reference:
- The project's `DESIGN.md` as the primary authority
- Impeccable-style anti-patterns (avoid generic AI aesthetics)
- Anthropic's frontend-design principles for creative direction

#### Step 3: Integrate into the build loop
- **Phase 0**: Builder invokes designer to create initial `DESIGN.md`
- **Slice loop**: When a slice touches UI code, builder invokes designer for review (in addition to code reviewer)
- **Code review prompt**: Add "design consistency" as a review dimension when UI files are changed

#### Step 4: Add design skill template
Add `.github/skills/design-system/SKILL.md` template that references `DESIGN.md` and Impeccable patterns. This makes design guidance auto-discoverable by all agents.

#### Alternative: Fold into reviewer
Instead of a separate designer agent, add design review capabilities to the existing reviewer:
- When reviewing files matching `*.css`, `*.scss`, `*.tsx`, `*.vue`, `*.html`, etc., also check against `DESIGN.md`
- Add design anti-patterns to the reviewer's checklist

**Recommendation**: Start with a separate `designer` agent. Design review is a different skill than code review — combining them dilutes both. The designer can be invoked selectively (only for UI-touching slices).

---

## 5. Evaluation: agency-agents (The Agency)

**Repo**: https://github.com/msitarzewski/agency-agents  
**Stats**: 144 agents across 12 divisions, 79.4k stars, 68 contributors

### What it is
A collection of personality-driven AI agent definitions organized by division (Engineering, Design, Product, Sales, Marketing, etc.). Each agent has strong personality, clear deliverables, success metrics, and proven workflows.

### Key differences from our approach
- **Breadth vs. depth**: Agency has 144 agents for every business function. We have 4 tightly integrated agents for software development.
- **Individual agents vs. workflow**: Agency agents are standalone personas. Our agents are parts of an orchestrated build loop.
- **No automation**: Agency doesn't have hooks, guardrails, or checkpoint protocols. It's a prompt library.
- **Multi-tool support**: Agency supports Claude Code, Copilot, Cursor, Aider, etc. via conversion scripts.

### Ideas worth adopting

#### From the Design Division
- **UI Designer**: Visual design, component libraries, design systems → feeds into our designer agent
- **UX Researcher**: User testing, behavior analysis → could inform our product-owner's user story quality
- **Brand Guardian**: Brand identity, consistency, positioning → the DESIGN.md approach addresses this
- **UX Architect**: Technical architecture, CSS systems, implementation → relevant for the designer agent

#### From the Product Division
- **Product Manager**: Full lifecycle product ownership. Discovery, PRDs, roadmap planning, GTM, outcome measurement → validates our product-owner proposal
- **Sprint Prioritizer**: Agile planning, feature prioritization → could fold into planner
- **Feedback Synthesizer**: User feedback analysis → useful for vision expansion mode

#### From the Engineering Division
- **Security Engineer**: Dedicated security agent vs. bundled into reviewer → could add as a subagent for security-critical slices
- **Codebase Onboarding Engineer**: "Helping new developers understand unfamiliar repos quickly by reading the code, tracing code paths, and stating facts about structure and behavior" → great for Phase 0. Could be a skill or mode of the planner.
- **Git Workflow Master**: "Branching strategies, conventional commits, advanced Git" → some of this should go into our copilot-instructions

#### From the Testing Division  
- **Accessibility Auditor**: WCAG auditing → relevant for design review
- **Reality Checker**: "Evidence-based certification, quality gates" → resonate with our reviewer but more focused on "is this actually done?"

### What NOT to adopt
- The sheer number of agents. 144 is overwhelming. Template should be opinionated and minimal.
- Business-function agents (Sales, Marketing, Finance). Out of scope for a dev workflow template.
- Personality-heavy framing. Our agents are functional, not persona-driven. This is a deliberate design choice — personality adds tokens to context without adding capability.

---

## 6. Synthesis: Priority Roadmap

### Tier 1 — High Impact, Addresses Observed Failures

| Change | Addresses | Effort |
|--------|-----------|--------|
| Enhance slice-gate.py with test/review verification | CI failures, skipped reviews | Small |
| Add slice checklist to CURRENT-STATE.md template | CI failures, process discipline | Small |
| Add commit trailers to builder instructions | Cross-session continuity | Small |
| Expand planner with product-thinking / user stories | "Don't know what you don't know" | Medium |
| Add decision gates (`vscode_askQuestions`) at key points | Human-in-the-loop for key decisions | Medium |
| Add context management instructions (checkpoint when saturated) | Long session reliability | Small |

### Tier 2 — New Capabilities

| Change | Addresses | Effort |
|--------|-----------|--------|
| Add `designer` agent + DESIGN.md scaffold | UI/design consistency | Medium |
| Add `/deep-interview` or `/clarify` prompt for requirements | Feature quality, "don't know what you don't know" | Medium |
| Add anti-AI-slop checklist to reviewer | Code quality | Small |
| Add tool guardrail instructions (block force push, etc.) | Safety | Small |
| Add RALPLAN-style critic pass in planning | Plan quality | Medium |

### Tier 3 — Stretch / Evaluate Later

| Change | Addresses | Effort |
|--------|-----------|--------|
| Product-owner as dedicated agent (if planner expansion insufficient) | Feature quality | Medium |
| Language-specific reviewer adaptation | Review quality | Medium |
| MCP server for state management | Complex workflows | Large |
| Context pressure monitoring (OMG-style) | Long sessions | Large |
| Parallel execution / ultrawork mode | Speed | Large |

---

## 7. Open Questions

1. **Hook API coverage**: What hooks does Copilot currently support beyond `Stop`? Can we do pre-terminal-command hooks? Need to check the copilot-customization-docs skill for current state.

2. **CI integration**: How to detect CI status from within Copilot? Options:
   - `gh run list` via terminal to check GitHub Actions status
   - Parse local test output
   - Require local test pass as proxy for CI

3. **DESIGN.md placement**: Root of project or under `docs/`? Google Stitch convention is project root. Makes sense — it's like AGENTS.md.

4. **Agent count sweet spot**: Currently 4 agents. Adding designer + product-owner = 6. Is that the right ceiling before complexity hurts more than helps? OMG's 28 seems excessive; agency-agents' 144 is absurd for a dev workflow. 5-7 seems right.

5. **Impeccable integration**: Should we bundle Impeccable's skill content into our designer agent, or reference it as an external skill/dependency? Probably reference — it's actively maintained and would go stale if copied.

6. **Parallel execution**: OMG has `ultrawork` for parallel execution. VS Code Copilot doesn't natively support parallel agent runs. This might need architectural changes (multiple worktrees? multiple chat sessions?). Likely blocked on tooling.

---

## 8. Implementation Order (Proposed)

**Phase A — Hardening (address observed failures)**
1. Enhance slice-gate.py with test/review evidence checking
2. Add slice checklist to CURRENT-STATE.md template
3. Add commit trailer format to builder instructions
4. Add context management / session health instructions to builder
5. Add tool safety instructions (block force push, protect critical files)

**Phase B — Product thinking (address "don't know what you don't know")**
1. Expand planner with product-thinking section and user story requirements
2. Add `/clarify` prompt for requirements interview (uses vscode_askQuestions)
3. Add decision gates at phase planning and vision expansion points
4. Add critic pass to planning workflow (RALPLAN-lite)

**Phase C — Design consistency**
1. Create DESIGN.md.jinja template
2. Create designer agent  
3. Integrate designer into build loop (optional invocation for UI slices)
4. Add design anti-patterns to reviewer checklist

**Phase D — Polish**
1. Add anti-AI-slop checklist to reviewer
2. Enhance commit protocol with trailers
3. Add onboarding/orientation mode for existing codebases
4. Document the full agent architecture in template README

---

## 9. Self-Expanding Workflow — Catalog Architecture

### The Core Idea

The workflow shouldn't just be able to tweak its own instructions (Section 5 of the builder). It should be able to **discover and activate entirely new capabilities** — agents, skills, hooks, patterns, prompts — from a built-in catalog and external sources. Think of it as `apt install` for workflow capabilities.

### Why This Matters

The current template ships a minimal set (4 agents, a few prompts). Users encounter needs the template didn't anticipate:
- "I'm building a frontend but there's no design guidance" → needs designer agent + DESIGN.md
- "CI keeps failing but the builder ignores it" → needs CI gate hooks
- "Features don't make sense from a user perspective" → needs product-owner agent
- "Security review is shallow" → needs dedicated security reviewer
- "The builder writes AI-slop code" → needs anti-slop skill

Instead of bloating the default template with everything, ship a **lean core + rich catalog**.

### Architecture

```
template/.github/
├── agents/                     # ACTIVE agents (the lean core)
│   ├── autonomous-builder.agent.md.jinja
│   ├── planner.agent.md.jinja
│   ├── reviewer.agent.md.jinja
│   └── tester.agent.md.jinja
├── catalog/                    # DORMANT capabilities (the storehouse)
│   ├── README.md               # How the catalog works
│   ├── MANIFEST.md             # Machine-readable index of all catalog items
│   ├── agents/                 # Pre-crafted agent templates
│   │   ├── designer.agent.md
│   │   ├── product-owner.agent.md
│   │   ├── security-reviewer.agent.md
│   │   └── critic.agent.md
│   ├── skills/                 # Pre-crafted skills
│   │   ├── deep-interview/
│   │   │   └── SKILL.md
│   │   ├── anti-slop/
│   │   │   └── SKILL.md
│   │   ├── design-system/
│   │   │   └── SKILL.md
│   │   └── ci-verification/
│   │       └── SKILL.md
│   ├── hooks/                  # Pre-crafted hook scripts
│   │   ├── ci-gate.py
│   │   ├── tool-guardrails.json
│   │   └── context-checkpoint.py
│   ├── prompts/                # Pre-crafted prompts
│   │   ├── clarify.prompt.md
│   │   └── design-review.prompt.md
│   └── patterns/               # Reusable implementation patterns
│       ├── DESIGN.md.template  # Skeleton DESIGN.md for projects
│       └── commit-trailers.md  # Commit convention with trailers
├── prompts/
├── skills/
├── hooks/
└── instructions/
```

### The MANIFEST.md — Machine-Readable Catalog Index

The key enabler. The builder reads this to understand what's available without loading every item.

```markdown
# Workflow Catalog

## Agents

### designer
- **File**: `catalog/agents/designer.agent.md`
- **Activates to**: `.github/agents/designer.agent.md`
- **Trigger**: Project has frontend/UI code, or vision mentions design/UX
- **Requires**: DESIGN.md pattern (auto-installed if missing)
- **Adds to builder**: `agents: [designer]` in frontmatter
- **Description**: Establishes and enforces visual design system via DESIGN.md

### product-owner
- **File**: `catalog/agents/product-owner.agent.md`
- **Activates to**: `.github/agents/product-owner.agent.md`
- **Trigger**: Phase planning, or builder encounters ambiguous requirements
- **Requires**: None
- **Adds to builder**: `agents: [product-owner]` in frontmatter
- **Description**: Writes user stories, acceptance criteria, validates user perspective

### security-reviewer
- **File**: `catalog/agents/security-reviewer.agent.md`
- **Activates to**: `.github/agents/security-reviewer.agent.md`
- **Trigger**: Project handles auth, payment, PII, or external APIs
- **Requires**: None
- **Adds to builder**: `agents: [security-reviewer]` in frontmatter
- **Description**: Dedicated OWASP, secrets, auth/z review beyond generic code review

### critic
- **File**: `catalog/agents/critic.agent.md`
- **Activates to**: `.github/agents/critic.agent.md`
- **Trigger**: Phase planning for phases with 5+ slices
- **Requires**: None  
- **Adds to builder**: `agents: [critic]` in frontmatter
- **Description**: Challenges implementation plans before coding starts (RALPLAN-style)

## Skills

### deep-interview
- **File**: `catalog/skills/deep-interview/SKILL.md`
- **Activates to**: `.github/skills/deep-interview/SKILL.md`
- **Trigger**: New project (Phase 0), vague requirements, or user asks for clarification
- **Description**: Socratic requirements elicitation with ambiguity gating

### anti-slop  
- **File**: `catalog/skills/anti-slop/SKILL.md`
- **Activates to**: `.github/skills/anti-slop/SKILL.md`
- **Trigger**: Reviewer finds AI-generated code smells, or after 10+ slices
- **Description**: Detect and clean AI-generated code: excessive comments, dead code, verbose abstractions

### design-system
- **File**: `catalog/skills/design-system/SKILL.md`
- **Activates to**: `.github/skills/design-system/SKILL.md`
- **Trigger**: Activated alongside designer agent
- **Description**: References Impeccable patterns, DESIGN.md format, design anti-patterns

### ci-verification
- **File**: `catalog/skills/ci-verification/SKILL.md`
- **Activates to**: `.github/skills/ci-verification/SKILL.md`
- **Trigger**: Project has CI pipeline (GitHub Actions, etc.)
- **Description**: How to check CI status, wait for results, gate on pass/fail

## Hooks

### ci-gate
- **File**: `catalog/hooks/ci-gate.py`
- **Activates to**: `.github/hooks/scripts/ci-gate.py` + agent frontmatter update
- **Trigger**: Project has GitHub Actions workflows
- **Description**: Blocks stop unless CI is green or check is explicitly waived

### tool-guardrails
- **File**: `catalog/hooks/tool-guardrails.json`
- **Activates to**: `.github/hooks/tool-guardrails.json`
- **Trigger**: Always recommended, activated during Phase 0
- **Description**: PreToolUse guards: block force-push, protect critical files, sanitize paths

### context-checkpoint
- **File**: `catalog/hooks/context-checkpoint.py`
- **Activates to**: `.github/hooks/scripts/context-checkpoint.py` + agent frontmatter update
- **Trigger**: Long-running sessions (10+ slices)
- **Description**: PostToolUse hook that tracks context pressure, advises checkpoint

## Prompts

### clarify
- **File**: `catalog/prompts/clarify.prompt.md`
- **Activates to**: `.github/prompts/clarify.prompt.md`
- **Trigger**: Ambiguous requirements, new features
- **Description**: Structured requirements interview using vscode_askQuestions

### design-review
- **File**: `catalog/prompts/design-review.prompt.md`
- **Activates to**: `.github/prompts/design-review.prompt.md`
- **Trigger**: Activated alongside designer agent
- **Description**: Review UI changes against DESIGN.md

## Patterns

### DESIGN.md
- **File**: `catalog/patterns/DESIGN.md.template`
- **Activates to**: `DESIGN.md` (project root)
- **Trigger**: Designer agent activation, or project has UI
- **Description**: Google Stitch format design system document

### commit-trailers
- **File**: `catalog/patterns/commit-trailers.md`
- **Activates to**: Referenced in copilot-instructions.md (append section)
- **Trigger**: Phase 0 or first session
- **Description**: Structured git trailers for decision context preservation
```

### Expansion Protocol — How the Builder Activates Catalog Items

This gets added to the autonomous builder's instructions as a new section:

```markdown
### Expand the workflow

During Phase 0 (and at any point when a capability gap is recognized),
you may activate items from `.github/catalog/`.

**Activation protocol:**

1. Read `.github/catalog/MANIFEST.md` to see available capabilities
2. Evaluate which items match the project's needs based on:
   - Technology stack (frontend → designer, design-system)
   - Project characteristics (auth/payments → security-reviewer)
   - Observed gaps (ambiguous specs → product-owner, deep-interview)
   - Scale (10+ slice phases → critic, context-checkpoint)
3. For each item to activate:
   a. Copy the file from `catalog/` to its activation path
   b. If the item adds a subagent, update your own frontmatter `agents:` list
   c. If the item adds a hook, update the relevant hook config
   d. Log the activation in `docs/reference/agent-improvement-log.md`
4. Commit the activation: `chore(workflow): activate {item} from catalog`

**Activation triggers by phase:**

| Phase | Auto-evaluate | Reason |
|-------|--------------|--------|
| Phase 0 | tool-guardrails, commit-trailers, ci-verification (if CI exists) | Safety baseline |
| Phase 0 | designer + DESIGN.md (if frontend) | Design before code |
| Phase 0 | deep-interview (if requirements are vague) | Clarify before building |
| Phase planning | product-owner (if user stories missing) | Build the right thing |
| Phase planning | critic (if 5+ slices) | Challenge the plan |
| Any | security-reviewer (if auth/PII/payments appear) | Security depth |
| 10+ slices | context-checkpoint | Session longevity |
| After reviewer feedback | anti-slop (if AI patterns detected) | Code quality |

**Activation requires no human approval** — these are pre-vetted items
from the catalog, not arbitrary changes. Log everything.

**External expansion** (requires human approval):
- If the catalog doesn't have what you need, you may propose fetching
  from external sources:
  - [Impeccable](https://github.com/pbakaus/impeccable) — design skills
  - [agency-agents](https://github.com/msitarzewski/agency-agents) — agent patterns
  - [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) — design templates  
  - [anthropic/skills](https://github.com/anthropics/skills) — community skills
- Propose in `roadmap/CURRENT-STATE.md` under `## Proposed Workflow Expansion`
- Set **Phase Status** to `Blocked: Workflow Expansion — awaiting approval`
- After approval, fetch, adapt to project conventions, and commit
```

### The Catalog MANIFEST.md as a Skill

Critical insight: The MANIFEST.md should also be discoverable as a **skill**, so that any agent (not just the builder) can discover catalog items when they hit a capability gap:

```yaml
---
name: workflow-catalog
description: "Catalog of dormant workflow capabilities that can be activated on demand. Consult when hitting a capability gap: missing design guidance, shallow security review, vague requirements, CI failures. Lists available agents, skills, hooks, prompts, and patterns with activation triggers."
---
```

This means any agent — planner hitting ambiguity, reviewer noticing security gaps — can say "there's a catalog item for this" and recommend activation.

### What Goes in Each Catalog Item

#### Catalog agents are **complete, ready-to-copy** agent definitions
Not templates with Jinja variables (since the project name etc. are already known by the time it's a generated project). They reference the project's existing docs structure.

Example: `catalog/agents/designer.agent.md`:
```yaml
---
description: "Design system agent — establishes visual identity, reviews UI consistency, maintains DESIGN.md."
tools:
  - search
  - codebase
  - web
handoffs:
  - label: Fix Design Issues
    agent: agent
    prompt: "Fix the design inconsistencies identified in the review above."
    send: false
---

# Designer

You are the design system agent. Your role is to establish, maintain,
and enforce visual design consistency across the project.

## Authority
- **DESIGN.md** (project root) is the design system source of truth
- When DESIGN.md doesn't exist, your first job is to create it

## Context
- [DESIGN.md](../../DESIGN.md)
- [Vision lock](../../docs/vision/VISION-LOCK.md)
- [Architecture overview](../../docs/architecture/overview.md)

## Responsibilities

### Establish (Phase 0 / Phase 1)
1. Read the vision lock for product personality, audience, brand intent
2. Survey existing UI code for patterns already in use
3. Create `DESIGN.md` in project root using Google Stitch format:
   - Visual Theme & Atmosphere
   - Color Palette (semantic names + hex + roles)
   - Typography (families, hierarchy, sizes, weights)
   - Component Patterns (buttons, cards, inputs, nav — with states)
   - Layout & Spacing (grid, spacing scale, whitespace)
   - Motion & Animation (easing, transitions, reduced-motion)
   - Do's and Don'ts (project-specific guardrails)
4. Commit: `chore(design): establish DESIGN.md`

### Review
When invoked as subagent on UI-touching slices:
1. Read DESIGN.md
2. Review changed files against the design system
3. Flag inconsistencies with severity ratings (Critical/Major/Minor)
4. Check for anti-patterns: overused fonts, AI-slop aesthetics,
   inconsistent spacing, color mismatches, missing states

### Maintain
When design evolves:
1. Update DESIGN.md with new patterns discovered during implementation
2. Keep the Do's and Don'ts section current
3. Version the design system (changelog section in DESIGN.md)

## Anti-Patterns (never do these)
- Overused fonts: Inter, Roboto, Arial, system defaults
- Purple-gradient-on-white (the universal AI-slop marker)
- Gray text on colored backgrounds
- Cards nested inside cards
- Bounce/elastic easing
- Cookie-cutter component patterns with no project personality

## References
- [Impeccable](https://impeccable.style/) — design vocabulary and anti-patterns
- [Google Stitch DESIGN.md format](https://stitch.withgoogle.com/docs/design-md/format/)
- [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) — real-world examples
```

### External Source Protocol

For capabilities beyond the built-in catalog, the builder follows a fetch-adapt-install pattern:

1. **Identify the gap** — what capability is missing?
2. **Search known sources** — check MANIFEST.md's external sources section
3. **Propose to human** — "I need X. Source Y has it. Shall I fetch and adapt it?"
4. **On approval**: Fetch via web/git, adapt to project conventions, install to `.github/`, log in improvement log
5. **On denial**: Record the gap in open-questions, move on

Known sources (maintained in MANIFEST.md):
| Source | What's there | URL |
|--------|-------------|-----|
| Impeccable | Design skills, anti-patterns, audit commands | https://github.com/pbakaus/impeccable |
| agency-agents | 144 agent personality templates across 12 divisions | https://github.com/msitarzewski/agency-agents |
| awesome-design-md | 66 DESIGN.md files from real brands | https://github.com/VoltAgent/awesome-design-md |
| anthropic/skills | Official community skills (frontend-design, etc.) | https://github.com/anthropics/skills |
| oh-my-githubcopilot | Workflow patterns: ultraqa, deep-interview, ralph loops | https://github.com/jmstar85/oh-my-githubcopilot |

### Self-Improvement vs. Self-Expansion — Clarifying the Boundary

Current "Section 5: Improve the development system":
- **Scope**: Tweak existing instructions/prompts/agents
- **Trigger**: Observed failure or repeated inefficiency
- **Authority**: Autonomous (no human approval)
- **Logged**: Agent improvement log

New "Expand the workflow":
- **Scope**: Activate dormant catalog items OR fetch from external sources
- **Trigger**: Capability gap recognized (by any agent or during planning)
- **Authority**: Catalog items = autonomous. External sources = human approval.
- **Logged**: Agent improvement log (with `[EXPANSION]` tag)

Both are evolution mechanisms, but with different trust levels:
- Catalog items are **pre-vetted** (shipped with the template) → autonomous
- External sources are **unvetted** → needs human approval
- Weakening standards is still forbidden in both cases

### Feedback Loop: Catalog Items Propose Themselves

The most powerful part: catalog items can include **trigger conditions** that the builder checks programmatically. During Phase 0 and at the start of each phase:

```
1. Read MANIFEST.md
2. For each unactivated item, evaluate its trigger condition:
   - "Project has frontend/UI code" → ls for *.tsx, *.vue, *.html, *.css
   - "Project has CI pipeline" → ls for .github/workflows/
   - "Phase has 5+ slices" → count slices in current phase plan
   - "Project handles auth/PII" → grep for auth, login, password, token, PII
3. If trigger matches and item is not yet activated → activate it
```

This makes the workflow **proactive** — it doesn't wait for failure before expanding. It scans for conditions that predict the need.

### Implementation Plan for the Catalog

**Phase E — Self-Expansion (new phase, after Phase D)**

1. Create `template/.github/catalog/` directory structure
2. Write `MANIFEST.md` with all catalog items and triggers
3. Create the `workflow-catalog` skill wrapper
4. Write each catalog agent:
   - designer.agent.md
   - product-owner.agent.md  
   - security-reviewer.agent.md
   - critic.agent.md
5. Write each catalog skill:
   - deep-interview/SKILL.md
   - anti-slop/SKILL.md
   - design-system/SKILL.md
   - ci-verification/SKILL.md
6. Write each catalog hook:
   - ci-gate.py
   - tool-guardrails.json
   - context-checkpoint.py
7. Write each catalog prompt:
   - clarify.prompt.md
   - design-review.prompt.md
8. Write each catalog pattern:
   - DESIGN.md.template
   - commit-trailers.md
9. Add "Expand the workflow" section to autonomous-builder.agent.md.jinja
10. Add trigger evaluation to Phase 0 and phase-start protocol
11. Update the template README and PROMPT-GUIDE with catalog documentation

### Open questions for self-expansion
1. **Catalog items are NOT .jinja files** — they're in the generated project, not the template source. But the template itself uses Jinja. So catalog items in the template source should NOT have `.jinja` extension. They should be copied verbatim. Need to verify they don't accidentally contain Jinja-like syntax (`{{ }}`) that Copier would try to render.

2. **Builder frontmatter is static** — The builder's `agents:` list in frontmatter can't be dynamically modified at runtime in VS Code. Workaround: ship the builder with all potential subagents listed, but mark the catalog agents as `user-invocable: false` until activated. OR: have the builder invoke catalog agents via natural language without the frontmatter restriction (test if this works).

3. **Catalog staleness** — As the ecosystem evolves, catalog items may become outdated. Include a `last-verified` date in MANIFEST.md. The builder should note when items haven't been verified in 90+ days.

4. **Catalog vs. just shipping more agents by default** — Why not just include all agents as active? Because:
   - Context window cost: every active agent's description is loaded by Copilot for routing
   - Cognitive overhead: users see 10 agents in the picker instead of 4
   - Irrelevance: a CLI tool project doesn't need a designer agent
   - The catalog teaches the builder *when* to use each capability, not just *what* it is

5. **Can the builder actually modify its own frontmatter?** — Yes, it can edit `.github/agents/autonomous-builder.agent.md`. But VS Code may not hot-reload the change mid-session. The activation likely takes effect next session. This is acceptable — catalog activations are forward-looking improvements.