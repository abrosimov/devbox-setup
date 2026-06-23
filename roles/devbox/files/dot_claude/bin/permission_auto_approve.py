#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks

CD_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"^cd\s+[^&]+&&\s*")
ENV_ASSIGN_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z_][A-Z0-9_]*=\S*\s*")
TRAILING_REDIRECT_RE: Final[re.Pattern[str]] = re.compile(r"\s*2>&1\s*$")
SHELL_METACHARS: Final[tuple[str, ...]] = ("&&", "||", "|", ";", "$(", "`")

SAFE_COMMAND_FAMILIES: Final[tuple[str, ...]] = (
    "go build",
    "go test",
    "go vet",
    "go mod",
    "go get",
    "go install",
    "go generate",
    "go run",
    "goimports",
    "golangci-lint",
    "mockery",
    "sqlc",
    "uv ",
    "uv\t",
    "uvx ",
    "pytest",
    "ruff ",
    "mypy ",
    "python ",
    "python3 ",
    "npm ",
    "npx ",
    "pnpm ",
    "node ",
    "make ",
    "cargo ",
    "rustc ",
)

# Standalone commands (no argument). Exact match against the normalised string.
SAFE_STANDALONE: Final[frozenset[str]] = frozenset(
    {
        "echo",
        "printf",
        "id",
        "whoami",
        "hostname",
        "uname",
        "arch",
        "locale",
        "make",
    }
)


def _starts_with_word(cmd: str, word: str) -> bool:
    if not cmd.startswith(word):
        return False
    if len(cmd) == len(word):
        return True
    return cmd[len(word)] in (" ", "\t")


def is_simple_read_only(cmd: str) -> bool:
    if "|" in cmd or ">" in cmd:
        return False
    if cmd in SAFE_STANDALONE:
        return True
    return _starts_with_word(cmd, "echo") or _starts_with_word(cmd, "printf")


def is_existence_check(cmd: str) -> bool:
    return (
        _starts_with_word(cmd, "type")
        or cmd.startswith("command -v ")
        or _starts_with_word(cmd, "hash")
    )


def is_system_info(cmd: str) -> bool:
    if cmd in {"id", "whoami", "hostname", "uname", "arch"}:
        return True
    if _starts_with_word(cmd, "id") or _starts_with_word(cmd, "uname"):
        return True
    return cmd.startswith("sw_vers")


def is_terminal_query(cmd: str) -> bool:
    if cmd == "locale":
        return True
    return (
        _starts_with_word(cmd, "tput")
        or _starts_with_word(cmd, "stty")
        or _starts_with_word(cmd, "locale")
    )


def normalise(cmd: str) -> str:
    normalised = CD_PREFIX_RE.sub("", cmd, count=1)
    while True:
        match = ENV_ASSIGN_RE.match(normalised)
        if not match:
            break
        normalised = normalised[match.end() :]
    return TRAILING_REDIRECT_RE.sub("", normalised)


def has_shell_metachars(cmd: str) -> bool:
    return any(token in cmd for token in SHELL_METACHARS)


def is_safe_family(cmd: str) -> bool:
    return any(cmd.startswith(prefix) for prefix in SAFE_COMMAND_FAMILIES) or cmd == "make"


def _matches_quick_checks(cmd: str) -> bool:
    return (
        is_simple_read_only(cmd)
        or is_existence_check(cmd)
        or is_system_info(cmd)
        or is_terminal_query(cmd)
    )


def should_allow(tool_name: str, tool_input: dict[str, object]) -> bool:
    if tool_name != "Bash":
        return False
    command_value = tool_input.get("command", "")
    cmd = command_value if isinstance(command_value, str) else ""
    if not cmd:
        return False

    if _matches_quick_checks(cmd):
        return True

    normalised = normalise(cmd)
    if normalised == cmd:
        return False
    if has_shell_metachars(normalised):
        return False
    return is_safe_family(normalised)


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW

    tool_name_value = data.get("tool_name", "")
    tool_name = tool_name_value if isinstance(tool_name_value, str) else ""
    tool_input_value = data.get("tool_input", {})
    tool_input = tool_input_value if isinstance(tool_input_value, dict) else {}

    if should_allow(tool_name, tool_input):
        hooks.write_permission_request_decision("allow")
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
