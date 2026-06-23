#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, paths, proc

if TYPE_CHECKING:
    from collections.abc import Callable

LINT_TIMEOUT: Final[int] = 30
GO_MARKERS: Final[tuple[str, ...]] = ("go.mod",)
PY_MARKERS: Final[tuple[str, ...]] = ("pyproject.toml", "mypy.ini", ".mypy.ini", "setup.cfg")
TS_MARKERS: Final[tuple[str, ...]] = ("tsconfig.json",)
ESLINT_MARKERS: Final[tuple[str, ...]] = (
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.ts",
)
LINTABLE_EXTS: Final[frozenset[str]] = frozenset(
    {
        ".go",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".yml",
        ".yaml",
    }
)


def is_dockerfile(file_path: Path) -> bool:
    name = file_path.name.lower()
    return name == "dockerfile" or name.startswith("dockerfile.") or name.endswith(".dockerfile")


def is_compose_file(file_path: Path) -> bool:
    name = file_path.name.lower()
    ext = file_path.suffix.lower()
    return ext in {".yml", ".yaml"} and name.startswith(("compose", "docker-compose"))


def is_lintable(file_path: Path) -> bool:
    return file_path.suffix.lower() in LINTABLE_EXTS or is_dockerfile(file_path)


def non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def filter_lines_for_file(text: str, file_name: str) -> list[str]:
    return [line for line in text.splitlines() if file_name in line]


def lint_dockerfile(file_path: Path) -> str | None:
    result = proc.run_cmd(["hadolint", str(file_path)], timeout=LINT_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    lines = non_empty_lines(combined)
    if not lines:
        return None
    return "hadolint: " + "\n".join(lines)


def lint_compose(file_path: Path) -> str | None:
    result = proc.run_cmd(["dclint", str(file_path)], timeout=LINT_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    lines = non_empty_lines(combined)
    if not lines:
        return None
    return "dclint: " + "\n".join(lines)


def lint_go(file_path: Path) -> str | None:
    project_root = paths.find_project_root(file_path.parent, GO_MARKERS)
    if project_root is None:
        return None
    try:
        rel_dir = file_path.parent.relative_to(project_root).as_posix()
    except ValueError:
        return None
    target = f"./{rel_dir}/..." if rel_dir and rel_dir != "." else "./..."
    result = proc.run_cmd(
        ["golangci-lint", "run", "--fast", target],
        cwd=project_root,
        timeout=LINT_TIMEOUT,
    )
    if result.success:
        return None
    lines = filter_lines_for_file(result.stdout, file_path.name)
    if not lines:
        return None
    return "golangci-lint:\n" + "\n".join(lines)


def lint_python(file_path: Path) -> str | None:
    result = proc.run_cmd(["ruff", "check", str(file_path)], timeout=LINT_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    lines = non_empty_lines(combined)
    if not lines:
        return None
    return "ruff:\n" + "\n".join(lines)


def lint_javascript(file_path: Path) -> str | None:
    project_root = paths.find_project_root(file_path.parent, ESLINT_MARKERS)
    if project_root is None:
        return None
    result = proc.run_cmd(
        ["npx", "eslint", "--no-error-on-unmatched-pattern", str(file_path)],
        cwd=project_root,
        timeout=LINT_TIMEOUT,
    )
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    lines = non_empty_lines(combined)
    if not lines:
        return None
    return "eslint:\n" + "\n".join(lines)


_LINT_BY_EXT: Final[dict[str, Callable[[Path], str | None]]] = {}


def _register_lint_dispatch() -> None:
    _LINT_BY_EXT[".go"] = lint_go
    _LINT_BY_EXT[".py"] = lint_python
    for ext in (".ts", ".tsx", ".js", ".jsx"):
        _LINT_BY_EXT[ext] = lint_javascript


_register_lint_dispatch()


def lint_file(file_path: Path) -> str | None:
    if not file_path.exists():
        return None
    if is_dockerfile(file_path):
        return lint_dockerfile(file_path)
    if is_compose_file(file_path):
        return lint_compose(file_path)
    dispatcher = _LINT_BY_EXT.get(file_path.suffix.lower())
    if dispatcher is None:
        return None
    return dispatcher(file_path)


def typecheck_python(file_path: Path) -> str | None:
    project_root = paths.find_project_root(file_path.parent, PY_MARKERS)
    if project_root is None:
        return None
    use_uv = (project_root / "uv.lock").exists()
    cmd = ["uv", "run", "mypy", str(file_path)] if use_uv else ["mypy", str(file_path)]
    result = proc.run_cmd(cmd, cwd=project_root, timeout=LINT_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    if not combined:
        return None
    lines = [line for line in combined.splitlines() if ": error:" in line]
    if not lines:
        return None
    return "mypy:\n" + "\n".join(lines)


def typecheck_typescript(file_path: Path) -> str | None:
    project_root = paths.find_project_root(file_path.parent, TS_MARKERS)
    if project_root is None:
        return None
    result = proc.run_cmd(["npx", "tsc", "--noEmit"], cwd=project_root, timeout=LINT_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    if not combined:
        return None
    lines = [line for line in combined.splitlines() if file_path.name in line and "error" in line]
    if not lines:
        return None
    return "tsc:\n" + "\n".join(lines)


def typecheck_file(file_path: Path) -> str | None:
    if not file_path.exists():
        return None
    ext = file_path.suffix.lower()
    if ext == ".py":
        return typecheck_python(file_path)
    if ext in {".ts", ".tsx"}:
        return typecheck_typescript(file_path)
    return None


def modified_files(cwd: Path) -> list[Path]:
    result = proc.run_cmd(["git", "diff", "--name-only", "HEAD"], cwd=cwd, timeout=10)
    if not result.success or not result.stdout.strip():
        return []
    out: list[Path] = []
    for raw in result.stdout.splitlines():
        rel = raw.strip()
        if not rel:
            continue
        candidate = (cwd / rel).resolve()
        if candidate.exists() and is_lintable(candidate):
            out.append(candidate)
    return out


def collect_issues(files: list[Path]) -> list[str]:
    issues: list[str] = []
    for file_path in files:
        lint_result = lint_file(file_path)
        if lint_result:
            issues.append(f"{file_path.name}:\n{lint_result}")
        type_result = typecheck_file(file_path)
        if type_result:
            issues.append(f"{file_path.name}:\n{type_result}")
    return issues


def render_message(issues: list[str]) -> str:
    return (
        f"[stop-lint-gate] Cannot complete: {len(issues)} file(s) have lint issues.\n\n"
        + "\n\n".join(issues)
        + "\n\nFix all lint issues before completing the task."
    )


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW

    if data.get("stop_hook_active"):
        return hooks.ALLOW

    cwd = Path.cwd()
    files = modified_files(cwd)
    if not files:
        return hooks.ALLOW

    issues = collect_issues(files)
    if not issues:
        return hooks.ALLOW

    hooks.write_additional_context(render_message(issues))
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
