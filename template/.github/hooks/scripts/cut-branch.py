#!/usr/bin/env python3
"""Helper: cut a workflow branch in the canonical pattern.

The autonomous workflow uses two branch shapes:

  * `strategy/YYYYMMDD` — short-lived branch off `main` between merge and
    next phase pick. Cut at end of bootstrap and on `/resume` post-merge.
  * `phase/N-<kebab-title>` — phase work branch. Cut on strategy approval
    (inline pick or `/resume awaiting-strategy-approval`).

Without this helper agents had to manually `git checkout`, with subtle
edge cases (a stale `phase/*` checkout would seed the next phase with
abandoned commits; running while dirty would silently fail). Centralising
the operation:

  * Refuses to run with a dirty working tree (the new branch would carry
    uncommitted noise).
  * If currently on a `phase/*` branch and asked to cut a new phase or
    strategy branch, switches to `main` first so the new branch is cut
    from the right base.
  * For strategy branches, optionally pulls `main` (--pull) so the cut
    is from the latest merged state. Skipped silently if no `origin`.
  * Idempotent: if the target branch already exists locally, checks it
    out instead of failing — re-running after a partial transition is
    safe.

Usage:
    python3 .github/hooks/scripts/cut-branch.py strategy
    python3 .github/hooks/scripts/cut-branch.py strategy --pull
    python3 .github/hooks/scripts/cut-branch.py phase --number 2 --title "Drive Integration"

Exits 0 on success, 1 on git/state error, 2 on argument error, 3 on
dirty-tree refusal.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys


PHASE_BRANCH_RE = re.compile(r"^phase/")
TRUNK_BRANCH_NAMES = {"main", "master", "trunk"}


def die(msg: str, code: int = 1) -> None:
    sys.stderr.write(f"cut-branch: {msg}\n")
    sys.exit(code)


def run(cmd, check=True, capture=True):
    """Run a git command; return (returncode, stdout)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        die(f"failed to run {' '.join(cmd)}: {exc}")
    if check and result.returncode != 0:
        die(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result.returncode, (result.stdout or "").strip()


def current_branch() -> str:
    _, out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not out or out == "HEAD":
        die("detached HEAD or not in a git repo")
    return out


def is_clean() -> bool:
    _, out = run(["git", "status", "--porcelain"])
    return out == ""


def trunk_branch() -> str:
    """Detect the trunk branch name. Falls back to `main`."""
    for name in ("main", "master", "trunk"):
        rc, _ = run(["git", "rev-parse", "--verify", name], check=False)
        if rc == 0:
            return name
    return "main"


def branch_exists(name: str) -> bool:
    rc, _ = run(["git", "rev-parse", "--verify", name], check=False)
    return rc == 0


def kebab(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9\s-]+", "", text or "").strip().lower()
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text or "untitled"


def cut_strategy(pull: bool) -> str:
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    target = f"strategy/{today}"
    trunk = trunk_branch()

    if not is_clean():
        die(
            "working tree is dirty — commit or stash before cutting a "
            "strategy branch.",
            code=3,
        )

    cur = current_branch()
    if cur != trunk:
        run(["git", "checkout", trunk])
    if pull:
        # Best-effort; ignore if no remote configured.
        rc, _ = run(["git", "remote", "get-url", "origin"], check=False)
        if rc == 0:
            run(["git", "pull", "--ff-only"], check=False)

    if branch_exists(target):
        run(["git", "checkout", target])
    else:
        run(["git", "checkout", "-b", target])
    return target


def cut_phase(number: int, title: str) -> str:
    if number < 1:
        die(f"--number must be >= 1, got {number}", code=2)
    if not title:
        die("--title is required for phase branches", code=2)
    target = f"phase/{number}-{kebab(title)}"

    if not is_clean():
        die(
            "working tree is dirty — commit or stash before cutting a "
            "phase branch.",
            code=3,
        )

    cur = current_branch()
    trunk = trunk_branch()
    # If on an old phase branch (e.g., post-/scrap-phase), get to trunk first
    # so the new phase branch isn't cut from abandoned commits.
    if PHASE_BRANCH_RE.match(cur):
        run(["git", "checkout", trunk])

    if branch_exists(target):
        run(["git", "checkout", target])
    else:
        run(["git", "checkout", "-b", target])
    return target


def main(argv) -> int:
    parser = argparse.ArgumentParser(
        prog="cut-branch.py",
        description="Cut the canonical workflow branch (strategy or phase).",
    )
    sub = parser.add_subparsers(dest="kind", required=True)

    strat = sub.add_parser("strategy", help="cut strategy/<UTC-date> off trunk")
    strat.add_argument(
        "--pull",
        action="store_true",
        help="git pull --ff-only on trunk before cutting (best-effort, "
        "skipped if no origin)",
    )

    phase = sub.add_parser("phase", help="cut phase/<N>-<title> off current branch")
    phase.add_argument("--number", type=int, required=True)
    phase.add_argument("--title", required=True)

    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    # Verify we're in a git repo.
    rc, _ = run(["git", "rev-parse", "--git-dir"], check=False)
    if rc != 0:
        die("not a git repo (or git not on PATH)", code=1)

    if args.kind == "strategy":
        target = cut_strategy(pull=args.pull)
    else:
        target = cut_phase(number=args.number, title=args.title)

    sys.stdout.write(f"cut-branch: on {target}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
