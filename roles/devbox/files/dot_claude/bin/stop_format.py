#!/usr/bin/env python3
"""stop-format — Stop hook that auto-formats git-modified files at turn end.

Stdlib only — no external dependencies.

Event: Stop
Exit codes:
    0  — always. The hook is advisory; per-file errors are swallowed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# Matches the legacy Node hook's 15s ceiling.
FORMATTER_TIMEOUT_SEC: int = 15

MAX_PARENT_WALK: int = 20

PRETTIER_MARKERS: tuple[str, ...] = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.js",
    "prettier.config.js",
    "package.json",
)

GO_MODULE_RE = re.compile(r"^module\s+(\S+)", re.MULTILINE)


def _run(argv: list[str], *, cwd: str | None = None) -> bool:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=FORMATTER_TIMEOUT_SEC,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _capture(argv: list[str]) -> str | None:
    try:
        out = subprocess.check_output(
            argv,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=FORMATTER_TIMEOUT_SEC,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return out.strip()


def _walk_ancestors(start_dir: Path, predicate: Callable[[Path], bool]) -> Path | None:
    current = start_dir
    for _ in range(MAX_PARENT_WALK):
        if predicate(current):
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return None


def _find_go_module(file_path: str) -> str | None:
    def has_gomod(d: Path) -> bool:
        return (d / "go.mod").is_file()

    module_dir = _walk_ancestors(Path(file_path).parent, has_gomod)
    if module_dir is None:
        return None
    try:
        with (module_dir / "go.mod").open(encoding="utf-8") as fh:
            match = GO_MODULE_RE.search(fh.read())
    except OSError:
        return None
    return match.group(1) if match else None


def _find_prettier_root(file_path: str) -> Path | None:
    def has_marker(d: Path) -> bool:
        return any((d / m).exists() for m in PRETTIER_MARKERS)

    return _walk_ancestors(Path(file_path).parent, has_marker)


def _log(tool: str, file_path: str) -> None:
    sys.stderr.write(f"[stop-format] {tool} → {Path(file_path).name}\n")


def format_go(file_path: str) -> str | None:
    module = _find_go_module(file_path)
    if module is None:
        return None
    gopath = _capture(["go", "env", "GOPATH"])
    goimports = f"{gopath}/bin/goimports" if gopath else "goimports"
    if _run([goimports, "-local", module, "-w", file_path]):
        return "goimports"
    return None


def format_python(file_path: str) -> str | None:
    check_ok = _run(["ruff", "check", "--fix", "--quiet", file_path])
    format_ok = _run(["ruff", "format", "--quiet", file_path])
    if check_ok and format_ok:
        return "ruff"
    if format_ok:
        return "ruff (format only)"
    if check_ok:
        return "ruff (check only)"
    return None


def format_prettier(file_path: str) -> str | None:
    root = _find_prettier_root(file_path)
    if root is None:
        return None
    if _run(["npx", "prettier", "--write", file_path], cwd=str(root)):
        return "prettier"
    return None


FORMATTERS: dict[str, Callable[[str], str | None]] = {
    ".go": format_go,
    ".py": format_python,
    ".ts": format_prettier,
    ".tsx": format_prettier,
    ".js": format_prettier,
    ".jsx": format_prettier,
}


def _git_modified_files() -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=FORMATTER_TIMEOUT_SEC,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    cwd = Path.cwd()
    files: list[str] = []
    for line in out.splitlines():
        rel = line.strip()
        if not rel:
            continue
        abs_path = cwd / rel
        if abs_path.is_file():
            files.append(str(abs_path))
    return files


def main() -> int:
    raw = sys.stdin.read()
    if raw.strip():
        try:
            json.loads(raw)
        except ValueError:
            sys.stderr.write("[stop-format] warning: invalid stdin JSON, formatting anyway\n")

    for file_path in _git_modified_files():
        ext = Path(file_path).suffix.lower()
        formatter = FORMATTERS.get(ext)
        if formatter is None:
            continue
        tool = formatter(file_path)
        if tool is not None:
            _log(tool, file_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
