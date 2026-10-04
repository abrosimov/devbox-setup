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


def test_blocks_bare_pyrefly_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("pyrefly check src/", project)
    assert result is not None
    assert "uv run pyrefly" in result.message


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


def test_allows_uv_run_pyrefly(tmp_path: Path) -> None:
    # `pyrefly check` has no cache or incrementality flag, so the skip-cache rule
    # has no type-checker clause and must not invent one.
    project = _project_with_marker(tmp_path, "uv.lock")
    assert guard.evaluate("uv run pyrefly check src/", project) is None


def test_blocks_ruff_no_cache(tmp_path: Path) -> None:
    result = guard.evaluate("uv run ruff check --no-cache .", tmp_path)
    assert result is not None


def test_blocks_pip_force_reinstall(tmp_path: Path) -> None:
    # `pip install` is already blocked upstream, but the flag rule is more
    # specific and comes first for a clearer message.
    result = guard.evaluate("pip install --force-reinstall x", tmp_path)
    assert result is not None


# --- pyrefly suppression surface ---


def test_blocks_pyrefly_suppress_subcommand(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly suppress src/", tmp_path)
    assert result is not None
    assert "pyrefly suppress" in result.message


def test_blocks_bare_pyrefly_suppress_without_paths(tmp_path: Path) -> None:
    # No positional args — project-checking mode, the widest possible rewrite.
    result = guard.evaluate("uv run pyrefly suppress", tmp_path)
    assert result is not None


def test_blocks_pyrefly_suppress_with_global_flag_before_subcommand(
    tmp_path: Path,
) -> None:
    result = guard.evaluate("uv run pyrefly -v suppress src/", tmp_path)
    assert result is not None


def test_blocks_pyrefly_check_suppress_errors(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --suppress-errors src/", tmp_path)
    assert result is not None
    assert "suppress-errors" in result.message


def test_pyrefly_suppress_message_wins_over_bare_invocation(tmp_path: Path) -> None:
    # A bare `pyrefly` in a uv project also trips _check_pyrefly; the
    # suppression message is the one that must surface.
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("pyrefly suppress src/", project)
    assert result is not None
    assert "uv run pyrefly" not in result.message
    assert "lint-discipline" in result.message


def test_allows_pyrefly_suppress_remove_unused(tmp_path: Path) -> None:
    # Cleanup is the opposite of suppression and must never be blocked.
    assert guard.evaluate("uv run pyrefly suppress --remove-unused", tmp_path) is None


def test_allows_pyrefly_suppress_remove_unused_with_kind(tmp_path: Path) -> None:
    assert guard.evaluate("uv run pyrefly suppress --remove-unused=all src/", tmp_path) is None


def test_allows_pyrefly_check_remove_unused_ignores(tmp_path: Path) -> None:
    # `check` spells the same cleanup differently from `suppress`.
    assert guard.evaluate("uv run pyrefly check --remove-unused-ignores", tmp_path) is None


def test_allows_pyrefly_check_remove_unused_ignores_with_kind(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --remove-unused-ignores=type src/", tmp_path)
    assert result is None


def test_allows_pyrefly_check_on_path_containing_suppress(tmp_path: Path) -> None:
    # `suppress` as a path component is not the subcommand.
    assert guard.evaluate("uv run pyrefly check tests/suppress/test_foo.py", tmp_path) is None


def test_allows_plain_pyrefly_check(tmp_path: Path) -> None:
    assert guard.evaluate("uv run pyrefly check src/", tmp_path) is None


def test_blocks_pyrefly_replace_imports_with_any(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --replace-imports-with-any yaml src/", tmp_path)
    assert result is not None
    assert "pyproject.toml" in result.message


def test_blocks_pyrefly_ignore_missing_imports(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --ignore-missing-imports deepeval", tmp_path)
    assert result is not None
    assert "tool.pyrefly" in result.message


def test_blocks_pyrefly_replace_untyped_imports_with_any(tmp_path: Path) -> None:
    # Same mechanism as the other two — leaving it out would leave the guard a
    # one-flag hole.
    result = guard.evaluate(
        "uv run pyrefly check --replace-untyped-imports-with-any tenacity",
        tmp_path,
    )
    assert result is not None


def test_allows_import_any_keys_in_committed_config(tmp_path: Path) -> None:
    # The flag names are blocked as command-line arguments only. Reading or
    # grepping the committed `[tool.pyrefly]` keys that spell the same thing
    # must stay allowed — that config is the sanctioned route.
    assert guard.evaluate("grep -n replace-imports-with-any pyproject.toml", tmp_path) is None


# --- pyrefly error-silencing flags (--ignore, --preset off) ---


def test_blocks_pyrefly_ignore_rule(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --ignore bad-assignment src/", tmp_path)
    assert result is not None
    assert "tool.pyrefly.errors" in result.message


def test_blocks_pyrefly_ignore_rule_with_equals(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --ignore=bad-return src/", tmp_path)
    assert result is not None
    assert "tool.pyrefly.errors" in result.message


def test_blocks_pyrefly_ignore_rule_at_end_of_command(tmp_path: Path) -> None:
    # The flag takes a value, so this invocation is malformed — but the intent is
    # the same one the rule refuses, and `$` must close the pattern.
    assert guard.evaluate("uv run pyrefly check --ignore", tmp_path) is not None


def test_ignore_rule_does_not_claim_ignore_missing_imports(tmp_path: Path) -> None:
    # `--ignore` is a prefix of a flag that belongs to the import-to-Any rule.
    assert (
        guard.PYREFLY_SILENCE_FLAGS_RE.search("uv run pyrefly check --ignore-missing-imports x")
        is None
    )
    result = guard.evaluate("uv run pyrefly check --ignore-missing-imports deepeval", tmp_path)
    assert result is not None
    assert "tool.pyrefly.errors" not in result.message


def test_ignore_rule_does_not_claim_permissive_ignores(tmp_path: Path) -> None:
    # Blocked too, but by its own rule: the reason is other tools' directives.
    assert (
        guard.PYREFLY_SILENCE_FLAGS_RE.search("uv run pyrefly check --permissive-ignores") is None
    )
    result = guard.evaluate("uv run pyrefly check --permissive-ignores", tmp_path)
    assert result is not None
    assert "pyright" in result.message


def test_ignore_rule_does_not_claim_remove_unused_ignores(tmp_path: Path) -> None:
    # The allowed cleanup flag also ends in `ignores`.
    assert (
        guard.PYREFLY_SILENCE_FLAGS_RE.search("uv run pyrefly check --remove-unused-ignores")
        is None
    )
    assert guard.evaluate("uv run pyrefly check --remove-unused-ignores", tmp_path) is None


def test_blocks_pyrefly_preset_off(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --preset off src/", tmp_path)
    assert result is not None
    assert "preset" in result.message


def test_blocks_pyrefly_preset_off_with_equals(tmp_path: Path) -> None:
    assert guard.evaluate("uv run pyrefly check --preset=off src/", tmp_path) is not None


def test_blocks_pyrefly_preset_off_short_flag(tmp_path: Path) -> None:
    # `-p` is `--preset` under its short spelling, so it carries the same refusal.
    assert guard.evaluate("uv run pyrefly check -p off src/", tmp_path) is not None


def test_allows_pyrefly_other_presets(tmp_path: Path) -> None:
    # Only `off` silences every error kind; choosing another base configuration is
    # an ordinary decision and must not be blocked.
    assert guard.evaluate("uv run pyrefly check --preset basic src/", tmp_path) is None
    assert guard.evaluate("uv run pyrefly check --preset=default src/", tmp_path) is None
    assert guard.evaluate("uv run pyrefly check -p legacy src/", tmp_path) is None


# --- pyrefly baseline flags ---


def test_blocks_pyrefly_update_baseline(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --update-baseline src/", tmp_path)
    assert result is not None
    assert "baseline" in result.message
    assert "lint-discipline" in result.message


def test_blocks_pyrefly_prune_baseline(tmp_path: Path) -> None:
    # Unlike `--remove-unused-ignores`, pruning a baseline is not sanctioned
    # cleanup: the repository holds no baseline for it to prune.
    result = guard.evaluate("uv run pyrefly check --prune-baseline src/", tmp_path)
    assert result is not None
    assert "baseline" in result.message


def test_prune_baseline_not_exempted_by_remove_unused(tmp_path: Path) -> None:
    result = guard.evaluate(
        "uv run pyrefly check --remove-unused-ignores --prune-baseline src/",
        tmp_path,
    )
    assert result is not None
    assert "baseline" in result.message


# --- pyrefly --permissive-ignores ---


def test_blocks_pyrefly_permissive_ignores(tmp_path: Path) -> None:
    result = guard.evaluate("uv run pyrefly check --permissive-ignores src/", tmp_path)
    assert result is not None
    assert "permissive-ignores = false" in result.message


def test_blocks_pyrefly_permissive_ignores_with_value(tmp_path: Path) -> None:
    # The flag takes an optional value; every spelling of it belongs in committed
    # config rather than on the command line.
    assert guard.evaluate("uv run pyrefly check --permissive-ignores=true", tmp_path) is not None


# --- pyrefly --min-severity stays allowed ---


def test_allows_pyrefly_min_severity(tmp_path: Path) -> None:
    # Measured against pyrefly, not assumed: the default display floor is already
    # `error`, the strictest of the flag's values (`ignore`, `info`, `warn`,
    # `error`), so the flag can only lower the floor and show more. On a file with
    # one warn-level diagnostic, plain `pyrefly check` reported
    # `0 errors (1 warning not shown)` while `--min-severity warn` reported
    # `1 diagnostic`. Blocking it would forbid looking closer, so no rule may
    # claim it — including any later "completion" of the silencing rule.
    for value in ("ignore", "info", "warn", "error"):
        assert guard.evaluate(f"uv run pyrefly check --min-severity {value} src/", tmp_path) is None
        assert guard.evaluate(f"uv run pyrefly check --min-severity={value} src/", tmp_path) is None


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


def test_blocks_kill_sigkill(tmp_path: Path) -> None:
    result = guard.evaluate("kill -KILL 1234", tmp_path)
    assert result is not None


def test_blocks_chmod_777(tmp_path: Path) -> None:
    result = guard.evaluate("chmod 777 file.sh", tmp_path)
    assert result is not None


def test_blocks_chmod_recursive_777(tmp_path: Path) -> None:
    result = guard.evaluate("chmod -R 777 dir/", tmp_path)
    assert result is not None


def test_allows_kill_sigterm(tmp_path: Path) -> None:
    assert guard.evaluate("kill -TERM 1234", tmp_path) is None
    assert guard.evaluate("kill 1234", tmp_path) is None


def test_allows_chmod_normal(tmp_path: Path) -> None:
    assert guard.evaluate("chmod 755 script.sh", tmp_path) is None
    assert guard.evaluate("chmod +x script.sh", tmp_path) is None


# --- export VAR=… cache/PYTHONPATH workaround ---


def test_blocks_export_uv_cache_dir(tmp_path: Path) -> None:
    result = guard.evaluate("export UV_CACHE_DIR=/tmp/x", tmp_path)
    assert result is not None
    assert "UV_CACHE_DIR" in result.message
    assert "cache clean" in result.message


def test_blocks_export_uv_tool_dir(tmp_path: Path) -> None:
    result = guard.evaluate("export UV_TOOL_DIR=/tmp/tools", tmp_path)
    assert result is not None
    assert "UV_TOOL_DIR" in result.message


def test_blocks_export_uv_cache_dir_then_uv_sync(tmp_path: Path) -> None:
    result = guard.evaluate("export UV_CACHE_DIR=/tmp/x; uv sync", tmp_path)
    assert result is not None
    assert "UV_CACHE_DIR" in result.message


def test_blocks_export_gocache(tmp_path: Path) -> None:
    result = guard.evaluate("export GOCACHE=/tmp/g && go build ./...", tmp_path)
    assert result is not None
    assert "GOCACHE" in result.message


def test_blocks_export_pythonpath(tmp_path: Path) -> None:
    result = guard.evaluate("export PYTHONPATH=/foo/bin", tmp_path)
    assert result is not None
    assert "PYTHONPATH" in result.message
    assert "pyproject.toml" in result.message


def test_allows_export_benign_var(tmp_path: Path) -> None:
    assert guard.evaluate("export TZ=UTC", tmp_path) is None
    assert guard.evaluate("export FOO=bar; echo $FOO", tmp_path) is None


# --- Inline UV_TOOL_DIR (leading env-prefix, existing pattern) ---


def test_blocks_inline_uv_tool_dir_override(tmp_path: Path) -> None:
    result = guard.evaluate("UV_TOOL_DIR=/tmp/tools uvx ruff", tmp_path)
    assert result is not None
    assert "UV_TOOL_DIR" in result.message


# --- Standalone VAR=…; assignment (mid-command) ---


def test_blocks_standalone_uv_cache_dir_assignment(tmp_path: Path) -> None:
    result = guard.evaluate("UV_CACHE_DIR=/tmp/x; uv sync", tmp_path)
    assert result is not None
    assert "UV_CACHE_DIR" in result.message


def test_blocks_standalone_pythonpath_with_and(tmp_path: Path) -> None:
    result = guard.evaluate("PYTHONPATH=/foo && python -m pytest", tmp_path)
    assert result is not None
    assert "PYTHONPATH" in result.message


def test_allows_docker_run_with_uv_tool_dir_e_flag(tmp_path: Path) -> None:
    # `-e VAR=x` inside docker run — no separator after value; must not
    # false-positive on either the export check or the standalone check.
    assert guard.evaluate("docker run -e UV_TOOL_DIR=/x image cmd", tmp_path) is None


def test_allows_benign_standalone_assignment(tmp_path: Path) -> None:
    # Non-cache vars are ignored by the standalone-assign check.
    assert guard.evaluate("FOO=1; echo $FOO", tmp_path) is None


# --- uvx blocked in uv project, allowed outside ---


def test_blocks_uvx_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("uvx ruff check .", project)
    assert result is not None
    assert "uvx" in result.message
    assert "uv add" in result.message


def test_blocks_bare_uvx_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("uvx", project)
    assert result is not None


def test_allows_uvx_outside_uv_project(tmp_path: Path) -> None:
    project = tmp_path / "no_markers"
    project.mkdir()
    assert guard.evaluate("uvx cookiecutter gh:foo/bar", project) is None


def test_allows_uvx_lookalike_prefix(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    # Word boundary — `uvxfoo` is not `uvx`.
    assert guard.evaluate("uvxfoo --help", project) is None


# --- Go toolchain / module-resolution override vars ---


def test_blocks_inline_gotoolchain_override(tmp_path: Path) -> None:
    result = guard.evaluate("GOTOOLCHAIN=go1.99 go build ./...", tmp_path)
    assert result is not None
    assert "GOTOOLCHAIN" in result.message
    assert "Go toolchain" in result.message or "toolchain" in result.message.lower()


def test_blocks_inline_goflags_override(tmp_path: Path) -> None:
    result = guard.evaluate("GOFLAGS=-mod=mod go test ./...", tmp_path)
    assert result is not None
    assert "GOFLAGS" in result.message


def test_blocks_inline_goproxy_override(tmp_path: Path) -> None:
    result = guard.evaluate("GOPROXY=direct go mod download", tmp_path)
    assert result is not None
    assert "GOPROXY" in result.message


def test_blocks_inline_gosumdb_off(tmp_path: Path) -> None:
    result = guard.evaluate("GOSUMDB=off go build ./...", tmp_path)
    assert result is not None
    assert "GOSUMDB" in result.message


def test_blocks_inline_goinsecure(tmp_path: Path) -> None:
    result = guard.evaluate(
        "GOINSECURE=example.com go get example.com/pkg",
        tmp_path,
    )
    assert result is not None
    assert "GOINSECURE" in result.message


def test_blocks_inline_go111module_off(tmp_path: Path) -> None:
    result = guard.evaluate("GO111MODULE=off go build ./...", tmp_path)
    assert result is not None
    assert "GO111MODULE" in result.message


def test_blocks_export_gotoolchain(tmp_path: Path) -> None:
    result = guard.evaluate(
        "export GOTOOLCHAIN=go1.99; go build",
        tmp_path,
    )
    assert result is not None
    assert "GOTOOLCHAIN" in result.message


def test_blocks_export_goflags(tmp_path: Path) -> None:
    result = guard.evaluate("export GOFLAGS=-mod=mod", tmp_path)
    assert result is not None
    assert "GOFLAGS" in result.message


def test_blocks_standalone_gosumdb_assignment(tmp_path: Path) -> None:
    result = guard.evaluate("GOSUMDB=off && go build ./...", tmp_path)
    assert result is not None
    assert "GOSUMDB" in result.message


def test_blocks_export_gowork_off(tmp_path: Path) -> None:
    result = guard.evaluate("export GOWORK=off", tmp_path)
    assert result is not None
    assert "GOWORK" in result.message


def test_blocks_export_govcs(tmp_path: Path) -> None:
    result = guard.evaluate("export GOVCS=*:all", tmp_path)
    assert result is not None
    assert "GOVCS" in result.message


def test_blocks_export_goexperiment(tmp_path: Path) -> None:
    result = guard.evaluate("export GOEXPERIMENT=rangefunc", tmp_path)
    assert result is not None
    assert "GOEXPERIMENT" in result.message


def test_blocks_env_prefixed_goprivate(tmp_path: Path) -> None:
    result = guard.evaluate(
        "env GOPRIVATE=example.com go build ./...",
        tmp_path,
    )
    assert result is not None
    assert "GOPRIVATE" in result.message


def test_allows_goos_cross_compile(tmp_path: Path) -> None:
    # Cross-compilation is legitimate — GOOS/GOARCH must not false-positive.
    assert guard.evaluate("GOOS=linux GOARCH=amd64 go build ./...", tmp_path) is None


def test_allows_cgo_enabled(tmp_path: Path) -> None:
    # CGO toggle is a legitimate build knob.
    assert guard.evaluate("CGO_ENABLED=1 go build ./...", tmp_path) is None
    assert guard.evaluate("export CGO_ENABLED=0", tmp_path) is None


def test_allows_docker_run_with_go_env_e_flag(tmp_path: Path) -> None:
    # `-e VAR=x` inside docker run — must not false-positive on the standalone
    # or export check.
    assert guard.evaluate("docker run -e GOFLAGS=-race image cmd", tmp_path) is None


# --- Leading env-prefix strip: downstream checks see the real command ---


def test_blocks_env_prefixed_pytest_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("ENV_NAME=local pytest tests/", project)
    assert result is not None
    assert "uv run pytest" in result.message


def test_blocks_env_prefixed_python_m_pytest_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate(
        "ENV_NAME=local python -m pytest tests/foo.py -q",
        project,
    )
    assert result is not None
    assert "uv run pytest" in result.message


def test_blocks_env_prefixed_bare_python_script_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("FOO=bar python script.py", project)
    assert result is not None
    assert "uv run python" in result.message


def test_blocks_env_prefixed_dotslash_venv_pytest_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate("ENV_NAME=local .venv/bin/pytest tests/", project)
    assert result is not None
    assert "uv run" in result.message


def test_blocks_env_prefixed_absolute_venv_python_pytest_in_uv_project(
    tmp_path: Path,
) -> None:
    # The exact form the user hit — permission-prompt trigger before the fix.
    project = _project_with_marker(tmp_path, "uv.lock")
    cmd = (
        f"ENV_NAME=local {project}/.venv/bin/python -m pytest "
        "tests/app/foo/test_bar.py --no-header 2>&1 | tail -5"
    )
    result = guard.evaluate(cmd, project)
    assert result is not None
    assert "uv run" in result.message


def test_blocks_absolute_venv_pytest_in_uv_project(tmp_path: Path) -> None:
    project = _project_with_marker(tmp_path, "uv.lock")
    result = guard.evaluate(f"{project}/.venv/bin/pytest tests/", project)
    assert result is not None
    assert "uv run" in result.message


def test_env_prefix_strip_still_catches_cache_workaround(tmp_path: Path) -> None:
    # A benign leading assign followed by a watched cache var must still block
    # on the watched one, not slip past because of the leading benign token.
    result = guard.evaluate(
        "ENV_NAME=local UV_CACHE_DIR=/tmp/x uv run pytest tests/",
        tmp_path,
    )
    assert result is not None
    assert "UV_CACHE_DIR" in result.message


def test_env_prefix_strip_preserves_allow_for_uv_run(tmp_path: Path) -> None:
    # Canonical form must remain allowed after the strip.
    project = _project_with_marker(tmp_path, "uv.lock")
    assert guard.evaluate("ENV_NAME=local uv run pytest tests/", project) is None
