#!/usr/bin/env python3
"""Stop hook: Session gate.

Parses machine-readable state from `roadmap/state.md` and blocks session stop
when the current stage has unmet requirements.

Also runs a git-diff backstop: during non-executing stages, if source files
outside the allowlist have been modified (e.g., via `run_in_terminal` bypass
of `stage-gate.py`), block stop and demand revert or stage advance.

Stage = `blocked` only allows stop when `Blocked Kind` is set to a valid
value — this prevents an agent from setting `Stage: blocked` with no
explanation as a way to bypass the gate.

Return schema (per Copilot hooks docs):
    {"hookSpecificOutput": {
        "hookEventName": "Stop",
        "decision": "block",
        "reason": "..."
    }}
Empty object on allow.
"""
import glob
import json
import os
import subprocess
import sys

from _state_io import (
    VALID_BLOCKED_KINDS,
    VALID_STAGES,
    load_json_config,
    parse_state,
    state_exists,
)


ALLOWLISTED_PREFIXES = ("roadmap/", "docs/", ".github/")

# Specific root-level files that are legitimately mutated outside the
# prefix allowlist. `BOOTSTRAP.md` is created by the template and deleted
# by the bootstrap stage itself; its deletion may still appear in
# `git diff HEAD` after Stage advances if the bootstrap commit lands
# in the same session as the Stage flip.
ALLOWLISTED_PATHS = frozenset({"BOOTSTRAP.md"})

NON_EXECUTING_STAGES = {
    "strategy",
    "planning",
    "design-critique",
    "implementation-planning",
    "implementation-critique",
    "reviewing",
}

INCOMPLETE_SLICE_VALUES = {"pending", "no"}
TERMINAL_REVIEW_VERDICTS = {"pass", "n/a"}
BLOCKING_REVIEW_VERDICTS = {"pending", "needs-fixes", "needs-rework"}


def block(reason, fields=None, cwd=None):
    out = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "decision": "block",
            "reason": _augment_with_next_prompt(reason, fields, cwd),
        }
    }
    json.dump(out, sys.stdout)


def allow(fields=None, cwd=None):
    """Allow Stop. Surface a `Next Prompt` / `Consider` hint via top-level
    `systemMessage` if state.md has them set (and not `n/a`).
    """
    msg = _next_prompt_message(fields, cwd)
    if msg:
        json.dump({"systemMessage": msg}, sys.stdout)
    else:
        json.dump({}, sys.stdout)


def _augment_with_next_prompt(reason, fields, cwd):
    msg = _next_prompt_message(fields, cwd)
    if msg:
        return f"{reason}\n\n{msg}"
    return reason


def _next_prompt_message(fields, cwd):
    if not fields:
        return ""
    parts = []
    next_prompt = (fields.get("next prompt", "") or "").strip()
    if next_prompt and next_prompt.lower() != "n/a":
        parts.append(f"→ Next: {next_prompt}")
    stage = (fields.get("stage", "") or "").strip().lower()
    if cwd and stage:
        recs = _stage_recommendations(cwd, stage)
        if recs:
            parts.append(f"→ Consider: {recs}")
    return "\n".join(parts)


def _stage_recommendations(cwd, stage):
    config = load_json_config(
        cwd,
        ".github/hooks/config/stage-recommendations.json",
        default={},
    )
    entry = config.get(stage) or {}
    items = []
    for prompt in entry.get("prompts", []) or []:
        items.append(str(prompt))
    for skill in entry.get("skills", []) or []:
        items.append(f"skill:{skill}")
    return ", ".join(items)


def get(fields, key, default=""):
    return fields.get(key, default).strip().lower()


def git_diff_source_changes(cwd):
    """Return list of paths changed (vs HEAD) outside the allowlist.

    Returns [] on git errors (missing git, unborn HEAD, etc.).
    """
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    if result.returncode != 0:
        return []
    changed = [p.strip() for p in result.stdout.splitlines() if p.strip()]
    return [
        p
        for p in changed
        if not any(p.startswith(pref) for pref in ALLOWLISTED_PREFIXES)
        and p not in ALLOWLISTED_PATHS
    ]


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    # Loop prevention: if we've already blocked once this stop cycle, let it go.
    if input_data.get("stop_hook_active", False):
        allow()
        return

    cwd = input_data.get("cwd", ".")

    if not state_exists(cwd):
        # No state file → allow (fresh workspace / bootstrap).
        allow()
        return

    fields, unchecked = parse_state(cwd)
    stage = get(fields, "stage")

    if not stage:
        allow(fields, cwd)
        return

    # Unknown stage value → fail CLOSED.
    if stage not in VALID_STAGES:
        block(
            f"Unknown Stage value '{stage}' in roadmap/state.md. "
            f"Valid values: {', '.join(sorted(VALID_STAGES))}. "
            f"Fix the Stage field before stopping.",
            fields,
            cwd,
        )
        return

    # `complete` allows stop unconditionally — vision exhausted.
    if stage == "complete":
        allow(fields, cwd)
        return

    # `blocked` allows stop only when Blocked Kind is set to a valid value.
    # Without that requirement, an agent could set `Stage: blocked` with no
    # explanation as a Stop-hook bypass.
    if stage == "blocked":
        kind = get(fields, "blocked kind")
        if kind not in VALID_BLOCKED_KINDS:
            block(
                f"Stage is 'blocked' but Blocked Kind is '{kind or 'unset'}'. "
                f"Set Blocked Kind in roadmap/state.md to one of "
                f"{', '.join(sorted(VALID_BLOCKED_KINDS))} and explain the "
                f"situation in Blocked Reason. Use /resume to unblock.",
                fields,
                cwd,
            )
            return
        allow(fields, cwd)
        return

    # Terminal-bypass backstop for non-executing stages.
    if stage in NON_EXECUTING_STAGES:
        outside = git_diff_source_changes(cwd)
        if outside:
            sample = ", ".join(outside[:5])
            more = f" (+{len(outside) - 5} more)" if len(outside) > 5 else ""
            block(
                f"Stage is '{stage}' but source files outside the allowlist have "
                f"been modified: {sample}{more}. Revert with "
                f"`git checkout -- <path>`, stash the changes, or advance Stage "
                f"to 'executing' (requires approved design + implementation plans).",
                fields,
                cwd,
            )
            return

    # Strategy-artifact gate: cannot stop in `planning` without evidence the
    # strategy stage produced an artifact (sets the candidate + rationale).
    if stage == "planning":
        if not _strategy_artifact_exists(cwd):
            block(
                "Stage is 'planning' but no strategy artifact "
                "(roadmap/strategy-*.md) exists. The strategize prompt must "
                "run before planning \u2014 a phase pick without recorded "
                "rationale is a gap. Run /strategize, or rewind Stage to "
                "'strategy' and produce the artifact.",
                fields,
                cwd,
            )
            return

    # Stage-specific field gates.
    if stage == "executing":
        reasons = []

        # Bug C: bind slice evidence to the current Active Slice. If the agent
        # has incremented Active Slice without resetting evidence (or without
        # rerunning write-test-evidence.py for the new slice), this catches it.
        active_slice = (fields.get("active slice", "") or "").strip()
        evidence_for = (fields.get("evidence for slice", "") or "").strip()
        if active_slice and active_slice.lower() not in ("n/a", ""):
            if not evidence_for or evidence_for.lower() == "n/a":
                reasons.append(
                    f"Evidence For Slice is unset but Active Slice is {active_slice} "
                    f"— run write-test-evidence.py for slice {active_slice}"
                )
            elif evidence_for != active_slice:
                reasons.append(
                    f"Evidence For Slice is '{evidence_for}' but Active Slice is "
                    f"'{active_slice}' — stale evidence from a prior slice. Reset "
                    f"Tests Written / Tests Pass / Reviewer Invoked / Review Verdict "
                    f"/ Critical Findings / Major Findings / Committed to pending, "
                    f"then complete the slice loop and rerun write-test-evidence.py"
                )

        tests_pass = get(fields, "tests pass")
        if tests_pass in INCOMPLETE_SLICE_VALUES:
            reasons.append(f"Tests Pass is '{tests_pass}' (need 'yes' or 'n/a')")

        reviewer_invoked = get(fields, "reviewer invoked")
        if reviewer_invoked in INCOMPLETE_SLICE_VALUES:
            reasons.append(
                f"Reviewer Invoked is '{reviewer_invoked}' (need 'yes' or 'n/a')"
            )

        verdict = get(fields, "review verdict")
        if verdict in BLOCKING_REVIEW_VERDICTS:
            reasons.append(
                f"Review Verdict is '{verdict}' (need 'pass' or 'n/a')"
            )

        try:
            critical = int(get(fields, "critical findings", "0") or "0")
        except ValueError:
            critical = 0
        if critical > 0:
            reasons.append(f"Critical Findings = {critical} (must be 0)")

        try:
            major = int(get(fields, "major findings", "0") or "0")
        except ValueError:
            major = 0
        if major > 0:
            reasons.append(f"Major Findings = {major} (must be 0)")

        committed = get(fields, "committed")
        if committed in INCOMPLETE_SLICE_VALUES:
            reasons.append(f"Committed is '{committed}' (need 'yes' or 'n/a')")

        if reasons:
            block(
                "Stage is 'executing' with incomplete Slice Evidence: "
                + "; ".join(reasons)
                + ". Finish the slice loop before stopping: run tests, invoke the "
                "reviewer, fix Critical/Major findings, commit, and update the "
                "Slice Evidence fields in roadmap/state.md.",
                fields,
                cwd,
            )
            return

    elif stage == "reviewing":
        strategic = get(fields, "strategic review")
        if strategic == "pending":
            block(
                "Stage is 'reviewing' but Strategic Review is 'pending'. Invoke "
                "the product-owner (or planner) to perform strategic review, "
                "then set Strategic Review to 'pass', 'replan', or 'n/a' in "
                "roadmap/state.md.",
                fields,
                cwd,
            )
            return

    elif stage == "cleanup":
        if unchecked:
            sample = "; ".join(unchecked[:3])
            more = f" (+{len(unchecked) - 3} more)" if len(unchecked) > 3 else ""
            block(
                f"Stage is 'cleanup' with unchecked Phase Completion Checklist "
                f"items: {sample}{more}. Complete the phase-complete protocol "
                f"and check all items in roadmap/state.md before stopping.",
                fields,
                cwd,
            )
            return

    elif stage == "design-critique":
        status = get(fields, "design status")
        if status == "in-critique":
            block(
                "Stage is 'design-critique' and Design Status is 'in-critique'. "
                "Finish the critique round and set Design Status to 'approved', "
                "'revise', or 'rethink'.",
                fields,
                cwd,
            )
            return

    elif stage == "implementation-critique":
        status = get(fields, "implementation status")
        if status == "in-critique":
            block(
                "Stage is 'implementation-critique' and Implementation Status is "
                "'in-critique'. Finish the critique round and set Implementation "
                "Status to 'approved', 'revise', or 'rethink'.",
                fields,
                cwd,
            )
            return

    allow(fields, cwd)


def _strategy_artifact_exists(cwd):
    pattern = os.path.join(cwd, "roadmap", "strategy-*.md")
    return bool(glob.glob(pattern))


if __name__ == "__main__":
    main()
