# Template Architecture Decision Records

Significant architectural decisions for `copilot-autonomous-template` itself
(the Copier template), distinct from the ADR skeleton this template generates
for downstream projects (`template/docs/architecture/decisions/`).

These ADRs record the **why** behind v1's hook-verified stage machine. They
are the durable replacement for the design notes that lived in `tmp/` during
the v1 redesign (April 2026).

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [001](001-hook-verified-stage-machine.md) | Hook-verified stage machine replaces narrative checkpoints | Accepted |
| [002](002-state-md-narrative-split.md) | Split workflow state into `state.md` (machine) + `CURRENT-STATE.md` (narrative) + `sessions/` (logs) | Accepted |
| [003](003-agents-write-state-hooks-verify.md) | Agents write state, hooks verify state | Accepted |
| [004](004-stage-pipeline-and-critique-loops.md) | Bounded critique loops with iterative planner ↔ critic rounds | Accepted |
| [005](005-design-approval-as-session-break.md) | Design approval is the only mandatory human gate; uses session-break pattern | Accepted |
| [006](006-tester-isolation-via-pretooluse-hook.md) | Tester source-isolation via PreToolUse hook (not tool restriction) | Accepted |
| [007](007-enforcement-layer-self-modification-ban.md) | Builder cannot self-modify the enforcement layer | Accepted |
| [008](008-promote-critic-product-owner-to-core.md) | Promote critic and product-owner from catalog to core agents | Accepted |
| [009](009-bootstrap-carve-out-and-protected-state.md) | Bootstrap carve-out and `state.md` write-protection | Accepted |
| [010](010-three-tier-enforcement-honesty.md) | Three-tier enforcement vocabulary (deterministic / strongly-guided / advisory) | Accepted |

## Conventions

- File names are kebab-case with a leading 3-digit number.
- Status starts as **Proposed**, becomes **Accepted** when implemented, **Superseded by ADR-NNN** when replaced.
- ADRs are **append-only**. Don't edit the decision section of an accepted ADR — write a new one that supersedes it.
