# Commit Trailers Convention

Structured git trailers that preserve decision context in commit history. These help future sessions understand *why* a decision was made, not just *what* changed.

## Format

```
type(scope): description

Body explaining the change.

Constraint: [external limitation that shaped the decision]
Rejected: [alternative considered] | [reason it was rejected]
Confidence: high | medium | low
Scope-risk: narrow | moderate | broad
Not-tested: [what couldn't be tested and why]
```

## Trailers

| Trailer | When to Use | Example |
|---------|-------------|---------|
| `Constraint:` | External limitation that forced a specific approach | `Constraint: Auth service does not support token introspection` |
| `Rejected:` | Alternative that was considered and why it was dropped | `Rejected: Extend token TTL to 24h \| security policy violation` |
| `Confidence:` | How sure you are this is the right approach | `Confidence: medium` |
| `Scope-risk:` | How broadly this change could affect other code | `Scope-risk: broad` |
| `Not-tested:` | What wasn't testable and needs manual verification | `Not-tested: OAuth redirect flow — requires live IdP` |

## Rules

- `Constraint` and `Rejected` are the most valuable — always include when applicable
- `Confidence: low` signals to future sessions that this decision may need revisiting
- `Scope-risk: broad` signals to the reviewer that extra scrutiny is needed
- Multiple `Rejected:` trailers are fine for decisions with several alternatives
- Keep trailers concise — one line each

## Examples

### Simple feature commit
```
feat(auth): add session timeout after 30 minutes of inactivity

Tokens are refreshed silently up to 8 hours, then force re-login.

Constraint: Auth provider rate-limits token refresh to 1/minute
Rejected: Sliding window timeout | complicates token refresh logic
Confidence: high
Scope-risk: narrow
```

### Decision with uncertainty
```
feat(api): use polling instead of WebSocket for status updates

Polling at 5s interval. WebSocket would be more efficient but adds
operational complexity for the current team size.

Rejected: WebSocket | adds infrastructure dependency (Redis pub/sub)
Rejected: SSE | poor proxy support in target deployment environment
Confidence: medium
Scope-risk: moderate
Not-tested: Polling behavior under 1000+ concurrent clients
```

## Activation

To activate this convention, the builder should add the following to the project's `copilot-instructions.md`:

```markdown
## Commit Convention

Use conventional commits with decision trailers:
`type(scope): description` + optional trailers: `Constraint:`, `Rejected:`, `Confidence:`, `Scope-risk:`, `Not-tested:`.
See `.github/catalog/patterns/commit-trailers.md` for the full specification.
```
