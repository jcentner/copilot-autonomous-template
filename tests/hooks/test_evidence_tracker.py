"""Unit tests for evidence-tracker.py and write-test-evidence.py.

evidence-tracker is a per-session log writer — it does NOT mutate state.md
fields. write-test-evidence is the agent-invoked helper that writes
Tests Written / Tests Pass to state.md.
"""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

from _helpers import HOOK_DIR, make_state, run_hook


class EvidenceTrackerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(self.tmp, tests_written="n/a", tests_pass="n/a")
        self.state_file = self.tmp / "roadmap" / "state.md"
        self.narrative_file = self.tmp / "roadmap" / "CURRENT-STATE.md"
        self.sessions_dir = self.tmp / "roadmap" / "sessions"

    def tearDown(self):
        self._tmp.cleanup()

    def _post(self, tool_name, tool_input=None, tool_response=None, session_id="sess-1"):
        rc, out, _ = run_hook(
            "evidence-tracker.py",
            {
                "cwd": str(self.tmp),
                "sessionId": session_id,
                "tool_name": tool_name,
                "tool_input": tool_input or {},
                "tool_response": tool_response,
            },
            cwd=self.tmp,
        )
        self.assertEqual(rc, 0)
        return out

    def _session_log(self, session_id="sess-1"):
        path = self.sessions_dir / f"{session_id}.md"
        return path.read_text() if path.exists() else ""

    # --- State.md is never touched ---

    def test_does_not_mutate_state_md(self):
        before = self.state_file.read_text()
        self._post("create_file", {"filePath": "src/x.py"})
        self._post("run_in_terminal", {"command": "pytest"}, "5 passed")
        self._post(
            "run_in_terminal", {"command": "pytest"}, "FAILED test_x"
        )
        after = self.state_file.read_text()
        self.assertEqual(before, after)

    def test_does_not_infer_test_results(self):
        self._post("run_in_terminal", {"command": "pytest -q"}, "5 passed")
        content = self.state_file.read_text()
        self.assertIn("**Tests Written**: n/a", content)
        self.assertIn("**Tests Pass**: n/a", content)

    # --- Per-session log writes ---

    def test_creates_per_session_log_on_first_call(self):
        self._post("create_file", {"filePath": "src/x.py"})
        log = self._session_log()
        self.assertIn("create_file", log)
        self.assertIn("src/x.py", log)

    def test_appends_in_order(self):
        self._post("create_file", {"filePath": "src/a.py"})
        self._post("create_file", {"filePath": "src/b.py"})
        log = self._session_log()
        self.assertEqual(log.count("create_file"), 2)
        a_idx = log.find("src/a.py")
        b_idx = log.find("src/b.py")
        self.assertLess(a_idx, b_idx)

    def test_terminal_command_logged(self):
        self._post("run_in_terminal", {"command": "npm test"}, "tests pass")
        log = self._session_log()
        self.assertIn("run_in_terminal", log)
        self.assertIn("npm test", log)

    def test_distinct_sessions_separate_files(self):
        self._post("create_file", {"filePath": "src/a.py"}, session_id="sess-A")
        self._post("create_file", {"filePath": "src/b.py"}, session_id="sess-B")
        a = (self.sessions_dir / "sess-A.md").read_text()
        b = (self.sessions_dir / "sess-B.md").read_text()
        self.assertIn("src/a.py", a)
        self.assertNotIn("src/b.py", a)
        self.assertIn("src/b.py", b)
        self.assertNotIn("src/a.py", b)

    def test_session_id_sanitised(self):
        # Slashes in sessionId must not escape the sessions directory.
        self._post(
            "create_file",
            {"filePath": "src/x.py"},
            session_id="../escape/attempt",
        )
        # Whatever filename was used must be inside sessions/ with no escape.
        children = list(self.sessions_dir.iterdir())
        for c in children:
            resolved = c.resolve()
            self.assertTrue(
                str(resolved).startswith(str(self.sessions_dir.resolve())),
                f"session log escaped sessions dir: {resolved}",
            )

    def test_active_session_link_updated(self):
        self._post("create_file", {"filePath": "src/x.py"}, session_id="sess-1")
        narrative = self.narrative_file.read_text()
        self.assertIn("sessions/sess-1.md", narrative)

    def test_active_session_link_idempotent(self):
        self._post("create_file", {"filePath": "src/a.py"}, session_id="sess-1")
        first = self.narrative_file.read_text()
        self._post("create_file", {"filePath": "src/b.py"}, session_id="sess-1")
        second = self.narrative_file.read_text()
        # Active session line should not duplicate.
        self.assertEqual(
            first.count("sessions/sess-1.md"),
            second.count("sessions/sess-1.md"),
        )

    # --- Edge cases ---

    def test_missing_state_exits_cleanly(self):
        (self.state_file).unlink()
        rc, out, _ = run_hook(
            "evidence-tracker.py",
            {
                "cwd": str(self.tmp),
                "tool_name": "create_file",
                "tool_input": {"filePath": "x"},
            },
            cwd=self.tmp,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, {})
        # No log file created when state.md is missing.
        self.assertFalse(self.sessions_dir.exists() and any(self.sessions_dir.iterdir()))

    def test_multi_replace_summary(self):
        self._post(
            "multi_replace_string_in_file",
            {
                "replacements": [
                    {"filePath": "a.py", "oldString": "x", "newString": "y"},
                    {"filePath": "b.py", "oldString": "x", "newString": "y"},
                ]
            },
        )
        log = self._session_log()
        self.assertIn("2 edits", log)


class WriteTestEvidenceTests(unittest.TestCase):
    """The agent-invoked helper that writes Tests Pass / Tests Written."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(self.tmp, tests_written="n/a", tests_pass="n/a")
        self.state_file = self.tmp / "roadmap" / "state.md"
        self.helper = HOOK_DIR / "write-test-evidence.py"

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, arg):
        return subprocess.run(
            [sys.executable, str(self.helper), arg],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_pass_sets_both_fields(self):
        r = self._run("pass")
        self.assertEqual(r.returncode, 0, r.stderr)
        content = self.state_file.read_text()
        self.assertIn("**Tests Written**: yes", content)
        self.assertIn("**Tests Pass**: yes", content)

    def test_fail_sets_tests_pass_no(self):
        r = self._run("fail")
        self.assertEqual(r.returncode, 0, r.stderr)
        content = self.state_file.read_text()
        self.assertIn("**Tests Written**: yes", content)
        self.assertIn("**Tests Pass**: no", content)

    def test_na_sets_both_na(self):
        make_state(self.tmp, tests_written="yes", tests_pass="yes")
        r = self._run("n/a")
        self.assertEqual(r.returncode, 0, r.stderr)
        content = self.state_file.read_text()
        self.assertIn("**Tests Written**: n/a", content)
        self.assertIn("**Tests Pass**: n/a", content)

    def test_invalid_arg_exits_nonzero(self):
        r = self._run("maybe")
        self.assertEqual(r.returncode, 2)

    def test_missing_state_exits_nonzero(self):
        self.state_file.unlink()
        r = self._run("pass")
        self.assertEqual(r.returncode, 1)

    def test_atomic_write_leaves_no_temp_files(self):
        self._run("pass")
        residue = list((self.tmp / "roadmap").glob(".state-*.tmp"))
        self.assertEqual(residue, [])

    def test_pass_stamps_evidence_for_slice(self):
        # Bug C enforcement: write-test-evidence binds the recorded result to
        # the current Active Slice so session-gate can detect stale evidence.
        make_state(self.tmp, active_slice=3, evidence_for_slice="n/a",
                   tests_written="n/a", tests_pass="n/a")
        r = self._run("pass")
        self.assertEqual(r.returncode, 0, r.stderr)
        content = self.state_file.read_text()
        self.assertIn("**Evidence For Slice**: 3", content)


if __name__ == "__main__":
    unittest.main()
