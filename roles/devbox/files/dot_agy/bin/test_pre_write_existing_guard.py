#!/usr/bin/env python3
"""Tests for pre-write-existing-guard.

Run from any directory:
    pytest roles/devbox/files/dot_claude/bin/test_pre_write_existing_guard.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_write_existing_guard as guard

# --- _extract_file_path ------------------------------------------------------


def test_returns_path_from_valid_event() -> None:
    raw = '{"tool_input": {"file_path": "/tmp/foo.py"}}'
    assert guard._extract_file_path(raw) == "/tmp/foo.py"


def test_returns_none_on_empty_string() -> None:
    assert guard._extract_file_path("") is None


def test_returns_none_on_whitespace_only() -> None:
    assert guard._extract_file_path("   \n  ") is None


def test_returns_none_on_invalid_json() -> None:
    assert guard._extract_file_path("{not json") is None


def test_returns_none_when_event_is_not_dict() -> None:
    assert guard._extract_file_path('["list", "not", "dict"]') is None


def test_returns_none_when_tool_input_missing() -> None:
    assert guard._extract_file_path('{"other_key": "value"}') is None


def test_returns_none_when_tool_input_is_not_dict() -> None:
    assert guard._extract_file_path('{"tool_input": "a string"}') is None


def test_returns_none_when_tool_input_is_null() -> None:
    assert guard._extract_file_path('{"tool_input": null}') is None


def test_returns_none_when_file_path_missing() -> None:
    assert guard._extract_file_path('{"tool_input": {"other": "x"}}') is None


def test_returns_none_when_file_path_is_not_string() -> None:
    assert guard._extract_file_path('{"tool_input": {"file_path": 42}}') is None


def test_returns_none_when_file_path_is_null() -> None:
    assert guard._extract_file_path('{"tool_input": {"file_path": null}}') is None


def test_returns_none_when_file_path_is_empty_string() -> None:
    assert guard._extract_file_path('{"tool_input": {"file_path": ""}}') is None


def test_returns_none_when_file_path_is_false() -> None:
    assert guard._extract_file_path('{"tool_input": {"file_path": false}}') is None


def test_accepts_path_with_spaces() -> None:
    raw = '{"tool_input": {"file_path": "/home/user/my file.py"}}'
    assert guard._extract_file_path(raw) == "/home/user/my file.py"


def test_extra_keys_are_ignored() -> None:
    raw = '{"tool_name": "Write", "tool_input": {"file_path": "/x.py", "content": "..."}}'
    assert guard._extract_file_path(raw) == "/x.py"


# --- _is_blocking: True only for existing non-empty files --------------------


def test_true_for_existing_non_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_bytes(b"content")
    assert guard._is_blocking(str(f)) is True


def test_false_for_missing_file() -> None:
    # OSError must be swallowed, not propagated.
    assert guard._is_blocking("/no/such/path/file.py") is False


def test_false_for_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "empty.txt"
    f.touch()
    assert guard._is_blocking(str(f)) is False


def test_true_for_single_byte_file(tmp_path: Path) -> None:
    # Boundary: size == 1 must block.
    f = tmp_path / "one.txt"
    f.write_bytes(b"x")
    assert guard._is_blocking(str(f)) is True


def test_true_for_file_with_only_newline(tmp_path: Path) -> None:
    # Newline-only files have size > 0 — must block.
    f = tmp_path / "nl.txt"
    f.write_bytes(b"\n")
    assert guard._is_blocking(str(f)) is True


# --- _is_blocking: fails open on any OSError --------------------------------


def test_false_when_stat_raises_oserror() -> None:
    with mock.patch("pathlib.Path.stat", side_effect=OSError("permission denied")):
        assert guard._is_blocking("/some/path.py") is False


def test_false_when_stat_raises_permission_error() -> None:
    # PermissionError is a subclass of OSError.
    with mock.patch("pathlib.Path.stat", side_effect=PermissionError("denied")):
        assert guard._is_blocking("/root/secret.py") is False


def test_false_when_stat_raises_file_not_found() -> None:
    # FileNotFoundError is a subclass of OSError — explicit mock for clarity.
    with mock.patch("pathlib.Path.stat", side_effect=FileNotFoundError("missing")):
        assert guard._is_blocking("/missing.py") is False


def test_main_exit_0_when_stat_raises_oserror() -> None:
    # Fail-open: any stat error must not block the write.
    raw = '{"tool_input": {"file_path": "/some/file.py"}}'
    with (
        mock.patch("pathlib.Path.stat", side_effect=OSError("disk error")),
        mock.patch.object(sys, "stdin", io.StringIO(raw)),
        mock.patch.object(sys, "stderr", io.StringIO()),
    ):
        assert guard.main() == 0


# --- main: end-to-end via stdin and exit-code capture ----------------------


def _run_main(stdin_text: str) -> tuple[int, str]:
    stderr_cap = io.StringIO()
    with (
        mock.patch.object(sys, "stdin", io.StringIO(stdin_text)),
        mock.patch.object(sys, "stderr", stderr_cap),
    ):
        exit_code = guard.main()
    return exit_code, stderr_cap.getvalue()


def test_exit_0_when_no_file_path() -> None:
    code, err = _run_main('{"tool_input": {}}')
    assert code == 0
    assert err == ""


def test_exit_0_when_file_path_missing_on_disk() -> None:
    raw = '{"tool_input": {"file_path": "/no/such/file.py"}}'
    code, err = _run_main(raw)
    assert code == 0
    assert err == ""


def test_exit_0_when_file_exists_but_is_empty(tmp_path: Path) -> None:
    f = tmp_path / "empty.txt"
    f.touch()
    raw = f'{{"tool_input": {{"file_path": "{f}"}}}}'
    code, err = _run_main(raw)
    assert code == 0
    assert err == ""


def test_exit_2_when_file_exists_non_empty(tmp_path: Path) -> None:
    f = tmp_path / "nonempty.txt"
    f.write_bytes(b"existing content")
    raw = f'{{"tool_input": {{"file_path": "{f}"}}}}'
    code, _ = _run_main(raw)
    assert code == 2


def test_stderr_contains_blocked_prefix_on_exit_2(tmp_path: Path) -> None:
    f = tmp_path / "data.txt"
    f.write_bytes(b"data")
    raw = f'{{"tool_input": {{"file_path": "{f}"}}}}'
    _, err = _run_main(raw)
    assert err.startswith("BLOCKED [pre-write-existing-guard]:")


def test_stderr_contains_file_path_on_exit_2(tmp_path: Path) -> None:
    f = tmp_path / "data.txt"
    f.write_bytes(b"data")
    raw = f'{{"tool_input": {{"file_path": "{f}"}}}}'
    _, err = _run_main(raw)
    assert str(f) in err


def test_stderr_suggests_edit_alternative_on_exit_2(tmp_path: Path) -> None:
    f = tmp_path / "data.txt"
    f.write_bytes(b"data")
    raw = f'{{"tool_input": {{"file_path": "{f}"}}}}'
    _, err = _run_main(raw)
    assert "Edit" in err
    assert "MultiEdit" in err


def test_exit_0_on_empty_stdin() -> None:
    code, err = _run_main("")
    assert code == 0
    assert err == ""


def test_exit_0_on_invalid_json() -> None:
    code, err = _run_main("{bad json")
    assert code == 0
    assert err == ""
