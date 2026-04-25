#!/usr/bin/env python3
"""PreToolUse hook: Tool guardrails.

Blocks known-destructive operations before they execute. Denylist-based —
novel patterns will slip through. This is belt-and-suspenders on top of
stage-gate and session-gate, not a substitute for them.

Covered today:
- Destructive git commands (`push --force`, `reset --hard`, `clean -fd`,
  `filter-branch`, `update-ref -d`).
- `rm -rf` on root / home / workspace-critical paths.
- Pipe-to-interpreter installers (`curl ... | sh`, `wget ... | bash`).
- `dd of=/dev/...` writes to raw devices.
- Package-manager foot-guns (`npm install --force`,
  `pip install --break-system-packages`).
- Writes to `node_modules/`, `.env*`, or paths containing `..`.
- Deletion of protected project files (package.json, pyproject.toml, etc.).
"""
import json
import os
import re
import sys

try:
    from _state_io import is_bootstrap_stage as _shared_is_bootstrap_stage
except ImportError:  # pragma: no cover — running standalone without sibling module
    _shared_is_bootstrap_stage = None


TERMINAL_TOOLS = {"run_in_terminal", "send_to_terminal"}
FILE_TOOLS = {
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "edit_notebook_file",
}

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

# Enforcement-layer paths: agents must never rewrite their own hooks,
# agent definitions, instructions, or top-level Copilot instructions during
# any stage. Self-modification of these defeats the entire stage machine.
# Updates come from humans (`copier update` or explicit unblock), never
# from the autonomous loop.
PROTECTED_PATH_PREFIXES = (
    ".github/hooks/scripts/",
    ".github/agents/",
    ".github/instructions/",
)

PROTECTED_EXACT_PATHS = {
    ".github/copilot-instructions.md",
    "AGENTS.md",
}

# Writes to state.md are heavily restricted outside `bootstrap`. The legitimate
# writers are:
#   (a) BOOTSTRAP.md during bootstrap (carve-out below covers it),
#   (b) hook helpers `write-test-evidence.py`, `write-commit-evidence.py`,
#       `write-plan-evidence.py`, `write-stage.py`, `write-phase.py`, and
#       `record-verdict.py`,
#   (c) other hooks calling `_state_io.update_state_field(s)` directly,
#   (d) line-shape `replace_string_in_file` / `multi_replace_string_in_file`
#       edits that touch a single `- **Field**: value` line for a field NOT
#       in `STATE_HELPER_REQUIRED_FIELDS` (see `_check_state_md_edit`).
#
# The line-shape carve-out exists because the threat model is narrow:
# forging `Stage: bootstrap` (or its coupled fields) would unlock the
# enforcement-layer carve-out and let an agent rewrite hooks/agents/instructions.
# Other fields are just data the hooks read; mis-writing them mis-routes the
# next prompt at worst, which the next session will catch. Helpers stay
# mandatory only where the threat or the cross-field invariant is real.
#
# `create_file` against state.md remains blocked unconditionally outside
# bootstrap — it would replace the whole file and bypass the line-shape check.
#
# CURRENT-STATE.md is intentionally NOT protected here — it is narrative
# and agents append to it (Context, Proposed Improvements, Vision Pivots,
# Active Session link).
PROTECTED_STATE_FILES = {
    "roadmap/state.md",
}

# Fields whose writes MUST go through a sanctioned helper. Stage and its
# coupled fields are gated because forging Stage=bootstrap unlocks the
# enforcement-layer carve-out, and because (Stage, Blocked Kind, Blocked
# Reason) carry a cross-field invariant that `write-stage.py` enforces.
STATE_HELPER_REQUIRED_FIELDS = {
    "Stage",
    "Blocked Kind",
    "Blocked Reason",
}

# Matches a single `- **Field**: value` line (no surrounding context). Used by
# the line-shape carve-out to verify that an edit is targeting one machine
# field, not arbitrary file content. Anchored to the whole string and explicit
# about no embedded newlines so multi-line strings (which could smuggle a
# Stage change inside) fail the match.
_STATE_LINE_RE = re.compile(
    r"\A\s*-\s+\*\*(?P<field>[^*\n]+)\*\*:\s*(?P<value>[^\n]*?)\s*\Z",
)

DANGEROUS_TERMINAL_PATTERNS = [
    (
        re.compile(r"\bgit\s+push\s+(?:-f(?![a-zA-Z])|--force(?![a-zA-Z-]))"),
        "git push --force",
        "destructive git push. Use --force-with-lease if you must rewrite a remote branch.",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b"),
        "git reset --hard",
        "discards uncommitted work irreversibly.",
    ),
    (
        re.compile(r"\bgit\s+clean\s+-[a-z]*[fd][a-z]*\b"),
        "git clean -fd",
        "deletes untracked files, including in-progress work.",
    ),
    (
        re.compile(r"\bgit\s+filter-branch\b"),
        "git filter-branch",
        "rewrites history across the repo. Use git-filter-repo under human direction instead.",
    ),
    (
        re.compile(r"\bgit\s+update-ref\s+-d\b"),
        "git update-ref -d",
        "deletes refs directly, bypassing normal branch/tag semantics.",
    ),
    (
        re.compile(r"\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+(?:/|~|\$HOME|\$\{HOME\})(?:\s|$|/)"),
        "rm -rf on /, ~, or $HOME",
        "recursive delete of root or home directory.",
    ),
    (
        re.compile(r"\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+(?:\.git|node_modules|/\*)(?:\s|$|/)"),
        "rm -rf on .git, node_modules, or /*",
        "would destroy repo state or globs outside workspace.",
    ),
    (
        re.compile(r"(?:curl|wget)\s[^|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh|python3?|node|ruby|perl)\b"),
        "curl|wget piped to interpreter",
        "remote-code-execution pattern. Download the script, audit it, then run it.",
    ),
    (
        re.compile(r"\bdd\b[^|]*\bof=/dev/"),
        "dd of=/dev/...",
        "raw-device write; a typo here destroys disks.",
    ),
    (
        re.compile(r"\bnpm\s+(?:install|i|add)\b[^|&;]*--force\b"),
        "npm install --force",
        "overwrites peer-dependency safety. Pin versions or resolve the conflict instead.",
    ),
    (
        re.compile(r"\bpip\s+install\b[^|&;]*--break-system-packages\b"),
        "pip install --break-system-packages",
        "mutates the system Python. Use a venv.",
    ),
    (
        re.compile(r":\(\)\s*\{.*\};:"),
        "fork bomb",
        "denial-of-service pattern.",
    ),
    (
        re.compile(r"\bchmod\s+-R\s+777\s+/(?:\s|$)"),
        "chmod -R 777 /",
        "opens permissions on the entire filesystem.",
    ),
    (
        re.compile(
            r"\b(?:rm|mv|shred|unlink)\b[^|&;]*"
            r"\broadmap/(?:state|CURRENT-STATE)\.md\b"
        ),
        "rm/mv on roadmap/state.md or roadmap/CURRENT-STATE.md",
        (
            "deleting state.md bypasses the stage machine — the bootstrap "
            "carve-out in tool-guardrails treats an absent state.md as a "
            "fresh workspace, which would unlock enforcement-layer paths. "
            "If the file really needs to be reset, get human approval."
        ),
    ),
]


def check_terminal_command(tool_input):
    command = tool_input.get("command", "") or tool_input.get("input", "")
    if not command:
        return None
    for pattern, label, explanation in DANGEROUS_TERMINAL_PATTERNS:
        if pattern.search(command):
            return (
                f"Blocked: '{label}' - {explanation} "
                "If this is genuinely needed, get human approval and run it yourself."
            )
    return None


def _is_bootstrap_stage(cwd):
    """Return True when state.md is absent OR Stage is `bootstrap`.

    Bootstrap is the only stage where the builder may legitimately write to
    enforcement-layer paths — catalog activation copies files into
    `.github/agents/` from `.github/catalog/`. Every other stage remains
    locked.

    Delegates to the shared `_state_io.is_bootstrap_stage` so branch-gate
    and tool-guardrails agree on the carve-out semantics. Fails closed if
    the helper is unavailable.
    """
    if _shared_is_bootstrap_stage is None:
        return False
    return _shared_is_bootstrap_stage(cwd)


def _normalize(path, cwd=None):
    if not path:
        return ""
    if cwd and os.path.isabs(path):
        try:
            path = os.path.relpath(path, cwd)
        except ValueError:
            return path.replace("\\", "/")
    return os.path.normpath(path).replace("\\", "/")


def _is_protected_path(rel_path):
    if not rel_path:
        return False
    if rel_path in PROTECTED_EXACT_PATHS:
        return True
    return any(rel_path.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES)


def _check_state_md_edit(tool_name, tool_input, rel, cwd=None):
    """Apply the line-shape carve-out for edits against `roadmap/state.md`.

    Returns a denial string if the edit must be blocked, or None to allow.

    The carve-out:
      - `create_file` against state.md is always blocked outside bootstrap
        (would replace the whole file and bypass the line-shape check).
      - `replace_string_in_file` and `multi_replace_string_in_file` are
        allowed iff every (oldString, newString) pair targets a single
        `- **Field**: value` line for the same field, AND that field is NOT
        in `STATE_HELPER_REQUIRED_FIELDS` (Stage / Blocked Kind /
        Blocked Reason must go through `write-stage.py`).

    Rationale: the threat model that justifies blocking direct edits is
    forging Stage=bootstrap to unlock the enforcement-layer carve-out.
    Other fields are just data; helpers exist for them where validation or
    cross-field invariants are valuable, but agents can also edit them
    directly via line-shape replacements when terminal access is gated.
    """
    if tool_name == "create_file":
        return (
            f"Blocked: 'create_file' against '{rel}' would overwrite workflow "
            "state. Use the line-shape `replace_string_in_file` carve-out or "
            "the helpers in `.github/hooks/scripts/write-*.py`."
        )

    edits = []
    if tool_name == "replace_string_in_file":
        old = tool_input.get("oldString") or tool_input.get("old_string") or ""
        new = tool_input.get("newString") or tool_input.get("new_string") or ""
        edits.append((old, new))
    elif tool_name == "multi_replace_string_in_file":
        for r in tool_input.get("replacements") or []:
            if not isinstance(r, dict):
                continue
            # Only the entries actually targeting state.md count; the helper
            # path-collector flagged the call because at least one did.
            # Normalize the same way `check_file_operation` does so an
            # obfuscated path like `./roadmap/state.md` cannot bypass the
            # match (which would leave `edits` empty and falsely allow).
            target = r.get("filePath") or r.get("file_path") or ""
            if not target:
                continue
            target_rel = _normalize(target, cwd)
            if target_rel != rel:
                continue
            old = r.get("oldString") or r.get("old_string") or ""
            new = r.get("newString") or r.get("new_string") or ""
            edits.append((old, new))
    else:
        # Unknown edit tool against state.md — be conservative.
        return (
            f"Blocked: tool '{tool_name}' may not write '{rel}'. Use a "
            "sanctioned helper under `.github/hooks/scripts/write-*.py` or a "
            "single-line `replace_string_in_file` edit."
        )

    if not edits:
        return None

    for old, new in edits:
        old_match = _STATE_LINE_RE.match(old or "")
        new_match = _STATE_LINE_RE.match(new or "")
        if not old_match or not new_match:
            return (
                f"Blocked: edit to '{rel}' is not a single-line "
                "`- **Field**: value` change. Multi-line edits to state.md "
                "must go through a sanctioned helper "
                "(`.github/hooks/scripts/write-*.py`)."
            )
        old_field = old_match.group("field").strip()
        new_field = new_match.group("field").strip()
        if old_field != new_field:
            return (
                f"Blocked: edit to '{rel}' rewrites field name "
                f"('{old_field}' -> '{new_field}'). Field renames require "
                "a copier update, not a runtime edit."
            )
        if old_field in STATE_HELPER_REQUIRED_FIELDS:
            return (
                f"Blocked: '{old_field}' must be written via "
                "`.github/hooks/scripts/write-stage.py` (it enforces the "
                "Stage / Blocked Kind invariant and is the gate against "
                "forging `Stage: bootstrap` to unlock the enforcement-layer "
                "carve-out)."
            )
    return None


def _collect_paths(tool_input, tool_name):
    """Return all candidate target paths for an edit tool, including every
    entry in `multi_replace_string_in_file`'s `replacements` array."""
    paths = []
    primary = (
        tool_input.get("filePath")
        or tool_input.get("file_path")
        or tool_input.get("path")
        or ""
    )
    if primary:
        paths.append(primary)
    if tool_name == "multi_replace_string_in_file":
        for r in tool_input.get("replacements") or []:
            if isinstance(r, dict):
                p = r.get("filePath") or r.get("file_path") or ""
                if p:
                    paths.append(p)
    return paths


def check_file_operation(tool_input, tool_name, cwd=None):
    paths = _collect_paths(tool_input, tool_name)
    if not paths:
        return None

    bootstrap = _is_bootstrap_stage(cwd)

    for raw in paths:
        # Path-traversal must be checked against the RAW input, before
        # `os.path.normpath` collapses `foo/../..` and silently eats the
        # `..` segments. Anything containing a `..` segment is rejected.
        raw_norm = (raw or "").replace("\\", "/")
        if ".." in raw_norm.split("/"):
            return f"Blocked: Path traversal detected in '{raw}'. Use absolute or clean relative paths."
        # CR-3: when `cwd` is missing we cannot resolve absolute paths
        # against the workspace, so we cannot apply the enforcement-layer
        # carve-out safely. Refuse absolute paths in that case.
        if not cwd and os.path.isabs(raw_norm):
            return (
                f"Blocked: Absolute path '{raw}' supplied without `cwd` in the "
                "hook payload — cannot validate against workspace boundaries."
            )
        rel = _normalize(raw, cwd)
        if "node_modules/" in rel or "node_modules\\" in raw:
            return "Blocked: Cannot modify files inside node_modules/. Use package manager commands instead."
        if rel in PROTECTED_STATE_FILES and not bootstrap:
            denial = _check_state_md_edit(tool_name, tool_input, rel, cwd)
            if denial is not None:
                return denial
        if _is_protected_path(rel) and not bootstrap:
            return (
                f"Blocked: '{rel}' is part of the enforcement layer (hooks, agents, "
                "instructions, or copilot-instructions.md). Agents must not rewrite "
                "their own enforcement outside the `bootstrap` stage. Updates come "
                "from humans via `copier update` or an explicit unblock."
            )
        basename = os.path.basename(rel)
        if "delete" in tool_name.lower() and basename in PROTECTED_FILES:
            return f"Blocked: Cannot delete critical file '{basename}'. This requires human approval."
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
    tool_input = input_data.get("tool_input", {}) or {}
    cwd = input_data.get("cwd")

    reason = None
    if tool_name in TERMINAL_TOOLS:
        reason = check_terminal_command(tool_input)
    elif tool_name in FILE_TOOLS:
        reason = check_file_operation(tool_input, tool_name, cwd=cwd)

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
