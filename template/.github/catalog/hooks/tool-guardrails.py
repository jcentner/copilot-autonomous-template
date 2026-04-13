#!/usr/bin/env python3
"""PreToolUse hook: Tool guardrails.

Blocks dangerous operations before they execute:
- git push --force / git reset --hard
- Deletion of critical project files
- Writes to node_modules/
- Path traversal in file operations
"""
import json
import sys


# Critical files that should never be deleted by an agent
PROTECTED_FILES = {
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    ".gitignore",
    "Cargo.toml",
    "Cargo.lock",
    "pyproject.toml",
    "go.mod",
    "go.sum",
    "copier.yml",
}

# Patterns that indicate destructive git commands
DANGEROUS_GIT_PATTERNS = [
    "push --force",
    "push -f",
    "reset --hard",
    "clean -fd",
    "clean -df",
    "clean -xfd",
]


def check_terminal_command(tool_input):
    """Check terminal commands for dangerous patterns."""
    command = tool_input.get("command", "") or tool_input.get("input", "")
    if not command:
        return None

    command_lower = command.lower()

    # Allow --force-with-lease (it's safe)
    if "--force-with-lease" in command_lower:
        return None

    for pattern in DANGEROUS_GIT_PATTERNS:
        if pattern in command_lower:
            return f"Blocked: '{pattern}' is a destructive git operation. Use safer alternatives (e.g., --force-with-lease for push)."

    return None


def check_file_operation(tool_input, tool_name):
    """Check file operations for protected files and dangerous paths."""
    # Get the file path from various possible input field names
    file_path = (
        tool_input.get("filePath", "")
        or tool_input.get("file_path", "")
        or tool_input.get("path", "")
        or ""
    )

    if not file_path:
        return None

    # Block path traversal
    if ".." in file_path:
        return f"Blocked: Path traversal detected in '{file_path}'. Use absolute or clean relative paths."

    # Block writes to node_modules
    if "node_modules/" in file_path or "node_modules\\" in file_path:
        return f"Blocked: Cannot modify files inside node_modules/. Use package manager commands instead."

    # Block deletion of critical files (only for delete operations)
    if "delete" in tool_name.lower():
        import os

        basename = os.path.basename(file_path)
        if basename in PROTECTED_FILES:
            return f"Blocked: Cannot delete critical file '{basename}'. This requires human approval."

    # Block direct .env edits
    import os

    basename = os.path.basename(file_path)
    if basename.startswith(".env"):
        return f"Blocked: Cannot directly modify '{basename}'. Use environment variable management instead."

    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        json.dump({}, sys.stdout)
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    reason = None

    # Check terminal/command tools
    if "terminal" in tool_name.lower() or "command" in tool_name.lower() or tool_name in (
        "run_in_terminal",
        "send_to_terminal",
    ):
        reason = check_terminal_command(tool_input)

    # Check file operation tools
    if "file" in tool_name.lower() or "edit" in tool_name.lower() or tool_name in (
        "create_file",
        "replace_string_in_file",
        "multi_replace_string_in_file",
    ):
        reason = check_file_operation(tool_input, tool_name)

    if reason:
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
    else:
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
