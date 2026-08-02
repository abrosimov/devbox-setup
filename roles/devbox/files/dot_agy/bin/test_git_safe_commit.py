from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import git_safe_commit as gsc
from _claude_lib import proc

if TYPE_CHECKING:
    import pytest


def _ok(stdout: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _err(stderr: str = "fatal") -> proc.CmdResult:
    return proc.CmdResult(stdout="", stderr=stderr, returncode=1, timed_out=False)


def test_is_secret_path_dotenv() -> None:
    assert gsc.is_secret_path(".env")
    assert gsc.is_secret_path(".env.production")
    assert gsc.is_secret_path("config/.env")
    assert gsc.is_secret_path("path/to/.env.local")


def test_is_secret_path_pem_key() -> None:
    assert gsc.is_secret_path("server.pem")
    assert gsc.is_secret_path("path/to/private.key")


def test_is_secret_path_credentials() -> None:
    assert gsc.is_secret_path("aws-credentials.json")
    assert gsc.is_secret_path("credentials.yml")


def test_is_secret_path_secrets_directory() -> None:
    assert gsc.is_secret_path("secrets/db.yml")
    assert gsc.is_secret_path("app/secrets/config.json")


def test_is_secret_path_allows_safe_paths() -> None:
    assert not gsc.is_secret_path("src/main.py")
    assert not gsc.is_secret_path("README.md")
    assert not gsc.is_secret_path("docs/env-vars.md")


def test_secret_category_classifies_env() -> None:
    assert gsc.secret_category(".env") == "environment file"
    assert gsc.secret_category("path/.env.local") == "environment file"


def test_secret_category_classifies_secrets_dir() -> None:
    assert gsc.secret_category("secrets/x") == "secrets directory file"


def test_secret_category_classifies_pem() -> None:
    assert gsc.secret_category("x.pem") == "sensitive file"


def test_secret_category_empty_for_safe() -> None:
    assert gsc.secret_category("src/main.py") == ""


def test_parse_args_success_with_message() -> None:
    result = gsc.parse_args(["-m", "fix: bug"])
    assert isinstance(result, gsc.ParsedArgs)
    assert result.message == "fix: bug"
    assert result.files == []


def test_parse_args_success_with_files() -> None:
    result = gsc.parse_args(["-m", "feat", "src/a.py", "src/b.py"])
    assert isinstance(result, gsc.ParsedArgs)
    assert result.files == ["src/a.py", "src/b.py"]


def test_parse_args_dashdash_separator() -> None:
    result = gsc.parse_args(["-m", "msg", "--", "-weird-name.py"])
    assert isinstance(result, gsc.ParsedArgs)
    assert result.files == ["-weird-name.py"]


def test_parse_args_missing_message() -> None:
    result = gsc.parse_args([])
    assert isinstance(result, gsc.ParseFailure)
    assert "message required" in result.reason


def test_parse_args_m_without_value() -> None:
    result = gsc.parse_args(["-m"])
    assert isinstance(result, gsc.ParseFailure)
    assert "-m requires" in result.reason


def test_parse_args_rejects_unknown_flag() -> None:
    result = gsc.parse_args(["--foo", "bar"])
    assert isinstance(result, gsc.ParseFailure)
    assert "Unknown flag" in result.reason


def _setup_repo(
    monkeypatch: pytest.MonkeyPatch, responses: dict[str, proc.CmdResult]
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake(cmd: list[str], **_kwargs: object) -> proc.CmdResult:
        calls.append(list(cmd))
        key = " ".join(cmd)
        for prefix, response in responses.items():
            if key.startswith(prefix):
                return response
        return _ok()

    monkeypatch.setattr(proc, "run_cmd", fake)
    return calls


def test_run_blocks_on_main(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("main\n"),
            "git config --get claude.integrationBranch": _err(),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsc.run(["-m", "fix"]) == 1
    assert "protected branch 'main'" in err.getvalue()


def test_run_blocks_on_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("build/stable\n"),
            "git config --get claude.integrationBranch": _err(),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsc.run(["-m", "fix"]) == 1
    assert "build/stable" in err.getvalue()


def test_run_blocks_on_custom_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("integration\n"),
            "git config --get claude.integrationBranch": _ok("integration\n"),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsc.run(["-m", "fix"]) == 1
    assert "integration" in err.getvalue()


def test_run_blocks_detached_head(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok(""),
            "git config --get claude.integrationBranch": _err(),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsc.run(["-m", "fix"]) == 1
    assert "detached HEAD" in err.getvalue()


def test_run_rejects_missing_message(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("feature/x\n"),
            "git config --get claude.integrationBranch": _err(),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsc.run([]) == 1
    assert "message required" in err.getvalue()


def test_run_blocks_staged_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("feature/x\n"),
            "git config --get claude.integrationBranch": _err(),
            "git add": _ok(),
            "git diff --cached --name-only": _ok(".env\n"),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsc.run(["-m", "feat"]) == 1
    assert "environment file" in err.getvalue()
    assert ".env" in err.getvalue()


def test_run_nothing_to_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("feature/x\n"),
            "git config --get claude.integrationBranch": _err(),
            "git add": _ok(),
            "git diff --cached --name-only": _ok(""),
            "git diff --cached --quiet": _ok(),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert gsc.run(["-m", "feat"]) == 0
    assert "Nothing to commit" in out.getvalue()


def test_run_successful_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("feature/x\n"),
            "git config --get claude.integrationBranch": _err(),
            "git add": _ok(),
            "git diff --cached --name-only": _ok("src/main.py\n"),
            "git diff --cached --quiet": _err(),
            "git commit": _ok("[feature/x abc1234] feat\n"),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert gsc.run(["-m", "feat"]) == 0
    assert "feature/x abc1234" in out.getvalue()


def test_run_passes_files_to_git_add(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("feature/x\n"),
            "git config --get claude.integrationBranch": _err(),
            "git add": _ok(),
            "git diff --cached --name-only": _ok("src/a.py\n"),
            "git diff --cached --quiet": _err(),
            "git commit": _ok(""),
        },
    )
    assert gsc.run(["-m", "feat", "src/a.py", "src/b.py"]) == 0
    add_calls = [c for c in calls if c[:2] == ["git", "add"]]
    assert add_calls
    assert "src/a.py" in add_calls[0]
    assert "src/b.py" in add_calls[0]


def test_run_git_add_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_repo(
        monkeypatch,
        {
            "git branch --show-current": _ok("feature/x\n"),
            "git config --get claude.integrationBranch": _err(),
            "git add": _err("conflict"),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsc.run(["-m", "feat"]) == 1
    assert "git add failed" in err.getvalue()
