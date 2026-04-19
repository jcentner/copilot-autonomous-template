#!/usr/bin/env python3
"""Sole writer of Design/Implementation Critique Rounds + verdict mutations.

Per ADR-011 / Decision #21 of the v1.2 plan, the critic agent does NOT
write state.md fields. After the critic returns its artifact, the
autonomous-builder runs this script to:

    1. Locate the round artifact at
       ``roadmap/phases/phase-{N}-critique-{design|implementation}-R{n}.md``.
    2. Parse a single ``^VERDICT: (approve|revise|rethink)$`` trailer line.
    3. Apply asymmetric state mutations:
       * design + approve → Design Status=approved, Stage=blocked,
         Blocked Kind=awaiting-design-approval, Next Prompt=/resume.
       * impl + approve → Implementation Status=approved, Stage=executing,
         Active Slice=1, Next Prompt=/implement.
       * {design,impl} + revise → status=revise, Next Prompt=
         /design-plan (or /implementation-plan); no Stage change.
       * {design,impl} + rethink → status=rethink, Next Prompt=
         /design-plan (or /implementation-plan); no Stage change.
    4. Increment the matching critique-rounds counter, refusing if the
       increment would exceed the cap (3 for design, 2 for implementation
       per ADR-004).

Refuses with a non-zero exit if the trailer is missing, ambiguous, or
the round cap would be exceeded.

Usage:
    record-verdict.py design  R{n}
    record-verdict.py impl    R{n}
    record-verdict.py implementation R{n}    # alias
"""
from __future__ import annotations

import os
import re
import sys

from _state_io import (
    get_field,
    get_field_raw,
    state_exists,
    state_path,
    update_state_field,
)


VERDICT_RE = re.compile(r"^VERDICT: (approve|revise|rethink)\s*$", re.MULTILINE)
ROUND_ARG_RE = re.compile(r"^R(\d+)$")

DESIGN_CAP = 3
IMPL_CAP = 2

KIND_DESIGN = "design"
KIND_IMPL = "implementation"

# CLI alias → canonical kind.
KIND_ALIAS = {
    "design": KIND_DESIGN,
    "impl": KIND_IMPL,
    "implementation": KIND_IMPL,
}


def die(msg: str, code: int = 1) -> None:
    sys.stderr.write(f"record-verdict: {msg}\n")
    sys.exit(code)


def parse_args(argv):
    if len(argv) != 3:
        die(
            "usage: record-verdict.py <design|impl|implementation> R<n>",
            code=2,
        )
    raw_kind = argv[1].strip().lower()
    if raw_kind not in KIND_ALIAS:
        die(
            f"unknown kind '{argv[1]}' — expected one of "
            f"{sorted(KIND_ALIAS)}",
            code=2,
        )
    kind = KIND_ALIAS[raw_kind]
    m = ROUND_ARG_RE.match(argv[2].strip())
    if not m:
        die(
            f"round arg '{argv[2]}' must match 'R<positive integer>' "
            f"(e.g., R1, R2)",
            code=2,
        )
    round_no = int(m.group(1))
    if round_no < 1:
        die(f"round must be >= 1, got R{round_no}", code=2)
    return kind, round_no


def coerce_phase(cwd: str) -> int:
    raw = get_field_raw(cwd, "Phase", "")
    if not raw:
        die("Phase field in roadmap/state.md is empty.")
    try:
        value = int(raw)
    except ValueError:
        die(
            f"Phase field is '{raw}' — must be a bare non-negative integer "
            f"(e.g., '1'). Critique artifacts embed this value in their "
            f"filenames."
        )
    if value < 1:
        die(
            f"Phase is {value} — must be >= 1 to record a critique verdict. "
            f"Phase 0 is reserved for bootstrap."
        )
    return value


def coerce_rounds(cwd: str, field: str) -> int:
    raw = get_field_raw(cwd, field, "0") or "0"
    try:
        value = int(raw)
    except ValueError:
        die(f"{field} is '{raw}' — must be a non-negative integer.")
    if value < 0:
        die(f"{field} is negative ({value}) — must be >= 0.")
    return value


def artifact_path(cwd: str, kind: str, phase: int, round_no: int) -> str:
    return os.path.join(
        cwd,
        "roadmap",
        "phases",
        f"phase-{phase}-critique-{kind}-R{round_no}.md",
    )


def read_artifact(path: str) -> str:
    if not os.path.exists(path):
        die(f"artifact missing: {os.path.relpath(path)}")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as exc:
        die(f"cannot read artifact {os.path.relpath(path)}: {exc}")


def parse_verdict(text: str, artifact_rel: str) -> str:
    matches = VERDICT_RE.findall(text)
    if not matches:
        die(
            f"artifact {artifact_rel} is missing the verdict trailer. "
            f"Add a single line at the end of the file matching "
            f"'^VERDICT: (approve|revise|rethink)$' (case-sensitive, "
            f"exact)."
        )
    if len(matches) > 1:
        die(
            f"artifact {artifact_rel} contains {len(matches)} VERDICT lines "
            f"({matches}). Exactly one is required."
        )
    return matches[0]


def apply_design(cwd: str, verdict: str, round_no: int) -> None:
    current = coerce_rounds(cwd, "Design Critique Rounds")
    if round_no != current + 1:
        die(
            f"round arg R{round_no} does not follow Design Critique Rounds "
            f"= {current}; expected R{current + 1}."
        )
    if round_no > DESIGN_CAP:
        die(
            f"design critique round cap exceeded: R{round_no} > "
            f"{DESIGN_CAP}. Escalate to a human (set Stage: blocked, "
            f"Blocked Kind: awaiting-human-decision) instead."
        )
    if not update_state_field(cwd, "Design Status", verdict_to_status(verdict)):
        die("Design Status field not found in state.md.")
    if not update_state_field(cwd, "Design Critique Rounds", str(round_no)):
        die("Design Critique Rounds field not found in state.md.")
    if verdict == "approve":
        update_state_field(cwd, "Stage", "blocked")
        update_state_field(cwd, "Blocked Kind", "awaiting-design-approval")
        update_state_field(
            cwd,
            "Blocked Reason",
            "Design plan approved by critic; awaiting human approval before "
            "implementation planning.",
        )
        update_state_field(cwd, "Next Prompt", "/resume")
    else:
        # revise / rethink — stay in design-critique conceptually but route
        # the next prompt back to /design-plan so the planner re-runs.
        update_state_field(cwd, "Next Prompt", "/design-plan")


def apply_impl(cwd: str, verdict: str, round_no: int) -> None:
    current = coerce_rounds(cwd, "Implementation Critique Rounds")
    if round_no != current + 1:
        die(
            f"round arg R{round_no} does not follow Implementation Critique "
            f"Rounds = {current}; expected R{current + 1}."
        )
    if round_no > IMPL_CAP:
        die(
            f"implementation critique round cap exceeded: R{round_no} > "
            f"{IMPL_CAP}. Escalate to a human instead."
        )
    if not update_state_field(
        cwd, "Implementation Status", verdict_to_status(verdict)
    ):
        die("Implementation Status field not found in state.md.")
    if not update_state_field(
        cwd, "Implementation Critique Rounds", str(round_no)
    ):
        die("Implementation Critique Rounds field not found in state.md.")
    if verdict == "approve":
        update_state_field(cwd, "Stage", "executing")
        update_state_field(cwd, "Active Slice", "1")
        update_state_field(cwd, "Next Prompt", "/implement")
    else:
        update_state_field(cwd, "Next Prompt", "/implementation-plan")


def verdict_to_status(verdict: str) -> str:
    # Plan: artifact verdict words → state field canonical values.
    return {"approve": "approved", "revise": "revise", "rethink": "rethink"}[verdict]


def main(argv) -> int:
    kind, round_no = parse_args(argv)
    cwd = os.getcwd()
    if not state_exists(cwd):
        die("roadmap/state.md not found in current working directory.")

    stage = get_field(cwd, "Stage")
    expected_stage = (
        "design-critique" if kind == KIND_DESIGN else "implementation-critique"
    )
    if stage != expected_stage:
        die(
            f"Stage is '{stage}' but record-verdict expects "
            f"'{expected_stage}' for kind '{kind}'."
        )

    phase = coerce_phase(cwd)
    path = artifact_path(cwd, kind, phase, round_no)
    text = read_artifact(path)
    verdict = parse_verdict(text, os.path.relpath(path))

    if kind == KIND_DESIGN:
        apply_design(cwd, verdict, round_no)
    else:
        apply_impl(cwd, verdict, round_no)

    sys.stdout.write(
        f"record-verdict: {kind} R{round_no} → {verdict}; "
        f"state.md updated.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
