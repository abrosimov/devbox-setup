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


def _fail(stdout: str) -> CmdResult:
    return CmdResult(stdout=stdout, stderr="", returncode=1, timed_out=False)


def test_mypy_report_returns_none_when_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x: int = 1\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_typecheck.proc, "run_cmd", lambda *_a, **_k: _ok())
    assert post_edit_typecheck.mypy_report(target) is None


def test_mypy_report_filters_to_error_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    output = "x.py:1: note: skip\nx.py:2: error: bad type\nx.py:3: error: more\n"
    monkeypatch.setattr(post_edit_typecheck.proc, "run_cmd", lambda *_a, **_k: _fail(output))
    report = post_edit_typecheck.mypy_report(target)
    assert report is not None
    assert "mypy errors in x.py" in report
    assert "bad type" in report
    assert "more" in report
    assert "skip" not in report


def test_mypy_report_truncates_above_max(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    lines = "\n".join(f"x.py:{i}: error: bug {i}" for i in range(15))
    monkeypatch.setattr(post_edit_typecheck.proc, "run_cmd", lambda *_a, **_k: _fail(lines))
    report = post_edit_typecheck.mypy_report(target)
    assert report is not None
    assert "and 5 more" in report


def test_mypy_report_skips_without_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_typecheck.paths, "find_project_root", lambda *_a, **_k: None)
    assert post_edit_typecheck.mypy_report(target) is None


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
        post_edit_typecheck, "report_for", lambda _p: "[typecheck] mypy errors in x.py:\nfoo"
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
    assert "mypy errors" in payload["additionalContext"]


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
