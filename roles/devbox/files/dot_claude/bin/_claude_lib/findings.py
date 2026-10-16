from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable

LOCATED_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<path>[^\s:][^:]*):(?P<line>\d+)(?::\d+)?:?\s+(?P<message>\S.*)$",
)
HADOLINT_LOW_SEVERITY_RE: Final[re.Pattern[str]] = re.compile(r"^\S+ (?:info|style): ")
JSON_SEVERITY_NAMES: Final[dict[object, str]] = {1: "warning", 2: "error"}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path.name}:{self.line}: {self.message}"

    def dedupe_key(self, tool: str, source_lines: list[str]) -> str:
        # Keyed on the flagged source text rather than the line number, so a
        # finding that only moved because lines above it changed stays the same.
        index = self.line - 1
        source = source_lines[index].strip() if 0 <= index < len(source_lines) else ""
        material = "\0".join((tool, str(self.path), self.message, source))
        return "lint:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def _resolve(raw: str, cwd: Path) -> Path:
    candidate = Path(raw)
    return (candidate if candidate.is_absolute() else cwd / candidate).resolve()


def parse_located_lines(output: str, cwd: Path) -> list[Finding]:
    found: list[Finding] = []
    for line in output.splitlines():
        match = LOCATED_LINE_RE.match(line.strip())
        if match is None:
            continue
        found.append(
            Finding(
                path=_resolve(match.group("path"), cwd),
                line=int(match.group("line")),
                message=match.group("message").strip(),
            ),
        )
    return found


def parse_json_report(output: str, cwd: Path) -> list[Finding]:
    try:
        data: object = json.loads(output)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    found: list[Finding] = []
    for file_entry in data:
        if not isinstance(file_entry, dict):
            continue
        raw_path = file_entry.get("filePath")
        messages = file_entry.get("messages")
        if not isinstance(raw_path, str) or not isinstance(messages, list):
            continue
        path = _resolve(raw_path, cwd)
        for message in messages:
            if not isinstance(message, dict):
                continue
            line = message.get("line")
            text = message.get("message")
            if not isinstance(line, int) or not isinstance(text, str):
                continue
            severity = message.get("type") or JSON_SEVERITY_NAMES.get(message.get("severity"))
            rule = message.get("ruleId") or message.get("rule")
            parts = [str(severity) if severity else "", text, f"({rule})" if rule else ""]
            found.append(Finding(path=path, line=line, message=" ".join(p for p in parts if p)))
    return found


def drop_hadolint_low_severity(findings: Iterable[Finding]) -> list[Finding]:
    return [item for item in findings if not HADOLINT_LOW_SEVERITY_RE.match(item.message)]


def drop_hadolint_low_severity_lines(output: str) -> str:
    kept: list[str] = []
    for line in output.splitlines():
        match = LOCATED_LINE_RE.match(line.strip())
        if match and HADOLINT_LOW_SEVERITY_RE.match(match.group("message")):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def for_file(findings: Iterable[Finding], target: Path) -> list[Finding]:
    resolved = target.resolve()
    return [item for item in findings if item.path == resolved]


def on_lines(findings: Iterable[Finding], lines: frozenset[int] | None) -> list[Finding]:
    if lines is None:
        return list(findings)
    return [item for item in findings if item.line in lines]
