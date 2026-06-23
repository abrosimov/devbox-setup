#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, paths, proc

PY_MARKERS: Final[tuple[str, ...]] = ("pyproject.toml", "mypy.ini", ".mypy.ini", "setup.cfg")
TS_MARKERS: Final[tuple[str, ...]] = ("tsconfig.json",)
TYPECHECK_TIMEOUT: Final[int] = 30
MAX_REPORTED_LINES: Final[int] = 10


def edited_file_path(data: dict[str, object]) -> Path | None:
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_value = tool_input.get("file_path")
    if not isinstance(file_value, str) or not file_value:
        return None
    candidate = Path(file_value)
    if not candidate.exists():
        return None
    return candidate


def mypy_report(file_path: Path) -> str | None:
    project_root = paths.find_project_root(file_path.parent, PY_MARKERS)
    if project_root is None:
        return None
    use_uv = (project_root / "uv.lock").exists()
    cmd = ["uv", "run", "mypy", str(file_path)] if use_uv else ["mypy", str(file_path)]
    result = proc.run_cmd(cmd, cwd=project_root, timeout=TYPECHECK_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    if not combined:
        return None
    error_lines = [line for line in combined.splitlines() if ": error:" in line]
    if not error_lines:
        return None
    shown = error_lines[:MAX_REPORTED_LINES]
    suffix = (
        f"\n... and {len(error_lines) - MAX_REPORTED_LINES} more"
        if len(error_lines) > MAX_REPORTED_LINES
        else ""
    )
    return (
        f"[typecheck] mypy errors in {file_path.name}:\n"
        + "\n".join(shown)
        + suffix
        + "\nFix type errors — use proper types instead of Any."
    )


def tsc_report(file_path: Path) -> str | None:
    project_root = paths.find_project_root(file_path.parent, TS_MARKERS)
    if project_root is None:
        return None
    result = proc.run_cmd(["npx", "tsc", "--noEmit"], cwd=project_root, timeout=TYPECHECK_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    if not combined:
        return None
    try:
        rel = file_path.relative_to(project_root).as_posix()
    except ValueError:
        rel = str(file_path)
    candidates = {file_path.name, rel, str(file_path)}
    relevant = [
        line.strip()
        for line in combined.splitlines()
        if any(candidate in line for candidate in candidates)
    ]
    if not relevant:
        return None
    shown = relevant[:MAX_REPORTED_LINES]
    suffix = (
        f"\n... and {len(relevant) - MAX_REPORTED_LINES} more"
        if len(relevant) > MAX_REPORTED_LINES
        else ""
    )
    return f"[typecheck] TypeScript errors in {file_path.name}:\n" + "\n".join(shown) + suffix


def report_for(file_path: Path) -> str | None:
    ext = file_path.suffix.lower()
    if ext == ".py":
        return mypy_report(file_path)
    if ext in {".ts", ".tsx"}:
        return tsc_report(file_path)
    return None


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW
    file_path = edited_file_path(data)
    if file_path is None:
        return hooks.ALLOW
    message = report_for(file_path)
    if message is None:
        return hooks.ALLOW
    hooks.write_additional_context(message)
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
