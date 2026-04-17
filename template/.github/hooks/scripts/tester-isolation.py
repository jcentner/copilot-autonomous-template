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
import sys

from _state_io import read_state_text as _read_state_text_from_state_md


DEFAULT_SOURCE_ROOT = "src/"

# Default tester-visible patterns. Can be overridden per-project via
# `Test Path Globs` and `Config File Globs` fields in roadmap/CURRENT-STATE.md
# (comma-separated).
DEFAULT_TEST_PATH_GLOBS = [
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

DEFAULT_CONFIG_GLOBS = [
    "package.json",
    "tsconfig.json",
    "tsconfig*.json",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "pnpm-workspace.yaml",
    "yarn.lock",
    "pnpm-lock.yaml",
    "package-lock.json",
    "jest.config.*",
    "vitest.config.*",
    "pytest.ini",
    "tox.ini",
    "karma.conf.*",
    "mocha.opts",
    ".mocharc.*",
    "conftest.py",
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


def _read_state_text(cwd):
    return _read_state_text_from_state_md(cwd)


def _read_field(content, field_name):
    if not content:
        return None
    import re
    pattern = re.compile(
        r"^\s*-\s+\*\*" + re.escape(field_name) + r"\*\*:\s*(.*?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    m = pattern.search(content)
    return m.group(1).strip() if m else None


def _parse_glob_list(value, defaults):
    if not value:
        return list(defaults)
    items = [p.strip() for p in value.split(",") if p.strip()]
    return items or list(defaults)


def read_source_root(cwd):
    content = _read_state_text(cwd)
    val = _read_field(content, "Source Root")
    if not val:
        return DEFAULT_SOURCE_ROOT
    if not val.endswith("/"):
        val += "/"
    return val


def read_glob_config(cwd):
    """Return (test_globs, config_globs) from state.md with fallbacks."""
    content = _read_state_text(cwd)
    test_globs = _parse_glob_list(
        _read_field(content, "Test Path Globs"), DEFAULT_TEST_PATH_GLOBS
    )
    config_globs = _parse_glob_list(
        _read_field(content, "Config File Globs"), DEFAULT_CONFIG_GLOBS
    )
    return test_globs, config_globs


def normalize(path, cwd):
    if not path:
        return ""
    if os.path.isabs(path):
        try:
            path = os.path.relpath(path, cwd)
        except ValueError:
            return path.replace("\\", "/")
    return os.path.normpath(path).replace("\\", "/")


def path_is_test_or_config(rel_path, test_globs, config_globs):
    """True if the path is a test file or config file that's safe to read."""
    if not rel_path:
        return False
    basename = os.path.basename(rel_path)
    for pat in config_globs:
        if fnmatch.fnmatch(basename, pat) or fnmatch.fnmatch(basename.lower(), pat.lower()):
            return True
    for pat in test_globs:
        if fnmatch.fnmatch(rel_path, pat):
            return True
    return False


def path_under_source(rel_path, source_root):
    if not rel_path:
        return False
    return rel_path.startswith(source_root) or rel_path == source_root.rstrip("/")


def _strip_leading_globstar(glob):
    """Drop a leading `**/` from a glob so substring/fnmatch checks against
    user includePatterns work for collocated tests.

    `**/tests/**` -> `tests/**`
    `**/*.test.*` -> `*.test.*`
    `tests/**`    -> `tests/**` (unchanged)
    """
    if glob.startswith("**/"):
        return glob[3:]
    return glob


def includePattern_scoped_safely(pattern, source_root, test_globs, config_globs):
    """True if an `includePattern` confines the search to safe locations.

    Safe means one of:
      1. Pattern is itself a known test/config glob (or matches one by fnmatch).
      2. Pattern stays outside Source Root *and* is not an unscoped glob root
         (`**/...`, `*`, `*.ext`, single segment) that could reach source.
      3. Pattern is under Source Root but explicitly narrows to a test
         subdirectory or test-suffix pattern (e.g., `src/tests/**`,
         `src/foo/__tests__/**`, `src/**/*.test.*`).
    """
    if not pattern:
        return False

    # 1) Pattern matches a known test/config glob directly.
    for safe in test_globs + config_globs:
        if pattern == safe or fnmatch.fnmatch(pattern, safe):
            return True

    pattern_norm = pattern.replace("\\", "/")
    src_norm = source_root.rstrip("/")

    touches_source = (
        pattern_norm == src_norm
        or pattern_norm.startswith(src_norm + "/")
        or src_norm + "/" in pattern_norm
    )

    # 3) Pattern under Source Root — require an embedded test marker that
    # aligns to a path-segment boundary. Raw substring would admit names
    # like `src/pretests/**` or `src/latest/**` as "safe" because they
    # contain `tests` / `test` as substrings.
    if touches_source:
        anchored_pattern = "/" + pattern_norm
        for safe in test_globs:
            tail = _strip_leading_globstar(safe)
            if not tail:
                continue
            # Prepending `/` to both sides forces the tail to start at a
            # path-segment boundary. `/tests/**` matches `src/tests/**`
            # (has `/tests/**`) but not `src/pretests/**` (has `/pretests/**`).
            # Filename-glob tails like `*.test.*` need `/*.test.*` which
            # only matches user patterns that glob-descend (e.g.,
            # `src/**/*.test.*`).
            if ("/" + tail) in anchored_pattern:
                return True
        return False

    # 2) Pattern outside Source Root — reject only unscoped roots that
    #    could still reach source files (e.g., `**/*.py`, `*.py`, `*`).
    if pattern_norm.startswith("**/") or pattern_norm.startswith("*") or "/" not in pattern_norm:
        return False
    return True


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
    test_globs, config_globs = read_glob_config(cwd)

    # 2) read_file: path-gate.
    if tool_name in READ_TOOLS:
        rel = normalize(extract_path(tool_input), cwd)
        if not rel:
            allow()
            return
        if path_is_test_or_config(rel, test_globs, config_globs):
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

        if includePattern_scoped_safely(pattern, source_root, test_globs, config_globs):
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
