"""Unit tests for tool-guardrails.py (PreToolUse)."""
import pathlib
import tempfile
import unittest

from _helpers import run_hook


class ToolGuardrailsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, tool_name, tool_input):
        rc, out, _ = run_hook(
            "tool-guardrails.py",
            {
                "cwd": str(self.tmp),
                "tool_name": tool_name,
                "tool_input": tool_input,
            },
            cwd=self.tmp,
        )
        self.assertEqual(rc, 0)
        return out

    def _decision(self, out):
        return out.get("hookSpecificOutput", {}).get("permissionDecision")

    def test_force_push_denied(self):
        out = self._run("run_in_terminal", {"command": "git push --force origin main"})
        self.assertEqual(self._decision(out), "deny")

    def test_force_push_short_denied(self):
        out = self._run("run_in_terminal", {"command": "git push -f"})
        self.assertEqual(self._decision(out), "deny")

    def test_force_with_lease_allowed(self):
        out = self._run(
            "run_in_terminal", {"command": "git push --force-with-lease origin feature"}
        )
        # No hookSpecificOutput → empty {} means allow.
        self.assertNotEqual(self._decision(out), "deny")

    def test_reset_hard_denied(self):
        out = self._run("run_in_terminal", {"command": "git reset --hard HEAD~1"})
        self.assertEqual(self._decision(out), "deny")

    def test_node_modules_write_denied(self):
        out = self._run(
            "create_file", {"filePath": "node_modules/foo/index.js"}
        )
        self.assertEqual(self._decision(out), "deny")

    def test_path_traversal_denied(self):
        out = self._run(
            "create_file", {"filePath": "../../etc/passwd"}
        )
        self.assertEqual(self._decision(out), "deny")

    def test_env_file_denied(self):
        out = self._run("create_file", {"filePath": ".env"})
        self.assertEqual(self._decision(out), "deny")

    def test_normal_source_edit_allowed(self):
        out = self._run("create_file", {"filePath": "src/foo.py"})
        self.assertNotEqual(self._decision(out), "deny")

    def test_normal_git_command_allowed(self):
        out = self._run("run_in_terminal", {"command": "git status"})
        self.assertNotEqual(self._decision(out), "deny")


if __name__ == "__main__":
    unittest.main()
