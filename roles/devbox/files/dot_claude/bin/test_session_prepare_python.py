from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import session_prepare_python as spp
from _claude_lib import proc

if TYPE_CHECKING:
    import pytest


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_pyproject_returns_none_when_missing(tmp_path: Path) -> None:
    assert spp._load_pyproject(tmp_path) is None


def test_load_pyproject_parses_valid_toml(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    parsed = spp._load_pyproject(tmp_path)
    assert isinstance(parsed, dict)
    assert parsed["project"] == {"name": "x"}


def test_load_pyproject_returns_none_on_invalid_toml(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "not valid = = toml [[[")
    assert spp._load_pyproject(tmp_path) is None


def test_declared_groups_extracts_group_names() -> None:
    pyproject = {
        "dependency-groups": {"dev": [], "test": ["pytest"], "local": ["black"]},
    }
    assert spp._declared_groups(pyproject) == ["dev", "local", "test"]


def test_declared_groups_returns_empty_when_absent() -> None:
    assert spp._declared_groups({}) == []


def test_declared_groups_returns_empty_when_wrong_type() -> None:
    assert spp._declared_groups({"dependency-groups": ["dev"]}) == []


def test_declared_extras_extracts_extra_names() -> None:
    pyproject = {"project": {"optional-dependencies": {"postgres": [], "kafka": []}}}
    assert spp._declared_extras(pyproject) == ["kafka", "postgres"]


def test_declared_extras_returns_empty_when_project_missing() -> None:
    assert spp._declared_extras({}) == []


def test_declared_extras_returns_empty_when_no_optional_deps() -> None:
    assert spp._declared_extras({"project": {"name": "x"}}) == []


def test_load_sync_config_returns_none_when_missing(tmp_path: Path) -> None:
    assert spp._load_sync_config(tmp_path) is None


def test_load_sync_config_returns_empty_dict_for_empty_file(tmp_path: Path) -> None:
    _write(tmp_path / ".claude" / "sync.toml", "")
    assert spp._load_sync_config(tmp_path) == {}


def test_load_sync_config_parses_valid_toml(tmp_path: Path) -> None:
    _write(
        tmp_path / ".claude" / "sync.toml",
        'groups = ["test"]\nextras = ["postgres"]\n',
    )
    assert spp._load_sync_config(tmp_path) == {
        "groups": ["test"],
        "extras": ["postgres"],
    }


def test_load_sync_config_returns_empty_dict_on_invalid_toml(tmp_path: Path) -> None:
    _write(tmp_path / ".claude" / "sync.toml", "not = = valid [[[")
    assert spp._load_sync_config(tmp_path) == {}


def test_build_sync_args_empty_config_syncs_everything() -> None:
    assert spp._build_sync_args({}) == [
        "uv",
        "sync",
        "--frozen",
        "--all-groups",
        "--all-extras",
    ]


def test_build_sync_args_all_groups_flag() -> None:
    args = spp._build_sync_args({"all_groups": True})
    assert args == ["uv", "sync", "--frozen", "--all-groups"]


def test_build_sync_args_explicit_groups() -> None:
    args = spp._build_sync_args({"groups": ["test", "local"]})
    assert args == [
        "uv",
        "sync",
        "--frozen",
        "--group",
        "test",
        "--group",
        "local",
    ]


def test_build_sync_args_explicit_extras() -> None:
    args = spp._build_sync_args({"extras": ["postgres", "kafka"]})
    assert args == [
        "uv",
        "sync",
        "--frozen",
        "--extra",
        "postgres",
        "--extra",
        "kafka",
    ]


def test_build_sync_args_all_extras_flag() -> None:
    args = spp._build_sync_args({"all_extras": True})
    assert args == ["uv", "sync", "--frozen", "--all-extras"]


def test_build_sync_args_all_groups_wins_over_groups_list() -> None:
    args = spp._build_sync_args({"all_groups": True, "groups": ["test"]})
    assert args == ["uv", "sync", "--frozen", "--all-groups"]


def test_build_sync_args_ignores_non_string_group_names() -> None:
    args = spp._build_sync_args({"groups": ["test", 42, "", None, "dev"]})
    assert args == [
        "uv",
        "sync",
        "--frozen",
        "--group",
        "test",
        "--group",
        "dev",
    ]


def test_build_sync_args_combined_groups_and_extras() -> None:
    args = spp._build_sync_args({"groups": ["test"], "extras": ["postgres"]})
    assert args == [
        "uv",
        "sync",
        "--frozen",
        "--group",
        "test",
        "--extra",
        "postgres",
    ]


def test_detect_mode_returns_none_when_no_optional_deps(tmp_path: Path) -> None:
    assert spp._detect_mode(tmp_path, {}) is None


def test_detect_mode_lists_groups(tmp_path: Path) -> None:
    pyproject = {"dependency-groups": {"test": [], "local": []}}
    message = spp._detect_mode(tmp_path, pyproject)
    assert message is not None
    assert "dependency-groups: local, test" in message
    assert "do not invent flags silently" in message
    assert ".claude/sync.toml" in message


def test_detect_mode_lists_extras(tmp_path: Path) -> None:
    pyproject = {"project": {"optional-dependencies": {"postgres": [], "kafka": []}}}
    message = spp._detect_mode(tmp_path, pyproject)
    assert message is not None
    assert "extras: kafka, postgres" in message


def test_detect_mode_lists_both_groups_and_extras(tmp_path: Path) -> None:
    pyproject = {
        "dependency-groups": {"test": []},
        "project": {"optional-dependencies": {"postgres": []}},
    }
    message = spp._detect_mode(tmp_path, pyproject)
    assert message is not None
    assert "dependency-groups: test" in message
    assert "extras: postgres" in message


def test_project_dir_prefers_claude_project_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    resolved = spp._project_dir({"cwd": "/some/other/path"})
    assert resolved == tmp_path


def test_project_dir_falls_back_to_cwd_field(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    resolved = spp._project_dir({"cwd": str(tmp_path)})
    assert resolved == tmp_path


def test_project_dir_returns_none_when_no_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    assert spp._project_dir({}) is None


def test_main_exits_silently_when_not_python_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert spp.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_exits_silently_when_no_optional_deps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert spp.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_detect_mode_emits_additional_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "x"\n\n[dependency-groups]\ndev = []\ntest = ["pytest"]\n',
    )
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert spp.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "additionalContext" in payload
    assert "dependency-groups: dev, test" in payload["additionalContext"]


def test_main_sync_mode_invokes_uv_and_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    _write(tmp_path / ".claude" / "sync.toml", 'groups = ["test"]\n')
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    calls: list[list[str]] = []

    def _fake_run(cmd: list[str] | str, **_: object) -> proc.CmdResult:
        assert isinstance(cmd, list)
        calls.append(cmd)
        return proc.CmdResult(stdout="", stderr="", returncode=0, timed_out=False)

    monkeypatch.setattr(spp.proc, "run_cmd", _fake_run)

    assert spp.main() == 0
    assert calls == [["uv", "sync", "--frozen", "--group", "test"]]
    payload = json.loads(capsys.readouterr().out)
    assert "Ran `uv sync --frozen --group test`" in payload["additionalContext"]


def test_main_sync_mode_reports_failure_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    _write(tmp_path / ".claude" / "sync.toml", "")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    def _fake_run(cmd: list[str] | str, **_: object) -> proc.CmdResult:
        assert isinstance(cmd, list)
        return proc.CmdResult(
            stdout="",
            stderr="error: no lockfile\nrun `uv lock` first",
            returncode=2,
            timed_out=False,
        )

    monkeypatch.setattr(spp.proc, "run_cmd", _fake_run)

    assert spp.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "failed (exit 2)" in payload["additionalContext"]
    assert "run `uv lock` first" in payload["additionalContext"]


def test_main_sync_mode_reports_timeout_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    _write(tmp_path / ".claude" / "sync.toml", "")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    def _fake_run(cmd: list[str] | str, **_: object) -> proc.CmdResult:
        assert isinstance(cmd, list)
        return proc.CmdResult(stdout="", stderr="", returncode=-1, timed_out=True)

    monkeypatch.setattr(spp.proc, "run_cmd", _fake_run)

    assert spp.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "timed out" in payload["additionalContext"]
