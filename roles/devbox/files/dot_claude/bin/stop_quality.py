#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, paths, proc

GIT_TIMEOUT: Final[int] = 10
FORMAT_TIMEOUT: Final[int] = 15
CHECK_TIMEOUT: Final[int] = 30
PIPELINE_TIMEOUT: Final[int] = 50

GO_MARKERS: Final[tuple[str, ...]] = ("go.mod",)
RUFF_MARKERS: Final[tuple[str, ...]] = (
    "pyproject.toml",
    "ruff.toml",
    ".ruff.toml",
)
PRETTIER_MARKERS: Final[tuple[str, ...]] = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.js",
    ".prettierrc.cjs",
    "prettier.config.js",
    "prettier.config.cjs",
    "prettier.config.mjs",
    "package.json",
)
ESLINT_MARKERS: Final[tuple[str, ...]] = (
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.yaml",
    ".eslintrc.yml",
    ".eslintrc.js",
    ".eslintrc.cjs",
    "eslint.config.js",
    "eslint.config.cjs",
    "eslint.config.mjs",
    "eslint.config.ts",
)
TYPESCRIPT_MARKERS: Final[tuple[str, ...]] = ("tsconfig.json",)
JAVASCRIPT_EXTENSIONS: Final[frozenset[str]] = frozenset({".js", ".jsx", ".ts", ".tsx"})
TYPESCRIPT_EXTENSIONS: Final[frozenset[str]] = frozenset({".ts", ".tsx"})
GO_MODULE_RE: Final[re.Pattern[str]] = re.compile(r"^module\s+(\S+)", re.MULTILINE)
MYPY_PYPROJECT_RE: Final[re.Pattern[str]] = re.compile(r"^\[tool\.mypy\]\s*$", re.MULTILINE)
MYPY_SETUP_RE: Final[re.Pattern[str]] = re.compile(r"^\[mypy\]\s*$", re.MULTILINE)
BLACK_PYPROJECT_RE: Final[re.Pattern[str]] = re.compile(r"^\[tool\.black\]\s*$", re.MULTILINE)
BLACK_PRECOMMIT_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:-\s*)?repo:\s*\S*/psf/black(?:-pre-commit-mirror)?(?:\.git)?\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class ChangeSet:
    root: Path
    files: tuple[Path, ...]


@dataclass
class QualityPipeline:
    expires_at: float
    clock: Callable[[], float]
    advisories: list[str]

    @classmethod
    def start(
        cls,
        timeout: int = PIPELINE_TIMEOUT,
        clock: Callable[[], float] = time.monotonic,
    ) -> QualityPipeline:
        return cls(expires_at=clock() + timeout, clock=clock, advisories=[])

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        cap: int,
        label: str,
    ) -> proc.CmdResult | None:
        remaining = int(self.expires_at - self.clock())
        if remaining < 1:
            self.advisories.append(f"{label}: skipped because the pipeline deadline was exhausted")
            return None
        timeout = min(cap, remaining)
        result = proc.run_cmd(command, cwd=cwd, timeout=timeout)
        if result.timed_out:
            self.advisories.append(f"{label}: timed out after {timeout}s")
        return result


def collect_git_changes(
    cwd: Path,
    pipeline: QualityPipeline | None = None,
) -> ChangeSet | None:
    active_pipeline = pipeline or QualityPipeline.start()
    root_result = active_pipeline.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        cap=GIT_TIMEOUT,
        label="Git repository discovery",
    )
    if root_result is None or not root_result.success or not root_result.stdout.strip():
        return None

    root = Path(root_result.stdout.rstrip("\r\n")).resolve()
    tracked = active_pipeline.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", "HEAD", "--"],
        cwd=root,
        cap=GIT_TIMEOUT,
        label="Git tracked-change discovery",
    )
    untracked = active_pipeline.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z", "--"],
        cwd=root,
        cap=GIT_TIMEOUT,
        label="Git untracked-file discovery",
    )

    relative_paths: set[str] = set()
    for result in (tracked, untracked):
        if result is not None and result.success:
            relative_paths.update(name for name in result.stdout.split("\0") if name)

    files: list[Path] = []
    for name in sorted(relative_paths):
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        candidate = root / relative
        if candidate.is_symlink():
            continue
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved.is_relative_to(root) and resolved.is_file():
            files.append(candidate)
    return ChangeSet(root=root, files=tuple(files))


def _group_by_root(
    files: tuple[Path, ...],
    extensions: frozenset[str],
    markers: tuple[str, ...],
    fallback: Path | None,
) -> dict[Path, tuple[Path, ...]]:
    grouped: dict[Path, list[Path]] = {}
    for file_path in files:
        if file_path.suffix.lower() not in extensions:
            continue
        root = paths.find_project_root(file_path.parent, markers) or fallback
        if root is not None:
            grouped.setdefault(root, []).append(file_path)
    return {
        root: tuple(grouped[root])
        for root in sorted(grouped, key=lambda candidate: candidate.as_posix())
    }


def _ancestors_within(start: Path, boundary: Path) -> tuple[Path, ...]:
    resolved_boundary = boundary.resolve()
    current = start.resolve()
    if not current.is_relative_to(resolved_boundary):
        return ()
    ancestors: list[Path] = []
    while True:
        ancestors.append(current)
        if current == resolved_boundary:
            return tuple(ancestors)
        current = current.parent


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _find_mypy_root(start: Path, boundary: Path) -> Path | None:
    for candidate in _ancestors_within(start, boundary):
        if (candidate / "mypy.ini").is_file() or (candidate / ".mypy.ini").is_file():
            return candidate
        if MYPY_PYPROJECT_RE.search(_read_text(candidate / "pyproject.toml")):
            return candidate
        if MYPY_SETUP_RE.search(_read_text(candidate / "setup.cfg")):
            return candidate
    return None


def _package_has_eslint_config(path: Path) -> bool:
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and "eslintConfig" in data


def _find_eslint_root(start: Path, boundary: Path) -> Path | None:
    for candidate in _ancestors_within(start, boundary):
        if any((candidate / marker).is_file() for marker in ESLINT_MARKERS):
            return candidate
        if _package_has_eslint_config(candidate / "package.json"):
            return candidate
    return None


def _group_by_finder(
    files: tuple[Path, ...],
    extensions: frozenset[str],
    boundary: Path,
    finder: Callable[[Path, Path], Path | None],
) -> dict[Path, tuple[Path, ...]]:
    grouped: dict[Path, list[Path]] = {}
    for file_path in files:
        if file_path.suffix.lower() not in extensions:
            continue
        root = finder(file_path.parent, boundary)
        if root is not None:
            grouped.setdefault(root, []).append(file_path)
    return {
        root: tuple(grouped[root])
        for root in sorted(grouped, key=lambda candidate: candidate.as_posix())
    }


def _go_groups(files: tuple[Path, ...]) -> dict[Path, tuple[Path, ...]]:
    return _group_by_root(files, frozenset({".go"}), GO_MARKERS, None)


def _go_module(root: Path) -> str | None:
    try:
        content = (root / "go.mod").read_text(encoding="utf-8")
    except OSError:
        return None
    match = GO_MODULE_RE.search(content)
    return match.group(1) if match else None


def _goimports_command(root: Path, pipeline: QualityPipeline) -> str:
    result = pipeline.run(
        ["go", "env", "GOPATH"],
        cwd=root,
        cap=FORMAT_TIMEOUT,
        label=f"go env GOPATH ({root})",
    )
    if result is not None and result.success and result.stdout.strip():
        first_gopath = result.stdout.strip().split(os.pathsep, maxsplit=1)[0]
        candidate = Path(first_gopath) / "bin" / "goimports"
        if candidate.is_file():
            return str(candidate)
    return "goimports"


def _run_formatter(
    command: list[str],
    *,
    cwd: Path,
    label: str,
    count: int,
    pipeline: QualityPipeline,
) -> None:
    result = pipeline.run(
        command,
        cwd=cwd,
        cap=FORMAT_TIMEOUT,
        label=f"{label} ({cwd})",
    )
    if result is not None and result.success:
        sys.stderr.write(f"[stop-quality] {label}: formatted {count} file(s)\n")


def _format_go(changes: ChangeSet, pipeline: QualityPipeline) -> None:
    groups = _go_groups(changes.files)
    if not groups:
        return
    goimports = _goimports_command(next(iter(groups)), pipeline)
    for root, files in groups.items():
        module = _go_module(root)
        if module is None:
            continue
        command = [goimports, "-local", module, "-w", *(str(file_path) for file_path in files)]
        _run_formatter(
            command,
            cwd=root,
            label="goimports",
            count=len(files),
            pipeline=pipeline,
        )


def _uses_black(root: Path) -> bool:
    return bool(
        BLACK_PYPROJECT_RE.search(_read_text(root / "pyproject.toml"))
        or BLACK_PRECOMMIT_RE.search(_read_text(root / ".pre-commit-config.yaml"))
    )


def _format_python(changes: ChangeSet, pipeline: QualityPipeline) -> None:
    groups = _group_by_root(
        changes.files,
        frozenset({".py"}),
        RUFF_MARKERS,
        changes.root,
    )
    for root, files in groups.items():
        file_args = [str(file_path) for file_path in files]
        _run_formatter(
            ["ruff", "check", "--fix", "--quiet", *file_args],
            cwd=root,
            label="ruff check --fix",
            count=len(files),
            pipeline=pipeline,
        )
        if _uses_black(root):
            # ruff format and black disagree on layout, so a black project gets
            # only its own pinned black; any other version would fight its CI.
            black = root / ".venv" / "bin" / "black"
            if not black.is_file():
                pipeline.advisories.append(
                    f"black ({root}): the project formats with black but {black} "
                    "is missing, so formatting was skipped"
                )
                continue
            _run_formatter(
                [str(black), "--quiet", *file_args],
                cwd=root,
                label="black",
                count=len(files),
                pipeline=pipeline,
            )
            continue
        _run_formatter(
            ["ruff", "format", "--quiet", *file_args],
            cwd=root,
            label="ruff format",
            count=len(files),
            pipeline=pipeline,
        )


def _format_javascript(changes: ChangeSet, pipeline: QualityPipeline) -> None:
    groups = _group_by_root(
        changes.files,
        JAVASCRIPT_EXTENSIONS,
        PRETTIER_MARKERS,
        None,
    )
    for root, files in groups.items():
        command = ["npx", "prettier", "--write", *(str(file_path) for file_path in files)]
        _run_formatter(
            command,
            cwd=root,
            label="prettier",
            count=len(files),
            pipeline=pipeline,
        )


def format_changes(
    changes: ChangeSet,
    pipeline: QualityPipeline | None = None,
) -> QualityPipeline:
    active_pipeline = pipeline or QualityPipeline.start()
    _format_go(changes, active_pipeline)
    _format_python(changes, active_pipeline)
    _format_javascript(changes, active_pipeline)
    return active_pipeline


def _combined_output(result: proc.CmdResult) -> str:
    return "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)


def _issue_from_result(label: str, result: proc.CmdResult) -> str | None:
    if result.success or result.timed_out:
        return None
    output = _combined_output(result)
    if not output:
        return f"{label}: exited with status {result.returncode}"
    return f"{label}:\n{output}"


def _filtered_issue(
    label: str,
    result: proc.CmdResult,
    files: tuple[Path, ...],
    root: Path,
) -> str | None:
    if result.success or result.timed_out:
        return None
    output = _combined_output(result)
    needles = {
        needle
        for file_path in files
        for needle in (file_path.name, file_path.relative_to(root).as_posix())
    }
    lines = [line for line in output.splitlines() if any(needle in line for needle in needles)]
    if not lines:
        return None
    return f"{label}:\n" + "\n".join(lines)


def _is_dockerfile(file_path: Path) -> bool:
    name = file_path.name.lower()
    return name == "dockerfile" or name.startswith("dockerfile.") or name.endswith(".dockerfile")


def _is_compose_file(file_path: Path) -> bool:
    name = file_path.name.lower()
    return file_path.suffix.lower() in {".yml", ".yaml"} and name.startswith(
        ("compose", "docker-compose"),
    )


def _lint_containers(changes: ChangeSet, pipeline: QualityPipeline) -> list[str]:
    issues: list[str] = []
    dockerfiles = tuple(file_path for file_path in changes.files if _is_dockerfile(file_path))
    if dockerfiles:
        result = pipeline.run(
            ["hadolint", *(str(file_path) for file_path in dockerfiles)],
            cwd=changes.root,
            cap=CHECK_TIMEOUT,
            label="hadolint",
        )
        issue = _issue_from_result("hadolint", result) if result is not None else None
        if issue is not None:
            issues.append(issue)

    compose_files = tuple(file_path for file_path in changes.files if _is_compose_file(file_path))
    if compose_files:
        result = pipeline.run(
            ["dclint", *(str(file_path) for file_path in compose_files)],
            cwd=changes.root,
            cap=CHECK_TIMEOUT,
            label="dclint",
        )
        issue = _issue_from_result("dclint", result) if result is not None else None
        if issue is not None:
            issues.append(issue)
    return issues


def _go_targets(root: Path, files: tuple[Path, ...]) -> list[str]:
    relative_dirs = {file_path.parent.relative_to(root).as_posix() for file_path in files}
    if "." in relative_dirs:
        return ["./..."]
    return [f"./{relative_dir}/..." for relative_dir in sorted(relative_dirs)]


def _lint_go(changes: ChangeSet, pipeline: QualityPipeline) -> list[str]:
    issues: list[str] = []
    for root, files in _go_groups(changes.files).items():
        result = pipeline.run(
            ["golangci-lint", "run", "--fast", *_go_targets(root, files)],
            cwd=root,
            cap=CHECK_TIMEOUT,
            label=f"golangci-lint ({root})",
        )
        issue = (
            _filtered_issue("golangci-lint", result, files, root) if result is not None else None
        )
        if issue is not None:
            issues.append(issue)
    return issues


def _lint_python(changes: ChangeSet, pipeline: QualityPipeline) -> list[str]:
    issues: list[str] = []
    groups = _group_by_root(
        changes.files,
        frozenset({".py"}),
        RUFF_MARKERS,
        changes.root,
    )
    for root, files in groups.items():
        file_args = [str(file_path) for file_path in files]
        ruff_result = pipeline.run(
            ["ruff", "check", *file_args],
            cwd=root,
            cap=CHECK_TIMEOUT,
            label=f"ruff ({root})",
        )
        ruff_issue = _issue_from_result("ruff", ruff_result) if ruff_result is not None else None
        if ruff_issue is not None:
            issues.append(ruff_issue)

    mypy_groups = _group_by_finder(
        changes.files,
        frozenset({".py"}),
        changes.root,
        _find_mypy_root,
    )
    for root, files in mypy_groups.items():
        file_args = [str(file_path) for file_path in files]
        command = (
            ["uv", "run", "mypy", *file_args]
            if (root / "uv.lock").exists()
            else [
                "mypy",
                *file_args,
            ]
        )
        mypy_result = pipeline.run(
            command,
            cwd=root,
            cap=CHECK_TIMEOUT,
            label=f"mypy ({root})",
        )
        mypy_issue = _issue_from_result("mypy", mypy_result) if mypy_result is not None else None
        if mypy_issue is not None:
            issues.append(mypy_issue)
    return issues


def _lint_javascript(changes: ChangeSet, pipeline: QualityPipeline) -> list[str]:
    issues: list[str] = []
    eslint_groups = _group_by_finder(
        changes.files,
        JAVASCRIPT_EXTENSIONS,
        changes.root,
        _find_eslint_root,
    )
    for root, files in eslint_groups.items():
        result = pipeline.run(
            [
                "npx",
                "eslint",
                "--no-error-on-unmatched-pattern",
                *(str(file_path) for file_path in files),
            ],
            cwd=root,
            cap=CHECK_TIMEOUT,
            label=f"eslint ({root})",
        )
        issue = _issue_from_result("eslint", result) if result is not None else None
        if issue is not None:
            issues.append(issue)

    typescript_groups = _group_by_root(
        changes.files,
        TYPESCRIPT_EXTENSIONS,
        TYPESCRIPT_MARKERS,
        None,
    )
    for root, files in typescript_groups.items():
        result = pipeline.run(
            ["npx", "tsc", "--noEmit"],
            cwd=root,
            cap=CHECK_TIMEOUT,
            label=f"tsc ({root})",
        )
        issue = _filtered_issue("tsc", result, files, root) if result is not None else None
        if issue is not None:
            issues.append(issue)
    return issues


def lint_changes(
    changes: ChangeSet,
    pipeline: QualityPipeline | None = None,
) -> list[str]:
    active_pipeline = pipeline or QualityPipeline.start()
    return [
        *_lint_containers(changes, active_pipeline),
        *_lint_go(changes, active_pipeline),
        *_lint_python(changes, active_pipeline),
        *_lint_javascript(changes, active_pipeline),
    ]


def render_message(issues: list[str], advisories: list[str]) -> str:
    sections: list[str] = []
    if issues:
        sections.append(
            f"Quality checks reported {len(issues)} issue group(s).\n\n" + "\n\n".join(issues),
        )
    if advisories:
        sections.append(
            "Quality checks were incomplete:\n" + "\n".join(f"- {item}" for item in advisories),
        )
    return (
        "[stop-quality] "
        + "\n\n".join(sections)
        + "\n\nFix reported issues and run incomplete checks before completing the task."
    )


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data or data.get("stop_hook_active"):
        return hooks.ALLOW

    pipeline = QualityPipeline.start()
    changes = collect_git_changes(Path.cwd(), pipeline)
    if changes is None or not changes.files:
        if pipeline.advisories:
            hooks.write_additional_context(render_message([], pipeline.advisories))
        return hooks.ALLOW

    format_changes(changes, pipeline)
    issues = lint_changes(changes, pipeline)
    if issues or pipeline.advisories:
        hooks.write_additional_context(render_message(issues, pipeline.advisories))
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
