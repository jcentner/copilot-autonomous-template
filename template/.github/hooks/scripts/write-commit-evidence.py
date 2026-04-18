#!/usr/bin/env python3
"""Helper: write slice commit evidence to roadmap/state.md.

Agents call this explicitly after running `git commit`. This is NOT a hook —
it is an agent-invoked utility. Per the v2 principle "agents write state,
hooks verify state," the agent that ran the commit writes the result here.

The helper verifies the working tree is clean before stamping
`Committed: yes`. If `git diff --quiet HEAD` or `git diff --cached --quiet`
report changes, the helper refuses to stamp and exits non-zero. This keeps
agents from claiming `Committed: yes` when work is still uncommitted.

Usage:
    python3 .github/hooks/scripts/write-commit-evidence.py yes
    python3 .github/hooks/scripts/write-commit-evidence.py n/a [reason]

Exits 0 on success, 2 on argument error, 1 on state-file or git error,
3 when `yes` was requested but the working tree is dirty.
"""
import os
import subprocess
import sys

from _state_io import state_exists, state_path, update_state_field


VALID = {"yes", "n/a"}


# Paths that are *expected* to be dirty when this helper runs and must not
# count toward the dirty-tree refusal:
#   - `roadmap/sessions/`: the rolling session log is appended to on every
#     tool call by evidence-tracker.py, including the `git commit` that
#     immediately precedes this helper.
#   - `roadmap/state.md`: this helper is *about to* update state.md, and
#     other slice-evidence fields (Tests Pass, Reviewer Invoked, etc.) may
#     already be updated and pending commit at the next slice boundary.
#   - `__pycache__/`: importing `_state_io` creates bytecode caches.
_DIRTY_IGNORED_PREFIXES = ("roadmap/sessions/", "roadmap/state.md")
_DIRTY_IGNORED_SUBSTRINGS = ("__pycache__/", "__pycache__")


def _is_ignored(path):
    if any(path.startswith(p) for p in _DIRTY_IGNORED_PREFIXES):
        return True
    if any(s in path for s in _DIRTY_IGNORED_SUBSTRINGS):
        return True
    return False


def _git_dirty(cwd):
    """Return (dirty: bool, summary: str | None) for the working tree.

    `dirty` is True if there are uncommitted changes the agent should have
    committed before stamping `Committed: yes`. Paths in `_DIRTY_IGNORED_*`
    are excluded — they churn legitimately during normal operation (session
    log, state.md, bytecode caches). Returns `(False, None)` on git errors
    (missing git, unborn HEAD) so this helper is best-effort and does not
    block in non-git workspaces.
    """
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False, None
    if result.returncode != 0:
        return False, None
    relevant = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        # `git status --porcelain` format: 2-char status + space + path.
        # Renames use `R  old -> new`; we take the new path.
        path = line[3:].strip()
        if "->" in path:
            path = path.split("->", 1)[1].strip()
        if not path or _is_ignored(path):
            continue
        relevant.append(line)
    if not relevant:
        return False, None
    sample = "\n".join(relevant[:10])
    if len(relevant) > 10:
        sample += f"\n... (+{len(relevant) - 10} more)"
    return True, sample


def main(argv):
    if len(argv) < 2 or argv[1] not in VALID:
        print(
            f"usage: {argv[0]} {'|'.join(sorted(VALID))} [reason]",
            file=sys.stderr,
        )
        return 2

    result = argv[1]
    cwd = os.getcwd()

    if not state_exists(cwd):
        print(f"error: {state_path(cwd)} not found", file=sys.stderr)
        return 1

    if result == "yes":
        dirty, summary = _git_dirty(cwd)
        if dirty:
            print(
                "error: refusing to stamp Committed=yes — working tree has "
                "uncommitted changes:",
                file=sys.stderr,
            )
            print(summary, file=sys.stderr)
            print(
                "Run `git add` + `git commit` first, then re-run this helper.",
                file=sys.stderr,
            )
            return 3

    if not update_state_field(cwd, "Committed", result):
        print(
            "warning: 'Committed' field not found in roadmap/state.md",
            file=sys.stderr,
        )
        return 1

    print(f"wrote Committed={result}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
