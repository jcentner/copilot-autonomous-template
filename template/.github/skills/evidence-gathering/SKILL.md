---
name: evidence-gathering
description: "Patterns for gathering empirical evidence to satisfy `evidence-status: needed` findings from the critic agent. USE FOR: planner responding to a critic verdict that flagged needed evidence; pre-emptively grounding design-plan claims; researcher gathering external grounding for a strategize candidate. DO NOT USE FOR: findings tagged `unmeasurable` (judgment / taste / future-fit) — argue on merits, do not invent measurements."
---

# Evidence Gathering

The [critic](../../agents/critic.agent.md) tags each finding with `evidence-status: present | needed | unmeasurable`. A `needed` tag means: **the claim is checkable, but no one has checked it yet.** This skill describes the audit patterns the planner runs **before** the next critique round, so the next round can see real evidence instead of conjecture.

## When to use

- You are the planner (or autonomous-builder) responding to a critic verdict of `revise` whose findings include any `evidence-status: needed` items.
- You are writing a design plan and want to pre-empt `needed` findings by grounding claims now.
- You are the researcher gathering external grounding for a strategize candidate.

## When NOT to use

- The finding is `evidence-status: unmeasurable` (judgment, taste, future fit). Argue on merits; do not invent measurements.
- The finding is `evidence-status: present` and you disagree with the cited evidence. Re-read the citation; if still in disagreement, write a counter-finding with your own `evidence-status: present` cite.

## Audit patterns

### 1. Live API audit

When the finding is "API X probably returns shape Y" or "we assume endpoint Z exists":

```bash
# HTTP status + headers
curl -sSI <url> | head -20

# Response shape (one record):
curl -sS <url> | jq '.[0] | keys'

# Pagination evidence:
curl -sS <url> | jq '{count: (.data | length), next: .next_cursor}'
```

Capture the exact command + first ~20 lines of output in the design plan under the finding being addressed. Include retrieval timestamp.

For external public APIs, prefer delegating to the **researcher** subagent (`/research <api-name>`) — it produces a durable `docs/reference/<api>.md` you can cite from multiple findings.

### 2. Schema dump

When the finding is "field X exists" or "table Y has column Z":

```bash
# Postgres
psql "$DATABASE_URL" -c '\d+ <table>'

# JSON schema from sample data
cat sample.json | jq 'paths(scalars) | join(".")' | sort -u

# OpenAPI spec extract
yq '.components.schemas.<Type>.properties | keys' openapi.yaml
```

### 3. File / dependency inventory

When the finding is "we already have X somewhere" or "library Y is/isn't a dep":

```bash
# Codebase grep — let grep_search do this; no manual rg needed
# (grep_search returns matches with file paths and line numbers)

# Package manifest probes
jq '.dependencies, .devDependencies | keys[]?' package.json | sort -u
grep -E '^(name|version) ' pyproject.toml
cargo metadata --format-version 1 | jq -r '.packages[].name'
```

Cite the exact match count and a representative path. "There are 3 callers of `foo()`: src/a.ts:42, src/b.ts:11, src/c.ts:88" is a `present` evidence string.

### 4. Concurrent-access / race-condition audit

When the finding is "this could race":

- Identify the shared resource (file, DB row, in-memory cache).
- Identify each writer + reader path (cite by file:line).
- State the ordering guarantee — atomic? lock? optimistic? "no guarantee, accepted because <reason>"?

The output is a written assertion in the plan, not a measurement. Tag it `evidence-status: present` only if you've cited every writer/reader path.

### 5. Performance probe

When the finding is "this might be slow":

- Pick a representative input size.
- Time it: `time <command>`, or wrap a function with `console.time` / `time.perf_counter`.
- Record the measured wall-clock + the input size + the machine.

A single measurement on a laptop is enough to convert `needed` to `present`. Production-load benchmarks are out of scope unless the finding specifies them.

### 6. External-system grounding (delegate)

For any finding involving a third-party system without a `docs/reference/<system>.md` doc:

- Run `/research <system>` to invoke the researcher subagent.
- Cite the produced reference doc (`docs/reference/<system>.md`) in the next planner pass.
- The researcher writes citations with retrieval timestamps; you inherit them.

## Output

After running the audit(s), update the design or implementation plan:

- For each `evidence-status: needed` finding, add a sub-section **"Evidence (gathered <ISO8601>)"** containing the command run, the captured output (truncated to ~20 lines), and a one-sentence interpretation.
- The next critic round must see the evidence and either accept the rebuttal (re-tag `evidence-status: present` in the next critique) or escalate to a `Blocking` finding with concrete reasoning.

## Anti-patterns

- **Hand-waving "we'll check later".** That's exactly what `needed` flagged. If you cannot run the check this session, mark the finding `evidence-status: deferred` in your reply and explain why — but the critic is allowed to refuse approval until it's resolved.
- **Inventing measurements.** "It's probably ~50ms" is not evidence. If you didn't run the timer, don't cite a number.
- **Citing the plan to itself.** Evidence comes from outside the plan: code, fetched docs, measured output. Plans citing themselves are circular.

## Cross-reference

- Critic agent: [`.github/agents/critic.agent.md`](../../agents/critic.agent.md) — produces the `evidence-status` tags.
- Researcher agent: [`.github/agents/researcher.agent.md`](../../agents/researcher.agent.md) — for external-system grounding.
- ADR-011 (strategy stage and three-gate approval) — origin of the evidence-status convention.
