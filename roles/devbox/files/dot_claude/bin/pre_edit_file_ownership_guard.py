#!/usr/bin/env python3
from __future__ import annotations

import posixpath
import re
import sys
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_config
from _claude_lib import hooks

AGENTS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "agents"
NEGATION_PREFIX: Final[str] = "!"
TARGET_PATH_KEYS: Final[tuple[str, ...]] = ("file_path", "notebook_path")
GIT_ENTRY: Final[str] = ".git"


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    # A relative pattern not starting with "**" matches at any depth, as in .gitignore.
    anchored = pattern.startswith(("/", "**"))
    parts: list[str] = [] if anchored else ["(?:.*/)?"]
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            parts.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(parts))


def path_matches(pattern: str, path: str) -> bool:
    return glob_to_regex(pattern).fullmatch(path) is not None


def agent_globs(agents_dir: Path, agent_name: str) -> list[str]:
    for agent_file in sorted(agents_dir.glob("*.md")):
        try:
            content = agent_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        frontmatter = validate_config.parse_frontmatter(content)
        if frontmatter is None or frontmatter.get("name") != agent_name:
            continue
        return validate_config.parse_globs(frontmatter.get("globs", "")) or []
    return []


def excluding_pattern(globs: list[str], path: str) -> str | None:
    for glob in globs:
        if glob.startswith(NEGATION_PREFIX) and path_matches(
            glob.removeprefix(NEGATION_PREFIX), path
        ):
            return glob
    return None


def target_path(tool_input: dict[str, object]) -> str:
    for key in TARGET_PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return posixpath.normpath(Path(value).as_posix())
    return ""


def repository_root(path: Path) -> Path | None:
    for ancestor in path.parents:
        try:
            if (ancestor / GIT_ENTRY).exists():
                return ancestor
        except OSError:
            return None
    return None


# Relative to the repository, so a checkout under a directory named "tests" is not a test file.
def matched_path(path: str, cwd: str) -> str:
    target = Path(path)
    if not target.is_absolute():
        return path
    root = repository_root(target)
    if root is not None:
        return target.relative_to(root).as_posix()
    if cwd:
        base = Path(posixpath.normpath(cwd))
        if base.is_absolute() and target.is_relative_to(base):
            return target.relative_to(base).as_posix()
    return path


def deny_reason(agent_name: str, path: str, pattern: str) -> str:
    return (
        f"{agent_name} does not own {path}: its globs exclude it ({pattern}). "
        "Test files are owned by the test writers (unit-test-writer, the "
        "integration-tests-writer agents, fuzzing-tests-writer). Do not create, edit "
        "or delete them. If a test fails after your change, stop and report to the "
        "parent: the test, its output, and whether you believe the test or the code "
        "is wrong."
    )


def decide(data: dict[str, object], agents_dir: Path) -> str | None:
    agent_name = data.get("agent_type")
    if not isinstance(agent_name, str) or not agent_name:
        return None
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    path = target_path(tool_input)
    if not path:
        return None
    cwd = data.get("cwd")
    relative = matched_path(path, cwd if isinstance(cwd, str) else "")
    pattern = excluding_pattern(agent_globs(agents_dir, agent_name), relative)
    if pattern is None:
        return None
    return deny_reason(agent_name, path, pattern)


def main() -> int:
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW
    reason = decide(data, AGENTS_DIR)
    if reason is not None:
        hooks.write_decision("deny", reason)
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
