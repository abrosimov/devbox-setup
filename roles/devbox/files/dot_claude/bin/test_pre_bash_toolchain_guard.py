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


# --- Inline env-var workaround (cache paths / PYTHONPATH) ---


def test_blocks_inline_uv_cache_dir_override(tmp_path: Path) -> None:
    result = guard.evaluate("UV_CACHE_DIR=/tmp/x uv run pytest", tmp_path)
    assert result is not None
    assert "UV_CACHE_DIR" in result.message


def test_blocks_env_prefixed_gocache_override(tmp_path: Path) -> None:
    result = guard.evaluate("env GOCACHE=/tmp/x go build ./...", tmp_path)
    assert result is not None
    assert "GOCACHE" in result.message


def test_blocks_multi_assign_with_cache_var(tmp_path: Path) -> None:
    cmd = "ENV_NAME=local UV_CACHE_DIR=/tmp/fresh uv run --no-sync pytest"
    result = guard.evaluate(cmd, tmp_path)
    assert result is not None
    # First matched — either UV_CACHE_DIR or --no-sync — both valid to catch.


def test_blocks_pythonpath_override(tmp_path: Path) -> None:
    cmd = "PYTHONPATH=/foo/bin .venv/bin/python -c 'import x'"
    result = guard.evaluate(cmd, tmp_path)
    assert result is not None
    assert "PYTHONPATH" in result.message


def test_allows_docker_run_with_env_flag(tmp_path: Path) -> None:
    # docker uses `-e VAR=…`, not leading VAR=…; must not false-positive.
    result = guard.evaluate("docker run -e UV_CACHE_DIR=/x image cmd", tmp_path)
    assert result is None


def test_allows_env_alone(tmp_path: Path) -> None:
    assert guard.evaluate("env", tmp_path) is None
    assert guard.evaluate("env | grep UV", tmp_path) is None


def test_allows_benign_leading_env(tmp_path: Path) -> None:
    assert guard.evaluate("TZ=UTC pytest", tmp_path) is None


# --- Direct .venv/bin invocations ---


def test_blocks_venv_bin_pytest_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate(".venv/bin/pytest", project)
    assert result is not None
    assert "uv run" in result.message


def test_blocks_absolute_venv_python_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("/repo/.venv/bin/python -c 'import x'", project)
    assert result is not None


def test_blocks_dotslash_venv_pytest_in_poetry_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "poetry.lock")
    result = guard.evaluate("./.venv/bin/pytest", project)
    assert result is not None
    assert "poetry run" in result.message


def test_allows_venv_bin_outside_python_project(tmp_path: Path) -> None:
    project = tmp_path / "misc"
    project.mkdir()
    assert guard.evaluate(".venv/bin/pytest", project) is None


# --- Ad-hoc python -c import validation ---


def test_blocks_python_c_import_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("python -c 'import config_validator'", project)
    assert result is not None
    assert "ad-hoc" in result.message.lower()


def test_blocks_python3_c_import_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate('python3 -c "import foo"', project)
    assert result is not None


def test_blocks_uv_run_python_c_import(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("uv run python -c 'import config_validator'", project)
    assert result is not None
    assert "ad-hoc" in result.message.lower()


def test_allows_python_c_non_import(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    # print/computation is a legitimate use of -c; not our target
    assert guard.evaluate("python -c 'print(1+1)'", project) is None


def test_allows_python_c_import_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "no_markers"
    project.mkdir()
    assert guard.evaluate("python -c 'import sys'", project) is None


# --- pytest --collect-only (ad-hoc wiring check) ---


def test_blocks_pytest_collect_only(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pytest --collect-only", tmp_path)
    assert result is not None
    assert "ad-hoc" in result.message.lower()


def test_blocks_pytest_co_short_flag(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pytest --co tests/", tmp_path)
    assert result is not None


def test_allows_pytest_regular(tmp_path: Path) -> None:
    assert guard.evaluate("uv run pytest tests/", tmp_path) is None


# --- --no-sync workaround ---


def test_blocks_uv_run_no_sync(tmp_path: Path) -> None:
    result = guard.evaluate("uv run --no-sync pytest", tmp_path)
    assert result is not None
    assert "no-sync" in result.message


# --- Skip-cache/skip-verify flags ---


def test_blocks_pytest_no_cacheprovider(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pytest -p no:cacheprovider", tmp_path)
    assert result is not None


def test_blocks_pytest_no_cacheprovider_long(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pytest --no-cacheprovider", tmp_path)
    assert result is not None


def test_blocks_mypy_no_incremental(tmp_path: Path) -> None:
    result = guard.evaluate("uv run mypy --no-incremental src/", tmp_path)
    assert result is not None


def test_blocks_ruff_no_cache(tmp_path: Path) -> None:
    result = guard.evaluate("uv run ruff check --no-cache .", tmp_path)
    assert result is not None


def test_blocks_pip_force_reinstall(tmp_path: Path) -> None:
    # `pip install` is already blocked upstream, but the flag rule is more
    # specific and comes first for a clearer message.
    result = guard.evaluate("pip install --force-reinstall x", tmp_path)
    assert result is not None


# --- git commit --allow-empty ---


def test_blocks_git_commit_allow_empty(tmp_path: Path) -> None:
    result = guard.evaluate("git commit --allow-empty -m 'trigger'", tmp_path)
    assert result is not None
    assert "empty" in result.message.lower()


def test_allows_git_commit_normal(tmp_path: Path) -> None:
    assert guard.evaluate("git commit -m 'msg'", tmp_path) is None


# --- Force flags (kill -9, chmod 777) ---


def test_blocks_kill_9(tmp_path: Path) -> None:
    result = guard.evaluate("kill -9 1234", tmp_path)
    assert result is not None
    assert "Force" in result.message or "force" in result.message


def test_blocks_kill_KILL(tmp_path: Path) -> None:
    result = guard.evaluate("kill -KILL 1234", tmp_path)
    assert result is not None


def test_blocks_chmod_777(tmp_path: Path) -> None:
    result = guard.evaluate("chmod 777 file.sh", tmp_path)
    assert result is not None


def test_blocks_chmod_recursive_777(tmp_path: Path) -> None:
    result = guard.evaluate("chmod -R 777 dir/", tmp_path)
    assert result is not None


def test_allows_kill_TERM(tmp_path: Path) -> None:
    assert guard.evaluate("kill -TERM 1234", tmp_path) is None
    assert guard.evaluate("kill 1234", tmp_path) is None


def test_allows_chmod_normal(tmp_path: Path) -> None:
    assert guard.evaluate("chmod 755 script.sh", tmp_path) is None
    assert guard.evaluate("chmod +x script.sh", tmp_path) is None
