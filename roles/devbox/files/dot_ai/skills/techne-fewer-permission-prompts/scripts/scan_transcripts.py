#!/usr/bin/env python3
"""Scan recent Claude Code transcripts and tally Bash/MCP tool-call frequencies.

Two sources are merged:

  1. ~/.claude/projects/*/*.jsonl — transcripts (all tool calls)
  2. ~/.claude/state/missed_approvals/YYYY/MM/DD/HH.jsonl — telemetry from
     the bash_decision_gate hook (commands that did NOT auto-approve and
     thus prompted; the high-signal source for "what should be on the
     allowlist but isn't")

Emits JSON on stdout by default; pass ``--pretty`` for a human-readable table.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

MAX_FILES: Final[int] = 50
TOP_BASH: Final[int] = 60
TOP_MCP: Final[int] = 30
SAMPLE_LIMIT: Final[int] = 120

TELEMETRY_ROOT: Final[Path] = Path.home() / ".claude" / "state" / "missed_approvals"

ENV_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z_][A-Z0-9_]*=\S+\s+")
SUBSHELL_LEADERS: Final[frozenset[str]] = frozenset(
    {"sudo", "timeout", "nice", "env", "command", "exec", "time"},
)


def split_pipes(cmd: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_squote = False
    in_dquote = False
    i = 0
    n = len(cmd)
    while i < n:
        c = cmd[i]
        if c == "'" and not in_dquote:
            in_squote = not in_squote
            buf.append(c)
        elif c == '"' and not in_squote:
            in_dquote = not in_dquote
            buf.append(c)
        elif not (in_squote or in_dquote):
            two = cmd[i : i + 2]
            if two in ("&&", "||"):
                parts.append("".join(buf).strip())
                buf = []
                i += 2
                continue
            if c in "|;":
                parts.append("".join(buf).strip())
                buf = []
                i += 1
                continue
            buf.append(c)
        else:
            buf.append(c)
        i += 1
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


def extract_head(cmd: str) -> tuple[str, str] | None:
    cmd = cmd.strip()
    while True:
        m = ENV_RE.match(cmd)
        if not m:
            break
        cmd = cmd[m.end() :]
    tokens = cmd.split()
    if not tokens:
        return None
    while tokens and tokens[0] in SUBSHELL_LEADERS:
        tokens = tokens[1:]
        # Strip flags and numeric args belonging to the stripped leader
        # (e.g. ``sudo -E``, ``timeout 30``).
        while tokens and (tokens[0].startswith("-") or tokens[0].isdigit()):
            tokens = tokens[1:]
    if not tokens:
        return None
    head = tokens[0]
    if "/" in head:
        head = head.rsplit("/", 1)[-1]
    sub = ""
    for t in tokens[1:]:
        if not t.startswith("-"):
            sub = t
            break
    return head, sub


def discover_transcripts() -> list[Path]:
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return []
    files = [p for p in root.glob("*/*.jsonl") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:MAX_FILES]


def discover_telemetry() -> list[Path]:
    """Find hourly missed-approval shards under TELEMETRY_ROOT.

    Layout: YYYY/MM/DD/HH.jsonl. Newest-first ordering by path components
    (date is in the path; no stat call needed).
    """
    if not TELEMETRY_ROOT.is_dir():
        return []
    files = [p for p in TELEMETRY_ROOT.glob("*/*/*/*.jsonl") if p.is_file()]
    files.sort(key=lambda p: p.parts[-4:], reverse=True)
    return files


def _iter_telemetry_cmds(path: Path) -> Iterator[str]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cmd = obj.get("cmd")
                if isinstance(cmd, str) and cmd.strip():
                    yield cmd
    except OSError:
        return


def _iter_tool_uses(path: Path) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                out.extend(
                    c for c in content if isinstance(c, dict) and c.get("type") == "tool_use"
                )
    except OSError:
        return []
    return out


def _absorb_bash(
    use: dict[str, object],
    counts: Counter[tuple[str, str]],
    samples: dict[tuple[str, str], str],
) -> None:
    inp = use.get("input")
    if not isinstance(inp, dict):
        return
    cmd = inp.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return
    _absorb_bash_cmd(cmd, counts, samples)


def _absorb_bash_cmd(
    cmd: str,
    counts: Counter[tuple[str, str]],
    samples: dict[tuple[str, str], str],
) -> None:
    """Shared cmd-string ingester used by both transcript and telemetry sources."""
    for segment in split_pipes(cmd):
        head = extract_head(segment)
        if head is None:
            continue
        counts[head] += 1
        if head not in samples:
            sample = segment.strip()
            if len(sample) > SAMPLE_LIMIT:
                sample = sample[: SAMPLE_LIMIT - 3] + "..."
            samples[head] = sample


def tally(
    files: list[Path],
    telemetry_files: list[Path] | None = None,
) -> tuple[Counter[tuple[str, str]], dict[tuple[str, str], str], Counter[str]]:
    bash_counts: Counter[tuple[str, str]] = Counter()
    bash_samples: dict[tuple[str, str], str] = {}
    mcp_counts: Counter[str] = Counter()
    for f in files:
        for use in _iter_tool_uses(f):
            name = use.get("name")
            if not isinstance(name, str):
                continue
            if name == "Bash":
                _absorb_bash(use, bash_counts, bash_samples)
            elif name.startswith("mcp__"):
                mcp_counts[name] += 1
    for t in telemetry_files or []:
        for cmd in _iter_telemetry_cmds(t):
            _absorb_bash_cmd(cmd, bash_counts, bash_samples)
    return bash_counts, bash_samples, mcp_counts


def build_payload(
    files: list[Path],
    bash_counts: Counter[tuple[str, str]],
    bash_samples: dict[tuple[str, str], str],
    mcp_counts: Counter[str],
    telemetry_files: list[Path] | None = None,
) -> dict[str, object]:
    bash_rows = [
        {"cmd": cmd, "sub": sub, "count": count, "sample": bash_samples.get((cmd, sub), "")}
        for (cmd, sub), count in bash_counts.most_common(TOP_BASH)
    ]
    mcp_rows = [{"name": name, "count": count} for name, count in mcp_counts.most_common(TOP_MCP)]
    return {
        "scanned_files": len(files),
        "scanned_telemetry": len(telemetry_files or []),
        "bash": bash_rows,
        "mcp": mcp_rows,
    }


def render_pretty(payload: dict[str, object]) -> str:
    lines: list[str] = []
    scanned = payload.get("scanned_files", 0)
    scanned_telemetry = payload.get("scanned_telemetry", 0)
    lines.append(f"Scanned {scanned} transcript(s), {scanned_telemetry} telemetry shard(s)")
    lines.append("")
    lines.append("Bash:")
    bash = payload.get("bash")
    if isinstance(bash, list) and bash:
        for row in bash:
            if not isinstance(row, dict):
                continue
            count = row.get("count", 0)
            cmd = str(row.get("cmd", ""))
            sub = str(row.get("sub", ""))
            sample = str(row.get("sample", ""))
            lines.append(f"  {count:>5}  {cmd:<20} {sub:<24} | {sample}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("MCP:")
    mcp = payload.get("mcp")
    if isinstance(mcp, list) and mcp:
        for row in mcp:
            if not isinstance(row, dict):
                continue
            count = row.get("count", 0)
            name = str(row.get("name", ""))
            lines.append(f"  {count:>5}  {name}")
    else:
        lines.append("  (none)")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    pretty = "--pretty" in argv[1:]
    skip_telemetry = "--no-telemetry" in argv[1:]
    files = discover_transcripts()
    telemetry_files = [] if skip_telemetry else discover_telemetry()
    bash_counts, bash_samples, mcp_counts = tally(files, telemetry_files)
    payload = build_payload(files, bash_counts, bash_samples, mcp_counts, telemetry_files)
    if pretty:
        sys.stdout.write(render_pretty(payload))
    else:
        json.dump(payload, sys.stdout, indent=2, sort_keys=False)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
