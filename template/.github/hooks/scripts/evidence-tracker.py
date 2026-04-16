#!/usr/bin/env python3
"""PostToolUse hook: Evidence tracker (pure logger).

Scope: This hook is a *pure logger*. It does not parse subagent verdicts.
Verdict recording is the responsibility of the critic / product-owner /
reviewer subagents — they write directly to CURRENT-STATE fields before
returning. SubagentStop hooks (Phase B) verify the write happened.

Behavior:
1. Append a line to the Session Log summarizing the tool call.
2. If the tool was `run_in_terminal` running a test command, update
   `Tests Written` and `Tests Pass` in CURRENT-STATE.md.
3. Never modify Design Status, Implementation Status, Review Verdict,
   Critical/Major Findings, or Strategic Review — those are agent-owned.

Idempotent: field updates use single-line replacement so re-running the same
tool does not corrupt state.

Return schema (per Copilot hooks docs):
    {"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "optional note"
    }}
Empty object is also valid.
"""
import datetime
import json
import os
import re
import sys


TEST_CMD_PATTERN = re.compile(
    r"\b(pytest|jest|vitest|go\s+test|cargo\s+test|npm\s+test|yarn\s+test|pnpm\s+test|mocha|rspec|phpunit|dotnet\s+test)\b",
    re.IGNORECASE,
)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_path(cwd):
    return os.path.join(cwd, "roadmap", "CURRENT-STATE.md")


def read_state(cwd):
    path = state_path(cwd)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def write_state(cwd, content):
    path = state_path(cwd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError:
        pass


def update_field(content, field_name, new_value):
    """Update `- **Field Name**: <old>` to `- **Field Name**: <new>`. Case-sensitive field match."""
    pattern = re.compile(
        r"^(\s*-\s+\*\*" + re.escape(field_name) + r"\*\*:)\s*.*$",
        re.MULTILINE,
    )
    return pattern.sub(rf"\1 {new_value}", content, count=1)


def append_session_log(content, line):
    """Append `- <line>` under the `## Session Log` section.

    If the section is absent, append a new section at end of file.
    """
    header = "## Session Log"
    idx = content.find(header)
    if idx == -1:
        suffix = "" if content.endswith("\n") else "\n"
        return content + f"{suffix}\n{header}\n\n- {line}\n"

    # Find end of Session Log section = start of next `## ` heading or EOF.
    after = content.find("\n## ", idx + len(header))
    if after == -1:
        # Section runs to end of file.
        body = content[idx:].rstrip("\n")
        new_body = body + f"\n- {line}\n"
        return content[:idx] + new_body
    # Section ends at `after` (which points at the `\n` before next heading).
    body = content[idx:after].rstrip("\n")
    new_body = body + f"\n- {line}\n"
    return content[:idx] + new_body + content[after:]


def is_test_command(tool_name, tool_input):
    if tool_name != "run_in_terminal":
        return False
    cmd = tool_input.get("command", "") or tool_input.get("input", "")
    return bool(TEST_CMD_PATTERN.search(cmd))


def test_passed(tool_response):
    """Best-effort: infer test pass/fail from tool_response.

    `tool_response` may be a string or dict. We look for an explicit exit_code
    field first, then fall back to common failure markers in output text.
    """
    if tool_response is None:
        return None
    if isinstance(tool_response, dict):
        if "exit_code" in tool_response:
            try:
                return int(tool_response["exit_code"]) == 0
            except (TypeError, ValueError):
                pass
        text = str(tool_response.get("output", "") or tool_response.get("stdout", ""))
    else:
        text = str(tool_response)
    if not text:
        return None
    lower = text.lower()
    # Obvious failure markers.
    failure_markers = [
        "failed",
        "error:",
        "traceback",
        "assertionerror",
        " fail ",
        "tests failed",
    ]
    if any(m in lower for m in failure_markers):
        # Guard against false positives from phrases like "0 failed".
        if re.search(r"\b0\s+failed\b", lower) or re.search(r"\bfailures?:\s*0\b", lower):
            return True
        return False
    success_markers = ["passed", "ok", "all tests pass", "0 failed"]
    if any(m in lower for m in success_markers):
        return True
    return None


def summarize(tool_name, tool_input, tool_response):
    """Short one-line summary for the Session Log."""
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
    tool_response = input_data.get("tool_response")

    content = read_state(cwd)
    if content is None:
        # No state file to log against — exit silently.
        json.dump({}, sys.stdout)
        return

    new_content = content
    log_line = f"[{now_iso()}] {summarize(tool_name, tool_input, tool_response)}"

    # Update test evidence on test commands.
    if is_test_command(tool_name, tool_input):
        new_content = update_field(new_content, "Tests Written", "yes")
        result = test_passed(tool_response)
        if result is True:
            new_content = update_field(new_content, "Tests Pass", "yes")
            log_line += " [tests pass]"
        elif result is False:
            new_content = update_field(new_content, "Tests Pass", "no")
            log_line += " [tests fail]"
        else:
            log_line += " [tests: result unknown]"

    new_content = append_session_log(new_content, log_line)

    if new_content != content:
        write_state(cwd, new_content)

    json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
