from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import statusline as sl

if TYPE_CHECKING:
    import pytest


def test_parse_input_full_payload() -> None:
    payload = {
        "cwd": "/Users/me/Projects",
        "model": {"display_name": "Opus 4.7"},
        "workspace": {"current_dir": "/Users/me/Projects"},
        "context_window": {"remaining_percentage": 73, "context_window_size": 200_000},
    }
    parsed = sl.parse_input(payload)
    assert parsed.cwd == "/Users/me/Projects"
    assert parsed.model == "Opus 4.7"
    assert parsed.remaining == 73


def test_parse_input_falls_back_to_workspace() -> None:
    payload = {
        "workspace": {"current_dir": "/Users/me/Work"},
        "model": {"display_name": "Sonnet"},
    }
    parsed = sl.parse_input(payload)
    assert parsed.cwd == "/Users/me/Work"


def test_parse_input_missing_cwd_returns_question_mark() -> None:
    parsed = sl.parse_input({"model": {"display_name": "X"}})
    assert parsed.cwd == "?"
    assert parsed.model == "X"
    assert parsed.remaining is None


def test_parse_input_empty_payload() -> None:
    parsed = sl.parse_input({})
    assert parsed.cwd == "?"
    assert parsed.model == "?"
    assert parsed.remaining is None


def test_parse_input_non_string_workspace_ignored() -> None:
    payload: dict[str, object] = {"workspace": "not-a-dict", "model": {"display_name": "X"}}
    parsed = sl.parse_input(payload)
    assert parsed.cwd == "?"


def test_parse_input_remaining_from_float() -> None:
    payload = {"context_window": {"remaining_percentage": 42.7}}
    parsed = sl.parse_input(payload)
    assert parsed.remaining == 42


def test_parse_input_remaining_from_string() -> None:
    payload = {"context_window": {"remaining_percentage": "55"}}
    parsed = sl.parse_input(payload)
    assert parsed.remaining == 55


def test_parse_input_remaining_invalid_string() -> None:
    payload = {"context_window": {"remaining_percentage": "abc"}}
    parsed = sl.parse_input(payload)
    assert parsed.remaining is None


def test_parse_input_remaining_bool_ignored() -> None:
    payload = {"context_window": {"remaining_percentage": True}}
    parsed = sl.parse_input(payload)
    assert parsed.remaining is None


def test_shorten_path_replaces_home_prefix() -> None:
    assert sl.shorten_path("/Users/foo/Projects/x", "/Users/foo") == "~/Projects/x"


def test_shorten_path_exact_home() -> None:
    assert sl.shorten_path("/Users/foo", "/Users/foo") == "~"


def test_shorten_path_unrelated_returns_input() -> None:
    assert sl.shorten_path("/etc/hosts", "/Users/foo") == "/etc/hosts"


def test_shorten_path_no_home_returns_input() -> None:
    assert sl.shorten_path("/Users/foo/x", "") == "/Users/foo/x"


def test_shorten_path_avoids_partial_match() -> None:
    assert sl.shorten_path("/Users/foobar/x", "/Users/foo") == "/Users/foobar/x"


def test_context_color_thresholds() -> None:
    assert sl.context_color(99) == sl.C_GREEN
    assert sl.context_color(50) == sl.C_GREEN
    assert sl.context_color(49) == sl.C_YELLOW
    assert sl.context_color(20) == sl.C_YELLOW
    assert sl.context_color(19) == sl.C_RED
    assert sl.context_color(0) == sl.C_RED


def test_context_bar_full() -> None:
    bar = sl.context_bar(100)
    assert bar == "▪" * 10


def test_context_bar_empty() -> None:
    assert sl.context_bar(0) == "·" * 10


def test_context_bar_half() -> None:
    bar = sl.context_bar(50)
    assert bar == "▪" * 5 + "·" * 5


def test_context_bar_clamps_high() -> None:
    bar = sl.context_bar(250)
    assert bar == "▪" * 10


def test_context_bar_clamps_low() -> None:
    bar = sl.context_bar(-10)
    assert bar == "·" * 10


def test_context_segment_unknown() -> None:
    assert sl.context_segment(None) == f"{sl.C_MUTED}ctx —"


def test_context_segment_contains_pct_and_bar() -> None:
    seg = sl.context_segment(75)
    assert "75%" in seg
    assert "▪" in seg
    assert "·" in seg
    assert sl.C_GREEN in seg


def test_ansi_escape_format() -> None:
    # Sanity: truecolor escape format is `\x1b[38;2;R;G;Bm`
    assert sl.C_GOLD.startswith("\x1b[38;2;")
    assert sl.C_GOLD.endswith("m")
    parts = sl.C_GOLD[len("\x1b[38;2;") : -1].split(";")
    assert len(parts) == 3
    assert all(0 <= int(p) <= 255 for p in parts)


def test_git_segment_empty_when_no_branch() -> None:
    assert sl.git_segment(None) == ""


def test_git_segment_includes_branch_name() -> None:
    seg = sl.git_segment("feature/login")
    assert "feature/login" in seg
    assert sl.C_GOLD in seg


def test_git_branch_returns_none_for_nonexistent_dir(tmp_path: Path) -> None:
    missing = tmp_path / "no-such"
    assert sl.git_branch(str(missing)) is None


def test_git_branch_invokes_subprocess(tmp_path: Path) -> None:
    completed = mock.Mock()
    completed.returncode = 0
    completed.stdout = "main\n"
    with mock.patch.object(sl.subprocess, "run", return_value=completed) as run_mock:
        assert sl.git_branch(str(tmp_path)) == "main"
    args, _ = run_mock.call_args
    cmd = args[0]
    assert cmd[0] == "git"
    assert "--no-optional-locks" in cmd
    assert str(tmp_path) in cmd


def test_git_branch_handles_nonzero_exit(tmp_path: Path) -> None:
    completed = mock.Mock()
    completed.returncode = 128
    completed.stdout = ""
    with mock.patch.object(sl.subprocess, "run", return_value=completed):
        assert sl.git_branch(str(tmp_path)) is None


def test_git_branch_handles_timeout(tmp_path: Path) -> None:
    def raise_timeout(*_a: object, **_kw: object) -> object:
        raise sl.subprocess.TimeoutExpired(cmd="git", timeout=2)

    with mock.patch.object(sl.subprocess, "run", side_effect=raise_timeout):
        assert sl.git_branch(str(tmp_path)) is None


def test_fpf_state_path_uses_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert sl.fpf_state_path() == tmp_path / "devbox-setup" / "fpf-drift"


def test_fpf_state_path_falls_back_to_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert sl.fpf_state_path() == tmp_path / ".cache" / "devbox-setup" / "fpf-drift"


def test_fpf_drift_value_missing(tmp_path: Path) -> None:
    assert sl.fpf_drift_value(tmp_path / "absent") is None


def test_fpf_drift_value_parses_number(tmp_path: Path) -> None:
    target = tmp_path / "state"
    target.write_text("42\n", encoding="utf-8")
    assert sl.fpf_drift_value(target) == 42


def test_fpf_drift_value_invalid_returns_none(tmp_path: Path) -> None:
    target = tmp_path / "state"
    target.write_text("not-a-number\n", encoding="utf-8")
    assert sl.fpf_drift_value(target) is None


def test_fpf_drift_value_empty_returns_none(tmp_path: Path) -> None:
    target = tmp_path / "state"
    target.write_text("", encoding="utf-8")
    assert sl.fpf_drift_value(target) is None


def test_fpf_segment_hidden_when_none() -> None:
    assert sl.fpf_segment(None) == ""


def test_fpf_segment_hidden_when_zero() -> None:
    assert sl.fpf_segment(0) == ""


def test_fpf_segment_yellow_under_threshold() -> None:
    seg = sl.fpf_segment(150)
    assert sl.C_YELLOW in seg
    assert "FPF Δ150" in seg


def test_fpf_segment_red_above_threshold() -> None:
    seg = sl.fpf_segment(201)
    assert sl.C_RED in seg
    assert "FPF Δ201" in seg


def test_trigger_fpf_refresh_no_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    # No script present — Popen must not be called.
    with mock.patch.object(sl.subprocess, "Popen") as popen:
        sl.trigger_fpf_refresh(tmp_path / "spec.md")
    popen.assert_not_called()


def test_trigger_fpf_refresh_invokes_popen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    bin_dir = tmp_path / ".claude" / "bin"
    bin_dir.mkdir(parents=True)
    script = bin_dir / "fpf_drift_check.py"
    script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    spec = tmp_path / "spec.md"
    spec.write_text("# fpf\n", encoding="utf-8")

    with mock.patch.object(sl.subprocess, "Popen") as popen:
        sl.trigger_fpf_refresh(spec)

    popen.assert_called_once()
    args, _ = popen.call_args
    assert str(script) in args[0]
    assert str(spec) in args[0]


def test_trigger_fpf_refresh_swallows_oserror(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    bin_dir = tmp_path / ".claude" / "bin"
    bin_dir.mkdir(parents=True)
    script = bin_dir / "fpf_drift_check.py"
    script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    err_msg = "nope"

    def boom(*_a: object, **_kw: object) -> object:
        raise OSError(err_msg)

    with mock.patch.object(sl.subprocess, "Popen", side_effect=boom):
        sl.trigger_fpf_refresh(tmp_path / "spec.md")


def test_render_assembles_cwd_ctx_model() -> None:
    parsed = sl.StatuslineInput(cwd="/tmp/x", model="Opus 4.7", remaining=80)
    with mock.patch.object(sl, "git_branch", return_value=None):
        line = sl.render(parsed, "", None)
    assert "/tmp/x" in line
    assert "80%" in line
    assert "Opus 4.7" in line
    # Two separators present in output.
    assert line.count("│") >= 2


def test_render_includes_git_branch(tmp_path: Path) -> None:
    parsed = sl.StatuslineInput(cwd=str(tmp_path), model="Sonnet", remaining=10)
    with mock.patch.object(sl, "git_branch", return_value="main"):
        line = sl.render(parsed, "", None)
    assert "main" in line


def test_render_includes_fpf_when_positive(tmp_path: Path) -> None:
    parsed = sl.StatuslineInput(cwd=str(tmp_path), model="X", remaining=50)
    with mock.patch.object(sl, "git_branch", return_value=None):
        line = sl.render(parsed, "", 250)
    assert "FPF Δ250" in line
    assert sl.C_RED in line


def test_render_omits_fpf_when_zero(tmp_path: Path) -> None:
    parsed = sl.StatuslineInput(cwd=str(tmp_path), model="X", remaining=50)
    with mock.patch.object(sl, "git_branch", return_value=None):
        line = sl.render(parsed, "", 0)
    assert "FPF" not in line


def test_render_shortens_home_path() -> None:
    parsed = sl.StatuslineInput(cwd="/Users/me/Projects/x", model="X", remaining=50)
    with mock.patch.object(sl, "git_branch", return_value=None):
        line = sl.render(parsed, "/Users/me", None)
    assert "~/Projects/x" in line
    assert "/Users/me/Projects/x" not in line


def test_run_reads_stdin_and_writes_line(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "cwd": "/no/such/dir",
        "model": {"display_name": "Opus"},
        "context_window": {"remaining_percentage": 75},
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sl, "git_branch", lambda _cwd: None)
    monkeypatch.setattr(sl, "trigger_fpf_refresh", lambda _path: None)
    monkeypatch.setattr(sl, "fpf_drift_value", lambda _path: None)

    assert sl.run() == 0
    output = out.getvalue()
    assert output.endswith("\n")
    assert "Opus" in output
    assert "75%" in output


def test_run_handles_empty_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sl, "git_branch", lambda _cwd: None)
    monkeypatch.setattr(sl, "trigger_fpf_refresh", lambda _path: None)
    monkeypatch.setattr(sl, "fpf_drift_value", lambda _path: None)

    assert sl.run() == 0
    output = out.getvalue()
    assert output.endswith("\n")
    # Unknown ctx renders dash.
    assert "ctx —" in output


def test_run_skips_fpf_refresh_outside_devbox(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {"cwd": str(tmp_path), "model": {"display_name": "X"}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    monkeypatch.setattr(sl, "git_branch", lambda _cwd: None)
    monkeypatch.setattr(sl, "fpf_drift_value", lambda _path: None)

    called: list[bool] = []

    def fake_refresh(_path: Path) -> None:
        called.append(True)

    monkeypatch.setattr(sl, "trigger_fpf_refresh", fake_refresh)
    assert sl.run() == 0
    assert called == []
