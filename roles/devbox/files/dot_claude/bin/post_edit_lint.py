#!/usr/bin/env python3
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, lint, paths, proc

if TYPE_CHECKING:
    from collections.abc import Callable

    ReporterFn = Callable[[Path], "LintReport | None"]

GO_MARKERS: Final[tuple[str, ...]] = ("go.mod",)
ESLINT_MARKERS: Final[tuple[str, ...]] = (
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.ts",
)
LINT_TIMEOUT: Final[int] = 30


@dataclass(frozen=True)
class LintReport:
    tool: str
    body: str

    def render(self, file_name: str) -> str:
        return f"[lint] {self.tool} issues in {file_name}:\n{self.body}"


def non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def filter_lines_for_file(text: str, file_name: str) -> list[str]:
    return [line for line in text.splitlines() if file_name in line]


def hadolint_report(file_path: Path) -> LintReport | None:
    result = proc.run_cmd(["hadolint", str(file_path)], timeout=LINT_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    lines = non_empty_lines(combined)
    if not lines:
        return None
    return LintReport(tool="hadolint", body="\n".join(lines))


def dclint_report(file_path: Path) -> LintReport | None:
    result = proc.run_cmd(["dclint", str(file_path)], timeout=LINT_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    lines = non_empty_lines(combined)
    if not lines:
        return None
    return LintReport(tool="dclint", body="\n".join(lines))


def golangci_report(file_path: Path) -> LintReport | None:
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
    return LintReport(tool="golangci-lint", body="\n".join(lines))


def ruff_report(file_path: Path) -> LintReport | None:
    result = proc.run_cmd(["ruff", "check", str(file_path)], timeout=LINT_TIMEOUT)
    if result.success:
        return None
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    lines = non_empty_lines(combined)
    if not lines:
        return None
    return LintReport(tool="ruff", body="\n".join(lines))


def eslint_report(file_path: Path) -> LintReport | None:
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
    return LintReport(tool="eslint", body="\n".join(lines))


def is_dockerfile(file_path: Path) -> bool:
    name = file_path.name.lower()
    return name == "dockerfile" or name.startswith("dockerfile.") or name.endswith(".dockerfile")


def is_compose_file(file_path: Path) -> bool:
    name = file_path.name.lower()
    ext = file_path.suffix.lower()
    return ext in {".yml", ".yaml"} and name.startswith(("compose", "docker-compose"))


_EXT_REPORTERS: Final[dict[str, ReporterFn]] = {}


def _eslint_dispatch(path: Path) -> LintReport | None:
    return eslint_report(path)


def _register_reporters() -> None:
    _EXT_REPORTERS[".go"] = golangci_report
    _EXT_REPORTERS[".py"] = ruff_report
    for ext in (".ts", ".tsx", ".js", ".jsx"):
        _EXT_REPORTERS[ext] = _eslint_dispatch


_register_reporters()


def report_for(file_path: Path) -> LintReport | None:
    if is_dockerfile(file_path):
        return hadolint_report(file_path)
    if is_compose_file(file_path):
        return dclint_report(file_path)
    if lint.linter_for_file(file_path) is None:
        return None
    reporter = _EXT_REPORTERS.get(file_path.suffix.lower())
    if reporter is None:
        return None
    return reporter(file_path)


def edited_file_path(data: dict[str, object]) -> Path | None:
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_path_value = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(file_path_value, str) or not file_path_value:
        return None
    candidate = Path(file_path_value)
    if not candidate.exists():
        return None
    return candidate


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW
    file_path = edited_file_path(data)
    if file_path is None:
        return hooks.ALLOW

    report = report_for(file_path)
    if report is None:
        return hooks.ALLOW

    hooks.write_additional_context(
        report.render(file_path.name) + "\nFix these lint issues before proceeding.",
    )
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
