#!/usr/bin/env python3
"""SubagentStop hook: verify the subagent wrote its verdict to state.md.

Agents write state, hooks verify state wrote. The critic, product-owner, and
reviewer agents' instructions explicitly require updating specific fields in
`roadmap/state.md` before returning. This hook verifies the write happened —
it does not parse prose or tool output.

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

from _state_io import parse_state


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


def get(fields, key, default=""):
    return fields.get(key, default).strip().lower()


def get_raw(fields, key, default=""):
    return fields.get(key, default).strip()


def coerce_phase(fields):
    """Return (phase_int, error_message).

    Phase must be a bare non-negative integer. Values like '1.0', 'Phase 1',
    or '' are treated as corruption — the critic/reviewer artifact paths
    embed this value, so a fuzzy parse silently writes to the wrong file.
    """
    raw = get_raw(fields, "phase", "").strip()
    if not raw:
        return None, "Phase field in state.md is empty — cannot locate artifact path."
    try:
        value = int(raw)
    except ValueError:
        return None, (
            f"Phase field in state.md is '{raw}' — must be a bare non-negative "
            f"integer (e.g., '1', not 'Phase 1' or '1.0'). The critic and reviewer "
            f"artifact paths embed this value."
        )
    if value < 0:
        return None, f"Phase field is negative ('{raw}') — must be >= 0."
    return value, None


# Stages where Phase=0 is a configuration error: the critic/reviewer should
# never be invoked during bootstrap, so a `phase-0-*.md` artifact path
# indicates Phase wasn't advanced before entering the stage.
_NON_BOOTSTRAP_PHASE_STAGES = {
    "design-critique",
    "implementation-critique",
    "executing",
    "reviewing",
}


def _phase_for_artifact(fields, stage, role):
    """Coerce Phase and reject Phase=0 in stages that require Phase >= 1."""
    phase, err = coerce_phase(fields)
    if err:
        return None, f"{role}: {err}"
    if phase == 0 and stage in _NON_BOOTSTRAP_PHASE_STAGES:
        return None, (
            f"{role}: Phase is 0 but Stage is '{stage}'. Phase must be "
            f"incremented to >= 1 before entering this stage — Phase 0 is "
            f"reserved for bootstrap."
        )
    return phase, None


def check_critic(fields, cwd):
    stage = get(fields, "stage")
    phase, err = _phase_for_artifact(fields, stage, "critic")
    if err:
        return err
    if stage == "design-critique":
        status = get(fields, "design status")
        if status in NON_TERMINAL_STATUS:
            return (
                f"critic: Design Status is '{status}' — must be set to a terminal "
                f"value ({', '.join(sorted(TERMINAL_STATUS))}) in "
                f"roadmap/state.md before returning."
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
        artifact = os.path.join(
            cwd, "roadmap", "phases", f"phase-{phase}-critique-design-R{rounds}.md"
        )
        if not os.path.exists(artifact):
            return (
                f"critic: expected artifact '{os.path.relpath(artifact, cwd)}' is "
                f"missing. The critique file for the current round must exist on "
                f"disk before returning."
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
        artifact = os.path.join(
            cwd, "roadmap", "phases",
            f"phase-{phase}-critique-implementation-R{rounds}.md",
        )
        if not os.path.exists(artifact):
            return (
                f"critic: expected artifact '{os.path.relpath(artifact, cwd)}' is "
                f"missing. The critique file for the current round must exist on "
                f"disk before returning."
            )
        return None
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
        design_plan = get_raw(fields, "design plan")
        if not design_plan or design_plan.lower() == "n/a":
            return (
                "product-owner (design): Design Plan field in state.md is unset — "
                "cannot verify user stories were written."
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
        if not re.search(r"\*\*As a\*\*|^-\s+As a\b", plan_text, re.MULTILINE | re.IGNORECASE):
            return (
                f"product-owner (design): design plan '{design_plan}' has a User "
                f"Stories section but no story body ('As a ... I want to ...')."
            )
        return None
    return None


def check_reviewer(fields, cwd):
    invoked = get(fields, "reviewer invoked")
    if invoked != "yes":
        return (
            "reviewer: Reviewer Invoked must be 'yes' in state.md before returning."
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
                f"reviewer: '{field.title()}' must be a non-negative integer; "
                f"got '{raw}'."
            )
    if verdict == "n/a":
        return None
    # Backstop: review artifact must exist on disk.
    stage = get(fields, "stage")
    phase, err = _phase_for_artifact(fields, stage, "reviewer")
    if err:
        return err
    slice_no = get_raw(fields, "active slice", "0") or "0"
    try:
        slice_int = int(slice_no)
    except ValueError:
        slice_int = 0
    if slice_int < 1:
        return (
            f"reviewer: Active Slice is '{slice_no}' — cannot locate the review "
            f"artifact path. Set Active Slice to a positive integer."
        )
    artifact = os.path.join(
        cwd, "roadmap", "phases", f"phase-{phase}-review-slice-{slice_int}.md"
    )
    if not os.path.exists(artifact):
        return (
            f"reviewer: expected artifact '{os.path.relpath(artifact, cwd)}' is "
            f"missing. Write the slice review file before returning."
        )
    return None


def check_planner(fields, cwd):
    """Verify the planner wrote the plan file it claims to have written.

    - In `planning`: Design Plan field must point at an existing file.
    - In `implementation-planning`: Implementation Plan field must point at
      an existing file.
    - In `design-critique` (re-planning round): Design Plan must still resolve.
    - In `implementation-critique` (re-planning round): Implementation Plan
      must still resolve.
    - In other stages (e.g., planner invoked as fallback reviewer during
      `reviewing`): no plan-file check, rely on the stage-specific verdict.
    """
    stage = get(fields, "stage")

    def _check_plan(field_name, human_name):
        path = get_raw(fields, field_name)
        if not path or path.lower() == "n/a":
            return (
                f"planner: {human_name} field in state.md is unset — planner "
                f"must write the plan file path before returning."
            )
        full = os.path.join(cwd, path)
        if not os.path.exists(full):
            return (
                f"planner: {human_name} points to '{path}' but that file does "
                f"not exist. Write the plan file, then set the field."
            )
        # Minimum sanity: non-empty file.
        try:
            if os.path.getsize(full) == 0:
                return (
                    f"planner: {human_name} file '{path}' exists but is empty. "
                    f"Populate it before returning."
                )
        except OSError:
            pass
        return None

    if stage in ("planning", "design-critique"):
        return _check_plan("design plan", "Design Plan")
    if stage in ("implementation-planning", "implementation-critique"):
        return _check_plan("implementation plan", "Implementation Plan")
    # Planner may also perform strategic review as a fallback in `reviewing`.
    if stage == "reviewing":
        strategic = get(fields, "strategic review")
        if strategic not in TERMINAL_STRATEGIC:
            return (
                f"planner (strategic-review fallback): Strategic Review is "
                f"'{strategic}' — must be set to one of "
                f"{', '.join(sorted(TERMINAL_STRATEGIC))} before returning."
            )
    return None


CHECKS = {
    "critic": check_critic,
    "product-owner": check_product_owner,
    "reviewer": check_reviewer,
    "planner": check_planner,
}


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} {'|'.join(sorted(CHECKS))}", file=sys.stderr)
        sys.exit(2)
    subagent = argv[1]
    if subagent not in CHECKS:
        # Unknown subagent — allow (no rule defined).
        allow()
        return

    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    if input_data.get("stop_hook_active", False):
        allow()
        return

    cwd = input_data.get("cwd", ".")
    fields, _ = parse_state(cwd)
    if not fields:
        # No state file → nothing to verify.
        allow()
        return

    reason = CHECKS[subagent](fields, cwd)
    if reason:
        block(reason)
    else:
        allow()


if __name__ == "__main__":
    main(sys.argv)
