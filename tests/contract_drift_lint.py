#!/usr/bin/env python3
"""Contract-drift lint. Catches the class of bug we kept shipping patches for:

  v1.2.1 — Stage routing wrote 'Next Prompt: /code-review' while the field
           value was missing from VALID_NEXT_PROMPTS.
  v1.2.2 — Prompt prose said 'Set Design Plan / Status' but no helper or
           edit path existed, so the agent hit a guardrail dead-end.
  v1.2.3 — /design-plan body said 'Hand off to product-owner / critic' but
           the planner agent had no 'agent' tool and no 'agents:' whitelist
           to actually dispatch them.

Common shape: prose promises a behavior the contract doesn't support.
This lint compares every documented value / reference in prompt + agent
files against the source-of-truth contract (vocabulary in _state_io.py,
agent files on disk, hook scripts on disk, prompt files on disk).

Categories:
  A. Agent 'agents:' frontmatter references must resolve to an agent file
     (template or catalog) or 'Explore'.
  B. When a prompt pins a non-builder agent and its body says 'hand off /
     dispatch / invoke <subagent>', that pinned agent must declare the
     'agent' tool and list <subagent> in its 'agents:' whitelist.
  C. Every '/<command>' slash-command reference (excluding URL paths,
     glob patterns, and file paths) must resolve to a real prompt or be
     in the catalog.
  D. Every 'Next Prompt: /foo' value must be in VALID_NEXT_PROMPTS.
  E. Every 'Stage: foo' value must be in VALID_STAGES.
  F. Every 'Blocked Kind: foo' value must be in VALID_BLOCKED_KINDS.
  G. Every '.github/hooks/scripts/<name>.py' reference must exist.

Usage: contract_drift_lint.py <generated-workspace-root>
"""
import pathlib
import re
import sys


def split_fm(text):
    if not text.startswith("---"):
        return "", text
    end = text.find("---", 3)
    return (text[3:end], text[end + 3:]) if end > 0 else ("", text)


def yaml_list(fm, key):
    m = re.search(rf"^{key}:\s*$\n((?:[ \t]+-[ \t]*\S.*\n?)+)", fm, re.MULTILINE)
    if m:
        return re.findall(r"-\s*([^\s#]+)", m.group(1))
    m = re.search(rf"^{key}:\s*\[(.*?)\]", fm, re.MULTILINE)
    if m:
        return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]
    return []


def yaml_scalar(fm, key):
    m = re.search(rf"^{key}:\s*(\S.*?)\s*$", fm, re.MULTILINE)
    return m.group(1).strip() if m else None


def main(root_arg):
    ROOT = pathlib.Path(root_arg)
    PROMPTS = sorted((ROOT / ".github/prompts").glob("*.prompt.md"))
    AGENTS = sorted((ROOT / ".github/agents").glob("*.agent.md"))
    CATALOG_AGENTS = sorted((ROOT / ".github/catalog/agents").glob("*.agent.md"))
    CATALOG_PROMPTS = sorted((ROOT / ".github/catalog/prompts").glob("*.prompt.md"))
    HOOK_SCRIPTS = {p.name for p in (ROOT / ".github/hooks/scripts").glob("*.py")}

    state_io = (ROOT / ".github/hooks/scripts/_state_io.py").read_text()

    def vocab(name):
        m = re.search(rf"{name}\s*=\s*\{{(.*?)\}}", state_io, re.DOTALL)
        return set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()

    VALID_STAGES = vocab("VALID_STAGES")
    VALID_BLOCKED_KINDS = vocab("VALID_BLOCKED_KINDS")
    VALID_NEXT_PROMPTS = vocab("VALID_NEXT_PROMPTS")

    AGENT_NAMES = {p.stem.replace(".agent", "") for p in AGENTS}
    AGENT_NAMES |= {p.stem.replace(".agent", "") for p in CATALOG_AGENTS}
    AGENT_NAMES |= {"Explore"}

    PROMPT_NAMES = {p.stem.replace(".prompt", "") for p in PROMPTS}
    PROMPT_NAMES |= {p.stem.replace(".prompt", "") for p in CATALOG_PROMPTS}
    # VS Code built-ins / common safe-list slash commands the human may type.
    PROMPT_NAMES |= {"resume", "clear", "help", "new", "compact", "explain", "fix"}

    failures = []

    # A. agents: references resolve.
    for f in AGENTS:
        fm, _ = split_fm(f.read_text())
        for a in yaml_list(fm, "agents"):
            if a == "*":
                continue
            if a not in AGENT_NAMES:
                failures.append(
                    f"A {f.name}: declares subagent '{a}' (no agent file in template or catalog)"
                )

    # B. Pinned-agent prompts: body handoffs must match pinned-agent's tools+agents.
    handoff_re = re.compile(
        r"\b(?:hand off to|dispatch(?:es)?|invoke|invokes|delegates? to)\s+"
        r"(?:the\s+)?\*{0,2}([a-z][a-z-]*)\*{0,2}",
        re.IGNORECASE,
    )
    for prompt in PROMPTS:
        fm, body = split_fm(prompt.read_text())
        pinned = yaml_scalar(fm, "agent")
        if not pinned or pinned == "autonomous-builder":
            continue
        pf = ROOT / f".github/agents/{pinned}.agent.md"
        if not pf.exists():
            failures.append(f"B {prompt.name}: pins agent '{pinned}' (no file)")
            continue
        pfm, _ = split_fm(pf.read_text())
        p_tools = set(yaml_list(pfm, "tools"))
        p_agents = set(yaml_list(pfm, "agents"))
        refs = {
            m.group(1)
            for m in handoff_re.finditer(body)
            if m.group(1) in AGENT_NAMES and m.group(1) != pinned
        }
        if refs and "agent" not in p_tools:
            failures.append(
                f"B {prompt.name}: pins '{pinned}' (no 'agent' tool) but body handoffs to {sorted(refs)}"
            )
        if "agent" in p_tools and p_agents and (refs - p_agents):
            failures.append(
                f"B {prompt.name}: handoffs to {sorted(refs - p_agents)} not in {pinned}.agents"
            )

    # C. Slash-command references resolve. Exclude URL paths, file paths, globs.
    slash_re = re.compile(
        r"(?<![\w./*])/([a-z][a-z0-9-]+)(?=\s|[.,;:)`'\"]|$)", re.MULTILINE
    )
    path_hint_re = re.compile(
        r"(?:https?://|github\.com|2>|\.github/|docs/|roadmap/|tests/|catalog/|memories/|/dev/|/tmp/|/var/)",
        re.IGNORECASE,
    )
    for f in PROMPTS + AGENTS:
        text = f.read_text()
        for m in slash_re.finditer(text):
            cmd = m.group(1)
            if cmd in PROMPT_NAMES:
                continue
            win = text[max(0, m.start() - 30): m.end() + 30]
            if path_hint_re.search(win):
                continue
            failures.append(
                f"C {f.name}: '/{cmd}' is not a known prompt and no path-like context nearby"
            )

    # D/E/F. Vocab values in `Field: value` literal shapes.
    # Match three real shapes seen in the codebase:
    #   `Field: value`        — whole phrase in a single backtick block
    #   `Field`: `value`      — separate backtick blocks
    #   Field: value          — bare (in stage-table cells)
    # The leading and trailing backticks are optional; the inner colon is
    # required.
    next_re = re.compile(r"`?Next Prompt`?:\s*`?(/[a-z][a-z0-9-]*)`?")
    stage_re = re.compile(r"`?Stage`?:\s*`?([a-z][a-z-]+)`?")
    bk_re = re.compile(r"`?Blocked Kind`?:\s*`?([a-z][a-z-]+)`?")
    # Conservative value-token denylist to suppress matches against meta-words
    # ("the Stage value", "Stage field name") — those don't end in real vocab.
    META = {"value", "field", "name", "x", "n"}
    for f in PROMPTS + AGENTS:
        text = f.read_text()
        for m in next_re.finditer(text):
            if m.group(1) not in VALID_NEXT_PROMPTS:
                failures.append(
                    f"D {f.name}: 'Next Prompt: {m.group(1)}' not in VALID_NEXT_PROMPTS"
                )
        for m in stage_re.finditer(text):
            v = m.group(1)
            if v in META:
                continue
            if v not in VALID_STAGES:
                failures.append(f"E {f.name}: 'Stage: {v}' not in VALID_STAGES")
        for m in bk_re.finditer(text):
            v = m.group(1)
            if v in META:
                continue
            if v not in VALID_BLOCKED_KINDS:
                failures.append(
                    f"F {f.name}: 'Blocked Kind: {v}' not in VALID_BLOCKED_KINDS"
                )

    # G. Hook script references exist.
    hook_ref_re = re.compile(r"\.github/hooks/scripts/([a-z_-]+\.py)")
    candidates = list(PROMPTS) + list(AGENTS) + [ROOT / "AGENTS.md"]
    for f in candidates:
        if not f.exists():
            continue
        for m in hook_ref_re.finditer(f.read_text()):
            if m.group(1) not in HOOK_SCRIPTS:
                failures.append(f"G {f.name}: references missing hook script '{m.group(1)}'")

    if failures:
        print("FAIL: contract drift detected:")
        for fail in failures:
            print(f"  {fail}")
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: contract_drift_lint.py <generated-workspace-root>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
