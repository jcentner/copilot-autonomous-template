#!/usr/bin/env python3
"""Helper: write Phase identity (and optional full evidence reset) to state.md.

Sanctioned writer for `Phase`, `Phase Title`, and the slice-evidence reset
that happens at phase boundaries (post-merge resume, vision-expand pivot).

Direct edits to `roadmap/state.md` are blocked by `tool-guardrails.py`
outside `bootstrap`; this helper is the agent-facing path.

Subcommands and flags:
    write-phase.py [--number=N] [--title=TITLE] [--reset-evidence]

At least one of --number / --title / --reset-evidence must be supplied.
--number must be a non-negative integer. --title is recorded verbatim
(empty string clears it back to a blank value, used by vision-expand on
pivot). --reset-evidence resets every field that is logically scoped to a
single phase back to its `state.md.jinja` default; use it on phase
transitions (post-merge resume) and pivots (vision-expand mid-phase).

Atomic via `_state_io.update_state_fields`; the combined Phase / Title /
reset cannot leave state.md in a half-applied shape.

Exits 0 on success, 1 on state-file or missing-field error, 2 on argument
error.
"""
import argparse
import os
import sys

from _state_io import (
    state_exists,
    state_path,
    update_state_fields,
)


# Fields reset on `--reset-evidence`. These mirror the defaults written by
# `template/roadmap/state.md.jinja` for a fresh phase. Slice Evidence,
# planning artifacts, critique-round counters, and active-slice cursor —
# everything that is logically scoped to a single phase.
RESET_FIELDS = {
    # Plan artifacts (vision-expand and post-merge resume both clear these
    # so the next planner run does not collide with a stale path).
    "Design Plan": "n/a",
    "Design Status": "n/a",
    "Implementation Plan": "n/a",
    "Implementation Status": "n/a",
    # Slice cursor.
    "Active Slice": "n/a",
    "Slice Total": "n/a",
    # Critique round counters.
    "Design Critique Rounds": "0",
    "Implementation Critique Rounds": "0",
    # Slice evidence.
    "Evidence For Slice": "n/a",
    "Tests Written": "n/a",
    "Tests Pass": "n/a",
    "Reviewer Invoked": "n/a",
    "Review Verdict": "n/a",
    "Critical Findings": "0",
    "Major Findings": "0",
    "Strategic Review": "n/a",
    "Committed": "n/a",
}


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="write-phase.py",
        description=(
            "Sanctioned writer for Phase / Phase Title and the phase-boundary "
            "evidence reset."
        ),
    )
    parser.add_argument(
        "--number",
        type=str,
        default=None,
        help="non-negative integer to write into the `Phase` field",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help=(
            "value for `Phase Title`. Pass an empty string ('') to clear "
            "the title (vision-expand pivot scenario)."
        ),
    )
    parser.add_argument(
        "--reset-evidence",
        action="store_true",
        help=(
            "reset every phase-scoped field (slice evidence, planning "
            "artifacts, critique-round counters, slice cursor) back to its "
            "fresh-phase default. Use on post-merge resume and vision-expand "
            "mid-phase pivot."
        ),
    )
    return parser


def main(argv):
    parser = _build_parser()
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    if args.number is None and args.title is None and not args.reset_evidence:
        print(
            "error: pass at least one of --number, --title, --reset-evidence",
            file=sys.stderr,
        )
        return 2

    if args.number is not None:
        try:
            n = int(args.number)
        except ValueError:
            print(
                f"error: --number must be an integer, got '{args.number}'",
                file=sys.stderr,
            )
            return 2
        if n < 0:
            print("error: --number must be >= 0", file=sys.stderr)
            return 2
        number_value = str(n)
    else:
        number_value = None

    cwd = os.getcwd()
    if not state_exists(cwd):
        print(f"error: {state_path(cwd)} not found", file=sys.stderr)
        return 1

    updates: dict = {}
    if args.reset_evidence:
        updates.update(RESET_FIELDS)
    if number_value is not None:
        updates["Phase"] = number_value
    if args.title is not None:
        # Empty string is a legitimate "clear" value for vision-expand pivot.
        updates["Phase Title"] = args.title if args.title != "" else ""

    written = update_state_fields(cwd, updates)
    missing = [field for field, ok in written.items() if not ok]
    if missing:
        print(
            f"error: field(s) not found in roadmap/state.md: "
            f"{', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    summary_parts = []
    if number_value is not None:
        summary_parts.append(f"Phase={number_value}")
    if args.title is not None:
        summary_parts.append(f"Phase Title={args.title or '(cleared)'}")
    if args.reset_evidence:
        summary_parts.append(f"reset-evidence ({len(RESET_FIELDS)} fields)")
    print("wrote " + ", ".join(summary_parts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
