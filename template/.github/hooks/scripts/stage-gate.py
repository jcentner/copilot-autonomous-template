#!/usr/bin/env python3
"""PreToolUse hook: Stage gate.

Blocks code-editing tools during non-executing stages. Only allows edits to
`roadmap/**`, `docs/**`, and `.github/**` when Stage is anything other than
`executing` or `bootstrap`.

Reads Stage from `roadmap/state.md`. If the file is missing, allows
(bootstrap edge case).

Terminal commands (`run_in_terminal`) are allowed at this layer — terminal-
based bypass (e.g., `echo ... > src/foo.py`) is caught at session end by
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

from _state_io import VALID_STAGES, get_field, state_exists


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
# `cleanup` is intentionally NOT in this set: during phase wrap-up, only
# doc/roadmap/.github edits should happen. If a source fix is genuinely
# needed during cleanup, reopen a slice under `executing` rather than
# smuggling source edits through cleanup.
UNRESTRICTED_STAGES = {"executing", "bootstrap"}


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


def normalize_path(path, cwd):
    """Normalize a tool-call path to a workspace-relative forward-slash string."""
    if not path:
        return ""
    if os.path.isabs(path):
        try:
            path = os.path.relpath(path, cwd)
        except ValueError:
            return path.replace("\\", "/")
    path = os.path.normpath(path).replace("\\", "/")
    return path


def extract_target_paths(tool_name, tool_input):
    """Return all target filesystem paths from a tool-call payload.

    Returns a list because `multi_replace_string_in_file` carries multiple
    replacements; we must check every one.
    """
    if tool_name == "create_file":
        p = tool_input.get("filePath", "") or tool_input.get("file_path", "")
        return [p] if p else []
    if tool_name in ("replace_string_in_file", "edit_notebook_file"):
        p = tool_input.get("filePath", "") or tool_input.get("file_path", "")
        return [p] if p else []
    if tool_name == "multi_replace_string_in_file":
        replacements = tool_input.get("replacements") or []
        if not isinstance(replacements, list):
            return []
        paths = []
        for r in replacements:
            if not isinstance(r, dict):
                continue
            p = r.get("filePath", "") or r.get("file_path", "")
            if p:
                paths.append(p)
        return paths
    return []


def path_is_allowlisted(rel_path):
    """True if path is under roadmap/, docs/, or .github/."""
    if not rel_path:
        return False
    # Path traversal guard — if .. still present after normpath, refuse.
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

    # Missing or unreadable state → allow (bootstrap edge case, fresh workspace).
    if not state_exists(cwd):
        allow()
        return

    stage = get_field(cwd, "Stage")
    if not stage:
        allow()
        return

    # Unknown stage value → fail CLOSED. A typo in the state file
    # (e.g., `implementaion-critique`) must not silently disable the gate.
    if stage not in VALID_STAGES:
        deny(
            f"Unknown Stage value '{stage}' in roadmap/state.md. "
            f"Valid values: {', '.join(sorted(VALID_STAGES))}. "
            f"Fix the Stage field before continuing."
        )
        return

    # Unrestricted stages.
    if stage in UNRESTRICTED_STAGES:
        allow()
        return

    # Terminal commands are not path-gated here — session-gate catches source
    # edits at stop via git diff.
    if tool_name == "run_in_terminal":
        allow()
        return

    # Non-edit tools → allow.
    if tool_name not in EDIT_TOOLS:
        allow()
        return

    targets = extract_target_paths(tool_name, tool_input)
    # No identifiable target → conservative allow (lets edits with unusual
    # payload shapes through; tested edit tools always carry filePath).
    if not targets:
        allow()
        return

    for raw in targets:
        rel = normalize_path(raw, cwd)
        if not path_is_allowlisted(rel):
            deny(
                f"Stage is '{stage}' — edits to '{rel or raw}' are blocked. "
                "During non-executing stages, only edits under roadmap/, docs/, "
                "or .github/ are permitted. Advance Stage to 'executing' by "
                "completing plan approval first, or redirect this edit to an "
                "allowed path."
            )
            return

    allow()


if __name__ == "__main__":
    main()
