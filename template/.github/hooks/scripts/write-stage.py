#!/usr/bin/env python3
"""Helper: write a Stage transition to roadmap/state.md.

Sanctioned writer for the (Stage, Blocked Kind, Blocked Reason, Next Prompt)
tuple. Direct edits to `roadmap/state.md` are blocked by `tool-guardrails.py`
outside `bootstrap`; this helper is the agent-facing path. Mirrors the
existing `write-test-evidence.py` / `write-commit-evidence.py` pattern.

Cross-field invariants enforced here so they can't be violated:

  - When `Stage: blocked`, `Blocked Kind` MUST be one of the values in
    `_state_io.VALID_BLOCKED_KINDS`. The session-gate hook would block
    stop on a bare `blocked` anyway, but enforcing at write time gives
    a clearer error and prevents the file from ever holding the bad shape.
  - When `Stage: <not blocked>`, `Blocked Kind` and `Blocked Reason` are
    auto-cleared to `n/a` (unless explicitly overridden by the caller —
    overriding is rare; the typical use is "leaving blocked, clear both").
  - When `--next-prompt` is supplied, the value must be in
    `_state_io.VALID_NEXT_PROMPTS`.

Usage:
    python3 .github/hooks/scripts/write-stage.py executing
    python3 .github/hooks/scripts/write-stage.py blocked \\
        --blocked-kind awaiting-merge-approval \\
        --blocked-reason "Phase 2 cleanup complete; awaiting /merge-phase." \\
        --next-prompt /merge-phase
    python3 .github/hooks/scripts/write-stage.py planning \\
        --next-prompt /design-plan

Exits 0 on success, 2 on argument error, 1 on state-file error or missing
field, 3 on invariant violation (e.g. Stage=blocked without --blocked-kind).
"""
import argparse
import os
import sys

from _state_io import (
    VALID_BLOCKED_KINDS,
    VALID_NEXT_PROMPTS,
    VALID_STAGES,
    state_exists,
    state_path,
    update_state_fields,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="write-stage.py",
        description=(
            "Sanctioned writer for the Stage transition fields in "
            "roadmap/state.md."
        ),
    )
    parser.add_argument("stage", help=f"target Stage; one of: {sorted(VALID_STAGES)}")
    parser.add_argument(
        "--blocked-kind",
        default=None,
        help=(
            "required when stage=blocked; one of: "
            f"{sorted(VALID_BLOCKED_KINDS)}"
        ),
    )
    parser.add_argument(
        "--blocked-reason",
        default=None,
        help=(
            "human-readable reason recorded under `Blocked Reason`. "
            "Required text when stage=blocked unless caller passes "
            "`--blocked-reason ''` to leave it as `n/a`."
        ),
    )
    parser.add_argument(
        "--next-prompt",
        default=None,
        help=(
            "value for `Next Prompt` field; one of: "
            f"{sorted(VALID_NEXT_PROMPTS)}"
        ),
    )
    return parser


def main(argv):
    parser = _build_parser()
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    stage = args.stage
    if stage not in VALID_STAGES:
        print(
            f"error: invalid stage '{stage}'. Allowed: "
            f"{', '.join(sorted(VALID_STAGES))}",
            file=sys.stderr,
        )
        return 2

    if args.next_prompt is not None and args.next_prompt not in VALID_NEXT_PROMPTS:
        print(
            f"error: invalid --next-prompt '{args.next_prompt}'. Allowed: "
            f"{', '.join(sorted(VALID_NEXT_PROMPTS))}",
            file=sys.stderr,
        )
        return 2

    # Cross-field invariants.
    if stage == "blocked":
        if args.blocked_kind is None:
            print(
                "error: stage=blocked requires --blocked-kind. "
                f"Allowed: {', '.join(sorted(VALID_BLOCKED_KINDS))}",
                file=sys.stderr,
            )
            return 3
        if args.blocked_kind not in VALID_BLOCKED_KINDS:
            print(
                f"error: invalid --blocked-kind '{args.blocked_kind}'. "
                f"Allowed: {', '.join(sorted(VALID_BLOCKED_KINDS))}",
                file=sys.stderr,
            )
            return 2

    cwd = os.getcwd()
    if not state_exists(cwd):
        print(f"error: {state_path(cwd)} not found", file=sys.stderr)
        return 1

    # Build the multi-field update. For non-blocked stages, auto-clear
    # Blocked Kind / Blocked Reason so the file can't drift into
    # `Stage: planning` + `Blocked Kind: awaiting-merge-approval`.
    updates = {"Stage": stage}
    if stage == "blocked":
        updates["Blocked Kind"] = args.blocked_kind
        if args.blocked_reason is not None:
            # Empty string explicitly opts out of writing a reason; treat
            # as `n/a` so the field always parses.
            updates["Blocked Reason"] = args.blocked_reason or "n/a"
    else:
        # Allow caller to override the clear with --blocked-kind / --blocked-reason
        # but the common case is "transition out of blocked, clear both".
        updates["Blocked Kind"] = (
            args.blocked_kind if args.blocked_kind is not None else "n/a"
        )
        updates["Blocked Reason"] = (
            args.blocked_reason if args.blocked_reason is not None else "n/a"
        )
    if args.next_prompt is not None:
        updates["Next Prompt"] = args.next_prompt

    written = update_state_fields(cwd, updates)
    missing = [field for field, ok in written.items() if not ok]
    if missing:
        print(
            f"error: field(s) not found in roadmap/state.md: "
            f"{', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    summary = ", ".join(f"{k}={v}" for k, v in updates.items())
    print(f"wrote {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
