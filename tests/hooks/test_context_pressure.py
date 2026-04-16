"""Unit tests for context-pressure.py (PostToolUse advisory)."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import uuid

from _helpers import HOOK_DIR


class ContextPressureTests(unittest.TestCase):
    def _run(self, payload):
        result = subprocess.run(
            [sys.executable, str(HOOK_DIR / "context-pressure.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        stdout = result.stdout.strip()
        return json.loads(stdout) if stdout else {}

    def test_small_payload_no_advisory(self):
        out = self._run(
            {
                "sessionId": f"test-{uuid.uuid4()}",
                "tool_response": "small output",
            }
        )
        self.assertEqual(out, {})

    def test_large_payload_triggers_advisory(self):
        session_id = f"test-{uuid.uuid4()}"
        # Send one huge payload over threshold (default 400KB).
        big = "x" * 500_000
        out = self._run({"sessionId": session_id, "tool_response": big})
        advisory = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("Context Monitor", advisory)

    def test_advisory_only_once_per_session(self):
        session_id = f"test-{uuid.uuid4()}"
        big = "x" * 500_000
        out1 = self._run({"sessionId": session_id, "tool_response": big})
        self.assertIn("Context Monitor", out1["hookSpecificOutput"]["additionalContext"])
        out2 = self._run({"sessionId": session_id, "tool_response": big})
        self.assertEqual(out2, {})

    def test_never_blocks(self):
        # Should never emit permissionDecision; advisory is additionalContext.
        out = self._run(
            {"sessionId": f"test-{uuid.uuid4()}", "tool_response": "x" * 500_000}
        )
        self.assertNotIn(
            "permissionDecision", out.get("hookSpecificOutput", {})
        )


if __name__ == "__main__":
    unittest.main()
