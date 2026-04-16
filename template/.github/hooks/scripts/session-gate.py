#!/usr/bin/env python3
"""Stop hook: Session gate.

Replaces the prior `slice-gate.py`. Parses machine-readable state from
`roadmap/CURRENT-STATE.md` and blocks session stop when the current stage
has unmet requirements.

Also runs a git-diff backstop: during non-executing stages, if source files
outside the allowlist have been modified (e.g., via `run_in_terminal` bypass
of `stage-gate.py`), block stop and demand revert or stage advance.

Return schema (per Copilot hooks docs):
    {"hookSpecificOutput": {
        "hookEventName": "Stop",
        "decision": "block",
        "reason": "..."
    }}
Empty object on allow.
"""
import json
import os
import re
import subprocess
import sys


ALLOWLISTED_PREFIXES = ("roadmap/", "docs/", ".github/")

NON_EXECUTING_STAGES = {
    "planning",
    "design-critique",
    "implementation-planning",
    "implementation-critique",
    "reviewing",
}

# Slice Evidence values that indicate the slice is not yet complete.
INCOMPLETE_SLICE_VALUES = {"pending", "no"}

# Terminal Review Verdict values.
TERMINAL_REVIEW_VERDICTS = {"pass", "n/a"}
BLOCKING_REVIEW_VERDICTS = {"pending", "needs-fixes", "needs-rework"}


def block(reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "decision": "block",
                "reason": reason,
            }
        },
        sys.stdout,
    )


def allow():
    json.dump({}, sys.stdout)


def parse_state(cwd):
    """Return a dict of lowercase field-name → string-value parsed from CURRENT-STATE.md."""
    path = os.path.join(cwd, "roadmap", "CURRENT-STATE.md")
    fields = {}
    checklist_unchecked = []
    if not os.path.exists(path):
        return fields, checklist_unchecked
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return fields, checklist_unchecked

    field_re = re.compile(r"^\s*-\s+\*\*([^*]+)\*\*:\s*(.*?)\s*$")
    unchecked_re = re.compile(r"^\s*-\s+\[ \]\s+(.*?)\s*$")
    in_checklist = False
    for raw in lines:
        heading = raw.strip().lower()
        if heading.startswith("## "):
            in_checklist = heading == "## phase completion checklist"
            continue
        m = field_re.match(raw)
        if m:
            key = m.group(1).strip().lower()
            val = m.group(2).strip()
            # Strip inline HTML comments.
            val = re.sub(r"<!--.*?-->", "", val).strip()
            fields[key] = val
        elif in_checklist:
            u = unchecked_re.match(raw)
            if u:
                checklist_unchecked.append(u.group(1).strip())
    return fields, checklist_unchecked


def get(fields, key, default=""):
    return fields.get(key, default).strip().lower()


def git_diff_source_changes(cwd):
    """Return list of paths changed (vs HEAD) that are outside the allowlist.

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
    outside = [
        p for p in changed if not any(p.startswith(pref) for pref in ALLOWLISTED_PREFIXES)
    ]
    return outside


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
    fields, unchecked = parse_state(cwd)

    stage = get(fields, "stage")

    # No state file, or stage unreadable → allow (bootstrap / fresh workspace).
    if not stage:
        allow()
        return

    # Explicit escape hatches.
    if stage in ("blocked", "complete"):
        allow()
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
                f"`git checkout -- <path>`, stash the changes, or advance Stage to "
                f"'executing' (requires approved design + implementation plans)."
            )
            return

    # Stage-specific field gates.
    if stage == "executing":
        reasons = []
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
                "Slice Evidence fields in roadmap/CURRENT-STATE.md."
            )
            return

    elif stage == "reviewing":
        strategic = get(fields, "strategic review")
        if strategic == "pending":
            block(
                "Stage is 'reviewing' but Strategic Review is 'pending'. Invoke the "
                "product-owner (or planner) to perform strategic review, then set "
                "Strategic Review to 'pass', 'replan', or 'n/a' in "
                "roadmap/CURRENT-STATE.md."
            )
            return

    elif stage == "cleanup":
        if unchecked:
            sample = "; ".join(unchecked[:3])
            more = f" (+{len(unchecked) - 3} more)" if len(unchecked) > 3 else ""
            block(
                f"Stage is 'cleanup' with unchecked Phase Completion Checklist items: "
                f"{sample}{more}. Complete the phase-complete protocol and check all "
                f"items in roadmap/CURRENT-STATE.md before stopping."
            )
            return

    elif stage == "design-critique":
        status = get(fields, "design status")
        if status == "in-critique":
            block(
                "Stage is 'design-critique' and Design Status is 'in-critique'. "
                "Finish the critique round and set Design Status to 'approved', "
                "'revise', or 'rethink'."
            )
            return

    elif stage == "implementation-critique":
        status = get(fields, "implementation status")
        if status == "in-critique":
            block(
                "Stage is 'implementation-critique' and Implementation Status is "
                "'in-critique'. Finish the critique round and set Implementation "
                "Status to 'approved', 'revise', or 'rethink'."
            )
            return

    # All checks passed.
    allow()


if __name__ == "__main__":
    main()
