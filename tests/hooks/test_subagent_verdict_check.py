"""Unit tests for subagent-verdict-check.py (SubagentStop)."""
import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

from _helpers import HOOK_DIR, make_state, make_phase_artifact


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
    # SubagentStop output is top-level {decision, reason} per VS Code
    # Copilot hooks docs (NOT wrapped in hookSpecificOutput like Stop).
    return parsed.get("decision") == "block"


class CriticVerdictTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_critique(self, kind, round_no, body):
        return make_phase_artifact(
            self.tmp, f"phase-1-critique-{kind}-R{round_no}.md", body=body
        )

    def test_design_critique_missing_artifact_blocks(self):
        # Per Block 3 / Decision #21, critic does NOT write status anymore.
        # The hook now only checks artifact + VERDICT trailer presence.
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertEqual(rc, 0)
        self.assertTrue(is_block(out))

    def test_design_critique_artifact_with_approve_trailer_allows(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_critique("design", 1, "# critique\n\nVERDICT: approve\n")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_design_critique_artifact_with_revise_trailer_allows(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_critique("design", 1, "# critique\n\nVERDICT: revise\n")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_design_critique_artifact_missing_trailer_blocks(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_critique("design", 1, "# critique\n\nNo trailer here.\n")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_design_critique_lowercase_trailer_blocks(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_critique("design", 1, "# critique\n\nverdict: approve\n")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_design_critique_multiple_trailers_blocks(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_critique(
            "design", 1, "VERDICT: approve\n\nVERDICT: revise\n"
        )
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_implementation_critique_missing_artifact_blocks(self):
        make_state(
            self.tmp,
            stage="implementation-critique",
            implementation_status="in-critique",
        )
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_implementation_critique_with_trailer_allows(self):
        make_state(
            self.tmp,
            stage="implementation-critique",
            implementation_status="in-critique",
        )
        self._write_critique(
            "implementation", 1, "# critique\n\nVERDICT: approve\n"
        )
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_critic_uses_highest_round_artifact(self):
        # When R1 and R2 both exist, the hook validates R2 (latest).
        make_state(self.tmp, stage="design-critique", design_status="revise")
        self._write_critique("design", 1, "VERDICT: approve\n")
        # R2 has no trailer → should block even though R1 is fine.
        self._write_critique("design", 2, "# critique\n\n(no trailer)\n")
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

    def test_design_mode_na_with_reason_allows(self):
        # Phases with no user-facing surface (refactors, infra, build/CI)
        # may legitimately declare `n/a — <reason>` in the User Stories
        # section. The hook accepts this as terminal.
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_design_plan(
            textwrap.dedent(
                """\
                # Phase 1 Design

                ## User Stories

                n/a — phase replaces the internal build pipeline; no
                user-observable behavior changes.

                ## Acceptance Criteria

                - Build succeeds on CI.
                """
            )
        )
        rc, out, _ = run_verdict_hook(
            "product-owner", {"cwd": str(self.tmp)}, self.tmp
        )
        self.assertFalse(is_block(out))

    def test_design_mode_na_short_reason_blocks(self):
        # Drive-by `n/a` with a trivial reason must not pass — the agent
        # has to commit to a real justification.
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_design_plan(
            textwrap.dedent(
                """\
                # Phase 1 Design

                ## User Stories

                n/a — skip
                """
            )
        )
        rc, out, _ = run_verdict_hook(
            "product-owner", {"cwd": str(self.tmp)}, self.tmp
        )
        self.assertTrue(is_block(out))

    def test_design_mode_na_without_reason_blocks(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        self._write_design_plan(
            textwrap.dedent(
                """\
                # Phase 1 Design

                ## User Stories

                n/a
                """
            )
        )
        rc, out, _ = run_verdict_hook(
            "product-owner", {"cwd": str(self.tmp)}, self.tmp
        )
        self.assertTrue(is_block(out))


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
        make_phase_artifact(self.tmp, "phase-1-review-slice-1.md")
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
        make_phase_artifact(self.tmp, "phase-1-review-slice-1.md")
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_missing_review_artifact_blocks(self):
        make_state(
            self.tmp,
            reviewer_invoked="yes",
            review_verdict="pass",
            critical=0,
            major=0,
        )
        # No phase-1-review-slice-1.md on disk.
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_na_verdict_skips_artifact_check(self):
        make_state(
            self.tmp,
            reviewer_invoked="yes",
            review_verdict="n/a",
            critical=0,
            major=0,
        )
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))


class PlannerVerdictTests(unittest.TestCase):
    """Planner SubagentStop: verify the plan file the planner claims to have
    written actually exists and is non-empty."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_planning_missing_plan_file_blocks(self):
        make_state(self.tmp, stage="planning", design_status="draft")
        rc, out, _ = run_verdict_hook("planner", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_planning_with_plan_file_allows(self):
        make_state(self.tmp, stage="planning", design_status="draft")
        make_phase_artifact(self.tmp, "phase-1-design.md", body="# design\n")
        rc, out, _ = run_verdict_hook("planner", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_planning_empty_plan_file_blocks(self):
        make_state(self.tmp, stage="planning", design_status="draft")
        make_phase_artifact(self.tmp, "phase-1-design.md", body="")
        rc, out, _ = run_verdict_hook("planner", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_implementation_planning_missing_plan_blocks(self):
        make_state(
            self.tmp,
            stage="implementation-planning",
            implementation_status="draft",
        )
        rc, out, _ = run_verdict_hook("planner", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_implementation_planning_with_plan_allows(self):
        make_state(
            self.tmp,
            stage="implementation-planning",
            implementation_status="draft",
        )
        make_phase_artifact(self.tmp, "phase-1-implementation.md", body="# impl\n")
        rc, out, _ = run_verdict_hook("planner", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_reviewing_fallback_pending_blocks(self):
        make_state(self.tmp, stage="reviewing", strategic_review="pending")
        rc, out, _ = run_verdict_hook("planner", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_reviewing_fallback_pass_allows(self):
        make_state(self.tmp, stage="reviewing", strategic_review="pass")
        rc, out, _ = run_verdict_hook("planner", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))


class PhaseCoercionTests(unittest.TestCase):
    """Phase field must be a bare integer; non-numeric values are corruption."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _corrupt_phase(self, bad_value):
        state_path = self.tmp / "roadmap" / "state.md"
        state_path.write_text(
            state_path.read_text().replace("**Phase**: 1", f"**Phase**: {bad_value}")
        )

    def test_non_numeric_phase_blocks_critic(self):
        make_state(self.tmp, stage="design-critique", design_status="approved")
        self._corrupt_phase("Phase 1")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))
        self.assertIn("Phase", out["reason"])

    def test_float_phase_blocks_critic(self):
        make_state(self.tmp, stage="design-critique", design_status="approved")
        self._corrupt_phase("1.0")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_empty_phase_blocks_critic(self):
        make_state(self.tmp, stage="design-critique", design_status="approved")
        self._corrupt_phase("")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    def test_non_numeric_phase_blocks_reviewer(self):
        make_state(
            self.tmp,
            reviewer_invoked="yes",
            review_verdict="pass",
            critical=0,
            major=0,
        )
        self._corrupt_phase("two")
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))

    # CR-5: Phase=0 is reserved for bootstrap; critique stages require >= 1.

    def test_phase_zero_blocks_critic_in_design_critique(self):
        make_state(self.tmp, stage="design-critique", design_status="approved")
        self._corrupt_phase("0")
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))
        self.assertIn("Phase", out["reason"])

    def test_phase_zero_blocks_reviewer_in_executing(self):
        make_state(
            self.tmp,
            stage="executing",
            reviewer_invoked="yes",
            review_verdict="pass",
            critical=0,
            major=0,
        )
        self._corrupt_phase("0")
        rc, out, _ = run_verdict_hook("reviewer", {"cwd": str(self.tmp)}, self.tmp)
        self.assertTrue(is_block(out))


class UnknownSubagentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_unknown_subagent_allows(self):
        make_state(self.tmp)
        rc, out, _ = run_verdict_hook("mystery-agent", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))

    def test_missing_state_file_allows(self):
        rc, out, _ = run_verdict_hook("critic", {"cwd": str(self.tmp)}, self.tmp)
        self.assertFalse(is_block(out))


if __name__ == "__main__":
    unittest.main()
