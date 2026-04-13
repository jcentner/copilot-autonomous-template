#!/usr/bin/env python3
"""Stop hook enhancement: CI gate.

Checks that tests have been run and passed before allowing the agent to stop.
Works alongside slice-gate.py — this adds test verification to the existing
phase-completion check.

Looks for evidence of test execution in CURRENT-STATE.md's slice checklist.
"""
import json
import os
import re
import sys


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    # Prevent infinite loop
    if input_data.get("stop_hook_active", False):
        json.dump({}, sys.stdout)
        return

    checkpoint = os.path.join(
        input_data.get("cwd", "."), "roadmap", "CURRENT-STATE.md"
    )

    if not os.path.exists(checkpoint):
        json.dump({}, sys.stdout)
        return

    with open(checkpoint) as f:
        content = f.read()

    # Check for phase completion or blocked status — if so, allow stop
    for line in content.splitlines():
        stripped = line.strip().lower()
        if "**phase status**:" in stripped:
            if "complete" in stripped or "blocked" in stripped:
                json.dump({}, sys.stdout)
                return

    # Phase is in progress — check for test evidence in the slice checklist
    # Look for unchecked test items
    checklist_section = False
    has_checklist = False
    tests_verified = True
    review_done = True

    for line in content.splitlines():
        if "slice checklist" in line.lower() or "current slice" in line.lower():
            checklist_section = True
            has_checklist = True
            continue
        if checklist_section:
            # End of checklist section
            if line.startswith("##") or line.startswith("---"):
                checklist_section = False
                continue
            lower_line = line.lower()
            # Check for unchecked test items
            if "- [ ]" in line and ("test" in lower_line and "pass" in lower_line):
                tests_verified = False
            # Check for unchecked review items
            if "- [ ]" in line and "reviewer" in lower_line:
                review_done = False

    missing = []
    if not tests_verified:
        missing.append("tests have not been verified as passing")
    if not review_done:
        missing.append("reviewer has not been invoked")

    if missing:
        reason = (
            f"CI gate: {', '.join(missing)}. "
            "Before stopping, complete the slice checklist in "
            "roadmap/CURRENT-STATE.md. Run tests and invoke the reviewer "
            "subagent on changed files."
        )
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
    else:
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
