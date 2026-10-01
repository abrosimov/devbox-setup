#!/usr/bin/env python3
# Stop hook enforcing the end-of-turn user-action section (USER_AUTHORITY_PROTOCOL.md section 4).
# Shipped byte-identical to ~/.codex/bin (Codex hooks must be self-contained): stdlib only.
from __future__ import annotations

import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

MAX_CONSECUTIVE_BLOCKS: Final[int] = 3
COUNTER_DIR: Final[Path] = Path(tempfile.gettempdir()) / "stop_user_actions_guard"
SECTION_TITLE: Final[str] = "What I need from you"
SHELL_FENCE_TAGS: Final[frozenset[str]] = frozenset(
    {"", "bash", "sh", "zsh", "fish", "shell", "console"},
)

HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^ {0,3}#{1,6}(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$"
)
FENCE_OPEN_RE: Final[re.Pattern[str]] = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*([^\s`{]*)")
INLINE_CODE_RE: Final[re.Pattern[str]] = re.compile(r"`+[^`]*`+")
SESSION_KEY_RE: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9_.-]")

# Russian match data, escaped to keep the source ASCII (re decodes the escapes).
# Section: "chto nuzhno ot vas". Requests: "zapusti(te)", "vypolni(te)", "progoni(te)",
# "vam nuzhno|neobkhodimo|nado zapustit'|vypolnit'|prognat'".
SECTION_TITLE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:what\s+i\s+need\s+from\s+you"
    r"|\u0447\u0442\u043e\s+\u043d\u0443\u0436\u043d\u043e\s+\u043e\u0442\s+\u0432\u0430\u0441)"
    r"\s*:?$",
    re.IGNORECASE,
)
USER_ACTION_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:please\s+run|you\s+need\s+to\s+run|you\s+should\s+run|run\s+the\s+following)\b"
    r"|(?<!\w)(?:\u0437\u0430\u043f\u0443\u0441\u0442\u0438"
    r"|\u0432\u044b\u043f\u043e\u043b\u043d\u0438"
    r"|\u043f\u0440\u043e\u0433\u043e\u043d\u0438)(?:\u0442\u0435)?(?!\w)"
    r"|(?<!\w)\u0432\u0430\u043c\s+"
    r"(?:\u043d\u0443\u0436\u043d\u043e|\u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e"
    r"|\u043d\u0430\u0434\u043e)\s+"
    r"(?:\u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c"
    r"|\u0432\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u044c"
    r"|\u043f\u0440\u043e\u0433\u043d\u0430\u0442\u044c)(?!\w)",
    re.IGNORECASE,
)
CONTROL_FLOW_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[;&|(){}])\s*"
    r"(?:if|then|elif|else|fi|for|while|until|do|done|case|esac|switch|end)(?![\w.-])",
)
HEREDOC_RE: Final[re.Pattern[str]] = re.compile(r"(?<!<)<<(?!<)-?[ \t]*['\"]?[A-Za-z_]")


@dataclass(frozen=True)
class Fence:
    tag: str
    body: tuple[str, ...]
    in_section: bool


@dataclass(frozen=True)
class ParsedMessage:
    section_found: bool
    headings_after_section: tuple[str, ...]
    fences: tuple[Fence, ...]
    prose_outside_section: tuple[str, ...]


def _heading_title(line: str) -> str | None:
    match = HEADING_RE.match(line)
    if match is None:
        return None
    return (match.group(1) or "").strip().strip("*_").strip()


def _is_section_title(title: str) -> bool:
    return SECTION_TITLE_RE.match(title) is not None


def parse_message(message: str) -> ParsedMessage:
    lines = message.splitlines()
    section_found = False
    in_section = False
    headings_after: list[str] = []
    fences: list[Fence] = []
    prose: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        opening = FENCE_OPEN_RE.match(line)
        if opening is not None:
            marker = opening.group(1)
            closing = re.compile(rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*$")
            body: list[str] = []
            index += 1
            while index < len(lines) and closing.match(lines[index]) is None:
                body.append(lines[index])
                index += 1
            index += 1
            fences.append(Fence(opening.group(2).lower(), tuple(body), in_section))
            continue
        title = _heading_title(line)
        if title is not None:
            if section_found:
                headings_after.append(title)
                in_section = False
            elif _is_section_title(title):
                section_found = True
                in_section = True
        elif not in_section:
            prose.append(line)
        index += 1
    return ParsedMessage(
        section_found=section_found,
        headings_after_section=tuple(headings_after),
        fences=tuple(fences),
        prose_outside_section=tuple(prose),
    )


def command_lines(body: tuple[str, ...]) -> list[str]:
    commands: list[str] = []
    pending = ""
    for raw in body:
        stripped = raw.strip()
        if not pending:
            if not stripped or stripped.startswith("#"):
                continue
            stripped = stripped.removeprefix("$ ")
        elif not stripped:
            commands.append(pending.strip())
            pending = ""
            continue
        joined = pending + stripped
        if joined.endswith("\\"):
            pending = joined[:-1] + " "
            continue
        commands.append(joined)
        pending = ""
    if pending.strip():
        commands.append(pending.strip())
    return commands


def _fence_problems(fence: Fence) -> list[str]:
    problems: list[str] = []
    commands = command_lines(fence.body)
    if len(commands) > 1:
        problems.append(f"holds {len(commands)} command lines")
    if any(CONTROL_FLOW_RE.search(command) for command in commands):
        problems.append("contains shell control flow")
    if any(HEREDOC_RE.search(line) for line in fence.body):
        problems.append("contains a heredoc")
    return problems


def _user_action_phrases(prose: tuple[str, ...]) -> list[str]:
    phrases: dict[str, None] = {}
    for line in prose:
        for match in USER_ACTION_RE.finditer(INLINE_CODE_RE.sub(" ", line)):
            phrases.setdefault(" ".join(match.group(0).split()), None)
    return list(phrases)


def find_violations(message: str) -> list[str]:
    parsed = parse_message(message)
    violations: list[str] = []
    if parsed.headings_after_section:
        following = ", ".join(f'"{title}"' for title in parsed.headings_after_section)
        violations.append(
            f'R1: "{SECTION_TITLE}" must be the last section, but it is followed by '
            f"{following}. Move that content above it.",
        )
    shell_fences = [
        fence for fence in parsed.fences if fence.in_section and fence.tag in SHELL_FENCE_TAGS
    ]
    for number, fence in enumerate(shell_fences, start=1):
        problems = _fence_problems(fence)
        if problems:
            violations.append(
                f'R2: command block {number} in "{SECTION_TITLE}" {" and ".join(problems)}. '
                "Turn it into a script under ai_written_scripts/<slug>/ (Go if go.mod is at "
                "the repository root, else Python run via uv), with a test when it has logic, "
                "and ask the user to run that single command.",
            )
    phrases = _user_action_phrases(parsed.prose_outside_section)
    if phrases:
        quoted = ", ".join(f'"{phrase}"' for phrase in phrases)
        violations.append(
            f"R3: the message asks the user to act outside the final section ({quoted}). "
            f'Move the action into the final "{SECTION_TITLE}" section with the exact command.',
        )
    return violations


def render_reason(violations: list[str]) -> str:
    bullets = "\n".join(f"- {violation}" for violation in violations)
    return f"End-of-turn user-action check failed. Rewrite the final message:\n{bullets}"


class BlockCounter:
    def __init__(self, directory: Path, session_id: object) -> None:
        raw = session_id if isinstance(session_id, str) else ""
        key = SESSION_KEY_RE.sub("_", raw)[:128] or "unknown"
        self.__directory = directory
        self.__path = directory / f"{key}.count"

    def read(self) -> int:
        try:
            return max(int(self.__path.read_text(encoding="utf-8").strip()), 0)
        except (OSError, ValueError):
            return 0

    def write(self, value: int) -> bool:
        try:
            self.__directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.__path.write_text(str(value), encoding="utf-8")
        except OSError as err:
            _log(f"cannot persist block counter {self.__path}: {err}")
            return False
        return True

    def reset(self) -> None:
        try:
            self.__path.unlink(missing_ok=True)
        except OSError as err:
            _log(f"cannot reset block counter {self.__path}: {err}")


def _log(message: str) -> None:
    sys.stderr.write(f"[stop-user-actions-guard] {message}\n")


def _parse_payload(raw: str) -> dict[str, object] | None:
    try:
        payload: object = json.loads(raw)
    except json.JSONDecodeError as err:
        _log(f"malformed Stop input, allowing: {err}")
        return None
    if not isinstance(payload, dict):
        _log("Stop input is not a JSON object, allowing")
        return None
    return payload


def evaluate(raw: str, counter_dir: Path) -> str | None:
    payload = _parse_payload(raw)
    if payload is None:
        return None
    message = payload.get("last_assistant_message")
    if not isinstance(message, str):
        _log("Stop input has no last_assistant_message, allowing")
        return None

    counter = BlockCounter(counter_dir, payload.get("session_id"))
    violations = find_violations(message)
    if not violations:
        counter.reset()
        return None

    # Only an explicit False marks a fresh stop chain; an absent flag keeps the stored count.
    previous = 0 if payload.get("stop_hook_active") is False else counter.read()
    if previous >= MAX_CONSECUTIVE_BLOCKS:
        counter.reset()
        _log(f"allowing after {previous} consecutive blocks: {'; '.join(violations)}")
        return None
    if not counter.write(previous + 1):
        return None
    return json.dumps({"decision": "block", "reason": render_reason(violations)})


def main() -> int:
    output = evaluate(sys.stdin.read(), COUNTER_DIR)
    if output is not None:
        sys.stdout.write(output)
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
