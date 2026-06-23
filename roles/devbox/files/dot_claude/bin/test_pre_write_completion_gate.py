from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_write_completion_gate
from _claude_lib.proc import CmdResult

if TYPE_CHECKING:
    import pytest


def _cmd(
    stdout: str = "", returncode: int = 0, *, timed_out: bool = False, stderr: str = ""
) -> CmdResult:
    return CmdResult(stdout=stdout, stderr=stderr, returncode=returncode, timed_out=timed_out)


def test_lang_from_filename_known_suffixes() -> None:
    assert pre_write_completion_gate.lang_from_filename("se_go_output.json") == "go"
    assert pre_write_completion_gate.lang_from_filename("se_python_output.json") == "python"
    assert pre_write_completion_gate.lang_from_filename("se_frontend_output.json") == "node"


def test_lang_from_filename_unknown_returns_none() -> None:
    assert pre_write_completion_gate.lang_from_filename("se_rust_output.json") is None
    assert pre_write_completion_gate.lang_from_filename("notes.md") is None


def test_format_failures_collects_failed_checks() -> None:
    parsed: dict[str, object] = {
        "result": "FAIL",
        "checks": {
            "build": {"status": "FAIL", "detail": "compile error", "error": "x"},
            "lint": {"status": "PASS"},
            "test": {"status": "FAIL", "detail": "test failure"},
        },
    }
    out = pre_write_completion_gate.format_failures(parsed)
    assert "build: compile error" in out
    assert "test: test failure" in out
    assert "lint" not in out


def test_main_passes_through_for_unrelated_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {"file_path": str(tmp_path / "regular.py")},
                }
            )
        ),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_write_completion_gate.main() == 0
    assert err.getvalue() == ""


def test_main_blocks_unknown_lang(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "se_rust_output.json"
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
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_write_completion_gate.main() == 2
    assert "Unknown language suffix" in err.getvalue()


def test_main_blocks_when_no_project_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "se_go_output.json"
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
    monkeypatch.setattr(
        pre_write_completion_gate.paths, "find_project_root", lambda *_a, **_k: None
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_write_completion_gate.main() == 2
    assert "project root" in err.getvalue()


def test_main_blocks_when_verify_script_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "go.mod").write_text("module x", encoding="utf-8")
    target = project / "se_go_output.json"
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
    monkeypatch.setattr(
        pre_write_completion_gate,
        "verify_script_path",
        lambda: tmp_path / "nonexistent" / "verify-se-completion",
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_write_completion_gate.main() == 2
    assert "verify-se-completion script not found" in err.getvalue()


def test_main_allows_when_verification_passes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "go.mod").write_text("module x", encoding="utf-8")
    target = project / "se_go_output.json"
    verify_script = tmp_path / "verify"
    verify_script.write_text("#!/bin/sh\necho ok", encoding="utf-8")

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
    monkeypatch.setattr(pre_write_completion_gate, "verify_script_path", lambda: verify_script)
    monkeypatch.setattr(
        pre_write_completion_gate.proc,
        "run_cmd",
        lambda *_a, **_k: _cmd(stdout=json.dumps({"result": "PASS"})),
    )
    assert pre_write_completion_gate.main() == 0


def test_main_blocks_when_verification_fails_with_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "go.mod").write_text("module x", encoding="utf-8")
    target = project / "se_go_output.json"
    verify_script = tmp_path / "verify"
    verify_script.write_text("#!/bin/sh\necho fail", encoding="utf-8")

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
    monkeypatch.setattr(pre_write_completion_gate, "verify_script_path", lambda: verify_script)
    monkeypatch.setattr(
        pre_write_completion_gate.proc,
        "run_cmd",
        lambda *_a, **_k: _cmd(
            stdout=json.dumps(
                {
                    "result": "FAIL",
                    "checks": {"build": {"status": "FAIL", "detail": "boom"}},
                }
            ),
            returncode=1,
        ),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_write_completion_gate.main() == 2
    assert "build: boom" in err.getvalue()


def test_main_blocks_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "go.mod").write_text("module x", encoding="utf-8")
    target = project / "se_go_output.json"
    verify_script = tmp_path / "verify"
    verify_script.write_text("#!/bin/sh\nsleep 1", encoding="utf-8")

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
    monkeypatch.setattr(pre_write_completion_gate, "verify_script_path", lambda: verify_script)
    monkeypatch.setattr(
        pre_write_completion_gate.proc,
        "run_cmd",
        lambda *_a, **_k: _cmd(timed_out=True, returncode=-1),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_write_completion_gate.main() == 2
    assert "timed out" in err.getvalue()
