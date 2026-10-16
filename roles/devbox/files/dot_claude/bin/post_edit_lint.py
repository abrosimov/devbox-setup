#!/usr/bin/env python3
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, findings, hooks, lint, paths, proc, session_state

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
    findings: tuple[findings.Finding, ...]


def _combined(result: proc.CmdResult) -> str:
    return "\n".join(part for part in (result.stdout, result.stderr) if part)


def _report(
    tool: str,
    file_path: Path,
    found: list[findings.Finding],
) -> LintReport | None:
    own = findings.for_file(found, file_path)
    return LintReport(tool=tool, findings=tuple(own)) if own else None


def hadolint_report(file_path: Path) -> LintReport | None:
    result = proc.run_cmd(
        ["hadolint", "--no-color", str(file_path)],
        cwd=file_path.parent,
        timeout=LINT_TIMEOUT,
    )
    found = findings.parse_located_lines(_combined(result), file_path.parent)
    return _report("hadolint", file_path, findings.drop_hadolint_low_severity(found))


def dclint_report(file_path: Path) -> LintReport | None:
    result = proc.run_cmd(
        ["dclint", "--formatter", "json", str(file_path)],
        cwd=file_path.parent,
        timeout=LINT_TIMEOUT,
    )
    return _report("dclint", file_path, findings.parse_json_report(result.stdout, file_path.parent))


def golangci_report(file_path: Path) -> LintReport | None:
    project_root = paths.find_project_root(file_path.parent, GO_MARKERS)
    if project_root is None:
        return None
    try:
        rel_dir = file_path.parent.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return None
    target = f"./{rel_dir}/..." if rel_dir and rel_dir != "." else "./..."
    result = proc.run_cmd(
        [
            "golangci-lint",
            "run",
            "--fast-only",
            "--output.text.print-issued-lines=false",
            "--output.text.colors=false",
            target,
        ],
        cwd=project_root,
        timeout=LINT_TIMEOUT,
    )
    found = findings.parse_located_lines(result.stdout, project_root)
    return _report("golangci-lint", file_path, found)


def ruff_report(file_path: Path) -> LintReport | None:
    result = proc.run_cmd(
        ["ruff", "check", "--output-format", "concise", str(file_path)],
        cwd=file_path.parent,
        timeout=LINT_TIMEOUT,
    )
    return _report("ruff", file_path, findings.parse_located_lines(result.stdout, file_path.parent))


def eslint_report(file_path: Path) -> LintReport | None:
    project_root = paths.find_project_root(file_path.parent, ESLINT_MARKERS)
    if project_root is None:
        return None
    result = proc.run_cmd(
        ["npx", "eslint", "--no-error-on-unmatched-pattern", "--format", "json", str(file_path)],
        cwd=project_root,
        timeout=LINT_TIMEOUT,
    )
    return _report("eslint", file_path, findings.parse_json_report(result.stdout, project_root))


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


# A deletion marks the line now standing where the removed text was. A Write
# that creates a file has an empty patch: None, the whole file is the edit.
def touched_lines(data: dict[str, object]) -> frozenset[int] | None:
    response = data.get("tool_response")
    if not isinstance(response, dict):
        return None
    patch = response.get("structuredPatch")
    if not isinstance(patch, list) or not patch:
        return None
    lines: set[int] = set()
    for hunk in patch:
        if not isinstance(hunk, dict):
            return None
        current = hunk.get("newStart")
        body = hunk.get("lines")
        if not isinstance(current, int) or not isinstance(body, list):
            return None
        for entry in body:
            marker = entry[:1] if isinstance(entry, str) else ""
            if marker == "+":
                lines.add(current)
                current += 1
            elif marker == "-":
                lines.add(max(current, 1))
            elif marker != "\\":
                current += 1
    return frozenset(lines)


def _source_lines(file_path: Path) -> list[str]:
    try:
        return file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _unseen(
    state: session_state.SessionState,
    tool: str,
    file_path: Path,
    reported: list[findings.Finding],
) -> list[findings.Finding]:
    source = _source_lines(file_path)
    seen = state.seen_keys()
    fresh = {key: item for item in reported if (key := item.dedupe_key(tool, source)) not in seen}
    state.mark_seen(fresh)
    return list(fresh.values())


def render_message(tool: str, file_path: Path, reported: list[findings.Finding]) -> str:
    body = "\n".join(item.render() for item in reported)
    return (
        f"[lint] {tool} reported {len(reported)} issue(s) on lines your edit touched "
        f"in {file_path.name}:\n{body}\n"
        "Fix the issues your edit introduced. If one was already there before your edit "
        "and lies outside your task, leave it and mention it in your report."
    )


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW
    file_path = edited_file_path(data)
    if file_path is None or paths.is_temp_path(file_path):
        return hooks.ALLOW

    state = session_state.SessionState.from_hook_input(data)
    if state is not None:
        state.record_edit(file_path)

    report = report_for(file_path)
    if report is None:
        return hooks.ALLOW
    reported = findings.on_lines(report.findings, touched_lines(data))
    if state is not None and reported:
        reported = _unseen(state, report.tool, file_path, reported)
    if not reported:
        return hooks.ALLOW

    hooks.write_additional_context(render_message(report.tool, file_path, reported))
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
