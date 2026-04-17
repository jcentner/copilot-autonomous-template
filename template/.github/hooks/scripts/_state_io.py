"""Shared state I/O for hook scripts.

All hooks parse `roadmap/state.md` for machine-readable workflow fields and
narrative-only updates go to `roadmap/CURRENT-STATE.md`. This module
centralises both reads and atomic writes so individual hooks stay small.

Atomic writes use the standard "write temp + os.replace" pattern. POSIX
`rename(2)` is atomic across paths on the same filesystem, which is the
property we rely on to keep state.md consistent under concurrent hook
invocations from parallel tool calls.

Per-session log appends use `O_APPEND` directly. Linux guarantees atomicity
for `write(2)` calls smaller than `PIPE_BUF` (4 KiB); each log line is well
under that.
"""
from __future__ import annotations

import datetime
import hashlib
import os
import re
import tempfile
from typing import Iterable, Optional, Tuple


STATE_FILENAME = "state.md"
NARRATIVE_FILENAME = "CURRENT-STATE.md"
SESSIONS_DIRNAME = "sessions"
ROADMAP_DIRNAME = "roadmap"

# Stage vocabulary — kept here so every hook agrees on it.
VALID_STAGES = {
    "bootstrap",
    "planning",
    "design-critique",
    "implementation-planning",
    "implementation-critique",
    "executing",
    "reviewing",
    "cleanup",
    "blocked",
    "complete",
}

# When Stage = blocked, Blocked Kind must be one of these (anything else is
# treated as missing).
VALID_BLOCKED_KINDS = {
    "awaiting-design-approval",
    "awaiting-vision-update",
    "awaiting-human-decision",
    "error",
    "vision-exhausted",
}

_FIELD_RE = re.compile(r"^\s*-\s+\*\*([^*]+)\*\*:\s*(.*?)\s*$")
_UNCHECKED_RE = re.compile(r"^\s*-\s+\[ \]\s+(.*?)\s*$")


def state_path(cwd: str) -> str:
    return os.path.join(cwd, ROADMAP_DIRNAME, STATE_FILENAME)


def narrative_path(cwd: str) -> str:
    return os.path.join(cwd, ROADMAP_DIRNAME, NARRATIVE_FILENAME)


def sessions_dir(cwd: str) -> str:
    return os.path.join(cwd, ROADMAP_DIRNAME, SESSIONS_DIRNAME)


def state_exists(cwd: str) -> bool:
    return os.path.exists(state_path(cwd))


def read_state_text(cwd: str) -> Optional[str]:
    """Return the raw text of state.md, or None on any read error."""
    path = state_path(cwd)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def parse_state(cwd: str) -> Tuple[dict, list]:
    """Return (fields, checklist_unchecked) parsed from state.md.

    Field keys are lowercased; values are stripped of surrounding whitespace
    and inline HTML comments. Checklist items are collected only from the
    `## Phase Completion Checklist` section.
    """
    fields: dict = {}
    unchecked: list = []
    text = read_state_text(cwd)
    if text is None:
        return fields, unchecked

    in_checklist = False
    for raw in text.splitlines():
        heading = raw.strip().lower()
        if heading.startswith("## "):
            in_checklist = heading == "## phase completion checklist"
            continue
        m = _FIELD_RE.match(raw)
        if m:
            key = m.group(1).strip().lower()
            val = m.group(2).strip()
            val = re.sub(r"<!--.*?-->", "", val).strip()
            fields[key] = val
        elif in_checklist:
            u = _UNCHECKED_RE.match(raw)
            if u:
                unchecked.append(u.group(1).strip())
    return fields, unchecked


def get_field(cwd: str, name: str, default: str = "") -> str:
    """Return a single state.md field value, lowercased and stripped."""
    fields, _ = parse_state(cwd)
    return fields.get(name.strip().lower(), default).strip().lower()


def get_field_raw(cwd: str, name: str, default: str = "") -> str:
    """Return a single state.md field value preserving original case."""
    fields, _ = parse_state(cwd)
    return fields.get(name.strip().lower(), default).strip()


def atomic_write(path: str, content: str) -> None:
    """Write `content` to `path` atomically (temp + os.replace).

    Best-effort — silently swallows OS errors so hooks never crash on a
    transient filesystem issue. Hooks that need to know the write succeeded
    should re-read the file.
    """
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    except OSError:
        return


def update_state_field(cwd: str, field: str, value: str) -> bool:
    """Set one `- **Field**: value` line in state.md atomically.

    Returns True if the field was found and updated, False otherwise.
    """
    text = read_state_text(cwd)
    if text is None:
        return False
    pattern = re.compile(
        r"^(\s*-\s+\*\*" + re.escape(field) + r"\*\*:)\s*.*$",
        re.MULTILINE,
    )
    new, n = pattern.subn(rf"\1 {value}", text, count=1)
    if n == 0:
        return False
    if new != text:
        atomic_write(state_path(cwd), new)
    return True


def derive_session_id(input_data: dict) -> str:
    """Stable per-session identifier; falls back when Copilot omits sessionId."""
    sid = input_data.get("sessionId") or input_data.get("session_id")
    if sid:
        # Sanitise — sessionId can contain characters illegal in filenames.
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", str(sid))[:80]
        return safe or "anon"
    cwd = input_data.get("cwd") or os.getcwd()
    ppid = os.getppid()
    digest = hashlib.sha1(f"{cwd}|{ppid}".encode("utf-8")).hexdigest()[:12]
    return f"nosid-{digest}"


def session_log_path(cwd: str, session_id: str) -> str:
    return os.path.join(sessions_dir(cwd), f"{session_id}.md")


def append_session_log(cwd: str, session_id: str, line: str) -> None:
    """Append one line to the session log file, creating it if needed.

    Uses O_APPEND for atomic small-write semantics. Best-effort — swallows
    errors so the hook never breaks on an unwritable disk.
    """
    try:
        os.makedirs(sessions_dir(cwd), exist_ok=True)
        path = session_log_path(cwd, session_id)
        is_new = not os.path.exists(path)
        # O_APPEND ensures the kernel positions writes at end-of-file
        # atomically per write call (Linux guarantee for writes < PIPE_BUF).
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(path, flags, 0o644)
        try:
            payload = ""
            if is_new:
                payload = (
                    f"# Session {session_id}\n\n"
                    f"_Auto-generated by evidence-tracker.py — one line per "
                    f"tool call._\n\n"
                )
            payload += f"- {line}\n"
            os.write(fd, payload.encode("utf-8", errors="replace"))
        finally:
            os.close(fd)
    except OSError:
        return


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def update_active_session_link(cwd: str, session_id: str) -> None:
    """Set `- **Log**: sessions/<id>.md` under `## Active Session` in CURRENT-STATE.md.

    Best-effort and idempotent. If the line already points at this session,
    no write happens.
    """
    path = narrative_path(cwd)
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return
    target = f"sessions/{session_id}.md"
    pattern = re.compile(
        r"^(\s*-\s+\*\*Log\*\*:)\s*.*$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return
    if target in m.group(0):
        return
    new = pattern.sub(rf"\1 {target}", text, count=1)
    if new != text:
        atomic_write(path, new)


def is_unchecked_checklist(items: Iterable[str]) -> list:
    """Return the list as-is — kept as a thin alias for clarity at call sites."""
    return list(items)
