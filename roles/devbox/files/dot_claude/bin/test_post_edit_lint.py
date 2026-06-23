from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import post_edit_lint
from _claude_lib.proc import CmdResult

if TYPE_CHECKING:
    import pytest


def _fail(stdout: str = "", stderr: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr=stderr, returncode=1, timed_out=False)


def _ok(stdout: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def test_is_dockerfile_recognises_variants() -> None:
    assert post_edit_lint.is_dockerfile(Path("/tmp/Dockerfile"))
    assert post_edit_lint.is_dockerfile(Path("/tmp/Dockerfile.dev"))
    assert post_edit_lint.is_dockerfile(Path("/tmp/web.dockerfile"))
    assert not post_edit_lint.is_dockerfile(Path("/tmp/main.go"))


def test_is_compose_file_recognises_variants() -> None:
    assert post_edit_lint.is_compose_file(Path("/tmp/docker-compose.yml"))
    assert post_edit_lint.is_compose_file(Path("/tmp/compose.yaml"))
    assert not post_edit_lint.is_compose_file(Path("/tmp/notes.yml"))


def test_filter_lines_for_file_matches_name() -> None:
    text = "main.go:10:1 issue\nother.go:5 issue\nmain.go:20 also"
    assert post_edit_lint.filter_lines_for_file(text, "main.go") == [
        "main.go:10:1 issue",
        "main.go:20 also",
    ]


def test_ruff_report_returns_none_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_lint.proc, "run_cmd", lambda *_a, **_k: _ok())
    assert post_edit_lint.ruff_report(target) is None


def test_ruff_report_returns_lines_on_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        post_edit_lint.proc,
        "run_cmd",
        lambda *_a, **_k: _fail(stdout="x.py:1:1: F401 unused\n"),
    )
    report = post_edit_lint.ruff_report(target)
    assert report is not None
    assert report.tool == "ruff"
    assert "F401" in report.body


def test_eslint_report_skips_without_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "x.ts"
    target.write_text("export {}", encoding="utf-8")
    monkeypatch.setattr(post_edit_lint.paths, "find_project_root", lambda *_a, **_k: None)
    assert post_edit_lint.eslint_report(target) is None


def test_golangci_report_filters_lines(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    pkg = project / "pkg"
    pkg.mkdir(parents=True)
    (project / "go.mod").write_text("module test", encoding="utf-8")
    target = pkg / "main.go"
    target.write_text("package pkg\n", encoding="utf-8")

    monkeypatch.setattr(
        post_edit_lint.proc,
        "run_cmd",
        lambda *_a, **_k: _fail(stdout="pkg/main.go:1: issue\nother.go:1: skip"),
    )
    report = post_edit_lint.golangci_report(target)
    assert report is not None
    assert "main.go" in report.body
    assert "other.go" not in report.body


def test_report_for_unknown_extension_returns_none(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("notes", encoding="utf-8")
    assert post_edit_lint.report_for(target) is None


def test_edited_file_path_requires_existing_file(tmp_path: Path) -> None:
    existing = tmp_path / "x.py"
    existing.write_text("x = 1", encoding="utf-8")
    assert post_edit_lint.edited_file_path({"tool_input": {"file_path": str(existing)}}) == existing
    assert (
        post_edit_lint.edited_file_path({"tool_input": {"file_path": str(tmp_path / "missing.py")}})
        is None
    )
    assert post_edit_lint.edited_file_path({"tool_input": {}}) is None
    assert post_edit_lint.edited_file_path({}) is None


def test_main_writes_additional_context_when_issues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        post_edit_lint,
        "report_for",
        lambda _path: post_edit_lint.LintReport(tool="ruff", body="x.py:1:1: F401"),
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
    assert post_edit_lint.main() == 0
    payload = json.loads(out.getvalue())
    assert "ruff issues" in payload["additionalContext"]
    assert "Fix these lint issues" in payload["additionalContext"]


def test_main_silent_when_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_lint, "report_for", lambda _path: None)
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
    assert post_edit_lint.main() == 0
    assert out.getvalue() == ""


def test_main_handles_empty_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert post_edit_lint.main() == 0
    assert out.getvalue() == ""
