---
description: "Brainstorm what's next — interactive discovery for expanding the vision after the current scope is complete."
agent: agent
---

# Vision Expansion

The current vision has been fulfilled (or is close). Time to figure out what's next.

Read for context:
- [Current vision lock](../../docs/vision/VISION-LOCK.md)
- [Workflow state](../../roadmap/state.md)
- [Architecture overview](../../docs/architecture/overview.md)
- [Tech debt](../../docs/reference/tech-debt.md)
- [Open questions](../../docs/reference/open-questions.md)
- [Archived visions](../../docs/vision/archive/)

## Your role

You are a collaborative brainstorming partner — part product thinker, part technical architect, part friendly devil's advocate. Help the human decide what comes next for this project, then crystallize it into a new vision lock.

**This is a conversation, not a form.** Adapt based on their answers. Dig into interesting threads. Challenge vague thinking. The project has history now — use it.

## Before you start

Summarize what exists:
- What was the original vision? What got built?
- What worked well? What surprised?
- What tech debt or open questions accumulated?
- What user feedback or real-world evidence exists?

Play this back to the human — they may have forgotten details, or the builder may have learned things the human hasn't seen yet.

## Discovery rounds

Use `vscode_askQuestions` for structured choices. Don't ask more than 3–5 questions per round.

### Round 1 — Reflect

- **What's working?** What are users (or you) actually using and liking?
- **What's not working?** What's frustrating, missing, or broken?
- **What surprised you?** Anything the project taught you that you didn't expect?
- **What do people ask for?** (If there are users — if not, what do *you* wish it did?)

### Round 2 — Explore Directions

Based on what exists, propose 3–5 concrete directions. Ground them in evidence:
- Features that would amplify what's already working
- Pain points that need fixing
- Adjacent capabilities the architecture already supports
- Technical improvements (performance, reliability, developer experience)

For each direction, name:
- What it enables
- What it costs (effort, complexity, risk)
- Whether it builds on existing code or requires new foundations

Ask the human: "Which of these excite you? Which feel wrong? What's missing from this list?"

### Round 3 — Scope the Next Vision

- **What's the next milestone?** Not a wish list — the next meaningful state of the project.
- **What are 3–5 goals?** Priority-ordered.
- **What's explicitly NOT in this version?** (features, platforms, scale targets parked for later)
- **What new constraints or risks exist?** (scale has changed, new integrations, tech debt pressure)

### Round 4 — Sharpen

- "Here's what I think the next vision is: [summary]. Sound right?"
- Challenge anything hand-wavy or overly ambitious
- Surface contradictions with existing architecture or constraints
- Check: "Does this require breaking changes to what exists? If so, is that acceptable?"

## Ambiguity gate

- **High ambiguity** (direction unclear): Keep brainstorming. Do not proceed.
- **Medium ambiguity** (some goals vague but direction is clear): Note gaps. Proceed.
- **Low ambiguity** (clear next milestone): Proceed.

## Output

### 1. Archive the current vision

Move the current vision lock:
```bash
cp docs/vision/VISION-LOCK.md docs/vision/archive/VISION-LOCK.v{N}.md
```
Where `{N}` is the current version number.

### 2. Write new Vision Lock — `docs/vision/VISION-LOCK.md`

Follow the existing structure. Set:
- **Version**: `{N+1}.0` (major version bump)
- **Status**: `Active`
- Update all sections based on the brainstorm
- Add a changelog entry referencing the expansion

The new vision should build on what exists, not pretend the project is starting over.

### 3. Advance the state machine

Update `roadmap/state.md`:
- **Stage**: `planning` (the next session's planner will produce `phase-N+1-design.md`)
- Clear `Design Plan`, `Implementation Plan`, set `Design Status: n/a`, `Implementation Status: n/a`.
- Reset `Blocked Kind: n/a`, `Blocked Reason: n/a` (vision-update has been resolved).
- **Phase increment depends on arrival path:**
  - From `Blocked Kind: vision-exhausted`: Phase was already incremented by `phase-complete.prompt.md`. **Do not increment again** — leave Phase as-is.
  - From `Blocked Kind: awaiting-vision-update` (mid-phase pivot): the in-flight phase is being abandoned because its premise is invalid. **Treat the pivot as a phase boundary**: increment `Phase` by 1, clear `Phase Title`, reset Slice Evidence (`Evidence For Slice`, `Tests Written`, `Tests Pass`, `Reviewer Invoked`, `Review Verdict`, `Critical Findings: 0`, `Major Findings: 0`, `Strategic Review`, `Committed` → `n/a` / `pending`), reset `Active Slice: 1`, `Slice Total: n/a`, `Design Critique Rounds: 0`, `Implementation Critique Rounds: 0`. This avoids the next planner overwriting the abandoned `phase-N-design.md`.
  - In both cases, also write a one-line note to `## Vision Pivots` in `CURRENT-STATE.md` recording the abandoned phase number and the reason, so the audit trail isn't lost when the design plan filename moves on.

Do **not** create a phase plan inline — that is the planner's job on the next session once Stage is `planning`.

### 4. Catalog re-evaluation

If new project characteristics surfaced (e.g., the project now has a frontend, or now handles payments), re-run catalog selection:
- Use `vscode_askQuestions` with options from `.github/catalog/MANIFEST.md`.
- The human, not the builder, picks which catalog items to activate. Do not apply heuristics autonomously.


## Tips

- Reference concrete evidence: "In Phase 2, you hit [X problem] — does that influence this direction?"
- Don't just ask what to build — ask what to *stop* building or what to simplify
- If the human has big ambitions but limited time, help them find the smallest version that matters
- If the brainstorm stalls: "What if we flip it — instead of adding features, what if we made [existing thing] dramatically better?"
