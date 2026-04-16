#!/usr/bin/env python3
"""PreToolUse hook (tester-scoped): Source code isolation.

Blocks the tester subagent from reading implementation code. The tester's
entire value is writing tests without implementation bias — this hook
enforces that.

Policy:
1. `semantic_search` / `search/codebase` is denied entirely — semantic search
   returns source content in results and cannot be path-gated.
2. `read_file` on paths under `Source Root` is denied unless the path matches
   a test-location or config pattern.
3. `grep_search` / `file_search` without `includePattern`, or with an
   `includePattern` that could reach non-test files under `Source Root`, is
   denied.
4. Everything else is allowed.

`Source Root` is read from `roadmap/CURRENT-STATE.md` (default `src/`).

Return schema (per Copilot hooks docs):
    {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow" | "deny" | "ask",
        "permissionDecisionReason": "..."
    }}
"""
import fnmatch
import json
import os
import re
import sys


DEFAULT_SOURCE_ROOT = "src/"

# Paths/patterns the tester may read even under Source Root.
TEST_PATH_GLOBS = [
    "**/test/**",
    "**/tests/**",
    "**/test_*",
    "**/*_test.*",
    "**/*.test.*",
    "**/*.spec.*",
    "**/__tests__/**",
    "**/__test__/**",
    "**/spec/**",
    "**/specs/**",
]

CONFIG_BASENAMES = {
    "package.json",
    "tsconfig.json",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "cargo.toml",
    "go.mod",
    "pnpm-workspace.yaml",
    "yarn.lock",
    "pnpm-lock.yaml",
    "package-lock.json",
    "jest.config.js",
    "jest.config.ts",
    "vitest.config.js",
    "vitest.config.ts",
    "pytest.ini",
    "tox.ini",
    "karma.conf.js",
    "mocha.opts",
    ".mocharc.json",
    ".mocharc.js",
    "conftest.py",
}

CONFIG_NAME_GLOBS = [
    "tsconfig*.json",
    "*.config.*",
    "*.config",
]

SEMANTIC_SEARCH_TOOLS = {
    "semantic_search",
    "search/codebase",
    "codebase",
}

GREP_TOOLS = {"grep_search", "search/textSearch", "textSearch"}
FILE_SEARCH_TOOLS = {"file_search", "search/fileSearch", "fileSearch"}
READ_TOOLS = {"read_file", "search/readFile", "readFile"}


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


def read_source_root(cwd):
    path = os.path.join(cwd, "roadmap", "CURRENT-STATE.md")
    if not os.path.exists(path):
        return DEFAULT_SOURCE_ROOT
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return DEFAULT_SOURCE_ROOT
    for line in content.splitlines():
        m = re.match(r"^\s*-\s+\*\*Source Root\*\*:\s*(.*?)\s*$", line, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if not val.endswith("/"):
                val += "/"
            return val
    return DEFAULT_SOURCE_ROOT


def normalize(path, cwd):
    if not path:
        return ""
    if os.path.isabs(path):
        try:
            path = os.path.relpath(path, cwd)
        except ValueError:
            return path.replace("\\", "/")
    return os.path.normpath(path).replace("\\", "/")


def path_is_test_or_config(rel_path):
    """True if the path is a test file or config file that's safe to read."""
    if not rel_path:
        return False
    basename = os.path.basename(rel_path).lower()
    if basename in CONFIG_BASENAMES:
        return True
    for pat in CONFIG_NAME_GLOBS:
        if fnmatch.fnmatch(basename, pat):
            return True
    for pat in TEST_PATH_GLOBS:
        if fnmatch.fnmatch(rel_path, pat):
            return True
    return False


def path_under_source(rel_path, source_root):
    if not rel_path:
        return False
    return rel_path.startswith(source_root) or rel_path == source_root.rstrip("/")


def includePattern_scoped_safely(pattern, source_root):
    """True if an `includePattern` confines the search to safe locations.

    A safe pattern either stays outside Source Root, or explicitly targets
    test/config paths (matching one of TEST_PATH_GLOBS / CONFIG_NAME_GLOBS).
    """
    if not pattern:
        return False
    # If the pattern doesn't touch Source Root, it's fine.
    if source_root not in pattern and not pattern.startswith(source_root):
        # But patterns like `**/*.py` reach everywhere, including source. Reject
        # unscoped glob roots.
        if pattern.startswith(("**/", "*", "*.")) or "/" not in pattern:
            # Still allow if it's clearly a test/config pattern.
            for safe in TEST_PATH_GLOBS + CONFIG_NAME_GLOBS:
                if fnmatch.fnmatch(pattern, safe) or pattern == safe:
                    return True
            # Unscoped — could reach source.
            return False
        return True
    # Pattern references source root — allow only if it also explicitly
    # narrows to a test subdirectory.
    for safe in TEST_PATH_GLOBS:
        if safe in pattern:
            return True
    return False


def extract_path(tool_input):
    return (
        tool_input.get("filePath")
        or tool_input.get("file_path")
        or tool_input.get("path")
        or ""
    )


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        allow()
        return

    tool_name = (input_data.get("tool_name") or "").strip()
    tool_input = input_data.get("tool_input", {}) or {}
    cwd = input_data.get("cwd", ".")

    # 1) Semantic search is always denied for the tester.
    if tool_name in SEMANTIC_SEARCH_TOOLS:
        deny(
            "tester cannot use semantic_search — its results leak source content. "
            "Use grep_search / file_search with an explicit includePattern scoped "
            "to tests/ or config files."
        )
        return

    source_root = read_source_root(cwd)

    # 2) read_file: path-gate.
    if tool_name in READ_TOOLS:
        rel = normalize(extract_path(tool_input), cwd)
        if not rel:
            allow()
            return
        if path_is_test_or_config(rel):
            allow()
            return
        if not path_under_source(rel, source_root):
            allow()
            return
        deny(
            f"tester cannot read implementation files — '{rel}' is under Source "
            f"Root '{source_root}'. Allowed reads: tests (tests/, **/*.test.*, "
            f"**/*.spec.*, __tests__/), config files (package.json, pyproject.toml, "
            f"tsconfig.json, etc.), and paths outside Source Root."
        )
        return

    # 3) grep_search / file_search: require scoped includePattern.
    if tool_name in GREP_TOOLS or tool_name in FILE_SEARCH_TOOLS:
        pattern = tool_input.get("includePattern") or tool_input.get("query") or ""
        # For file_search the 'query' field is the pattern itself; accept it too.
        if tool_name in FILE_SEARCH_TOOLS and not pattern:
            pattern = tool_input.get("query", "")

        if includePattern_scoped_safely(pattern, source_root):
            allow()
            return

        deny(
            "tester must scope searches. Provide an includePattern that matches "
            "test locations (e.g., 'tests/**', '**/*.test.*', '**/__tests__/**') "
            "or config files. Unscoped searches that could reach "
            f"'{source_root}' non-test files are denied."
        )
        return

    # 4) Everything else (edit, terminal, etc.) — allow.
    allow()


if __name__ == "__main__":
    main()
