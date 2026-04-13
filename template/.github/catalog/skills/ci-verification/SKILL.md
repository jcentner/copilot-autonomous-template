---
name: ci-verification
description: "CI pipeline verification patterns. Use when checking GitHub Actions status, gating on CI results, or diagnosing CI failures. Ensures autonomous agents verify CI passes before considering work complete."
---

# CI Verification Skill

How to check, interpret, and gate on CI pipeline results during autonomous development.

## When to Use

- After pushing commits to verify CI status
- Before marking a phase as complete
- When diagnosing CI failures
- When the Stop hook requires CI verification

## Checking CI Status

### GitHub Actions (via `gh` CLI)

```bash
# Check status of the most recent run on current branch
gh run list --branch "$(git branch --show-current)" --limit 1

# Watch a specific run (blocks until complete)
gh run watch <run-id>

# View failed job logs
gh run view <run-id> --log-failed

# Check status of a specific commit
gh run list --commit "$(git rev-parse HEAD)" --limit 5
```

### Interpreting Results

| Status | Meaning | Action |
|--------|---------|--------|
| `completed` + `success` | All checks passed | Safe to proceed |
| `completed` + `failure` | One or more checks failed | Diagnose and fix before proceeding |
| `in_progress` | Still running | Wait and re-check (do other work in the meantime) |
| `queued` | Waiting for runner | Wait — don't assume success |
| `completed` + `cancelled` | Run was cancelled | Re-trigger or investigate why |

### When `gh` CLI Is Not Available

If `gh` is not installed or not authenticated:

1. Note this as a blocker in `roadmap/CURRENT-STATE.md`
2. Fall back to local test verification:
   ```bash
   # Run the project's test suite locally
   # (adapt to project's test command)
   npm test     # Node.js
   pytest       # Python
   cargo test   # Rust
   go test ./...  # Go
   ```
3. Local test pass is an acceptable proxy for CI pass in most cases
4. Note "CI not verified — local tests only" in the slice checklist

## Gating Protocol

### Before Marking Phase Complete

1. All local tests pass
2. Most recent CI run on the branch is green (if CI exists)
3. If CI is failing on unrelated tests, document which failures are pre-existing vs. introduced

### Handling Flaky Tests

If a test passes locally but fails in CI (or vice versa):

1. Re-run CI once to confirm it's flaky (not a real failure)
2. If flaky: log in `docs/reference/tech-debt.md` with the test name and failure pattern
3. Do not disable the test — mark the flake and continue
4. If the same test flakes 3+ times, it needs a dedicated fix (add to phase plan)

### Handling Pre-Existing CI Failures

If CI was already failing before your changes:

1. Run `gh run list --limit 5` to see if the failure predates your work
2. If pre-existing: document in `roadmap/CURRENT-STATE.md` as a known issue
3. Verify your changes don't add *new* failures (compare failure sets)
4. Do not block your work on pre-existing failures, but do note them

## Integration with Stop Hook

When the ci-gate hook is active, the Stop hook verifies:
1. The most recent local test run passed (checks for test output markers)
2. If CI exists, the builder has acknowledged CI status in the slice checklist

The hook does NOT block on CI directly (CI runs are async and may take minutes), but it requires the builder to have checked and recorded the status.
