from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import post_edit_lint
from _claude_lib import findings, paths, session_state
from _claude_lib.proc import CmdResult

if TYPE_CHECKING:
    import pytest


def _fail(stdout: str = "", stderr: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr=stderr, returncode=1, timed_out=False)


def _ok(stdout: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    state_root = tmp_path / "state"
    monkeypatch.setattr(session_state, "state_root", lambda: state_root)
    monkeypatch.setattr(paths, "temp_roots", lambda: (tmp_path / "scratch",))
    return state_root


def _run_main(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> str:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert post_edit_lint.main() == 0
    return out.getvalue()


def _edit_payload(target: Path, *, new_start: int, lines: list[str]) -> dict[str, object]:
    return {
        "session_id": "sess-1",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(target)},
        "tool_response": {
            "structuredPatch": [
                {"oldStart": new_start, "newStart": new_start, "lines": lines},
            ],
        },
    }


def test_is_dockerfile_recognises_variants() -> None:
    assert post_edit_lint.is_dockerfile(Path("/tmp/Dockerfile"))
    assert post_edit_lint.is_dockerfile(Path("/tmp/Dockerfile.dev"))
    assert post_edit_lint.is_dockerfile(Path("/tmp/web.dockerfile"))
    assert not post_edit_lint.is_dockerfile(Path("/tmp/main.go"))


def test_is_compose_file_recognises_variants() -> None:
    assert post_edit_lint.is_compose_file(Path("/tmp/docker-compose.yml"))
    assert post_edit_lint.is_compose_file(Path("/tmp/compose.yaml"))
    assert not post_edit_lint.is_compose_file(Path("/tmp/notes.yml"))


def test_ruff_report_returns_none_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_lint.proc, "run_cmd", lambda *_a, **_k: _ok())
    assert post_edit_lint.ruff_report(target) is None


def test_ruff_report_parses_concise_findings_for_the_edited_file_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    calls: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> CmdResult:
        calls.append(command)
        return _fail(
            stdout="x.py:1:1: F401 unused\nother.py:2:1: E999 elsewhere\nFound 2 errors.\n"
        )

    monkeypatch.setattr(post_edit_lint.proc, "run_cmd", run)
    report = post_edit_lint.ruff_report(target)
    assert report is not None
    assert report.tool == "ruff"
    assert report.findings == (
        findings.Finding(path=target.resolve(), line=1, message="F401 unused"),
    )
    assert calls[0][:4] == ["ruff", "check", "--output-format", "concise"]


def test_hadolint_report_drops_info_and_style_findings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "Dockerfile"
    target.write_text("FROM ubuntu\n", encoding="utf-8")
    output = (
        f"{target}:1 DL3006 warning: Always tag the version\n"
        f"{target}:2 DL3015 info: Avoid additional packages\n"
        f"{target}:3 DL3048 style: Invalid label key\n"
    )
    monkeypatch.setattr(post_edit_lint.proc, "run_cmd", lambda *_a, **_k: _fail(stdout=output))
    report = post_edit_lint.hadolint_report(target)
    assert report is not None
    assert [item.line for item in report.findings] == [1]


def test_hadolint_report_with_only_info_findings_is_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "Dockerfile"
    target.write_text("FROM ubuntu\n", encoding="utf-8")
    output = f"{target}:2 DL3015 info: Avoid additional packages\n"
    monkeypatch.setattr(post_edit_lint.proc, "run_cmd", lambda *_a, **_k: _fail(stdout=output))
    assert post_edit_lint.hadolint_report(target) is None


def test_dclint_report_parses_json_findings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "compose.yml"
    target.write_text("services: {}\n", encoding="utf-8")
    output = json.dumps(
        [
            {
                "filePath": str(target),
                "messages": [
                    {"rule": "no-version-field", "type": "error", "message": "No.", "line": 1},
                ],
            },
        ],
    )
    monkeypatch.setattr(post_edit_lint.proc, "run_cmd", lambda *_a, **_k: _fail(stdout=output))
    report = post_edit_lint.dclint_report(target)
    assert report is not None
    assert report.findings[0].message == "error No. (no-version-field)"


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

    calls: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> CmdResult:
        calls.append(command)
        return _fail(stdout="pkg/main.go:1:2: issue (errcheck)\nother.go:1: skip\n1 issues:\n")

    monkeypatch.setattr(post_edit_lint.proc, "run_cmd", run)
    report = post_edit_lint.golangci_report(target)
    assert report is not None
    assert [item.render() for item in report.findings] == ["main.go:1: issue (errcheck)"]
    assert "--fast-only" in calls[0]
    assert "--fast" not in calls[0]


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


class TestTouchedLines:
    def test_added_and_replaced_lines_are_touched(self) -> None:
        payload = _edit_payload(
            Path("x.py"),
            new_start=10,
            lines=[" context", "-old", "+new one", "+new two", " context"],
        )
        assert post_edit_lint.touched_lines(payload) == frozenset({11, 12})

    def test_pure_deletion_marks_the_line_now_in_its_place(self) -> None:
        payload = _edit_payload(Path("x.py"), new_start=4, lines=[" keep", "-gone", " next"])
        assert post_edit_lint.touched_lines(payload) == frozenset({5})

    def test_multiple_hunks_are_combined(self) -> None:
        payload: dict[str, object] = {
            "tool_response": {
                "structuredPatch": [
                    {"newStart": 1, "lines": ["+a"]},
                    {"newStart": 30, "lines": [" x", "+b", "\\ No newline at end of file"]},
                ],
            },
        }
        assert post_edit_lint.touched_lines(payload) == frozenset({1, 31})

    def test_write_that_creates_a_file_touches_the_whole_file(self) -> None:
        payload: dict[str, object] = {"tool_response": {"type": "create", "structuredPatch": []}}
        assert post_edit_lint.touched_lines(payload) is None

    def test_missing_tool_response_means_whole_file(self) -> None:
        assert post_edit_lint.touched_lines({"tool_input": {}}) is None


def _fake_ruff_report(target: Path, lines: list[int]) -> post_edit_lint.LintReport:
    return post_edit_lint.LintReport(
        tool="ruff",
        findings=tuple(
            findings.Finding(path=target.resolve(), line=line, message=f"F541 issue {line}")
            for line in lines
        ),
    )


def test_main_reports_only_findings_on_touched_lines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolate(monkeypatch, tmp_path)
    target = tmp_path / "x.py"
    target.write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_lint, "report_for", lambda path: _fake_ruff_report(path, [1, 2]))

    out = _run_main(monkeypatch, _edit_payload(target, new_start=1, lines=[" a = 1", "+b = 2"]))

    context = json.loads(out)["additionalContext"]
    assert "x.py:2: F541 issue 2" in context
    assert "issue 1" not in context
    assert "Fix the issues your edit introduced" in context
    assert "mention it in your report" in context


def test_main_does_not_repeat_an_identical_finding_in_one_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolate(monkeypatch, tmp_path)
    target = tmp_path / "x.py"
    target.write_text("a = 1\nb = 2\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_lint, "report_for", lambda path: _fake_ruff_report(path, [2]))
    payload = _edit_payload(target, new_start=1, lines=[" a = 1", "+b = 2"])

    first = _run_main(monkeypatch, payload)
    second = _run_main(monkeypatch, payload)

    assert first
    assert second == ""


def test_main_reports_the_same_finding_again_in_another_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolate(monkeypatch, tmp_path)
    target = tmp_path / "x.py"
    target.write_text("a = 1\nb = 2\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_lint, "report_for", lambda path: _fake_ruff_report(path, [2]))
    payload = _edit_payload(target, new_start=1, lines=[" a = 1", "+b = 2"])

    assert _run_main(monkeypatch, payload)
    assert _run_main(monkeypatch, {**payload, "session_id": "sess-2"})


def test_main_records_the_edited_file_for_the_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_root = _isolate(monkeypatch, tmp_path)
    target = tmp_path / "notes.md"
    target.write_text("notes\n", encoding="utf-8")

    assert (
        _run_main(monkeypatch, {"session_id": "sess-1", "tool_input": {"file_path": str(target)}})
        == ""
    )

    state = session_state.SessionState(state_root / "sess-1")
    assert state.edited_paths() == (target.resolve(),)


def test_main_skips_files_in_the_temp_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_root = _isolate(monkeypatch, tmp_path)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    target = scratch / "probe.py"
    target.write_text("x = f'a'\n", encoding="utf-8")

    def must_not_lint(_path: Path) -> post_edit_lint.LintReport | None:
        message = "temp files must not be linted"
        raise AssertionError(message)

    monkeypatch.setattr(post_edit_lint, "report_for", must_not_lint)

    assert (
        _run_main(monkeypatch, {"session_id": "sess-1", "tool_input": {"file_path": str(target)}})
        == ""
    )
    assert not (state_root / "sess-1").exists()


def test_main_silent_when_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolate(monkeypatch, tmp_path)
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(post_edit_lint, "report_for", lambda _path: None)
    assert _run_main(monkeypatch, {"tool_input": {"file_path": str(target)}}) == ""


def test_main_handles_empty_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert post_edit_lint.main() == 0
    assert out.getvalue() == ""
