#!/usr/bin/env python3
"""Stop hook for the autonomous builder agent.

Prevents premature stopping by checking:
1. Whether stop_hook_active is set (prevents infinite loops)
2. Whether the phase is marked complete in CURRENT-STATE.md

If the phase is not complete, blocks the stop and tells the agent to continue.
"""
import json
import os
import sys


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    # Prevent infinite loop — if we already blocked once, let it stop
    if input_data.get("stop_hook_active", False):
        json.dump({}, sys.stdout)
        return

    # Check CURRENT-STATE.md for phase status
    checkpoint = os.path.join(
        input_data.get("cwd", "."), "roadmap", "CURRENT-STATE.md"
    )

    if os.path.exists(checkpoint):
        with open(checkpoint) as f:
            content = f.read()

        # Machine-readable status field: **Phase Status**: Complete
        for line in content.splitlines():
            stripped = line.strip().lower()
            if "**phase status**:" in stripped:
                if "complete" in stripped or "blocked" in stripped:
                    # Phase is done or blocked (incl. vision expansion) — allow stop
                    json.dump({}, sys.stdout)
                    return

    # Phase not complete — block stop and tell agent to continue
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "decision": "block",
                "reason": (
                    "Phase is not yet complete. Check roadmap/CURRENT-STATE.md "
                    "for remaining work. Before stopping, ensure you have: "
                    "(1) run tests on your changes, "
                    "(2) invoked the reviewer subagent on changed files, "
                    "(3) fixed any Critical/Major findings, "
                    "(4) committed your work, "
                    "(5) updated CURRENT-STATE.md. "
                    "If the phase IS complete, set **Phase Status** to "
                    "'Complete' in CURRENT-STATE.md. "
                    "If you are blocked and need human input, set it to "
                    "'Blocked: [reason]'."
                ),
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
