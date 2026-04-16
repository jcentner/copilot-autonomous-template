#!/usr/bin/env python3
"""PreToolUse hook: Stage gate.

Blocks code-editing tools during non-executing stages of the workflow pipeline.
Only allows edits to `roadmap/**`, `docs/**`, and `.github/**` when Stage is
anything other than `executing`, `bootstrap`, or `cleanup`.

Reads Stage from `roadmap/CURRENT-STATE.md`. If the file is missing, allows
(bootstrap edge case).

Terminal commands (`run_in_terminal`) are allowed at this layer — terminal-based
bypass (e.g., `echo ... > src/foo.py`) is caught at session end by
`session-gate.py`'s git-diff backstop.

Return schema (per Copilot hooks docs):
    {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow" | "deny" | "ask",
        "permissionDecisionReason": "..."
    }}
"""
import json
import os
import sys


EDIT_TOOLS = {
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "edit_notebook_file",
}

ALLOWLISTED_PREFIXES = (
    "roadmap/",
    "docs/",
    ".github/",
)

# Stages where edits are unrestricted.
UNRESTRICTED_STAGES = {"executing", "bootstrap", "cleanup"}

VALID_STAGES = {
    "bootstrap",
    "planning",
    "design-critique",
    "implementation-planning",
    "implementation-critique",
    "executing",
    "reviewing",
    "cleanup",
    "blocked",
    "complete",
}


def allow(reason=""):
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }
    if reason:
        out["hookSpecificOutput"]["permissionDecisionReason"] = reason
    json.dump(out, sys.stdout)


def deny(reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )


def read_stage(cwd):
    """Return the current Stage value, or None if unreadable."""
    path = os.path.join(cwd, "roadmap", "CURRENT-STATE.md")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return None
    for line in content.splitlines():
        stripped = line.strip().lower()
        # Match lines like `- **Stage**: planning`
        if "**stage**:" in stripped:
            value = stripped.split("**stage**:", 1)[1].strip()
            # Strip trailing markdown/comment cruft
            value = value.split("<", 1)[0].strip()
            return value
    return None


def normalize_path(path, cwd):
    """Normalize a tool-call path to a workspace-relative forward-slash string."""
    if not path:
        return ""
    # Handle both absolute and relative
    if os.path.isabs(path):
        try:
            path = os.path.relpath(path, cwd)
        except ValueError:
            # Different drive on Windows — treat as outside workspace
            return path.replace("\\", "/")
    # Normalize separators and collapse ./, ../
    path = os.path.normpath(path).replace("\\", "/")
    return path


def extract_target_path(tool_name, tool_input):
    """Return the target filesystem path from a tool-call payload, or ''."""
    if tool_name == "create_file":
        return tool_input.get("filePath", "") or tool_input.get("file_path", "")
    if tool_name in ("replace_string_in_file", "edit_notebook_file"):
        return tool_input.get("filePath", "") or tool_input.get("file_path", "")
    if tool_name == "multi_replace_string_in_file":
        replacements = tool_input.get("replacements") or []
        if replacements and isinstance(replacements, list):
            first = replacements[0] or {}
            return first.get("filePath", "") or first.get("file_path", "")
    return ""


def path_is_allowlisted(rel_path):
    """True if path is under roadmap/, docs/, or .github/."""
    if not rel_path:
        return False
    # Path traversal guard — if .. still present after normpath, refuse
    if rel_path.startswith("../") or rel_path == "..":
        return False
    return any(rel_path.startswith(prefix) for prefix in ALLOWLISTED_PREFIXES)


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        allow()
        return

    cwd = input_data.get("cwd", ".")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {}) or {}

    stage = read_stage(cwd)

    # Missing or unreadable state → allow (bootstrap edge case).
    if stage is None:
        allow()
        return

    # Unknown stage value → allow but note reason (fail-open to avoid bricking sessions).
    if stage not in VALID_STAGES:
        allow(f"Unknown Stage value '{stage}'; allowing by default.")
        return

    # Unrestricted stages.
    if stage in UNRESTRICTED_STAGES:
        allow()
        return

    # Terminal commands are not path-gated here — session-gate catches source edits at stop.
    if tool_name == "run_in_terminal":
        allow()
        return

    # Non-edit tools → allow.
    if tool_name not in EDIT_TOOLS:
        allow()
        return

    target = extract_target_path(tool_name, tool_input)
    rel = normalize_path(target, cwd)

    if path_is_allowlisted(rel):
        allow()
        return

    deny(
        f"Stage is '{stage}' — edits to '{rel or target}' are blocked. "
        "During non-executing stages, only edits under roadmap/, docs/, or .github/ "
        "are permitted. Advance Stage to 'executing' by completing plan approval "
        "first, or redirect this edit to an allowed path."
    )


if __name__ == "__main__":
    main()
