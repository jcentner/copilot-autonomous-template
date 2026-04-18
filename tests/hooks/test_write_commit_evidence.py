"""Unit tests for write-commit-evidence.py helper."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

from _helpers import HOOK_DIR, make_state


HELPER = HOOK_DIR / "write-commit-evidence.py"


def run_helper(arg, cwd):
    return subprocess.run(
        [sys.executable, str(HELPER), arg],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=10,
    )


def read_field(state_path, field):
    for line in state_path.read_text().splitlines():
        marker = f"- **{field}**:"
        if line.strip().startswith(marker):
            return line.split(":", 1)[1].strip()
    return None


class WriteCommitEvidenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        # Initialise git so dirty-tree detection works.
        for cmd in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@t"],
            ["git", "config", "user.name", "t"],
        ):
            subprocess.run(cmd, cwd=self.tmp, check=True)
        (self.tmp / "README.md").write_text("seed\n")
        # Pre-track the scripts directory so __pycache__/ shows up as a
        # distinct untracked path, not collapsed under `?? .github/`.
        scripts_dir = self.tmp / ".github" / "hooks" / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / ".gitkeep").write_text("")
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed"], cwd=self.tmp, check=True
        )
        make_state(self.tmp, committed="pending")
        # Commit state.md so it's not itself "uncommitted".
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "state"], cwd=self.tmp, check=True
        )
        self.state = self.tmp / "roadmap" / "state.md"

    def tearDown(self):
        self._tmp.cleanup()

    def test_invalid_arg_exits_2(self):
        result = run_helper("maybe", self.tmp)
        self.assertEqual(result.returncode, 2)

    def test_clean_tree_yes_stamps_committed(self):
        result = run_helper("yes", self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Committed"), "yes")

    def test_dirty_tree_yes_refuses_and_exits_3(self):
        # Create an uncommitted change to a *non-ignored* path.
        (self.tmp / "app.py").write_text("feature\n")
        result = run_helper("yes", self.tmp)
        self.assertEqual(result.returncode, 3)
        # Field must NOT have been updated.
        self.assertEqual(read_field(self.state, "Committed"), "pending")
        self.assertIn("uncommitted", result.stderr.lower())

    def test_session_log_dirty_does_not_refuse(self):
        # The rolling session log is appended to by evidence-tracker.py on
        # every tool call — including the `git commit` that just landed.
        # The helper must not refuse on session-log-only churn.
        sessions = self.tmp / "roadmap" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "abc.md").write_text("[ts] log line\n")
        result = run_helper("yes", self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Committed"), "yes")

    def test_pycache_dirty_does_not_refuse(self):
        # Importing _state_io creates __pycache__/. That cache is the
        # helper's own footprint; refusing on it would make the helper
        # unusable in real workflows.
        cache = self.tmp / ".github" / "hooks" / "scripts" / "__pycache__"
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "_state_io.cpython-312.pyc").write_bytes(b"\x00\x00")
        result = run_helper("yes", self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Committed"), "yes")

    def test_state_md_dirty_does_not_refuse(self):
        # The agent typically updates other Slice Evidence fields (Tests
        # Pass, Reviewer Invoked, etc.) before calling this helper. state.md
        # is therefore expected to be dirty when the helper runs; refusing
        # on it would create a chicken-and-egg.
        self.state.write_text(self.state.read_text() + "\n<!-- mid-update -->\n")
        result = run_helper("yes", self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Committed"), "yes")

    def test_mixed_ignored_and_real_dirty_still_refuses(self):
        # If a real source file is uncommitted alongside ignored paths, the
        # helper still refuses — we filter, we don't whitelist-everything.
        sessions = self.tmp / "roadmap" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "abc.md").write_text("log\n")
        (self.tmp / "app.py").write_text("uncommitted feature\n")
        result = run_helper("yes", self.tmp)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(read_field(self.state, "Committed"), "pending")

    def test_na_always_stamps_even_when_dirty(self):
        # `n/a` is a deliberate declaration; the helper trusts it. (Use
        # sparingly — for slices that legitimately produce no commit.)
        (self.tmp / "app.py").write_text("dirty\n")
        result = run_helper("n/a", self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Committed"), "n/a")

    def test_missing_state_file_exits_1(self):
        # Wipe state.md before invoking.
        self.state.unlink()
        result = run_helper("yes", self.tmp)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
