#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, paths

UV_LOCK: Final[str] = "uv.lock"
POETRY_LOCK: Final[str] = "poetry.lock"
PNPM_LOCK: Final[str] = "pnpm-lock.yaml"
YARN_LOCK: Final[str] = "yarn.lock"
NPM_LOCK: Final[str] = "package-lock.json"

PYTHON_SCRIPT_RE: Final[re.Pattern[str]] = re.compile(r"^python3?\s+(?!-)")


@dataclass(frozen=True)
class Block:
    message: str


def _starts_with(cmd: str, prefix: str) -> bool:
    return cmd == prefix or cmd.startswith((prefix + " ", prefix + "\t"))


def _has_marker(start: Path, marker: str) -> bool:
    root = paths.find_project_root(start, (marker,))
    return root is not None


def _check_go_fmt(cmd: str) -> Block | None:
    if "go fmt" in cmd or "gofmt" in cmd:
        return Block(
            "Use `goimports -local <module-name>`, not go fmt/gofmt. "
            "Extract module name from go.mod.",
        )
    return None


def _check_pip(cmd: str) -> Block | None:
    pip_prefixes = (
        "pip install",
        "pip3 install",
        "python -m pip",
        "python3 -m pip",
    )
    for prefix in pip_prefixes:
        if cmd.startswith(prefix):
            return Block(
                "Use `uv add <package>` (or `poetry add` in poetry projects). "
                "Never use pip install directly.",
            )
    return None


def _check_venv(cmd: str) -> Block | None:
    venv_prefixes = ("python -m venv", "python3 -m venv")
    for prefix in venv_prefixes:
        if cmd.startswith(prefix):
            return Block(
                "Do not create venvs manually. Use `uv sync` — uv creates "
                "and manages .venv automatically.",
            )
    return None


def _check_python_tool(cmd: str, tool: str, start: Path) -> Block | None:
    if not (_starts_with(cmd, tool) or _starts_with(cmd, f"python -m {tool}")):
        return None
    if _has_marker(start, UV_LOCK):
        return Block(
            f"This is a uv project. Use `uv run {tool}` instead of bare `{tool}`.",
        )
    if _has_marker(start, POETRY_LOCK):
        return Block(
            f"This is a poetry project. Use `poetry run {tool}` instead of bare `{tool}`.",
        )
    return None


def _check_pytest(cmd: str, start: Path) -> Block | None:
    if _starts_with(cmd, "pytest") or _starts_with(cmd, "python -m pytest"):
        return _check_python_tool(cmd, "pytest", start)
    return None


def _check_mypy(cmd: str, start: Path) -> Block | None:
    if not _starts_with(cmd, "mypy"):
        return None
    return _check_python_tool(cmd, "mypy", start)


def _check_pylint(cmd: str, start: Path) -> Block | None:
    if not _starts_with(cmd, "pylint"):
        return None
    if _has_marker(start, UV_LOCK):
        return Block("This is a uv project. Use `uv run pylint` instead of bare `pylint`.")
    return None


def _check_bare_python_script(cmd: str, start: Path) -> Block | None:
    if not PYTHON_SCRIPT_RE.match(cmd):
        return None
    if _has_marker(start, UV_LOCK):
        return Block(
            "This is a uv project. Use `uv run python ...` instead of bare `python`.",
        )
    if _has_marker(start, POETRY_LOCK):
        return Block(
            "This is a poetry project. Use `poetry run python ...` instead of bare `python`.",
        )
    return None


def _npm_block_for_pnpm(start: Path) -> Block | None:
    if _has_marker(start, PNPM_LOCK):
        return Block(
            "This is a pnpm project (pnpm-lock.yaml exists). Use `pnpm install` / `pnpm add`.",
        )
    return None


def _npm_block_for_yarn(start: Path) -> Block | None:
    if _has_marker(start, YARN_LOCK):
        return Block(
            "This is a yarn project (yarn.lock exists). Use `yarn install` / `yarn add`.",
        )
    return None


def _check_npm(cmd: str, start: Path) -> Block | None:
    triggers = ("npm install", "npm i ", "npm i", "npm add", "npm ci")
    if not any(cmd.startswith(t) for t in triggers):
        return None
    block = _npm_block_for_pnpm(start)
    if block is not None:
        return block
    return _npm_block_for_yarn(start)


def _check_yarn(cmd: str, start: Path) -> Block | None:
    if not cmd.startswith(("yarn install", "yarn add")):
        return None
    block = _npm_block_for_pnpm(start)
    if block is not None:
        return block
    if _has_marker(start, NPM_LOCK):
        return Block(
            "This is an npm project (package-lock.json exists). Use `npm install`.",
        )
    return None


def _check_pnpm(cmd: str, start: Path) -> Block | None:
    if not cmd.startswith(("pnpm install", "pnpm add")):
        return None
    if _has_marker(start, NPM_LOCK):
        return Block(
            "This is an npm project (package-lock.json exists). Use `npm install`.",
        )
    return _npm_block_for_yarn(start)


def evaluate(cmd: str, start: Path) -> Block | None:
    for check in (_check_go_fmt, _check_pip, _check_venv):
        result = check(cmd)
        if result is not None:
            return result
    for context_check in (
        _check_pytest,
        _check_mypy,
        _check_pylint,
        _check_bare_python_script,
        _check_npm,
        _check_yarn,
        _check_pnpm,
    ):
        result = context_check(cmd, start)
        if result is not None:
            return result
    return None


def main() -> int:
    env.setup()
    cmd = os.environ.get("CC_BASH_COMMAND", "")
    if not cmd:
        return hooks.ALLOW
    cwd_value = os.environ.get("PWD") or str(Path.cwd())
    start = Path(cwd_value)
    block = evaluate(cmd, start)
    if block is not None:
        sys.stderr.write(f"BLOCKED: {block.message}\n")
        return hooks.BLOCK
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
