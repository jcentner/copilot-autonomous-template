#!/usr/bin/env python3
"""PreToolUse hook: Branch gate.

Refuses `git commit` invocations when HEAD is on a denylisted branch
(typically `main`, `master`, `trunk`, `prod`). Forces work to happen on a
feature branch (`phase/N-theme`, `strategy/YYYY-MM-DD`, `wip/<name>`).

Reads `.github/hooks/config/branch-policy.json` for the denylist; uses a
sensible fallback if the file is missing or malformed. Bootstrap stage is
exempt by default (controlled by `bootstrap_exempt` in the config) so the
initial bootstrap commit can land on `main`.

This hook only inspects terminal commands. Other commit paths (IDE GUI,
sub-shells launched outside the agent) are not covered \u2014 the agent
exclusively commits via `run_in_terminal` / `send_to_terminal`.

Return schema (per Copilot hooks docs):
    {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow" | "deny",
        "permissionDecisionReason": "..."
    }}
"""
import json
import os
import re
import subprocess
import sys

from _state_io import is_bootstrap_stage, load_json_config


TERMINAL_TOOLS = {"run_in_terminal", "send_to_terminal"}

DEFAULT_POLICY = {
    "denylist": ["main", "master", "trunk", "prod"],
    "denylist_patterns": ["^release/"],
    "allowlist_patterns": ["^phase/", "^strategy/", "^wip/", "^bootstrap/"],
    "bootstrap_exempt": True,
    "block_message": (
        "Direct commits to '{branch}' are denied. Create a feature branch "
        "(phase/N-theme, strategy/YYYY-MM-DD, or wip/<name>) and commit "
        "there. Edit .github/hooks/config/branch-policy.json to change the "
        "denylist."
    ),
}

# Recognise `git commit ...` even when prefixed (env vars, sudo, cd && ...)
# Excludes obvious non-commit subcommands like `git commit-tree` (porcelain
# only). Negative-lookahead `(?![-\w])` rejects `commit-tree`, `commit_x`,
# `commitfoo` while allowing `commit`, `commit ` (space), end-of-line, etc.
# Handles `git -C <path> commit`, `git --no-pager commit`, etc.
_COMMIT_RE = re.compile(
    r"(?:^|[\s;&|`(])git(?:\s+-[A-Za-z0-9-]+(?:[= ][^\s]+)?)*\s+commit(?![-\w])"
)


def allow():
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        },
        sys.stdout,
    )


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


def _command_text(tool_input):
    return (tool_input.get("command") or tool_input.get("input") or "").strip()


def _is_commit_command(command):
    if not command or "commit" not in command:
        return False
    return bool(_COMMIT_RE.search(command))


def _current_branch(cwd):
    """Return current git branch name, or None on any error / detached HEAD."""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    if not branch or branch == "HEAD":
        return None
    return branch


def _branch_denied(branch, policy):
    if branch in (policy.get("denylist") or []):
        return True
    for pat in policy.get("denylist_patterns") or []:
        try:
            if re.search(pat, branch):
                return True
        except re.error:
            continue
    return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        allow()
        return

    tool_name = input_data.get("tool_name", "")
    if tool_name not in TERMINAL_TOOLS:
        allow()
        return

    tool_input = input_data.get("tool_input", {}) or {}
    command = _command_text(tool_input)
    if not _is_commit_command(command):
        allow()
        return

    cwd = input_data.get("cwd", "")
    if not cwd:
        # Cannot resolve git repo without cwd \u2014 conservative allow.
        allow()
        return

    policy = load_json_config(
        cwd, ".github/hooks/config/branch-policy.json", DEFAULT_POLICY
    )

    if policy.get("bootstrap_exempt", True) and is_bootstrap_stage(cwd):
        allow()
        return

    branch = _current_branch(cwd)
    if branch is None:
        # No git repo / detached HEAD / git missing \u2014 nothing to enforce.
        allow()
        return

    if _branch_denied(branch, policy):
        msg_template = policy.get("block_message") or DEFAULT_POLICY["block_message"]
        try:
            reason = msg_template.format(branch=branch)
        except (KeyError, IndexError):
            reason = DEFAULT_POLICY["block_message"].format(branch=branch)
        deny(reason)
        return

    allow()


if __name__ == "__main__":
    main()
