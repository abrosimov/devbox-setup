from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_bash_toolchain_guard as guard

if TYPE_CHECKING:
    import pytest


def _project_with_marker(tmp_path: Path, marker: str) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / marker).write_text("", encoding="utf-8")
    return project


def test_blocks_go_fmt() -> None:
    result = guard.evaluate("go fmt ./...", Path("/"))
    assert result is not None
    assert "goimports" in result.message


def test_blocks_gofmt_binary() -> None:
    result = guard.evaluate("gofmt -w main.go", Path("/"))
    assert result is not None


def test_blocks_pip_install() -> None:
    result = guard.evaluate("pip install requests", Path("/"))
    assert result is not None
    assert "uv add" in result.message


def test_blocks_pip3_install() -> None:
    assert guard.evaluate("pip3 install x", Path("/")) is not None


def test_blocks_python_m_pip() -> None:
    assert guard.evaluate("python -m pip install x", Path("/")) is not None


def test_blocks_python_m_venv() -> None:
    result = guard.evaluate("python -m venv .venv", Path("/"))
    assert result is not None
    assert "uv sync" in result.message


def test_blocks_python3_m_venv() -> None:
    assert guard.evaluate("python3 -m venv .venv", Path("/")) is not None


def test_blocks_bare_pytest_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("pytest", project)
    assert result is not None
    assert "uv run pytest" in result.message


def test_blocks_bare_pytest_in_poetry_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "poetry.lock")
    result = guard.evaluate("pytest -k foo", project)
    assert result is not None
    assert "poetry run pytest" in result.message


def test_allows_pytest_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "no_markers"
    project.mkdir()
    assert guard.evaluate("pytest", project) is None


def test_blocks_bare_mypy_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("mypy src/", project)
    assert result is not None
    assert "uv run mypy" in result.message


def test_blocks_bare_pylint_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("pylint src/", project)
    assert result is not None


def test_blocks_bare_python_script_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("python script.py", project)
    assert result is not None
    assert "uv run python" in result.message


def test_allows_python_with_flag_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    assert guard.evaluate("python --version", project) is None
    assert guard.evaluate("python -c 'print(1)'", project) is None


def test_allows_bare_python_outside_project(tmp_path: Path) -> None:
    assert guard.evaluate("python script.py", tmp_path) is None


def test_blocks_npm_install_in_pnpm_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "pnpm-lock.yaml")
    result = guard.evaluate("npm install", project)
    assert result is not None
    assert "pnpm" in result.message


def test_blocks_npm_install_in_yarn_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "yarn.lock")
    result = guard.evaluate("npm install lodash", project)
    assert result is not None
    assert "yarn" in result.message


def test_blocks_yarn_install_in_pnpm_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "pnpm-lock.yaml")
    result = guard.evaluate("yarn install", project)
    assert result is not None
    assert "pnpm" in result.message


def test_blocks_pnpm_install_in_npm_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "package-lock.json")
    result = guard.evaluate("pnpm install", project)
    assert result is not None
    assert "npm" in result.message


def test_allows_clean_command(tmp_path: Path) -> None:
    assert guard.evaluate("ls -la", tmp_path) is None
    assert guard.evaluate("git status", tmp_path) is None


def test_main_no_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CC_BASH_COMMAND", raising=False)
    assert guard.main() == 0


def test_main_blocks_with_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_BASH_COMMAND", "go fmt ./...")
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert guard.main() == 2
    assert "BLOCKED" in err.getvalue()


def test_main_allows_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CC_BASH_COMMAND", "ls")
    monkeypatch.setenv("PWD", str(tmp_path))
    assert guard.main() == 0
