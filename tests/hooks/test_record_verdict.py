"""Unit tests for record-verdict.py — sole writer of critique-rounds + verdict mutations."""
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

from _helpers import HOOK_DIR, make_state, make_phase_artifact


def run_record(args, cwd):
    """Run record-verdict.py with positional args in `cwd`. Return (rc, stdout, stderr)."""
    hook_path = HOOK_DIR / "record-verdict.py"
    result = subprocess.run(
        [sys.executable, str(hook_path), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=10,
    )
    return result.returncode, result.stdout, result.stderr


def write_critique(tmp, kind, round_no, verdict_line):
    body = textwrap.dedent(
        f"""\
        # Phase 1 critique — {kind} R{round_no}

        Findings would go here.

        {verdict_line}
        """
    )
    return make_phase_artifact(
        tmp, f"phase-1-critique-{kind}-R{round_no}.md", body=body
    )


def field_value(state_text, field):
    m = re.search(rf"^\s*-\s+\*\*{re.escape(field)}\*\*:\s*(.*?)\s*$", state_text, re.MULTILINE)
    return m.group(1) if m else None


class RecordVerdictCLITests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_args_exits_2(self):
        make_state(self.tmp, stage="design-critique")
        rc, _, err = run_record([], self.tmp)
        self.assertEqual(rc, 2)
        self.assertIn("usage", err)

    def test_unknown_kind_exits_2(self):
        make_state(self.tmp, stage="design-critique")
        rc, _, err = run_record(["bogus", "R1"], self.tmp)
        self.assertEqual(rc, 2)
        self.assertIn("unknown kind", err)

    def test_round_arg_must_match_R_n(self):
        make_state(self.tmp, stage="design-critique")
        rc, _, err = run_record(["design", "1"], self.tmp)
        self.assertEqual(rc, 2)
        self.assertIn("R<positive integer>", err)


class DesignVerdictTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _state(self):
        return (self.tmp / "roadmap" / "state.md").read_text()

    def test_approve_promotes_to_design_approval_gate(self):
        make_state(
            self.tmp,
            stage="design-critique",
            design_status="in-critique",
        )
        # Reset rounds counter to 0 so R1 is the first round.
        path = self.tmp / "roadmap" / "state.md"
        text = path.read_text().replace(
            "Design Critique Rounds**: 1", "Design Critique Rounds**: 0"
        )
        path.write_text(text)
        write_critique(self.tmp, "design", 1, "VERDICT: approve")
        rc, out, err = run_record(["design", "R1"], self.tmp)
        self.assertEqual(rc, 0, msg=err)
        state = self._state()
        self.assertEqual(field_value(state, "Design Status"), "approved")
        self.assertEqual(field_value(state, "Design Critique Rounds"), "1")
        self.assertEqual(field_value(state, "Stage"), "blocked")
        self.assertEqual(
            field_value(state, "Blocked Kind"), "awaiting-design-approval"
        )
        self.assertEqual(field_value(state, "Next Prompt"), "/resume")

    def test_revise_routes_to_design_plan_no_stage_change(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        path = self.tmp / "roadmap" / "state.md"
        text = path.read_text().replace(
            "Design Critique Rounds**: 1", "Design Critique Rounds**: 0"
        )
        path.write_text(text)
        write_critique(self.tmp, "design", 1, "VERDICT: revise")
        rc, out, err = run_record(["design", "R1"], self.tmp)
        self.assertEqual(rc, 0, msg=err)
        state = self._state()
        self.assertEqual(field_value(state, "Design Status"), "revise")
        self.assertEqual(field_value(state, "Design Critique Rounds"), "1")
        self.assertEqual(field_value(state, "Stage"), "design-critique")
        self.assertEqual(field_value(state, "Next Prompt"), "/design-plan")

    def test_rethink_status(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        path = self.tmp / "roadmap" / "state.md"
        text = path.read_text().replace(
            "Design Critique Rounds**: 1", "Design Critique Rounds**: 0"
        )
        path.write_text(text)
        write_critique(self.tmp, "design", 1, "VERDICT: rethink")
        rc, _, err = run_record(["design", "R1"], self.tmp)
        self.assertEqual(rc, 0, msg=err)
        self.assertEqual(field_value(self._state(), "Design Status"), "rethink")

    def test_round_must_follow_current(self):
        # Current rounds = 1 → R3 should be rejected (expected R2).
        make_state(self.tmp, stage="design-critique", design_status="revise")
        write_critique(self.tmp, "design", 3, "VERDICT: approve")
        rc, _, err = run_record(["design", "R3"], self.tmp)
        self.assertEqual(rc, 1)
        self.assertIn("expected R2", err)

    def test_cap_exceeded_refused(self):
        # Set rounds counter to 3 (cap); R4 should refuse.
        make_state(self.tmp, stage="design-critique", design_status="revise")
        path = self.tmp / "roadmap" / "state.md"
        text = path.read_text().replace(
            "Design Critique Rounds**: 1", "Design Critique Rounds**: 3"
        )
        path.write_text(text)
        write_critique(self.tmp, "design", 4, "VERDICT: approve")
        rc, _, err = run_record(["design", "R4"], self.tmp)
        self.assertEqual(rc, 1)
        self.assertIn("cap exceeded", err)

    def test_missing_artifact_refused(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        # No artifact written.
        rc, _, err = run_record(["design", "R2"], self.tmp)
        self.assertEqual(rc, 1)
        self.assertIn("artifact missing", err)

    def test_missing_trailer_refused(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        path = self.tmp / "roadmap" / "state.md"
        text = path.read_text().replace(
            "Design Critique Rounds**: 1", "Design Critique Rounds**: 0"
        )
        path.write_text(text)
        make_phase_artifact(
            self.tmp,
            "phase-1-critique-design-R1.md",
            body="# critique\n\nNo verdict trailer here.\n",
        )
        rc, _, err = run_record(["design", "R1"], self.tmp)
        self.assertEqual(rc, 1)
        self.assertIn("missing the verdict trailer", err)

    def test_ambiguous_trailer_refused(self):
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        path = self.tmp / "roadmap" / "state.md"
        text = path.read_text().replace(
            "Design Critique Rounds**: 1", "Design Critique Rounds**: 0"
        )
        path.write_text(text)
        body = "# critique\n\nVERDICT: approve\nVERDICT: revise\n"
        make_phase_artifact(self.tmp, "phase-1-critique-design-R1.md", body=body)
        rc, _, err = run_record(["design", "R1"], self.tmp)
        self.assertEqual(rc, 1)
        self.assertIn("VERDICT lines", err)

    def test_lowercase_verdict_rejected(self):
        # Case-sensitive: 'verdict: approve' must not parse.
        make_state(self.tmp, stage="design-critique", design_status="in-critique")
        path = self.tmp / "roadmap" / "state.md"
        text = path.read_text().replace(
            "Design Critique Rounds**: 1", "Design Critique Rounds**: 0"
        )
        path.write_text(text)
        make_phase_artifact(
            self.tmp,
            "phase-1-critique-design-R1.md",
            body="# critique\n\nverdict: approve\n",
        )
        rc, _, err = run_record(["design", "R1"], self.tmp)
        self.assertEqual(rc, 1)
        self.assertIn("missing the verdict trailer", err)

    def test_wrong_stage_refused(self):
        # design verdict in implementation-critique stage.
        make_state(self.tmp, stage="implementation-critique")
        write_critique(self.tmp, "design", 1, "VERDICT: approve")
        rc, _, err = run_record(["design", "R1"], self.tmp)
        self.assertEqual(rc, 1)
        self.assertIn("Stage is", err)


class ImplementationVerdictTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _state(self):
        return (self.tmp / "roadmap" / "state.md").read_text()

    def _zero_impl_rounds(self):
        path = self.tmp / "roadmap" / "state.md"
        path.write_text(
            path.read_text().replace(
                "Implementation Critique Rounds**: 1",
                "Implementation Critique Rounds**: 0",
            )
        )

    def test_impl_alias(self):
        make_state(
            self.tmp, stage="implementation-critique",
            implementation_status="in-critique",
        )
        self._zero_impl_rounds()
        write_critique(self.tmp, "implementation", 1, "VERDICT: approve")
        rc, _, err = run_record(["impl", "R1"], self.tmp)
        self.assertEqual(rc, 0, msg=err)

    def test_implementation_alias(self):
        make_state(
            self.tmp, stage="implementation-critique",
            implementation_status="in-critique",
        )
        self._zero_impl_rounds()
        write_critique(self.tmp, "implementation", 1, "VERDICT: approve")
        rc, _, err = run_record(["implementation", "R1"], self.tmp)
        self.assertEqual(rc, 0, msg=err)

    def test_approve_advances_to_executing(self):
        make_state(
            self.tmp, stage="implementation-critique",
            implementation_status="in-critique",
        )
        self._zero_impl_rounds()
        write_critique(self.tmp, "implementation", 1, "VERDICT: approve")
        rc, _, err = run_record(["impl", "R1"], self.tmp)
        self.assertEqual(rc, 0, msg=err)
        state = self._state()
        self.assertEqual(field_value(state, "Implementation Status"), "approved")
        self.assertEqual(
            field_value(state, "Implementation Critique Rounds"), "1"
        )
        self.assertEqual(field_value(state, "Stage"), "executing")
        self.assertEqual(field_value(state, "Active Slice"), "1")
        self.assertEqual(field_value(state, "Next Prompt"), "/implement")

    def test_revise_routes_to_implementation_plan(self):
        make_state(
            self.tmp, stage="implementation-critique",
            implementation_status="in-critique",
        )
        self._zero_impl_rounds()
        write_critique(self.tmp, "implementation", 1, "VERDICT: revise")
        rc, _, err = run_record(["impl", "R1"], self.tmp)
        self.assertEqual(rc, 0, msg=err)
        state = self._state()
        self.assertEqual(field_value(state, "Implementation Status"), "revise")
        self.assertEqual(field_value(state, "Stage"), "implementation-critique")
        self.assertEqual(
            field_value(state, "Next Prompt"), "/implementation-plan"
        )

    def test_impl_cap_2(self):
        make_state(
            self.tmp, stage="implementation-critique",
            implementation_status="revise",
        )
        path = self.tmp / "roadmap" / "state.md"
        path.write_text(
            path.read_text().replace(
                "Implementation Critique Rounds**: 1",
                "Implementation Critique Rounds**: 2",
            )
        )
        write_critique(self.tmp, "implementation", 3, "VERDICT: approve")
        rc, _, err = run_record(["impl", "R3"], self.tmp)
        self.assertEqual(rc, 1)
        self.assertIn("cap exceeded", err)


if __name__ == "__main__":
    unittest.main()
