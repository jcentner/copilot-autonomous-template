#!/usr/bin/env python3
"""Helper: write planning artifact evidence to roadmap/state.md.

Agents (typically the planner) call this after writing a design or
implementation plan, after revising in response to critique, or after
counting slices. This is NOT a hook — it is an agent-invoked utility,
mirroring `write-test-evidence.py` and `write-commit-evidence.py`.

Direct edits to `roadmap/state.md` are blocked by `tool-guardrails.py`
(PROTECTED_STATE_FILES). This helper is the sanctioned writer for the
planning fields, so the planner does not need to shell out to a one-liner
that imports `_state_io` directly.

Subcommands:
    design-plan <path>            # set Design Plan
    design-status <value>         # set Design Status
    impl-plan <path>              # set Implementation Plan
    impl-status <value>           # set Implementation Status
    slice-total <int>             # set Slice Total

Status vocabulary (for design-status / impl-status):
    draft | in-critique | approved | revise | rethink | waived

Usage:
    python3 .github/hooks/scripts/write-plan-evidence.py \\
        design-plan roadmap/phases/phase-2-design.md
    python3 .github/hooks/scripts/write-plan-evidence.py design-status draft
    python3 .github/hooks/scripts/write-plan-evidence.py slice-total 4

Exit codes:
    0  success
    1  state.md not found, or field not present in state.md
    2  argument error (unknown subcommand, bad value)
    3  referenced plan file does not exist
"""
import os
import sys

from _state_io import state_exists, state_path, update_state_field


VALID_STATUS = {
    "draft",
    "in-critique",
    "approved",
    "revise",
    "rethink",
    "waived",
}

# Subcommand → state.md field name (canonical case as written in state.md).
FIELD_MAP = {
    "design-plan": "Design Plan",
    "design-status": "Design Status",
    "impl-plan": "Implementation Plan",
    "impl-status": "Implementation Status",
    "slice-total": "Slice Total",
}

USAGE = (
    "usage:\n"
    "  write-plan-evidence.py design-plan <path>\n"
    "  write-plan-evidence.py design-status "
    f"{'|'.join(sorted(VALID_STATUS))}\n"
    "  write-plan-evidence.py impl-plan <path>\n"
    "  write-plan-evidence.py impl-status "
    f"{'|'.join(sorted(VALID_STATUS))}\n"
    "  write-plan-evidence.py slice-total <int>"
)


def _normalize_path(value: str, cwd: str) -> str:
    """Normalize a plan-file path to a workspace-relative forward-slash form."""
    raw = value.replace("\\", "/")
    if os.path.isabs(raw):
        try:
            raw = os.path.relpath(raw, cwd)
        except ValueError:
            pass
    return os.path.normpath(raw).replace("\\", "/")


def main(argv):
    if len(argv) != 3:
        print(USAGE, file=sys.stderr)
        return 2

    subcommand = argv[1]
    value = argv[2]

    if subcommand not in FIELD_MAP:
        print(f"error: unknown subcommand '{subcommand}'", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    cwd = os.getcwd()
    if not state_exists(cwd):
        print(f"error: {state_path(cwd)} not found", file=sys.stderr)
        return 1

    # Per-subcommand validation. Status fields must use the canonical
    # vocabulary; plan-path fields must point at an existing file (the
    # planner writes the file *before* calling this helper); slice-total
    # must be a non-negative integer.
    if subcommand in ("design-status", "impl-status"):
        if value not in VALID_STATUS:
            print(
                f"error: invalid status '{value}'. Allowed: "
                f"{', '.join(sorted(VALID_STATUS))}",
                file=sys.stderr,
            )
            return 2
        write_value = value
    elif subcommand in ("design-plan", "impl-plan"):
        rel = _normalize_path(value, cwd)
        # Reject absolute paths that resolved outside the workspace and
        # path-traversal segments; the value lands in state.md verbatim and
        # other hooks will read it as workspace-relative.
        if rel.startswith("..") or rel.startswith("/"):
            print(
                f"error: plan path '{value}' must be inside the workspace",
                file=sys.stderr,
            )
            return 2
        abs_path = os.path.join(cwd, rel)
        if not os.path.isfile(abs_path):
            print(
                f"error: plan file '{rel}' does not exist — write the plan "
                "before stamping its path into state.md",
                file=sys.stderr,
            )
            return 3
        write_value = rel
    elif subcommand == "slice-total":
        try:
            n = int(value)
        except ValueError:
            print(
                f"error: slice-total must be an integer, got '{value}'",
                file=sys.stderr,
            )
            return 2
        if n < 0:
            print("error: slice-total must be >= 0", file=sys.stderr)
            return 2
        write_value = str(n)
    else:  # pragma: no cover — guarded by FIELD_MAP membership above
        print(USAGE, file=sys.stderr)
        return 2

    field = FIELD_MAP[subcommand]
    if not update_state_field(cwd, field, write_value):
        print(
            f"error: '{field}' field not found in roadmap/state.md",
            file=sys.stderr,
        )
        return 1

    print(f"wrote {field}={write_value}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
