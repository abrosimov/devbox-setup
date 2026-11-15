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
from _agy_lib import proc

if TYPE_CHECKING:
    from collections.abc import Callable

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
    assert result.references is None
    assert not result.show_usage


def test_parse_args_force() -> None:
    result = fdc.parse_args(["--force"])
    assert isinstance(result, fdc.ParsedArgs)
    assert result.force


def test_parse_args_references() -> None:
    result = fdc.parse_args(["--references", "/x/refs"])
    assert isinstance(result, fdc.ParsedArgs)
    assert result.references == "/x/refs"


def test_parse_args_help() -> None:
    result = fdc.parse_args(["--help"])
    assert isinstance(result, fdc.ParsedArgs)
    assert result.show_usage


def test_parse_args_references_requires_value() -> None:
    result = fdc.parse_args(["--references"])
    assert isinstance(result, fdc.ParseFailure)


def test_parse_args_unknown() -> None:
    result = fdc.parse_args(["--unknown"])
    assert isinstance(result, fdc.ParseFailure)


def test_state_dir_uses_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert fdc.state_dir() == tmp_path / "devbox-setup" / fdc.ENGINE_STATE_SUBDIR


def test_state_dir_falls_back_to_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert fdc.state_dir() == tmp_path / ".cache" / "devbox-setup" / fdc.ENGINE_STATE_SUBDIR


def test_state_file_for_each_doc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    base = tmp_path / "devbox-setup" / fdc.ENGINE_STATE_SUBDIR
    assert fdc.state_file_for(fdc.FPF_SPEC) == base / "fpf-drift"
    assert fdc.state_file_for(fdc.NARRATIVE_SPEC) == base / "narrative-drift"


def test_specs_cover_both_docs() -> None:
    assert {spec.name for spec in fdc.SPECS} == {"FPF", "Narrative"}
    assert {spec.state_filename for spec in fdc.SPECS} == {"fpf-drift", "narrative-drift"}


def test_references_dir_is_the_deployed_skill(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert fdc.references_dir() == tmp_path / fdc.REFERENCES_RELATIVE_PATH
    assert fdc.REFERENCES_RELATIVE_PATH.endswith("skills/fpf-thinking/references")


def _deploy(references: Path) -> None:
    for spec in fdc.SPECS:
        doc = references / spec.relative_path
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(f"# {spec.name} deployed\n", encoding="utf-8")


def _fake_cmd(calls: list[str]) -> Callable[..., proc.CmdResult]:
    def fake(cmd: list[str], **_kwargs: object) -> proc.CmdResult:
        calls.append(cmd[0])
        if cmd[0] == "curl":
            Path(cmd[cmd.index("-o") + 1]).write_text("# upstream\n", encoding="utf-8")
            return _ok()
        if cmd[0] == "diff":
            return _diff_result("1c1\n< up\n---\n> down\n", returncode=1)
        return _err()

    return fake


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


def _home_with_deployed_skill(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    # cwd must not matter: point it somewhere without any FPF copy.
    monkeypatch.chdir(tmp_path)
    references = home / fdc.REFERENCES_RELATIVE_PATH
    _deploy(references)
    return references


def test_run_compares_deployed_copy_from_any_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    references = _home_with_deployed_skill(monkeypatch, tmp_path)
    diffed: list[str] = []

    def fake(cmd: list[str], **_kwargs: object) -> proc.CmdResult:
        if cmd[0] == "diff":
            diffed.append(cmd[2])
        return _fake_cmd([])(cmd)

    monkeypatch.setattr(proc, "run_cmd", fake)
    assert fdc.run([]) == 0
    assert sorted(diffed) == sorted(str(references / spec.relative_path) for spec in fdc.SPECS)
    assert fdc.state_file_for(fdc.FPF_SPEC).read_text(encoding="utf-8") == "2\n"
    assert fdc.state_file_for(fdc.NARRATIVE_SPEC).read_text(encoding="utf-8") == "2\n"


def test_run_skips_when_current(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _home_with_deployed_skill(monkeypatch, tmp_path)
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd([]))
    assert fdc.run([]) == 0

    calls: list[str] = []
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd(calls))
    assert fdc.run([]) == 0
    assert calls == []


def test_run_refreshes_when_deployed_copy_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    references = _home_with_deployed_skill(monkeypatch, tmp_path)
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd([]))
    assert fdc.run([]) == 0

    (references / fdc.FPF_SPEC.relative_path).write_text("# redeployed, longer\n", encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd(calls))
    assert fdc.run([]) == 0
    # Only the changed doc is re-fetched; the Narrative doc is still current.
    assert calls == ["curl", "diff"]


def test_run_refreshes_when_ttl_expired(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _home_with_deployed_skill(monkeypatch, tmp_path)
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd([]))
    assert fdc.run([]) == 0
    stale = time.time() - 200 * 3600
    for spec in fdc.SPECS:
        os.utime(fdc.state_file_for(spec), (stale, stale))

    calls: list[str] = []
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd(calls))
    assert fdc.run([]) == 0
    assert calls.count("curl") == 2


def test_run_force_ignores_current_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _home_with_deployed_skill(monkeypatch, tmp_path)
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd([]))
    assert fdc.run([]) == 0

    calls: list[str] = []
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd(calls))
    assert fdc.run(["--force"]) == 0
    assert calls.count("curl") == 2


def test_run_uses_explicit_references(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    references = tmp_path / "elsewhere"
    _deploy(references)
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd([]))
    assert fdc.run(["--references", str(references)]) == 0
    assert fdc.state_file_for(fdc.FPF_SPEC).read_text(encoding="utf-8") == "2\n"


def test_run_returns_one_and_clears_state_when_nothing_deployed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    for spec in fdc.SPECS:
        fdc.write_state(40201, fdc.state_file_for(spec))
        fdc.write_state(1, fdc.source_file_for(spec))

    calls: list[str] = []
    monkeypatch.setattr(proc, "run_cmd", _fake_cmd(calls))
    assert fdc.run([]) == 1
    assert calls == []
    for spec in fdc.SPECS:
        assert not fdc.state_file_for(spec).exists()
        assert not fdc.source_file_for(spec).exists()


def test_run_network_failure_preserves_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _home_with_deployed_skill(monkeypatch, tmp_path)
    state = fdc.state_file_for(fdc.FPF_SPEC)
    fdc.write_state(99, state)

    monkeypatch.setattr(proc, "run_cmd", lambda *_a, **_kw: _err())
    assert fdc.run(["--force"]) == 0
    assert state.read_text(encoding="utf-8") == "99\n"
    # No signature is recorded, so the next run retries instead of trusting 99.
    assert not fdc.source_file_for(fdc.FPF_SPEC).exists()


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
