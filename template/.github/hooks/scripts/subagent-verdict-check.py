#!/usr/bin/env python3
"""SubagentStop hook: verify the subagent wrote its verdict to CURRENT-STATE.md.

Agents write state, hooks verify state wrote. The critic, product-owner, and
reviewer agents' instructions explicitly require updating specific fields in
`roadmap/CURRENT-STATE.md` before returning. This hook verifies the write
happened — it does not parse prose or tool output.

Usage:
    python3 subagent-verdict-check.py <subagent-name>

Where <subagent-name> is one of: critic | product-owner | reviewer.

Return schema (per Copilot hooks docs):
    {"hookSpecificOutput": {
        "hookEventName": "SubagentStop",
        "decision": "block",
        "reason": "..."
    }}
Empty object on allow.
"""
import json
import os
import re
import sys


NON_TERMINAL_STATUS = {"in-critique", "draft", "pending"}
TERMINAL_STATUS = {"approved", "revise", "rethink", "waived"}
TERMINAL_REVIEW_VERDICT = {"pass", "needs-fixes", "needs-rework", "n/a"}
TERMINAL_STRATEGIC = {"pass", "replan", "n/a"}


def block(reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStop",
                "decision": "block",
                "reason": reason,
            }
        },
        sys.stdout,
    )


def allow():
    json.dump({}, sys.stdout)


def parse_state(cwd):
    path = os.path.join(cwd, "roadmap", "CURRENT-STATE.md")
    fields = {}
    if not os.path.exists(path):
        return fields
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return fields
    for line in content.splitlines():
        m = re.match(r"^\s*-\s+\*\*([^*]+)\*\*:\s*(.*?)\s*$", line)
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip()
    return fields


def get(fields, key, default=""):
    return fields.get(key, default).strip().lower()


def check_critic(fields):
    stage = get(fields, "stage")
    if stage == "design-critique":
        status = get(fields, "design status")
        if status in NON_TERMINAL_STATUS:
            return (
                f"critic: Design Status is '{status}' — must be set to a terminal "
                f"value ({', '.join(sorted(TERMINAL_STATUS))}) in "
                f"roadmap/CURRENT-STATE.md before returning."
            )
        try:
            rounds = int(get(fields, "design critique rounds", "0") or "0")
        except ValueError:
            rounds = 0
        if rounds < 1:
            return (
                "critic: Design Critique Rounds must be incremented (>= 1) before "
                "returning."
            )
        return None
    if stage == "implementation-critique":
        status = get(fields, "implementation status")
        if status in NON_TERMINAL_STATUS:
            return (
                f"critic: Implementation Status is '{status}' — must be set to a "
                f"terminal value ({', '.join(sorted(TERMINAL_STATUS))}) before "
                f"returning."
            )
        try:
            rounds = int(get(fields, "implementation critique rounds", "0") or "0")
        except ValueError:
            rounds = 0
        if rounds < 1:
            return (
                "critic: Implementation Critique Rounds must be incremented (>= 1) "
                "before returning."
            )
        return None
    # Critic invoked outside an expected stage — allow, let the builder handle it.
    return None


def check_product_owner(fields, cwd):
    stage = get(fields, "stage")
    if stage == "reviewing":
        strategic = get(fields, "strategic review")
        if strategic not in TERMINAL_STRATEGIC:
            return (
                f"product-owner (review): Strategic Review is '{strategic}' — must "
                f"be set to one of {', '.join(sorted(TERMINAL_STRATEGIC))} before "
                f"returning."
            )
        return None
    if stage == "design-critique":
        # Design mode: verify the design plan file contains a User Stories section
        # with at least one `- As a` or `**As a**` bullet.
        design_plan = fields.get("design plan", "").strip()
        if not design_plan or design_plan.lower() == "n/a":
            return (
                "product-owner (design): Design Plan field in CURRENT-STATE is "
                "unset — cannot verify user stories were written."
            )
        plan_path = os.path.join(cwd, design_plan)
        if not os.path.exists(plan_path):
            return (
                f"product-owner (design): design plan '{design_plan}' does not "
                f"exist — write user stories to it before returning."
            )
        try:
            with open(plan_path, encoding="utf-8") as f:
                plan_text = f.read()
        except OSError:
            return (
                f"product-owner (design): cannot read design plan '{design_plan}'."
            )
        if "## User Stories" not in plan_text:
            return (
                f"product-owner (design): design plan '{design_plan}' has no "
                f"`## User Stories` section. Add at least one story before returning."
            )
        # Check for at least one story body.
        if not re.search(r"\*\*As a\*\*|^-\s+As a\b", plan_text, re.MULTILINE | re.IGNORECASE):
            return (
                f"product-owner (design): design plan '{design_plan}' has a User "
                f"Stories section but no story body ('As a ... I want to ...')."
            )
        return None
    return None


def check_reviewer(fields):
    invoked = get(fields, "reviewer invoked")
    if invoked != "yes":
        return (
            "reviewer: Reviewer Invoked must be 'yes' in CURRENT-STATE before "
            "returning."
        )
    verdict = get(fields, "review verdict")
    if verdict not in TERMINAL_REVIEW_VERDICT:
        return (
            f"reviewer: Review Verdict is '{verdict}' — must be set to one of "
            f"{', '.join(sorted(TERMINAL_REVIEW_VERDICT))} before returning."
        )
    for field in ("critical findings", "major findings"):
        raw = fields.get(field, "")
        try:
            int(raw)
        except (ValueError, TypeError):
            return (
                f"reviewer: {field.title()} must be a numeric count (got '{raw}')."
            )
    return None


def main():
    if len(sys.argv) < 2:
        # No subagent name — allow.
        allow()
        return
    subagent = sys.argv[1].strip().lower()

    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    # Loop prevention.
    if input_data.get("stop_hook_active", False):
        allow()
        return

    cwd = input_data.get("cwd", ".")
    fields = parse_state(cwd)

    if not fields:
        # No state file or empty — allow (can't verify).
        allow()
        return

    if subagent == "critic":
        reason = check_critic(fields)
    elif subagent == "product-owner":
        reason = check_product_owner(fields, cwd)
    elif subagent == "reviewer":
        reason = check_reviewer(fields)
    else:
        reason = None  # Unknown subagent name — allow.

    if reason:
        block(reason)
    else:
        allow()


if __name__ == "__main__":
    main()
