#!/usr/bin/env python3
from __future__ import annotations

import functools
import itertools
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


# As in Bash, only a brace pair holding a top-level comma expands: "{a}" stays literal.
def expand_braces(pattern: str) -> list[str]:
    for start, char in enumerate(pattern):
        if char != "{":
            continue
        depth = 0
        commas: list[int] = []
        end = start
        for end in range(start, len(pattern)):
            if pattern[end] == "{":
                depth += 1
            elif pattern[end] == "}":
                depth -= 1
                if depth == 0:
                    break
            elif pattern[end] == "," and depth == 1:
                commas.append(end)
        if depth != 0 or not commas:
            continue
        prefix, suffix = pattern[:start], pattern[end + 1 :]
        return [
            expanded
            for left, right in itertools.pairwise([start, *commas, end])
            for expanded in expand_braces(prefix + pattern[left + 1 : right] + suffix)
        ]
    return [pattern]


@functools.cache
def glob_to_regex(pattern: str) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{_regex_source(each)})" for each in expand_braces(pattern)))


def _regex_source(pattern: str) -> str:
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
    return "".join(parts)


def path_matches(pattern: str, path: str) -> bool:
    return glob_to_regex(pattern).fullmatch(path) is not None


def load_agent_globs(agents_dir: Path) -> dict[str, list[str]]:
    globs_by_agent: dict[str, list[str]] = {}
    for agent_file in sorted(agents_dir.glob("*.md")):
        try:
            content = agent_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        frontmatter = validate_config.parse_frontmatter(content)
        if frontmatter is None:
            continue
        name = frontmatter.get("name")
        if not name:
            continue
        globs = validate_config.parse_globs(frontmatter.get("globs", "")) or []
        globs_by_agent.setdefault(name, globs)
    return globs_by_agent


def excluding_pattern(globs: list[str], path: str) -> str | None:
    for glob in globs:
        if glob.startswith(NEGATION_PREFIX) and path_matches(
            glob.removeprefix(NEGATION_PREFIX), path
        ):
            return glob
    return None


def claims(globs: list[str], path: str) -> bool:
    return excluding_pattern(globs, path) is None and any(
        not glob.startswith(NEGATION_PREFIX) and path_matches(glob, path) for glob in globs
    )


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


def deny_reason(agent_name: str, path: str, pattern: str | None, owners: list[str]) -> str:
    causes: list[str] = []
    if pattern is not None:
        causes.append(f"its globs exclude it ({pattern})")
    if owners:
        causes.append(f"it is owned by {', '.join(owners)}")
    return (
        f"{agent_name} does not own {path}: {' and '.join(causes)}. Do not create, edit "
        "or delete it. Report the change it needs to the parent, which routes it to "
        "the owner."
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
    return ownership_reason(agent_name, path, relative, load_agent_globs(agents_dir))


def ownership_reason(
    agent_name: str, path: str, relative: str, globs_by_agent: dict[str, list[str]]
) -> str | None:
    # Agents without globs, such as build resolvers, must still edit files others own.
    own_globs = globs_by_agent.get(agent_name, [])
    if not own_globs:
        return None
    pattern = excluding_pattern(own_globs, relative)
    if pattern is None and claims(own_globs, relative):
        return None
    owners = sorted(
        name
        for name, globs in globs_by_agent.items()
        if name != agent_name and claims(globs, relative)
    )
    if pattern is None and not owners:
        return None
    return deny_reason(agent_name, path, pattern, owners)


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
