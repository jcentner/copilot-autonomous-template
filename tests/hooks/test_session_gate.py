"""Unit tests for session-gate.py (Stop)."""
import tempfile
import unittest
import pathlib

from _helpers import run_hook, make_state


class SessionGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, **state_kwargs):
        make_state(self.tmp, **state_kwargs)
        rc, out, _ = run_hook(
            "session-gate.py", {"cwd": str(self.tmp)}, cwd=self.tmp
        )
        self.assertEqual(rc, 0)
        return out

    def _decision(self, out):
        return out.get("hookSpecificOutput", {}).get("decision", "allow")

    # --- Allow cases ---

    def test_blocked_stage_with_kind_allows(self):
        out = self._run(stage="blocked", blocked_kind="awaiting-design-approval")
        self.assertEqual(self._decision(out), "allow")

    def test_blocked_without_kind_blocks(self):
        out = self._run(stage="blocked", blocked_kind="n/a")
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Blocked Kind", out["hookSpecificOutput"]["reason"])

    def test_blocked_with_invalid_kind_blocks(self):
        out = self._run(stage="blocked", blocked_kind="made-up-kind")
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Blocked Kind", out["hookSpecificOutput"]["reason"])

    def test_blocked_each_valid_kind_allows(self):
        for kind in (
            "awaiting-design-approval",
            "awaiting-vision-update",
            "awaiting-human-decision",
            "error",
            "vision-exhausted",
        ):
            with self.subTest(kind=kind):
                out = self._run(stage="blocked", blocked_kind=kind)
                self.assertEqual(self._decision(out), "allow")

    def test_complete_stage_allows_stop(self):
        out = self._run(stage="complete")
        self.assertEqual(self._decision(out), "allow")

    def test_executing_with_complete_slice_allows(self):
        out = self._run(
            stage="executing",
            tests_written="yes",
            tests_pass="yes",
            reviewer_invoked="yes",
            review_verdict="pass",
            critical=0,
            major=0,
            committed="yes",
        )
        self.assertEqual(self._decision(out), "allow")

    def test_stop_hook_active_allows(self):
        make_state(self.tmp, stage="executing", tests_pass="no")
        rc, out, _ = run_hook(
            "session-gate.py",
            {"cwd": str(self.tmp), "stop_hook_active": True},
            cwd=self.tmp,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._decision(out), "allow")

    def test_reviewing_with_strategic_pass_allows(self):
        out = self._run(stage="reviewing", strategic_review="pass")
        self.assertEqual(self._decision(out), "allow")

    def test_cleanup_with_checklist_done_allows(self):
        out = self._run(stage="cleanup", checklist_checked=True)
        self.assertEqual(self._decision(out), "allow")

    # --- Block cases ---

    def test_executing_blocks_on_failed_tests(self):
        out = self._run(stage="executing", tests_pass="no")
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Tests Pass", out["hookSpecificOutput"]["reason"])

    def test_executing_blocks_on_pending_review(self):
        out = self._run(stage="executing", review_verdict="pending")
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Review Verdict", out["hookSpecificOutput"]["reason"])

    def test_executing_blocks_on_critical_findings(self):
        out = self._run(stage="executing", critical=2)
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Critical", out["hookSpecificOutput"]["reason"])

    def test_executing_blocks_on_not_committed(self):
        out = self._run(stage="executing", committed="no")
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Committed", out["hookSpecificOutput"]["reason"])

    # --- Bug C regression: Evidence For Slice must match Active Slice. ---

    def test_executing_blocks_on_stale_evidence_from_prior_slice(self):
        # Active Slice advanced to 2 but evidence still bound to slice 1.
        out = self._run(
            stage="executing",
            active_slice=2,
            evidence_for_slice=1,
        )
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Evidence For Slice", out["hookSpecificOutput"]["reason"])

    def test_executing_blocks_when_evidence_for_slice_unset(self):
        # Active Slice set but no evidence recorded for it yet.
        out = self._run(
            stage="executing",
            active_slice=2,
            evidence_for_slice="n/a",
        )
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Evidence For Slice", out["hookSpecificOutput"]["reason"])

    def test_executing_allows_when_evidence_matches_active_slice(self):
        out = self._run(
            stage="executing",
            active_slice=2,
            evidence_for_slice=2,
        )
        self.assertEqual(self._decision(out), "allow")

    def test_reviewing_blocks_on_pending_strategic(self):
        out = self._run(stage="reviewing", strategic_review="pending")
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Strategic", out["hookSpecificOutput"]["reason"])

    def test_cleanup_blocks_on_unchecked_checklist(self):
        out = self._run(stage="cleanup", checklist_checked=False)
        self.assertEqual(self._decision(out), "block")
        self.assertIn("checklist", out["hookSpecificOutput"]["reason"].lower())

    def test_design_critique_blocks_when_in_critique(self):
        out = self._run(stage="design-critique", design_status="in-critique")
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Design Status", out["hookSpecificOutput"]["reason"])

    def test_implementation_critique_blocks_when_in_critique(self):
        out = self._run(
            stage="implementation-critique", implementation_status="in-critique"
        )
        self.assertEqual(self._decision(out), "block")
        self.assertIn("Implementation Status", out["hookSpecificOutput"]["reason"])

    # --- v1.2: New blocked kinds. ---

    def test_blocked_awaiting_strategy_approval_allows(self):
        out = self._run(stage="blocked", blocked_kind="awaiting-strategy-approval")
        self.assertEqual(self._decision(out), "allow")

    def test_blocked_awaiting_merge_approval_allows(self):
        out = self._run(stage="blocked", blocked_kind="awaiting-merge-approval")
        self.assertEqual(self._decision(out), "allow")

    def test_blocked_scrapped_by_human_allows(self):
        out = self._run(stage="blocked", blocked_kind="scrapped-by-human")
        self.assertEqual(self._decision(out), "allow")

    # --- v1.2: Next Prompt + recommendations rendering. ---

    def test_allow_includes_system_message_with_next_prompt(self):
        make_state(
            self.tmp,
            stage="blocked",
            blocked_kind="awaiting-design-approval",
            next_prompt="/resume",
        )
        rc, out, _ = run_hook(
            "session-gate.py", {"cwd": str(self.tmp)}, cwd=self.tmp
        )
        self.assertEqual(rc, 0)
        msg = out.get("systemMessage", "")
        self.assertIn("→ Next: /resume", msg)

    def test_allow_omits_message_when_next_prompt_is_na(self):
        make_state(
            self.tmp,
            stage="blocked",
            blocked_kind="awaiting-design-approval",
            next_prompt="n/a",
        )
        rc, out, _ = run_hook(
            "session-gate.py", {"cwd": str(self.tmp)}, cwd=self.tmp
        )
        self.assertEqual(rc, 0)
        # No systemMessage at all (or empty) when nothing useful to say.
        self.assertNotIn("→ Next:", out.get("systemMessage", ""))

    def test_block_reason_includes_next_prompt_when_set(self):
        make_state(
            self.tmp,
            stage="executing",
            tests_pass="no",
            next_prompt="/implement",
        )
        rc, out, _ = run_hook(
            "session-gate.py", {"cwd": str(self.tmp)}, cwd=self.tmp
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._decision(out), "block")
        reason = out["hookSpecificOutput"]["reason"]
        self.assertIn("→ Next: /implement", reason)

    def test_recommendations_rendered_when_config_present(self):
        make_state(
            self.tmp,
            stage="blocked",
            blocked_kind="awaiting-design-approval",
            next_prompt="/resume",
        )
        cfg_dir = self.tmp / ".github" / "hooks" / "config"
        cfg_dir.mkdir(parents=True)
        (cfg_dir / "stage-recommendations.json").write_text(
            '{"blocked": {"prompts": ["/resume"], "skills": ["evidence-gathering"]}}'
        )
        rc, out, _ = run_hook(
            "session-gate.py", {"cwd": str(self.tmp)}, cwd=self.tmp
        )
        self.assertEqual(rc, 0)
        msg = out.get("systemMessage", "")
        self.assertIn("→ Consider:", msg)
        self.assertIn("evidence-gathering", msg)

    # --- v1.2: Strategy-artifact gate (planning stage). ---

    def test_planning_stage_blocks_without_strategy_artifact(self):
        out = self._run(stage="planning")
        self.assertEqual(self._decision(out), "block")
        self.assertIn("strategy", out["hookSpecificOutput"]["reason"].lower())

    def test_planning_stage_allows_with_strategy_artifact(self):
        make_state(self.tmp, stage="planning")
        (self.tmp / "roadmap" / "strategy-20260419-120000.md").write_text("# pick\n")
        rc, out, _ = run_hook(
            "session-gate.py", {"cwd": str(self.tmp)}, cwd=self.tmp
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._decision(out), "allow")

    # --- v1.2: strategy stage falls under NON_EXECUTING_STAGES. ---

    def test_strategy_stage_allows_when_clean(self):
        out = self._run(stage="strategy")
        self.assertEqual(self._decision(out), "allow")


if __name__ == "__main__":
    unittest.main()
