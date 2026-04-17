#!/usr/bin/env python3
"""PostToolUse hook: Context pressure advisor.

Tracks accumulated tool I/O size across the session. When the accumulated
context exceeds a threshold, injects an advisory message telling the agent
to checkpoint and consider wrapping up.

Advisory only — never blocks. Uses a temp file keyed on sessionId to track
state across hook invocations within a session.
"""
import hashlib
import json
import os
import sys
import tempfile
import time


# Default threshold in bytes (400KB of accumulated tool I/O)
THRESHOLD = int(os.environ.get("CONTEXT_THRESHOLD", 400_000))

# State file location — one per session
STATE_DIR = os.path.join(tempfile.gettempdir(), "copilot-context-monitor")

# Drop per-session state files older than this many seconds. 7 days is long
# enough to span an extended project pause without eating disk.
STATE_TTL_SECONDS = 7 * 24 * 3600


def derive_session_id(input_data):
    """Use the model-provided sessionId when present; otherwise derive a
    stable fallback from (cwd, ppid) so sessions under the same VS Code
    window share a state file even when no sessionId is supplied."""
    sid = input_data.get("sessionId")
    if sid:
        return str(sid)
    cwd = input_data.get("cwd") or os.getcwd()
    ppid = os.getppid()
    digest = hashlib.sha1(f"{cwd}|{ppid}".encode("utf-8")).hexdigest()[:12]
    return f"nosid-{digest}"


def get_state_file(session_id):
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, f"{session_id}.json")


def prune_stale(now=None):
    """Remove per-session state files older than STATE_TTL_SECONDS.

    Errors are swallowed — this is best-effort housekeeping and must never
    break the hook contract.
    """
    if now is None:
        now = time.time()
    try:
        if not os.path.isdir(STATE_DIR):
            return
        cutoff = now - STATE_TTL_SECONDS
        for name in os.listdir(STATE_DIR):
            path = os.path.join(STATE_DIR, name)
            try:
                if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                continue
    except OSError:
        return


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

    session_id = derive_session_id(input_data)
    tool_response = input_data.get("tool_response", "")

    prune_stale()

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
