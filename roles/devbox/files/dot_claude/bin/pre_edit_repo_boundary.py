#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import hooks, paths

EDIT_TOOLS: Final[frozenset[str]] = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
CLAUDE_STATE_DIRS: Final[tuple[str, ...]] = ("memory", "plans", "projects")


def target_path(data: dict[str, object]) -> Path | None:
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    value = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(value, str) or not value:
        return None
    return Path(value).expanduser()


def hook_cwd(data: dict[str, object]) -> Path:
    cwd = data.get("cwd")
    return Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()


# CLAUDE_PROJECT_DIR is where the session started; a later `cd` in Bash moves the
# hook's cwd but must not move the boundary with it.
def session_project(data: dict[str, object]) -> Path:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    start = (Path(project_dir) if project_dir else hook_cwd(data)).resolve()
    return paths.find_git_root(start) or start


def exempt_roots() -> tuple[Path, ...]:
    claude_home = Path.home() / ".claude"
    return (
        *paths.temp_roots(),
        *((claude_home / name).resolve() for name in CLAUDE_STATE_DIRS),
    )


def boundary_reason(data: dict[str, object]) -> str | None:
    if data.get("tool_name") not in EDIT_TOOLS:
        return None
    target = target_path(data)
    if target is None:
        return None
    if not target.is_absolute():
        target = hook_cwd(data) / target
    resolved = target.resolve()
    project = session_project(data)
    if resolved.is_relative_to(project) or paths.is_within(resolved, exempt_roots()):
        return None
    return (
        f"{resolved} is outside this session's project ({project}). Editing another "
        "repository needs the user's explicit go."
    )


def main() -> int:
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW
    reason = boundary_reason(data)
    if reason is not None:
        hooks.write_decision("ask", reason)
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
