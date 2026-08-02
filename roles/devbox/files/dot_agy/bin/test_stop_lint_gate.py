from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stop_lint_gate
from _claude_lib.proc import CmdResult

if TYPE_CHECKING:
    import pytest


def _ok(stdout: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _fail(stdout: str = "", stderr: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr=stderr, returncode=1, timed_out=False)


def test_is_lintable_recognises_known_extensions() -> None:
    assert stop_lint_gate.is_lintable(Path("/tmp/foo.go"))
    assert stop_lint_gate.is_lintable(Path("/tmp/foo.py"))
    assert stop_lint_gate.is_lintable(Path("/tmp/Dockerfile"))
    assert not stop_lint_gate.is_lintable(Path("/tmp/notes.md"))


def test_filter_lines_for_file() -> None:
    text = "x.go:1 issue\ny.go:1 skip\nx.go:5 another"
    assert stop_lint_gate.filter_lines_for_file(text, "x.go") == [
        "x.go:1 issue",
        "x.go:5 another",
    ]


def test_lint_python_returns_none_when_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(stop_lint_gate.proc, "run_cmd", lambda *_a, **_k: _ok())
    assert stop_lint_gate.lint_python(target) is None


def test_lint_python_returns_diagnostic_when_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        stop_lint_gate.proc,
        "run_cmd",
        lambda *_a, **_k: _fail(stdout="x.py:1:1: F401 unused"),
    )
    result = stop_lint_gate.lint_python(target)
    assert result is not None
    assert "ruff:" in result
    assert "F401" in result


def test_lint_go_no_go_mod_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "main.go"
    target.write_text("package main", encoding="utf-8")
    monkeypatch.setattr(stop_lint_gate.paths, "find_project_root", lambda *_a, **_k: None)
    assert stop_lint_gate.lint_go(target) is None


def test_lint_file_dispatches_dockerfile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "Dockerfile"
    target.write_text("FROM scratch", encoding="utf-8")
    monkeypatch.setattr(
        stop_lint_gate.proc,
        "run_cmd",
        lambda *_a, **_k: _fail(stdout="DL3000"),
    )
    result = stop_lint_gate.lint_file(target)
    assert result is not None
    assert "hadolint" in result


def test_modified_files_filters_to_existing_lintable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    py_file = tmp_path / "x.py"
    py_file.write_text("x = 1", encoding="utf-8")
    md_file = tmp_path / "notes.md"
    md_file.write_text("notes", encoding="utf-8")

    monkeypatch.setattr(
        stop_lint_gate.proc,
        "run_cmd",
        lambda *_a, **_k: _ok(stdout="x.py\nnotes.md\nmissing.py"),
    )
    result = stop_lint_gate.modified_files(tmp_path)
    assert result == [py_file.resolve()]


def test_render_message_summarises_issues() -> None:
    msg = stop_lint_gate.render_message(["x.py:\nruff: F401", "y.go:\ngolangci-lint: error"])
    assert "2 file(s)" in msg
    assert "x.py" in msg
    assert "y.go" in msg
    assert "Fix all lint issues" in msg


def test_main_returns_zero_when_stop_hook_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"stop_hook_active": True})))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert stop_lint_gate.main() == 0
    assert out.getvalue() == ""


def test_main_returns_zero_when_no_modified_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"stop_hook_active": False})))
    monkeypatch.setattr(stop_lint_gate, "modified_files", lambda _cwd: [])
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert stop_lint_gate.main() == 0
    assert out.getvalue() == ""


def test_main_writes_context_when_issues_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1", encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"stop_hook_active": False})))
    monkeypatch.setattr(stop_lint_gate, "modified_files", lambda _cwd: [target])
    monkeypatch.setattr(stop_lint_gate, "lint_file", lambda _p: "ruff:\nbad")
    monkeypatch.setattr(stop_lint_gate, "typecheck_file", lambda _p: None)
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert stop_lint_gate.main() == 0
    payload = json.loads(out.getvalue())
    assert "1 file(s)" in payload["additionalContext"]


def test_main_silent_when_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1", encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"stop_hook_active": False})))
    monkeypatch.setattr(stop_lint_gate, "modified_files", lambda _cwd: [target])
    monkeypatch.setattr(stop_lint_gate, "lint_file", lambda _p: None)
    monkeypatch.setattr(stop_lint_gate, "typecheck_file", lambda _p: None)
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert stop_lint_gate.main() == 0
    assert out.getvalue() == ""
