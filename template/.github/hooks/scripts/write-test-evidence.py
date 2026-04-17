#!/usr/bin/env python3
"""Helper: write slice test evidence to roadmap/state.md.

Agents call this explicitly after running tests. This is NOT a hook — it is
an agent-invoked utility. Per the v2 principle "agents write state, hooks
verify state," the agent that ran tests writes the result here.

Usage:
    python3 .github/hooks/scripts/write-test-evidence.py pass
    python3 .github/hooks/scripts/write-test-evidence.py fail
    python3 .github/hooks/scripts/write-test-evidence.py n/a

Exits 0 on success, 2 on argument error, 1 on state-file error.
"""
import os
import sys

from _state_io import (
    get_field_raw,
    state_exists,
    state_path,
    update_state_field,
)


VALID = {"pass", "fail", "n/a"}
MAP = {"pass": "yes", "fail": "no", "n/a": "n/a"}


def main(argv):
    if len(argv) != 2 or argv[1] not in VALID:
        print(
            f"usage: {argv[0]} {'|'.join(sorted(VALID))}",
            file=sys.stderr,
        )
        return 2

    result = argv[1]
    tests_pass_value = MAP[result]
    tests_written_value = "yes" if result != "n/a" else "n/a"

    cwd = os.getcwd()
    if not state_exists(cwd):
        print(f"error: {state_path(cwd)} not found", file=sys.stderr)
        return 1

    ok1 = update_state_field(cwd, "Tests Written", tests_written_value)
    ok2 = update_state_field(cwd, "Tests Pass", tests_pass_value)

    # Bind the recorded evidence to the current Active Slice. The session-gate
    # uses this field to detect stale evidence carried over from a prior
    # slice (Bug C): if Evidence For Slice != Active Slice during `executing`,
    # stop is blocked.
    active_slice = get_field_raw(cwd, "Active Slice", "n/a") or "n/a"
    update_state_field(cwd, "Evidence For Slice", active_slice)

    if not (ok1 and ok2):
        print(
            "warning: one or more fields not found — are 'Tests Written' / "
            "'Tests Pass' present in roadmap/state.md?",
            file=sys.stderr,
        )

    print(f"wrote Tests Pass={tests_pass_value} (Evidence For Slice={active_slice})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
