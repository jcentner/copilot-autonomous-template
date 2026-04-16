"""Unit tests for tester-isolation.py (PreToolUse)."""
import pathlib
import tempfile
import unittest

from _helpers import run_hook, make_state


def decision(parsed):
    return parsed.get("hookSpecificOutput", {}).get("permissionDecision")


class SemanticSearchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_semantic_search_denied(self):
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "semantic_search",
            "tool_input": {"query": "login handler"},
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        self.assertEqual(decision(out), "deny")

    def test_codebase_search_denied(self):
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "search/codebase",
            "tool_input": {"query": "login handler"},
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        self.assertEqual(decision(out), "deny")


class ReadFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def _read(self, path):
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "read_file",
            "tool_input": {"filePath": path},
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        return decision(out)

    def test_source_file_denied(self):
        self.assertEqual(self._read("src/login.py"), "deny")

    def test_deep_source_file_denied(self):
        self.assertEqual(self._read("src/auth/handlers/login.py"), "deny")

    def test_test_file_allowed(self):
        self.assertEqual(self._read("tests/test_login.py"), "allow")

    def test_dot_test_suffix_allowed(self):
        self.assertEqual(self._read("src/foo.test.ts"), "allow")

    def test_dot_spec_suffix_allowed(self):
        self.assertEqual(self._read("src/foo.spec.ts"), "allow")

    def test_dunder_tests_dir_allowed(self):
        self.assertEqual(self._read("src/__tests__/foo.ts"), "allow")

    def test_package_json_allowed(self):
        self.assertEqual(self._read("package.json"), "allow")

    def test_pyproject_allowed(self):
        self.assertEqual(self._read("pyproject.toml"), "allow")

    def test_tsconfig_allowed(self):
        self.assertEqual(self._read("tsconfig.json"), "allow")

    def test_doc_outside_source_allowed(self):
        self.assertEqual(self._read("docs/architecture/overview.md"), "allow")

    def test_roadmap_file_allowed(self):
        self.assertEqual(self._read("roadmap/phases/phase-1-design.md"), "allow")


class GrepAndFileSearchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def _grep(self, include=None, query="x"):
        tool_input = {"query": query}
        if include is not None:
            tool_input["includePattern"] = include
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "grep_search",
            "tool_input": tool_input,
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        return decision(out)

    def _fsearch(self, pattern):
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "file_search",
            "tool_input": {"query": pattern},
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        return decision(out)

    def test_grep_without_include_denied(self):
        self.assertEqual(self._grep(include=None), "deny")

    def test_grep_with_tests_include_allowed(self):
        self.assertEqual(self._grep(include="tests/**"), "allow")

    def test_grep_with_test_glob_allowed(self):
        self.assertEqual(self._grep(include="**/*.test.*"), "allow")

    def test_grep_with_tests_dir_anywhere_allowed(self):
        self.assertEqual(self._grep(include="**/__tests__/**"), "allow")

    def test_grep_with_source_root_include_denied(self):
        self.assertEqual(self._grep(include="src/**"), "deny")

    def test_grep_with_unscoped_star_denied(self):
        self.assertEqual(self._grep(include="**/*.py"), "deny")

    def test_file_search_tests_pattern_allowed(self):
        self.assertEqual(self._fsearch("tests/**"), "allow")

    def test_file_search_source_pattern_denied(self):
        self.assertEqual(self._fsearch("src/**"), "deny")


class OtherToolsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        make_state(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_edit_allowed(self):
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "create_file",
            "tool_input": {"filePath": "tests/test_new.py"},
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        self.assertEqual(decision(out), "allow")

    def test_run_terminal_allowed(self):
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "run_in_terminal",
            "tool_input": {"command": "pytest"},
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        self.assertEqual(decision(out), "allow")

    def test_fetch_webpage_allowed(self):
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "fetch_webpage",
            "tool_input": {"urls": ["https://docs.pytest.org"]},
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        self.assertEqual(decision(out), "allow")


class CustomSourceRootTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_custom_source_root_applied(self):
        make_state(self.tmp)
        state_file = self.tmp / "roadmap" / "CURRENT-STATE.md"
        state_file.write_text(
            state_file.read_text().replace("Source Root**: src/", "Source Root**: app/")
        )
        payload = {
            "cwd": str(self.tmp),
            "tool_name": "read_file",
            "tool_input": {"filePath": "app/login.py"},
        }
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        self.assertEqual(decision(out), "deny")

        # But src/ is no longer protected.
        payload["tool_input"]["filePath"] = "src/login.py"
        rc, out, _ = run_hook("tester-isolation.py", payload, cwd=self.tmp)
        self.assertEqual(decision(out), "allow")


if __name__ == "__main__":
    unittest.main()
