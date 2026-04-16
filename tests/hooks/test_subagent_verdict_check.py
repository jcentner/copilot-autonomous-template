"""Unit tests for subagent-verdict-check.py (SubagentStop)."""
import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

from _helpers import HOOK_DIR, make_state


def run_verdict_hook(subagent, payload, cwd):
    """Run subagent-verdict-check.py with a positional arg."""
    hook_path = HOOK_DIR / "subagent-verdict-check.py"
    result = subprocess.run(
        [sys.executable, str(hook_path), subagent],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=10,
    )
    stdout = result.stdout.strip()
    parsed = json.loads(stdout) if stdout else {}
    return result.returncode, parsed, result.stderr


def is_block(parsed):
    return parsed.get("hookSpecificOutput", {}).get("decision") == "block"


class CriticVerdictTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_design_critique_non_terminal_blocks(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertEqual(rc, 0)
        self.assertTrue(is_block(out))

    def test_design_critique_approved_allows(self):
        make_state(self.tmp, stage="design-critique", design_status="approved")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_design_critique_revise_allows(self):
        make_state(self.tmp, stage="design-critique", design_status="revise")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_implementation_critique_non_terminal_blocks(self):
        make_state(
            self.tmp,
            stage="implementation-critique",
            implementation_status="in-critique",
        )
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_critic_in_other_stage_allows(self):
        make_state(self.tmp, stage="planning")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_stop_hook_active_short_circuits(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        rc, out, _ = run_verdict_hook(
            "critic",
            {"cwd": str(self.tmp), "stop_hook_active": True},
            self.tmp,
        )
        self.assertFalse(is_block(out))


class ProductOwnerVerdictTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_design_plan(self, body):
        plan = self.tmp / "roadmap" / "phases" / "phase-1-design.md"
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text(body)

    def test_review_mode_missing_strategic_blocks(self):
        make_state(self.tmp, stage="reviewing", strategic_review="pending")
        rc, out, _ = run_verdict_hook(
            "product-owner", {"cwd": str(self.tmp)}, self.tmp
        )
        self.assertTrue(is_block(out))

    def test_review_mode_pass_allows(self):
        make_state(self.tmp, stage="reviewing", strategic_review="pass")
        rc, out, _ = run_verdict_hook(
            "product-owner", {"cwd": str(self.tmp)}, self.tmp
        )
        self.assertFalse(is_block(out))

    def test_design_mode_missing_stories_blocks(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_design_plan("# Phase 1 Design\n\nNo stories here.\n")
        rc, out, _ = run_verdict_hook(
            "product-owner", {"cwd": str(self.tmp)}, self.tmp
        )
        self.assertTrue(is_block(out))

    def test_design_mode_empty_stories_section_blocks(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_design_plan(
            textwrap.dedent(
                """\
                # Phase 1 Design

                ## User Stories

                (to be populated)
                """
            )
        )
        rc, out, _ = run_verdict_hook(
            "product-owner", {"cwd": str(self.tmp)}, self.tmp
        )
        self.assertTrue(is_block(out))

    def test_design_mode_with_stories_allows(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_design_plan(
            textwrap.dedent(
                """\
                # Phase 1 Design

                ## User Stories

                - **As a** developer **I want to** do X **so that** Y.
                """
            )
        )
        rc, out, _ = run_verdict_hook(
            "product-owner", {"cwd": str(self.tmp)}, self.tmp
        )
        self.assertFalse(is_block(out))


class ReviewerVerdictTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_reviewer_not_invoked_blocks(self):
        make_state(self.tmp, reviewer_invoked="no", review_verdict="pass")
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_non_terminal_verdict_blocks(self):
        make_state(self.tmp, reviewer_invoked="yes", review_verdict="pending")
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_non_numeric_findings_blocks(self):
        # Build state manually with bad critical count.
        make_state(
            self.tmp,
            reviewer_invoked="yes",
            review_verdict="pass",
            critical="many",
        )
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_terminal_verdict_and_numeric_findings_allows(self):
        make_state(
            self.tmp,
            reviewer_invoked="yes",
            review_verdict="pass",
            critical=0,
            major=1,
        )
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_needs_fixes_verdict_allows(self):
        make_state(
            self.tmp,
            reviewer_invoked="yes",
            review_verdict="needs-fixes",
            critical=0,
            major=2,
        )
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))


class UnknownSubagentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_unknown_subagent_allows(self):
        make_state(self.tmp)
        rc, out, _ = run_verdict_hook("planner", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_missing_state_file_allows(self):
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))


if __name__ == "__main__":
    unittest.main()
