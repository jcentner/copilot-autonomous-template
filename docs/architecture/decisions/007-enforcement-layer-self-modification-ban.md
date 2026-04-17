# ADR-007: Builder cannot self-modify the enforcement layer

## Status

Accepted (April 2026, v1)

## Context

Pre-v1 had an "Improve the development system" section that explicitly
permitted the builder to edit its own instructions, prompts, and hook
scripts when it identified workflow improvements. The intent was a
self-improving loop.

In practice this is **incoherent**: the same agent that's supposed to be
constrained by hooks is also empowered to weaken or remove those hooks.
A bug or misjudgment becomes architectural drift. There is no human in
the loop and no audit trail beyond a commit message.

We also observed an attack pattern in adversarial testing: an agent
running into a stage-gate denial would consider editing the gate to
remove the denial, since "improving the workflow" was permitted. This
defeats the entire enforcement layer.

## Decision

The builder, and any subagent, **cannot edit the enforcement layer at
any time, including between phases**. `tool-guardrails.py` denies writes
to:

- `.github/copilot-instructions.md` (root project instructions)
- `AGENTS.md` (cross-agent rules)
- `.github/agents/**` (agent definitions)
- `.github/hooks/scripts/**` (hook scripts)
- `.github/instructions/**` (scoped instructions)
- `roadmap/state.md` (machine workflow state — see ADR-009)

Bootstrap is the **only** stage where writes to `.github/agents/**`,
`.github/hooks/scripts/**`, and `.github/instructions/**` are allowed,
because catalog activation copies files from `.github/catalog/` into
those directories. The carve-out is gated on `Stage: bootstrap` (or
state-file absence, which BOOTSTRAP.md resolves before doing anything
else).

Improvements are still possible, but they go through humans:

1. The agent records the proposal in
   `roadmap/CURRENT-STATE.md` under `## Proposed Workflow Improvements`
   (and `docs/reference/agent-improvement-log.md` if the project uses it).
2. The human applies the change via `copier update`, an explicit
   unblock, or a manual edit.

`.github/prompts/**` is **not** protected. Project-specific prompts
(adding a `/release` prompt, customizing `/code-review`) are an
intentional extension surface for the builder, and prompts cannot
weaken hook enforcement — they're inputs to agents, not gates.

## Consequences

### Positive
- The enforcement layer is stable across the agent's lifetime. A bug in
  reasoning cannot delete the hook that would have caught it.
- The audit trail is `git log` on `.github/hooks/scripts/`. Every change
  has a human author.
- Adversarial bypass attempts ("just edit the gate") are denied at the
  PreToolUse hook with a clear explanation.

### Negative
- Genuine workflow improvements take longer. The agent must record the
  proposal, the human must read it, decide, and apply it.
- During bootstrap, the carve-out is broad (everything except `state.md`
  is writable). This is the trust boundary: bootstrap runs once,
  produces a known-good initial layout, and the carve-out closes.

### Neutral
- The protection is also enforced against the multi-replace smuggle
  pattern — `multi_replace_string_in_file` iterates every entry in
  `replacements`, so an allowlisted first entry cannot smuggle a
  protected second entry past the check.
- See ADR-009 for the related `state.md` write protection and the
  `rm`/`mv` denylist that prevents an agent from deleting `state.md`
  to forge bootstrap status.
