"""Unit tests for write-phase.py helper."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

from _helpers import HOOK_DIR, make_state


HELPER = HOOK_DIR / "write-phase.py"


def run_helper(args, cwd):
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
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


class WritePhaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        # Pre-populate with a non-default phase + slice evidence so we can
        # observe the reset.
        make_state(
            self.tmp,
            stage="executing",
            tests_written="yes",
            tests_pass="yes",
            reviewer_invoked="yes",
            review_verdict="pass",
            critical=2,
            major=5,
            committed="yes",
            active_slice=3,
        )
        self.state = self.tmp / "roadmap" / "state.md"
        # Stamp Phase + Title so we can confirm we don't accidentally clobber.
        text = (
            self.state.read_text()
            .replace("- **Phase**: 1", "- **Phase**: 4")
            .replace("- **Phase Title**: Test", "- **Phase Title**: Old Title")
        )
        self.state.write_text(text)

    def tearDown(self):
        self._tmp.cleanup()

    # --- argument validation -------------------------------------------------

    def test_no_args_exits_2(self):
        result = run_helper([], self.tmp)
        self.assertEqual(result.returncode, 2)
        self.assertIn("at least one", result.stderr.lower())

    def test_non_integer_number_rejected(self):
        result = run_helper(["--number", "many"], self.tmp)
        self.assertEqual(result.returncode, 2)

    def test_negative_number_rejected(self):
        result = run_helper(["--number", "-1"], self.tmp)
        self.assertEqual(result.returncode, 2)

    # --- single-field updates -----------------------------------------------

    def test_set_number_only(self):
        result = run_helper(["--number", "5"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Phase"), "5")
        # Title untouched.
        self.assertEqual(read_field(self.state, "Phase Title"), "Old Title")

    def test_set_title_only(self):
        result = run_helper(["--title", "New Title"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Phase Title"), "New Title")
        self.assertEqual(read_field(self.state, "Phase"), "4")

    def test_clear_title_with_empty_string(self):
        result = run_helper(["--title", ""], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Phase Title"), "")

    def test_set_number_and_title(self):
        result = run_helper(
            ["--number", "5", "--title", "User Auth"], self.tmp
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Phase"), "5")
        self.assertEqual(read_field(self.state, "Phase Title"), "User Auth")

    # --- reset-evidence ------------------------------------------------------

    def test_reset_evidence_clears_slice_fields(self):
        result = run_helper(["--reset-evidence"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # Slice evidence should be back to defaults.
        self.assertEqual(read_field(self.state, "Tests Written"), "n/a")
        self.assertEqual(read_field(self.state, "Tests Pass"), "n/a")
        self.assertEqual(read_field(self.state, "Reviewer Invoked"), "n/a")
        self.assertEqual(read_field(self.state, "Review Verdict"), "n/a")
        self.assertEqual(read_field(self.state, "Critical Findings"), "0")
        self.assertEqual(read_field(self.state, "Major Findings"), "0")
        self.assertEqual(read_field(self.state, "Strategic Review"), "n/a")
        self.assertEqual(read_field(self.state, "Committed"), "n/a")
        self.assertEqual(read_field(self.state, "Active Slice"), "n/a")
        self.assertEqual(read_field(self.state, "Slice Total"), "n/a")
        self.assertEqual(read_field(self.state, "Design Status"), "n/a")
        self.assertEqual(read_field(self.state, "Implementation Status"), "n/a")
        self.assertEqual(read_field(self.state, "Design Critique Rounds"), "0")
        self.assertEqual(
            read_field(self.state, "Implementation Critique Rounds"), "0"
        )
        # Phase + Title untouched (unless caller asked).
        self.assertEqual(read_field(self.state, "Phase"), "4")
        self.assertEqual(read_field(self.state, "Phase Title"), "Old Title")

    def test_reset_evidence_with_phase_increment(self):
        # Real use case: vision-expand mid-phase pivot.
        result = run_helper(
            ["--number", "5", "--title", "", "--reset-evidence"], self.tmp
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Phase"), "5")
        self.assertEqual(read_field(self.state, "Phase Title"), "")
        self.assertEqual(read_field(self.state, "Tests Pass"), "n/a")

    # --- state file presence -------------------------------------------------

    def test_missing_state_md_exits_1(self):
        empty = pathlib.Path(tempfile.mkdtemp())
        try:
            result = run_helper(["--number", "1"], empty)
            self.assertEqual(result.returncode, 1)
        finally:
            import shutil

            shutil.rmtree(empty)


if __name__ == "__main__":
    unittest.main()
