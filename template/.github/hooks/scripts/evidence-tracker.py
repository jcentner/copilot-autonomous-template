#!/usr/bin/env python3
"""PostToolUse hook: per-session activity logger.

Appends one line per tool call to `roadmap/sessions/<sessionId>.md`. Updates
`roadmap/CURRENT-STATE.md`'s `## Active Session` link the first time it sees
this session.

Does **not** mutate workflow state. Per the v2 architectural principle
"agents write state, hooks verify state," only agents and the
`write-test-evidence.py` helper write state-machine fields.

Per-session log files are append-only. POSIX `O_APPEND` writes < PIPE_BUF
(4 KiB) are atomic on Linux, so concurrent invocations from parallel tool
calls cannot interleave-corrupt the log.
"""
import json
import sys

from _state_io import (
    append_session_log,
    derive_session_id,
    now_iso,
    state_exists,
    update_active_session_link,
)


def summarize(tool_name, tool_input):
    """Short one-line summary for the per-session log."""
    if tool_name == "run_in_terminal":
        cmd = tool_input.get("command", "") or tool_input.get("input", "")
        cmd = cmd.strip().splitlines()[0] if cmd else ""
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        return f"run_in_terminal: {cmd}"
    if tool_name in ("create_file", "replace_string_in_file", "edit_notebook_file"):
        path = tool_input.get("filePath", "") or tool_input.get("file_path", "")
        return f"{tool_name}: {path}"
    if tool_name == "multi_replace_string_in_file":
        reps = tool_input.get("replacements") or []
        return f"multi_replace_string_in_file: {len(reps)} edits"
    return tool_name or "tool"


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        json.dump({}, sys.stdout)
        return

    cwd = input_data.get("cwd", ".")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {}) or {}

    # No state.md → don't log; this is a fresh workspace before bootstrap.
    if not state_exists(cwd):
        json.dump({}, sys.stdout)
        return

    session_id = derive_session_id(input_data)
    line = f"[{now_iso()}] {summarize(tool_name, tool_input)}"

    append_session_log(cwd, session_id, line)
    update_active_session_link(cwd, session_id)

    json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
