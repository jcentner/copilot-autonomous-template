#!/usr/bin/env python3
"""PostToolUse hook: Context checkpoint advisor.

Tracks accumulated tool I/O size across the session. When the accumulated
context exceeds a threshold, injects an advisory message telling the agent
to checkpoint and consider wrapping up.

Uses a temp file to track state across hook invocations within a session.
"""
import json
import os
import sys
import tempfile


# Default threshold in bytes (400KB of accumulated tool I/O)
THRESHOLD = int(os.environ.get("CONTEXT_THRESHOLD", 400_000))

# State file location — one per session
STATE_DIR = os.path.join(tempfile.gettempdir(), "copilot-context-monitor")


def get_state_file(session_id):
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, f"{session_id}.json")


def load_state(state_file):
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"accumulated_bytes": 0, "tool_count": 0, "warned": False}


def save_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f)


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        json.dump({}, sys.stdout)
        return

    session_id = input_data.get("sessionId", "unknown")
    tool_response = input_data.get("tool_response", "")

    state_file = get_state_file(session_id)
    state = load_state(state_file)

    # Accumulate the size of tool responses
    response_size = len(str(tool_response).encode("utf-8", errors="replace"))
    state["accumulated_bytes"] += response_size
    state["tool_count"] += 1

    save_state(state_file, state)

    # Check if we should warn
    if state["accumulated_bytes"] >= THRESHOLD and not state["warned"]:
        state["warned"] = True
        save_state(state_file, state)

        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"[Context Monitor] Accumulated ~{state['accumulated_bytes'] // 1024}KB "
                        f"of tool I/O across {state['tool_count']} tool calls. "
                        "Context window pressure is high. Consider: "
                        "(1) Wrapping up the current slice cleanly, "
                        "(2) Updating CURRENT-STATE.md with detailed notes for the next session, "
                        "(3) Writing key observations to /memories/repo/, "
                        "(4) Committing all work. "
                        "Use subagents for any remaining research to avoid loading more into main context."
                    ),
                }
            },
            sys.stdout,
        )
    else:
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
