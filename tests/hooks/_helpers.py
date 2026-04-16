"""Shared helpers for hook unit tests."""
import json
import pathlib
import subprocess
import sys
import textwrap


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK_DIR = REPO_ROOT / "template" / ".github" / "hooks" / "scripts"


def run_hook(hook_name, stdin_payload, cwd=None):
    """Pipe JSON `stdin_payload` into the named hook and return (returncode, parsed_stdout, stderr)."""
    hook_path = HOOK_DIR / hook_name
    assert hook_path.exists(), f"missing hook: {hook_path}"
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=10,
    )
    stdout = result.stdout.strip()
    parsed = json.loads(stdout) if stdout else {}
    return result.returncode, parsed, result.stderr


def make_state(
    tmp_path,
    stage="executing",
    design_status="approved",
    implementation_status="approved",
    tests_written="yes",
    tests_pass="yes",
    reviewer_invoked="yes",
    review_verdict="pass",
    critical=0,
    major=0,
    strategic_review="n/a",
    committed="yes",
    checklist_checked=True,
):
    """Create a CURRENT-STATE.md under tmp_path/roadmap/ and return workspace root."""
    roadmap = tmp_path / "roadmap"
    roadmap.mkdir(parents=True, exist_ok=True)
    check = "x" if checklist_checked else " "
    content = textwrap.dedent(
        f"""\
        # Test — Current State

        ## Workflow State

        - **Stage**: {stage}
        - **Phase**: 1
        - **Phase Title**: Test
        - **Source Root**: src/
        - **Design Plan**: roadmap/phases/phase-1-design.md
        - **Design Status**: {design_status}
        - **Design Critique Rounds**: 1
        - **Implementation Plan**: roadmap/phases/phase-1-implementation.md
        - **Implementation Status**: {implementation_status}
        - **Implementation Critique Rounds**: 1
        - **Active Slice**: 1
        - **Slice Total**: 3
        - **Blocked Reason**: n/a

        ## Slice Evidence

        - **Tests Written**: {tests_written}
        - **Tests Pass**: {tests_pass}
        - **Reviewer Invoked**: {reviewer_invoked}
        - **Review Verdict**: {review_verdict}
        - **Critical Findings**: {critical}
        - **Major Findings**: {major}
        - **Strategic Review**: {strategic_review}
        - **Committed**: {committed}

        ## Phase Completion Checklist

        - [{check}] All acceptance criteria verified
        - [{check}] ADRs recorded for new decisions
        - [{check}] Open questions resolved or flagged
        - [{check}] Tech debt documented
        - [{check}] Docs synced (README, architecture, instructions)
        - [{check}] Wrap summary written
        - [{check}] Context notes saved to /memories/repo/
        - [{check}] CURRENT-STATE updated for next phase

        ## Waivers

        ## Proposed Workflow Improvements

        ## Session Log

        ## Context

        Test fixture.
        """
    )
    (roadmap / "CURRENT-STATE.md").write_text(content)
    return tmp_path
