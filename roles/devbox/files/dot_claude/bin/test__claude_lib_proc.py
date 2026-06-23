from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import proc


def test_run_cmd_success_captures_stdout() -> None:
    result = proc.run_cmd(["printf", "hello"])
    assert result.success
    assert result.returncode == 0
    assert result.stdout == "hello"
    assert result.stderr == ""
    assert not result.timed_out


def test_run_cmd_failure_returns_nonzero() -> None:
    result = proc.run_cmd(["false"])
    assert not result.success
    assert result.returncode != 0
    assert not result.timed_out


def test_run_cmd_missing_binary_returns_error() -> None:
    result = proc.run_cmd(["/no/such/binary-xyz123"])
    assert not result.success
    assert result.returncode != 0
    assert result.stderr != ""


def test_run_cmd_string_command_is_shell_split() -> None:
    result = proc.run_cmd("printf hello")
    assert result.success
    assert result.stdout == "hello"


def test_run_cmd_timeout_marks_timed_out() -> None:
    result = proc.run_cmd(["sleep", "5"], timeout=1)
    assert not result.success
    assert result.timed_out


def test_run_cmd_respects_cwd(tmp_path: Path) -> None:
    result = proc.run_cmd(["pwd"], cwd=tmp_path)
    assert result.success
    assert Path(result.stdout.strip()).resolve() == tmp_path.resolve()


def test_run_cmd_passes_input_text() -> None:
    result = proc.run_cmd(["cat"], input_text="piped-input")
    assert result.success
    assert result.stdout == "piped-input"


def test_cmd_result_is_immutable() -> None:
    result = proc.run_cmd(["true"])
    assert dataclasses.is_dataclass(result)
    msg = "CmdResult must be frozen"
    try:
        result.returncode = 99  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError(msg)
