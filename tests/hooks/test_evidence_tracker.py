"""Unit tests for evidence-tracker.py (PostToolUse)."""
import pathlib
import tempfile
import unittest

from _helpers import run_hook, make_state


class EvidenceTrackerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(self.tmp, tests_written="n/a", tests_pass="n/a")
        self.state_file = self.tmp / "roadmap" / "CURRENT-STATE.md"

    def tearDown(self):
        self._tmp.cleanup()

    def _post(self, tool_name, tool_input=None, tool_response=None):
        rc, out, _ = run_hook(
            "evidence-tracker.py",
            {
                "cwd": str(self.tmp),
                "tool_name": tool_name,
                "tool_input": tool_input or {},
                "tool_response": tool_response,
            },
            cwd=self.tmp,
        )
        self.assertEqual(rc, 0)
        return out

    def test_logs_non_test_commands(self):
        self._post("create_file", {"filePath": "src/x.py"})
        content = self.state_file.read_text()
        self.assertIn("create_file", content)
        # Should not touch Tests Written.
        self.assertIn("**Tests Written**: n/a", content)

    def test_pytest_pass_updates_fields(self):
        self._post(
            "run_in_terminal",
            {"command": "pytest -q"},
            "=== 5 passed in 0.12s ===",
        )
        content = self.state_file.read_text()
        self.assertIn("**Tests Written**: yes", content)
        self.assertIn("**Tests Pass**: yes", content)

    def test_pytest_fail_updates_fields(self):
        self._post(
            "run_in_terminal",
            {"command": "pytest"},
            "FAILED tests/test_foo.py::test_bar\nTraceback",
        )
        content = self.state_file.read_text()
        self.assertIn("**Tests Written**: yes", content)
        self.assertIn("**Tests Pass**: no", content)

    def test_npm_test_detected(self):
        self._post(
            "run_in_terminal",
            {"command": "npm test"},
            "Tests: 12 passed",
        )
        content = self.state_file.read_text()
        self.assertIn("**Tests Pass**: yes", content)

    def test_missing_state_exits_cleanly(self):
        (self.tmp / "roadmap" / "CURRENT-STATE.md").unlink()
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

    def test_does_not_modify_review_verdict(self):
        # Prior value is whatever make_state set (default 'pass').
        before = self.state_file.read_text()
        self._post(
            "run_in_terminal",
            {"command": "pytest"},
            "passed",
        )
        after = self.state_file.read_text()
        # Extract the Review Verdict line from both.
        import re

        pattern = re.compile(r"\*\*Review Verdict\*\*:\s*(\S+)")
        self.assertEqual(pattern.search(before).group(1), pattern.search(after).group(1))

    def test_idempotent_session_log_append(self):
        self._post("create_file", {"filePath": "src/a.py"})
        self._post("create_file", {"filePath": "src/b.py"})
        content = self.state_file.read_text()
        # Two log lines under Session Log, both present.
        log_section = content.split("## Session Log", 1)[1].split("## ", 1)[0]
        self.assertEqual(log_section.count("create_file"), 2)


if __name__ == "__main__":
    unittest.main()
