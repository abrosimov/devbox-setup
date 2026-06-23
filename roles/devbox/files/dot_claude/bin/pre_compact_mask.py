#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, io_json, proc


@dataclass
class State:
    branch: str = "unknown"
    modified: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    pipeline_state_path: str | None = None
    pipeline_state_stages: list[tuple[str, str]] = field(default_factory=list)
    workflow_active: bool = False


PIPELINE_PATTERNS: tuple[str, ...] = (
    "docs/implementation_plans/*/pipeline_state.json",
    ".claude/pipeline_state.json",
)


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


def find_pipeline_state(cwd: Path) -> str | None:
    for pattern in PIPELINE_PATTERNS:
        for candidate in sorted(cwd.glob(pattern)):
            if candidate.is_file():
                return str(candidate)
    return None


def read_pipeline_stages(state_path: str) -> list[tuple[str, str]]:
    try:
        data = io_json.load_json(Path(state_path))
    except (OSError, ValueError, TypeError):
        return []
    stages_value = data.get("stages")
    if not isinstance(stages_value, dict):
        return []
    out: list[tuple[str, str]] = []
    for key, value in stages_value.items():
        if not isinstance(value, dict):
            continue
        status_value = value.get("status", "")
        status = status_value if isinstance(status_value, str) else ""
        if status and status != "pending":
            out.append((str(key), status))
    return out


def workflow_active(cwd: Path) -> bool:
    return (cwd / ".claude" / "workflow.json").is_file()


def collect_state(cwd: Path) -> State:
    state = State()
    state.branch = current_branch(cwd)
    state.modified = _git_lines(["diff", "--name-only"], cwd)[:20]
    state.staged = _git_lines(["diff", "--cached", "--name-only"], cwd)[:20]
    state.pipeline_state_path = find_pipeline_state(cwd)
    if state.pipeline_state_path:
        state.pipeline_state_stages = read_pipeline_stages(state.pipeline_state_path)
    state.workflow_active = workflow_active(cwd)
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
    if state.pipeline_state_path:
        lines.append(f"Pipeline state: {state.pipeline_state_path}")
        for name, status in state.pipeline_state_stages:
            lines.append(f"  {name}: {status}")
    if state.workflow_active:
        lines.append("Workflow: active")
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
