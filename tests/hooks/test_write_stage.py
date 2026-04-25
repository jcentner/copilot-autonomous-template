"""Unit tests for write-stage.py helper."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

from _helpers import HOOK_DIR, make_state


HELPER = HOOK_DIR / "write-stage.py"


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


class WriteStageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(
            self.tmp,
            stage="planning",
            blocked_kind="n/a",
            next_prompt="/design-plan",
        )
        self.state = self.tmp / "roadmap" / "state.md"

    def tearDown(self):
        self._tmp.cleanup()

    # --- argument validation -------------------------------------------------

    def test_no_args_exits_2(self):
        result = run_helper([], self.tmp)
        self.assertEqual(result.returncode, 2)

    def test_invalid_stage_rejected(self):
        result = run_helper(["bogus-stage"], self.tmp)
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid stage", result.stderr.lower())

    def test_invalid_next_prompt_rejected(self):
        result = run_helper(
            ["executing", "--next-prompt", "/not-a-real-prompt"], self.tmp
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid --next-prompt", result.stderr.lower())

    # --- happy path ----------------------------------------------------------

    def test_simple_stage_change_clears_blocked_fields(self):
        # Prime with blocked-shape values to verify they get cleared.
        text = self.state.read_text().replace(
            "- **Blocked Kind**: n/a", "- **Blocked Kind**: error"
        ).replace(
            "- **Blocked Reason**: n/a", "- **Blocked Reason**: prior"
        )
        self.state.write_text(text)

        result = run_helper(["executing"], self.tmp)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Stage"), "executing")
        self.assertEqual(read_field(self.state, "Blocked Kind"), "n/a")
        self.assertEqual(read_field(self.state, "Blocked Reason"), "n/a")

    def test_next_prompt_written(self):
        result = run_helper(
            ["executing", "--next-prompt", "/implement"], self.tmp
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Next Prompt"), "/implement")

    # --- blocked invariant ---------------------------------------------------

    def test_blocked_without_kind_exits_3(self):
        result = run_helper(["blocked"], self.tmp)
        self.assertEqual(result.returncode, 3)
        self.assertIn("requires --blocked-kind", result.stderr.lower())
        # State must NOT have been mutated.
        self.assertEqual(read_field(self.state, "Stage"), "planning")

    def test_blocked_with_invalid_kind_rejected(self):
        result = run_helper(
            ["blocked", "--blocked-kind", "totally-made-up"], self.tmp
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(read_field(self.state, "Stage"), "planning")

    def test_blocked_full_transition(self):
        result = run_helper(
            [
                "blocked",
                "--blocked-kind",
                "awaiting-merge-approval",
                "--blocked-reason",
                "Phase 1 cleanup complete; awaiting /merge-phase.",
                "--next-prompt",
                "/merge-phase",
            ],
            self.tmp,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Stage"), "blocked")
        self.assertEqual(
            read_field(self.state, "Blocked Kind"), "awaiting-merge-approval"
        )
        self.assertEqual(
            read_field(self.state, "Blocked Reason"),
            "Phase 1 cleanup complete; awaiting /merge-phase.",
        )
        self.assertEqual(read_field(self.state, "Next Prompt"), "/merge-phase")

    def test_blocked_empty_reason_becomes_n_a(self):
        result = run_helper(
            [
                "blocked",
                "--blocked-kind",
                "awaiting-human-decision",
                "--blocked-reason",
                "",
            ],
            self.tmp,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(read_field(self.state, "Blocked Reason"), "n/a")

    # --- atomicity / state file ---------------------------------------------

    def test_missing_state_md_exits_1(self):
        empty = pathlib.Path(tempfile.mkdtemp())
        try:
            result = run_helper(["executing"], empty)
            self.assertEqual(result.returncode, 1)
        finally:
            import shutil

            shutil.rmtree(empty)


if __name__ == "__main__":
    unittest.main()
