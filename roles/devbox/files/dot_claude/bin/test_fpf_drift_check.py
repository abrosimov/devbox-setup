from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fpf_drift_check as fdc
from _claude_lib import proc

if TYPE_CHECKING:
    import pytest


def _ok(stdout: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _diff_result(stdout: str, returncode: int = 1) -> proc.CmdResult:
    return proc.CmdResult(stdout=stdout, stderr="", returncode=returncode, timed_out=False)


def _err() -> proc.CmdResult:
    return proc.CmdResult(stdout="", stderr="fatal", returncode=2, timed_out=False)


def test_parse_args_defaults() -> None:
    result = fdc.parse_args([])
    assert isinstance(result, fdc.ParsedArgs)
    assert not result.force
    assert result.local is None
    assert not result.show_usage


def test_parse_args_force() -> None:
    result = fdc.parse_args(["--force"])
    assert isinstance(result, fdc.ParsedArgs)
    assert result.force


def test_parse_args_local() -> None:
    result = fdc.parse_args(["--local", "/x/spec.md"])
    assert isinstance(result, fdc.ParsedArgs)
    assert result.local == "/x/spec.md"


def test_parse_args_help() -> None:
    result = fdc.parse_args(["--help"])
    assert isinstance(result, fdc.ParsedArgs)
    assert result.show_usage


def test_parse_args_local_requires_value() -> None:
    result = fdc.parse_args(["--local"])
    assert isinstance(result, fdc.ParseFailure)


def test_parse_args_unknown() -> None:
    result = fdc.parse_args(["--unknown"])
    assert isinstance(result, fdc.ParseFailure)


def test_state_dir_uses_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert fdc.state_dir() == tmp_path / "devbox-setup"


def test_state_dir_falls_back_to_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert fdc.state_dir() == tmp_path / ".cache" / "devbox-setup"


def test_is_fresh_returns_false_for_missing(tmp_path: Path) -> None:
    assert not fdc.is_fresh(tmp_path / "absent", 1)


def test_is_fresh_returns_true_for_recent(tmp_path: Path) -> None:
    target = tmp_path / "state"
    target.write_text("0\n", encoding="utf-8")
    assert fdc.is_fresh(target, 168)


def test_is_fresh_returns_false_for_stale(tmp_path: Path) -> None:
    target = tmp_path / "state"
    target.write_text("0\n", encoding="utf-8")
    stale = time.time() - 200 * 3600
    os.utime(target, (stale, stale))
    assert not fdc.is_fresh(target, 168)


def test_find_local_spec_walks_up(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    spec = tmp_path / fdc.LOCAL_RELATIVE_PATH
    spec.parent.mkdir(parents=True)
    spec.write_text("# fpf", encoding="utf-8")
    assert fdc.find_local_spec(nested) == spec


def test_find_local_spec_returns_none(tmp_path: Path) -> None:
    nested = tmp_path / "a"
    nested.mkdir()
    assert fdc.find_local_spec(nested) is None


def test_count_drift_counts_diff_lines() -> None:
    diff_output = "1c1\n< old\n---\n> new\n2a3\n> added\n"
    with mock.patch.object(proc, "run_cmd", return_value=_diff_result(diff_output, returncode=1)):
        assert fdc.count_drift(Path("u"), Path("l")) == 3


def test_count_drift_zero_when_identical() -> None:
    with mock.patch.object(proc, "run_cmd", return_value=_diff_result("", returncode=0)):
        assert fdc.count_drift(Path("u"), Path("l")) == 0


def test_count_drift_returns_zero_on_error() -> None:
    with mock.patch.object(proc, "run_cmd", return_value=_err()):
        assert fdc.count_drift(Path("u"), Path("l")) == 0


def test_write_state_writes_number_and_newline(tmp_path: Path) -> None:
    target = tmp_path / "state"
    fdc.write_state(42, target)
    assert target.read_text(encoding="utf-8") == "42\n"


def test_write_state_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "state"
    target.write_text("999\n", encoding="utf-8")
    fdc.write_state(0, target)
    assert target.read_text(encoding="utf-8") == "0\n"


def test_run_skips_when_fresh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    state = fdc.state_file()
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("3\n", encoding="utf-8")

    called: list[bool] = []

    def fail(*_a: object, **_kw: object) -> proc.CmdResult:
        called.append(True)
        return _err()

    monkeypatch.setattr(proc, "run_cmd", fail)
    assert fdc.run([]) == 0
    assert not called


def test_run_uses_explicit_local(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    local = tmp_path / "spec.md"
    local.write_text("# fpf local\n", encoding="utf-8")

    def fake(cmd: list[str], **_kwargs: object) -> proc.CmdResult:
        if cmd[0] == "curl":
            target = Path(cmd[cmd.index("-o") + 1])
            target.write_text("# upstream\n", encoding="utf-8")
            return _ok()
        if cmd[0] == "diff":
            return _diff_result("1c1\n< up\n---\n> down\n", returncode=1)
        return _err()

    monkeypatch.setattr(proc, "run_cmd", fake)
    assert fdc.run(["--force", "--local", str(local)]) == 0
    state = fdc.state_file()
    assert state.read_text(encoding="utf-8") == "2\n"


def test_run_returns_one_when_local_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setenv("PWD", str(tmp_path))
    monkeypatch.setattr(fdc, "find_local_spec", lambda _start: None)
    assert fdc.run(["--force"]) == 1


def test_run_network_failure_preserves_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    local = tmp_path / "spec.md"
    local.write_text("# fpf local\n", encoding="utf-8")
    state = fdc.state_file()
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("99\n", encoding="utf-8")

    monkeypatch.setattr(proc, "run_cmd", lambda *_a, **_kw: _err())
    assert fdc.run(["--force", "--local", str(local)]) == 0
    assert state.read_text(encoding="utf-8") == "99\n"


def test_run_help_prints_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert fdc.run(["--help"]) == 0
    assert "Usage:" in out.getvalue()


def test_run_unknown_arg_returns_two(monkeypatch: pytest.MonkeyPatch) -> None:
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert fdc.run(["--no-such"]) == 2
    assert "Unknown" in err.getvalue()
