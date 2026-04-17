"""Unit tests for stage-gate.py (PreToolUse)."""
import tempfile
import unittest
import pathlib

from _helpers import run_hook, make_state


class StageGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _payload(self, stage, tool_name, file_path=None, replacements=None):
        make_state(self.tmp, stage=stage)
        tool_input = {}
        if file_path is not None:
            tool_input["filePath"] = file_path
        if replacements is not None:
            tool_input["replacements"] = replacements
        return {
            "cwd": str(self.tmp),
            "tool_name": tool_name,
            "tool_input": tool_input,
        }

    def _decision(self, payload):
        rc, out, _ = run_hook("stage-gate.py", payload, cwd=self.tmp)
        self.assertEqual(rc, 0)
        return out.get("hookSpecificOutput", {}).get("permissionDecision")

    # --- Allow cases ---

    def test_executing_stage_allows_source_edit(self):
        payload = self._payload("executing", "create_file", file_path="src/foo.py")
        self.assertEqual(self._decision(payload), "allow")

    def test_bootstrap_stage_allows_anything(self):
        payload = self._payload("bootstrap", "create_file", file_path="src/foo.py")
        self.assertEqual(self._decision(payload), "allow")

    def test_cleanup_stage_denies_source_edit(self):
        # cleanup is NOT a source-writing stage; only executing and bootstrap are.
        payload = self._payload("cleanup", "create_file", file_path="src/foo.py")
        self.assertEqual(self._decision(payload), "deny")

    def test_cleanup_stage_allows_doc_edit(self):
        payload = self._payload(
            "cleanup", "create_file", file_path="docs/reference/x.md"
        )
        self.assertEqual(self._decision(payload), "allow")

    def test_unknown_stage_denies(self):
        # Unknown Stage values must fail closed, not fall through to allow.
        payload = self._payload("bogus", "create_file", file_path="src/foo.py")
        self.assertEqual(self._decision(payload), "deny")

    def test_terminal_command_always_allowed(self):
        make_state(self.tmp, stage="planning")
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "run_in_terminal",
            "tool_input": {"command": "echo hi > src/foo.py"},
        }
        self.assertEqual(self._decision(payload), "allow")

    def test_planning_stage_allows_roadmap_edit(self):
        payload = self._payload(
            "planning", "create_file", file_path="roadmap/phases/phase-1-design.md"
        )
        self.assertEqual(self._decision(payload), "allow")

    def test_planning_stage_allows_docs_edit(self):
        payload = self._payload(
            "planning", "create_file", file_path="docs/architecture/overview.md"
        )
        self.assertEqual(self._decision(payload), "allow")

    def test_planning_stage_allows_github_edit(self):
        payload = self._payload(
            "planning", "create_file", file_path=".github/agents/new.agent.md"
        )
        self.assertEqual(self._decision(payload), "allow")

    def test_missing_state_allows(self):
        # No roadmap/CURRENT-STATE.md exists — fallback is allow.
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "create_file",
            "tool_input": {"filePath": "src/foo.py"},
        }
        self.assertEqual(self._decision(payload), "allow")

    def test_non_edit_tool_allowed(self):
        payload = self._payload("planning", "read_file", file_path="src/foo.py")
        self.assertEqual(self._decision(payload), "allow")

    # --- Deny cases ---

    def test_planning_stage_denies_source_edit(self):
        payload = self._payload("planning", "create_file", file_path="src/foo.py")
        self.assertEqual(self._decision(payload), "deny")

    def test_design_critique_stage_denies_source_edit(self):
        payload = self._payload(
            "design-critique", "replace_string_in_file", file_path="src/app.ts"
        )
        self.assertEqual(self._decision(payload), "deny")

    def test_reviewing_stage_denies_source_edit(self):
        payload = self._payload(
            "reviewing", "create_file", file_path="lib/secret.py"
        )
        self.assertEqual(self._decision(payload), "deny")

    def test_multi_replace_denied_for_source(self):
        payload = self._payload(
            "implementation-planning",
            "multi_replace_string_in_file",
            replacements=[{"filePath": "src/foo.py"}],
        )
        self.assertEqual(self._decision(payload), "deny")

    def test_multi_replace_mixed_bypass_denied(self):
        # Bug A regression: an allow-listed first entry must NOT let a
        # source-tree second entry through. Hook must inspect every replacement.
        payload = self._payload(
            "planning",
            "multi_replace_string_in_file",
            replacements=[
                {"filePath": "roadmap/CURRENT-STATE.md"},
                {"filePath": "src/hacked.py"},
            ],
        )
        self.assertEqual(self._decision(payload), "deny")

    def test_multi_replace_all_allowlisted_allowed(self):
        payload = self._payload(
            "planning",
            "multi_replace_string_in_file",
            replacements=[
                {"filePath": "roadmap/CURRENT-STATE.md"},
                {"filePath": "docs/architecture/overview.md"},
                {"filePath": ".github/prompts/foo.prompt.md"},
            ],
        )
        self.assertEqual(self._decision(payload), "allow")

    def test_path_traversal_denied(self):
        payload = self._payload(
            "planning", "create_file", file_path="../../etc/passwd"
        )
        # Normalized path escapes allowlist → deny.
        self.assertEqual(self._decision(payload), "deny")


if __name__ == "__main__":
    unittest.main()
