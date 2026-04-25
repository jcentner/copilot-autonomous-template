"""Unit tests for write-plan-evidence.py helper."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

from _helpers import HOOK_DIR, make_state


HELPER = HOOK_DIR / "write-plan-evidence.py"


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


class WritePlanEvidenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(
            self.tmp,
            stage="planning",
            design_status="n/a",
            implementation_status="n/a",
        )
        self.state = self.tmp / "roadmap" / "state.md"
        # Pre-write plan files so plan-path subcommands can be exercised.
        phases = self.tmp / "roadmap" / "phases"
        phases.mkdir(parents=True, exist_ok=True)
        (phases / "phase-1-design.md").write_text("# design\n")
        (phases / "phase-1-implementation.md").write_text("# impl\n")

    def tearDown(self):
        self._tmp.cleanup()

    # --- argument validation -------------------------------------------------

    def test_no_args_exits_2(self):
        result = run_helper([], self.tmp)
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stderr.lower())

    def test_unknown_subcommand_exits_2(self):
        result = run_helper(["bogus", "x"], self.tmp)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown subcommand", result.stderr.lower())

    def test_missing_value_exits_2(self):
        result = run_helper(["design-status"], self.tmp)
        self.assertEqual(result.returncode, 2)

    # --- status validation ---------------------------------------------------

    def test_design_status_draft(self):
        result = run_helper(["design-status", "draft"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Design Status"), "draft")

    def test_design_status_in_critique(self):
        result = run_helper(["design-status", "in-critique"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Design Status"), "in-critique")

    def test_design_status_invalid_rejected(self):
        result = run_helper(["design-status", "ready"], self.tmp)
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid status", result.stderr.lower())
        # Field unchanged.
        self.assertEqual(read_field(self.state, "Design Status"), "n/a")

    def test_impl_status_approved(self):
        result = run_helper(["impl-status", "approved"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Implementation Status"), "approved")

    def test_impl_status_invalid_rejected(self):
        result = run_helper(["impl-status", "DONE"], self.tmp)
        self.assertEqual(result.returncode, 2)

    # --- plan-path validation ------------------------------------------------

    def test_design_plan_existing_file(self):
        result = run_helper(
            ["design-plan", "roadmap/phases/phase-1-design.md"], self.tmp
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            read_field(self.state, "Design Plan"),
            "roadmap/phases/phase-1-design.md",
        )

    def test_design_plan_missing_file_exits_3(self):
        result = run_helper(
            ["design-plan", "roadmap/phases/phase-99-design.md"], self.tmp
        )
        self.assertEqual(result.returncode, 3)
        self.assertIn("does not exist", result.stderr.lower())

    def test_impl_plan_existing_file(self):
        result = run_helper(
            ["impl-plan", "roadmap/phases/phase-1-implementation.md"], self.tmp
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            read_field(self.state, "Implementation Plan"),
            "roadmap/phases/phase-1-implementation.md",
        )

    def test_design_plan_path_traversal_rejected(self):
        result = run_helper(["design-plan", "../escape.md"], self.tmp)
        self.assertEqual(result.returncode, 2)

    def test_design_plan_absolute_path_normalized(self):
        # Absolute paths inside the workspace are normalized to relative.
        abs_target = self.tmp / "roadmap" / "phases" / "phase-1-design.md"
        result = run_helper(["design-plan", str(abs_target)], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            read_field(self.state, "Design Plan"),
            "roadmap/phases/phase-1-design.md",
        )

    # --- slice-total validation ----------------------------------------------

    def test_slice_total_integer(self):
        result = run_helper(["slice-total", "5"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Slice Total"), "5")

    def test_slice_total_non_integer_rejected(self):
        result = run_helper(["slice-total", "many"], self.tmp)
        self.assertEqual(result.returncode, 2)

    def test_slice_total_negative_rejected(self):
        result = run_helper(["slice-total", "-1"], self.tmp)
        self.assertEqual(result.returncode, 2)

    def test_slice_total_zero_allowed(self):
        result = run_helper(["slice-total", "0"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Slice Total"), "0")

    # --- state.md presence ---------------------------------------------------

    def test_missing_state_md_exits_1(self):
        empty = pathlib.Path(tempfile.mkdtemp())
        try:
            result = run_helper(["design-status", "draft"], empty)
            self.assertEqual(result.returncode, 1)
            self.assertIn("not found", result.stderr.lower())
        finally:
            import shutil

            shutil.rmtree(empty)


if __name__ == "__main__":
    unittest.main()
