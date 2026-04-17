"""Unit tests for tool-guardrails.py (PreToolUse)."""
import pathlib
import tempfile
import unittest

from _helpers import run_hook, make_state


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

    def test_path_traversal_via_segments_denied(self):
        # Regression: os.path.normpath('src/foo/../../etc/passwd') collapses
        # to 'etc/passwd' and silently swallows the .. segments. The check
        # must run against the raw input.
        out = self._run(
            "create_file", {"filePath": "src/foo/../../etc/passwd"}
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

    def test_rm_state_md_denied(self):
        # Deleting state.md would let tool-guardrails treat the workspace
        # as fresh (bootstrap) and unlock enforcement-layer paths.
        out = self._run(
            "run_in_terminal", {"command": "rm roadmap/state.md"}
        )
        self.assertEqual(self._decision(out), "deny")

    def test_rm_rf_state_md_denied(self):
        out = self._run(
            "run_in_terminal", {"command": "rm -rf roadmap/state.md"}
        )
        self.assertEqual(self._decision(out), "deny")

    def test_mv_state_md_denied(self):
        out = self._run(
            "run_in_terminal",
            {"command": "mv roadmap/state.md /tmp/backup.md"},
        )
        self.assertEqual(self._decision(out), "deny")

    def test_rm_current_state_md_denied(self):
        out = self._run(
            "run_in_terminal", {"command": "rm roadmap/CURRENT-STATE.md"}
        )
        self.assertEqual(self._decision(out), "deny")

    # --- Bug B regression: enforcement-layer paths are protected. ---

    def test_hook_script_write_denied(self):
        make_state(self.tmp, stage="planning")
        out = self._run(
            "create_file",
            {"filePath": ".github/hooks/scripts/stage-gate.py"},
        )
        self.assertEqual(self._decision(out), "deny")

    def test_agent_definition_write_denied(self):
        make_state(self.tmp, stage="planning")
        out = self._run(
            "replace_string_in_file",
            {"filePath": ".github/agents/autonomous-builder.agent.md"},
        )
        self.assertEqual(self._decision(out), "deny")

    def test_instruction_file_write_denied(self):
        make_state(self.tmp, stage="planning")
        out = self._run(
            "create_file",
            {"filePath": ".github/instructions/docs.instructions.md"},
        )
        self.assertEqual(self._decision(out), "deny")

    def test_copilot_instructions_write_denied(self):
        make_state(self.tmp, stage="planning")
        out = self._run(
            "replace_string_in_file",
            {"filePath": ".github/copilot-instructions.md"},
        )
        self.assertEqual(self._decision(out), "deny")

    def test_agents_md_write_denied(self):
        # AGENTS.md carries cross-agent rules — not mutable mid-phase.
        make_state(self.tmp, stage="planning")
        out = self._run(
            "replace_string_in_file",
            {"filePath": "AGENTS.md"},
        )
        self.assertEqual(self._decision(out), "deny")

    # --- CR-3: absolute paths without `cwd` cannot be validated. ---

    def test_absolute_path_without_cwd_denied(self):
        # When the hook payload omits `cwd`, an absolute path can't be
        # checked against workspace boundaries — refuse rather than allow.
        rc, out, _ = run_hook(
            "tool-guardrails.py",
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "/etc/passwd"},
            },
            cwd=self.tmp,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._decision(out), "deny")

    # --- CR-4: state files cannot be overwritten via file-edit tools. ---

    def test_state_md_write_denied_outside_bootstrap(self):
        make_state(self.tmp, stage="planning")
        out = self._run(
            "create_file", {"filePath": "roadmap/state.md"}
        )
        self.assertEqual(self._decision(out), "deny")

    def test_state_md_write_allowed_in_bootstrap(self):
        make_state(self.tmp, stage="bootstrap")
        out = self._run(
            "create_file", {"filePath": "roadmap/state.md"}
        )
        self.assertNotEqual(self._decision(out), "deny")

    def test_current_state_md_write_allowed_anytime(self):
        # CURRENT-STATE.md is narrative — agents append to Context,
        # Proposed Improvements, etc. throughout the lifecycle.
        make_state(self.tmp, stage="executing")
        out = self._run(
            "replace_string_in_file",
            {"filePath": "roadmap/CURRENT-STATE.md"},
        )
        self.assertNotEqual(self._decision(out), "deny")

    def test_prompt_file_write_allowed(self):
        # Prompts under .github/prompts/ are NOT in the protected list \u2014
        # the builder may legitimately add or edit project-specific prompts.
        out = self._run(
            "create_file",
            {"filePath": ".github/prompts/custom.prompt.md"},
        )
        self.assertNotEqual(self._decision(out), "deny")

    def test_multi_replace_protected_path_smuggled_denied(self):
        # Even if the first entry is innocuous, a single protected-path
        # replacement in the batch must trigger a deny.
        make_state(self.tmp, stage="planning")
        out = self._run(
            "multi_replace_string_in_file",
            {
                "replacements": [
                    {"filePath": "roadmap/CURRENT-STATE.md"},
                    {"filePath": ".github/hooks/scripts/session-gate.py"},
                ]
            },
        )
        self.assertEqual(self._decision(out), "deny")

    def test_multi_replace_safe_paths_allowed(self):
        out = self._run(
            "multi_replace_string_in_file",
            {
                "replacements": [
                    {"filePath": "roadmap/CURRENT-STATE.md"},
                    {"filePath": "docs/reference/glossary.md"},
                ]
            },
        )
        self.assertNotEqual(self._decision(out), "deny")

    # --- Bootstrap carve-out: catalog activation during `bootstrap` stage. ---

    def test_bootstrap_stage_allows_agent_write(self):
        # Catalog activation during bootstrap copies `.github/catalog/agents/*`
        # to `.github/agents/`. That must go through.
        make_state(self.tmp, stage="bootstrap")
        out = self._run(
            "create_file",
            {"filePath": ".github/agents/security-reviewer.agent.md"},
        )
        self.assertNotEqual(self._decision(out), "deny")

    def test_bootstrap_stage_allows_hook_script_write(self):
        make_state(self.tmp, stage="bootstrap")
        out = self._run(
            "create_file",
            {"filePath": ".github/hooks/scripts/ci-gate.py"},
        )
        self.assertNotEqual(self._decision(out), "deny")

    def test_planning_stage_still_blocks_agent_write(self):
        make_state(self.tmp, stage="planning")
        out = self._run(
            "create_file",
            {"filePath": ".github/agents/new.agent.md"},
        )
        self.assertEqual(self._decision(out), "deny")

    def test_no_state_file_allows_agent_write(self):
        # Fresh `copier copy` workspace (no roadmap/state.md yet) is
        # effectively bootstrap.
        out = self._run(
            "create_file",
            {"filePath": ".github/agents/bootstrap-init.agent.md"},
        )
        self.assertNotEqual(self._decision(out), "deny")


if __name__ == "__main__":
    unittest.main()
