#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, proc


@dataclass
class State:
    branch: str = "unknown"
    modified: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)


def _git_lines(args: list[str], cwd: Path) -> list[str]:
    result = proc.run_cmd(["git", *args], cwd=cwd, timeout=5)
    if not result.success:
        return []
    return [line for line in result.stdout.splitlines() if line]


def current_branch(cwd: Path) -> str:
    result = proc.run_cmd(["git", "branch", "--show-current"], cwd=cwd, timeout=5)
    if not result.success:
        return "unknown"
    branch = result.stdout.strip()
    return branch or "unknown"


def collect_state(cwd: Path) -> State:
    state = State()
    state.branch = current_branch(cwd)
    state.modified = _git_lines(["diff", "--name-only"], cwd)[:20]
    state.staged = _git_lines(["diff", "--cached", "--name-only"], cwd)[:20]
    return state


def render(state: State) -> str:
    lines: list[str] = [
        "--- CONTEXT PRESERVED ACROSS COMPACTION ---",
        "",
        f"Branch: {state.branch}",
    ]
    if state.modified:
        lines.append("Modified files:")
        lines.extend(f"  - {f}" for f in state.modified)
    if state.staged:
        lines.append("Staged files:")
        lines.extend(f"  - {f}" for f in state.staged)
    lines.append("--- END PRESERVED CONTEXT ---")
    return "\n".join(lines) + "\n"


def main() -> int:
    env.setup()
    cwd_value = os.environ.get("PWD") or str(Path.cwd())
    cwd = Path(cwd_value)
    sys.stdout.write(render(collect_state(cwd)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
