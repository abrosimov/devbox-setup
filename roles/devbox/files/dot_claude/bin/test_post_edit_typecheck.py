from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import post_edit_typecheck
from _claude_lib.proc import CmdResult

if TYPE_CHECKING:
    import pytest


def _ok() -> CmdResult:
    return CmdResult(stdout="", stderr="", returncode=0, timed_out=False)


def _fail(stdout: str, stderr: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr=stderr, returncode=1, timed_out=False)


def test_pyrefly_report_returns_none_when_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x: int = 1\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_typecheck.proc, "run_cmd", lambda *_a, **_k: _ok())
    assert post_edit_typecheck.pyrefly_report(target) is None


def test_pyrefly_report_requests_one_line_per_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The parser keys off `min-text`'s one-line-per-error shape, so the flag that
    # selects it is part of the contract, not an incidental argument.
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    captured: list[list[str]] = []

    def run(cmd: list[str], **_kwargs: object) -> CmdResult:
        captured.append(cmd)
        return _ok()

    monkeypatch.setattr(post_edit_typecheck.proc, "run_cmd", run)
    assert post_edit_typecheck.pyrefly_report(target) is None
    assert captured == [
        ["uv", "run", "pyrefly", "check", "--output-format", "min-text", str(target)]
    ]


def test_pyrefly_report_runs_bare_without_uv_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    captured: list[list[str]] = []

    def run(cmd: list[str], **_kwargs: object) -> CmdResult:
        captured.append(cmd)
        return _ok()

    monkeypatch.setattr(post_edit_typecheck.proc, "run_cmd", run)
    assert post_edit_typecheck.pyrefly_report(target) is None
    assert captured == [["pyrefly", "check", "--output-format", "min-text", str(target)]]


def test_pyrefly_report_filters_to_error_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    stdout = (
        "ERROR x.py:2:12-13: Returned type `int` is not assignable to "
        "declared return type `str` [bad-return]\n"
        "ERROR x.py:10:5-17: Could not find name `unknown_name` [unknown-name]\n"
    )
    stderr = " INFO 2 errors\nNo `pyrefly.toml` found — using preset `basic`.\n"
    monkeypatch.setattr(
        post_edit_typecheck.proc, "run_cmd", lambda *_a, **_k: _fail(stdout, stderr)
    )
    report = post_edit_typecheck.pyrefly_report(target)
    assert report is not None
    assert "pyrefly errors in x.py" in report
    assert "x.py:2:12-13: Returned type `int` is not assignable" in report
    assert "[unknown-name]" in report
    assert "ERROR" not in report
    assert "INFO" not in report
    assert "preset" not in report


def test_pyrefly_report_truncates_above_max(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    lines = "\n".join(
        f"ERROR x.py:{i}:1-2: Could not find name `n{i}` [unknown-name]" for i in range(15)
    )
    monkeypatch.setattr(post_edit_typecheck.proc, "run_cmd", lambda *_a, **_k: _fail(lines))
    report = post_edit_typecheck.pyrefly_report(target)
    assert report is not None
    assert "and 5 more" in report


def test_pyrefly_report_silent_when_only_non_error_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A missing binary or an unparseable config exits non-zero with nothing on
    # stdout; the hook must stay quiet rather than report a tool failure as a
    # type error.
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        post_edit_typecheck.proc,
        "run_cmd",
        lambda *_a, **_k: _fail("", "No such file or directory: 'pyrefly'"),
    )
    assert post_edit_typecheck.pyrefly_report(target) is None


def test_pyrefly_report_skips_without_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_typecheck.paths, "find_project_root", lambda *_a, **_k: None)
    assert post_edit_typecheck.pyrefly_report(target) is None


def test_tsc_report_filters_to_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "tsconfig.json").write_text("{}", encoding="utf-8")
    target = project / "src" / "x.ts"
    target.parent.mkdir()
    target.write_text("export const x: number = 1;", encoding="utf-8")
    output = "src/x.ts(2,1): error TS2322: Type bad\nother.ts(5,1): error TS999"
    monkeypatch.setattr(post_edit_typecheck.proc, "run_cmd", lambda *_a, **_k: _fail(output))
    report = post_edit_typecheck.tsc_report(target)
    assert report is not None
    assert "x.ts" in report
    assert "other.ts" not in report


def test_report_for_returns_none_for_unknown_ext(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    target.write_text("hello", encoding="utf-8")
    assert post_edit_typecheck.report_for(target) is None


def test_main_writes_when_report_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1", encoding="utf-8")
    monkeypatch.setattr(
        post_edit_typecheck, "report_for", lambda _p: "[typecheck] pyrefly errors in x.py:\nfoo"
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {"file_path": str(target)},
                }
            )
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert post_edit_typecheck.main() == 0
    payload = json.loads(out.getvalue())
    assert "pyrefly errors" in payload["additionalContext"]


def test_main_silent_when_no_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1", encoding="utf-8")
    monkeypatch.setattr(post_edit_typecheck, "report_for", lambda _p: None)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {"file_path": str(target)},
                }
            )
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert post_edit_typecheck.main() == 0
    assert out.getvalue() == ""
