"""Unit tests for branch-gate.py (PreToolUse).

branch-gate refuses `git commit` when HEAD is on a denylisted branch. We
isolate each test in a real git repo under tmp so the hook's
`git rev-parse --abbrev-ref HEAD` call has something real to inspect.
"""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from _helpers import HOOK_DIR, run_hook, make_state


def _git(cwd, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_repo(tmp, branch="main"):
    """Init a real git repo at tmp on the given initial branch."""
    _git(tmp, "init", "-q", f"--initial-branch={branch}")
    _git(tmp, "config", "user.email", "test@example.com")
    _git(tmp, "config", "user.name", "Test")
    # One commit so HEAD resolves.
    (tmp / "README").write_text("x\n")
    _git(tmp, "add", "README")
    _git(tmp, "commit", "-q", "-m", "init")
    return tmp


def _checkout(tmp, branch):
    _git(tmp, "checkout", "-q", "-b", branch)


def _commit_payload(cwd):
    return {
        "cwd": str(cwd),
        "tool_name": "run_in_terminal",
        "tool_input": {"command": "git commit -m 'feat: x'"},
    }


def _decision(parsed):
    return parsed.get("hookSpecificOutput", {}).get("permissionDecision")


class BranchGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_non_terminal_tool_allowed(self):
        rc, out, _ = run_hook(
            "branch-gate.py",
            {
                "cwd": str(self.tmp),
                "tool_name": "create_file",
                "tool_input": {"filePath": "x.py"},
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "allow")

    def test_non_commit_terminal_command_allowed(self):
        rc, out, _ = run_hook(
            "branch-gate.py",
            {
                "cwd": str(self.tmp),
                "tool_name": "run_in_terminal",
                "tool_input": {"command": "ls -la"},
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "allow")

    def test_commit_on_main_with_state_denied(self):
        _init_repo(self.tmp, branch="main")
        # Non-bootstrap stage in state.md so carve-out doesn't apply.
        make_state(self.tmp, stage="executing")
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "deny")
        reason = out["hookSpecificOutput"].get("permissionDecisionReason", "")
        self.assertIn("main", reason)

    def test_commit_on_phase_branch_allowed(self):
        _init_repo(self.tmp, branch="main")
        _checkout(self.tmp, "phase/1-foundation")
        make_state(self.tmp, stage="executing")
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "allow")

    def test_commit_during_bootstrap_stage_allowed_on_main(self):
        # Bootstrap carve-out: state.md present, Stage: bootstrap → allow.
        _init_repo(self.tmp, branch="main")
        make_state(self.tmp, stage="bootstrap")
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "allow")

    def test_commit_with_no_state_treated_as_bootstrap(self):
        # Fresh `copier copy` workspace — no state.md yet → bootstrap carve-out.
        _init_repo(self.tmp, branch="main")
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "allow")

    def test_commit_without_git_repo_allowed(self):
        # No git repo at all — `git rev-parse` fails → conservative allow.
        make_state(self.tmp, stage="executing")
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "allow")

    def test_release_branch_pattern_denied(self):
        _init_repo(self.tmp, branch="main")
        _checkout(self.tmp, "release/2026-04")
        make_state(self.tmp, stage="executing")
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "deny")

    def test_master_in_default_denylist(self):
        _init_repo(self.tmp, branch="master")
        make_state(self.tmp, stage="executing")
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "deny")

    def test_custom_config_overrides_default(self):
        # User edited branch-policy.json to drop `main` from denylist.
        _init_repo(self.tmp, branch="main")
        make_state(self.tmp, stage="executing")
        cfg_dir = self.tmp / ".github" / "hooks" / "config"
        cfg_dir.mkdir(parents=True)
        (cfg_dir / "branch-policy.json").write_text(
            json.dumps(
                {
                    "denylist": ["never-name-a-branch-this"],
                    "denylist_patterns": [],
                    "bootstrap_exempt": True,
                }
            )
        )
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "allow")

    def test_malformed_config_falls_back_to_defaults(self):
        _init_repo(self.tmp, branch="main")
        make_state(self.tmp, stage="executing")
        cfg_dir = self.tmp / ".github" / "hooks" / "config"
        cfg_dir.mkdir(parents=True)
        (cfg_dir / "branch-policy.json").write_text("{not valid json")
        rc, out, _ = run_hook("branch-gate.py", _commit_payload(self.tmp))
        self.assertEqual(rc, 0)
        # Fallback default has `main` in denylist → still denies.
        self.assertEqual(_decision(out), "deny")

    def test_commit_tree_porcelain_not_matched(self):
        # `git commit-tree` is plumbing, not the porcelain `git commit` we gate.
        _init_repo(self.tmp, branch="main")
        make_state(self.tmp, stage="executing")
        rc, out, _ = run_hook(
            "branch-gate.py",
            {
                "cwd": str(self.tmp),
                "tool_name": "run_in_terminal",
                "tool_input": {"command": "git commit-tree HEAD^{tree}"},
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out), "allow")


if __name__ == "__main__":
    unittest.main()
