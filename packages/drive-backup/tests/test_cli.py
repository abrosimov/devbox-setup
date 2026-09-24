from __future__ import annotations

from pathlib import Path

import pytest

from drive_backup import cli


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AION_AUTOPOIESEON", str(tmp_path / "Work"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)

    def _silent(_title: str, _message: str) -> None:
        pass

    monkeypatch.setattr(cli, "notify", _silent)
    return tmp_path


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_check_config_prints_plan(env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(
        env / ".config/drive-backup/config.toml",
        '[[dir]]\nname = "claude"\npath = "~/.claude"\nbusy = ["claude"]\n',
    )
    assert cli.main(["check-config"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert f"repo_dir: {env}/Work/drive/base  (missing)" in out
    assert f"- claude: {env}/.claude  (missing)" in out


def test_bad_config_exits_2(env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["run"]) == cli.EXIT_CONFIG
    assert "config file not found" in capsys.readouterr().err


def test_run_requires_profile(
    env: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MNEMOSYNE_PERISTASEOS", raising=False)
    cfg = _write(env / "c.toml", '[[dir]]\nname = "c"\npath = "~/.c"\n')
    assert cli.main(["--config", str(cfg), "run"]) == cli.EXIT_CONFIG
    assert "MNEMOSYNE_PERISTASEOS" in capsys.readouterr().err


def test_run_reports_failure(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MNEMOSYNE_PERISTASEOS", "work")
    cfg = _write(env / "c.toml", '[[dir]]\nname = "c"\npath = "~/.c"\n')
    assert cli.main(["--config", str(cfg), "run"]) == cli.EXIT_FAILED
