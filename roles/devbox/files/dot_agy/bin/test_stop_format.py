#!/usr/bin/env python3
"""Tests for stop-format.

Run from any directory:
    pytest roles/devbox/files/dot_claude/bin/test_stop_format.py
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stop_format as sf

# --- stdin handling ---------------------------------------------------------


def _run_main_with_empty_modified(stdin_text: str) -> int:
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[]),
        mock.patch.object(sys, "stdin", io.StringIO(stdin_text)),
    ):
        return sf.main()


def test_valid_json_proceeds() -> None:
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[]) as m,
        mock.patch.object(sys, "stdin", io.StringIO('{"type":"stop"}')),
    ):
        result = sf.main()
    assert result == 0
    m.assert_called_once()


def test_empty_stdin_proceeds() -> None:
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[]) as m,
        mock.patch.object(sys, "stdin", io.StringIO("")),
    ):
        result = sf.main()
    assert result == 0
    m.assert_called_once()


def test_whitespace_only_stdin_proceeds() -> None:
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[]) as m,
        mock.patch.object(sys, "stdin", io.StringIO("   \n  ")),
    ):
        result = sf.main()
    assert result == 0
    m.assert_called_once()


def test_invalid_json_warns_and_continues() -> None:
    stderr_cap = io.StringIO()
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[]) as m,
        mock.patch.object(sys, "stdin", io.StringIO("{not json")),
        mock.patch.object(sys, "stderr", stderr_cap),
    ):
        result = sf.main()
    assert result == 0
    m.assert_called_once()
    assert "[stop-format] warning: invalid stdin JSON, formatting anyway" in stderr_cap.getvalue()


def test_main_always_returns_zero() -> None:
    assert _run_main_with_empty_modified('{"ok": true}') == 0


# --- _git_modified_files ----------------------------------------------------


def test_returns_empty_on_git_failure() -> None:
    with mock.patch(
        "subprocess.check_output", side_effect=subprocess.CalledProcessError(128, "git")
    ):
        assert sf._git_modified_files() == []


def test_returns_empty_on_oserror() -> None:
    with mock.patch("subprocess.check_output", side_effect=OSError("no git")):
        assert sf._git_modified_files() == []


def test_returns_empty_on_timeout() -> None:
    with mock.patch("subprocess.check_output", side_effect=subprocess.TimeoutExpired("git", 15)):
        assert sf._git_modified_files() == []


def test_returns_empty_when_diff_is_empty() -> None:
    with mock.patch("subprocess.check_output", return_value=""):
        assert sf._git_modified_files() == []


def test_resolves_relative_paths_to_absolute(tmp_path: Path) -> None:
    f = tmp_path / "main.go"
    f.touch()
    # Give git a relative path and mock cwd so Path resolution finds the file.
    with (
        mock.patch("subprocess.check_output", return_value=f.name + "\n"),
        mock.patch.object(sf.Path, "cwd", return_value=tmp_path),
    ):
        result = sf._git_modified_files()
    assert result == [str(f)]


def test_filters_out_files_that_do_not_exist() -> None:
    with (
        mock.patch("subprocess.check_output", return_value="ghost/file.go\n"),
        mock.patch.object(sf.Path, "cwd", return_value=Path("/some/repo")),
    ):
        result = sf._git_modified_files()
    assert result == []


def test_skips_blank_lines() -> None:
    with mock.patch("subprocess.check_output", return_value="\n\n\n"):
        result = sf._git_modified_files()
    assert result == []


# --- Format dispatch (extension routing) ------------------------------------


def _run_with_extension(ext: str, tmp_path: Path) -> tuple[dict[str, list[str]], str]:
    """Drop a temp file with the given extension, capture which formatter ran."""
    called: dict[str, list[str]] = {"go": [], "py": [], "pr": []}

    def fake_go(p: str) -> None:
        called["go"].append(p)

    def fake_py(p: str) -> None:
        called["py"].append(p)

    def fake_pr(p: str) -> None:
        called["pr"].append(p)

    patched: dict[str, Callable[[str], None]] = {
        ".go": fake_go,
        ".py": fake_py,
        ".ts": fake_pr,
        ".tsx": fake_pr,
        ".js": fake_pr,
        ".jsx": fake_pr,
    }

    tmp = tmp_path / f"file{ext}"
    tmp.touch()
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "FORMATTERS", patched),
        mock.patch.object(sys, "stdin", io.StringIO("")),
    ):
        sf.main()
    return called, str(tmp)


def test_go_routes_to_format_go(tmp_path: Path) -> None:
    called, tmp = _run_with_extension(".go", tmp_path)
    assert called["go"] == [tmp]
    assert called["py"] == []
    assert called["pr"] == []


def test_py_routes_to_format_python(tmp_path: Path) -> None:
    called, tmp = _run_with_extension(".py", tmp_path)
    assert called["py"] == [tmp]
    assert called["go"] == []
    assert called["pr"] == []


def test_ts_routes_to_format_prettier(tmp_path: Path) -> None:
    called, tmp = _run_with_extension(".ts", tmp_path)
    assert called["pr"] == [tmp]
    assert called["go"] == []
    assert called["py"] == []


def test_tsx_routes_to_format_prettier(tmp_path: Path) -> None:
    called, tmp = _run_with_extension(".tsx", tmp_path)
    assert called["pr"] == [tmp]


def test_js_routes_to_format_prettier(tmp_path: Path) -> None:
    called, tmp = _run_with_extension(".js", tmp_path)
    assert called["pr"] == [tmp]


def test_jsx_routes_to_format_prettier(tmp_path: Path) -> None:
    called, tmp = _run_with_extension(".jsx", tmp_path)
    assert called["pr"] == [tmp]


def test_unknown_extension_no_formatter_invoked(tmp_path: Path) -> None:
    called, _ = _run_with_extension(".rb", tmp_path)
    assert called["go"] == []
    assert called["py"] == []
    assert called["pr"] == []


def test_no_extension_no_formatter_invoked(tmp_path: Path) -> None:
    # Files without extension (e.g. Makefile) are silently skipped.
    tmp = tmp_path / "Makefile"
    tmp.touch()
    called: list[str] = []

    def spy(p: str) -> None:
        called.append(p)

    patched: dict[str, Callable[[str], None]] = {
        ".go": spy,
        ".py": spy,
        ".ts": spy,
        ".tsx": spy,
        ".js": spy,
        ".jsx": spy,
    }
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "FORMATTERS", patched),
        mock.patch.object(sys, "stdin", io.StringIO("")),
    ):
        sf.main()
    assert called == []


def test_extension_matching_is_case_insensitive(tmp_path: Path) -> None:
    # main() lowercases the extension before lookup — .GO must route to format_go.
    tmp = tmp_path / "file.GO"
    tmp.touch()
    called: list[str] = []

    def spy(p: str) -> None:
        called.append(p)

    patched: dict[str, Callable[[str], None]] = {
        ".go": spy,
        ".py": spy,
        ".ts": spy,
        ".tsx": spy,
        ".js": spy,
        ".jsx": spy,
    }
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "FORMATTERS", patched),
        mock.patch.object(sys, "stdin", io.StringIO("")),
    ):
        sf.main()
    assert called == [str(tmp)]


# --- format_go --------------------------------------------------------------


def test_returns_none_when_no_gomod(tmp_path: Path) -> None:
    file_path = tmp_path / "main.go"
    file_path.touch()
    result = sf.format_go(str(file_path))
    assert result is None


def test_returns_none_when_gomod_has_no_module_line(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("go 1.21\n", encoding="utf-8")
    file_path = tmp_path / "main.go"
    file_path.touch()
    result = sf.format_go(str(file_path))
    assert result is None


def test_returns_goimports_on_success(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/foo\n\ngo 1.21\n", encoding="utf-8")
    file_path = tmp_path / "main.go"
    file_path.touch()
    with (
        mock.patch.object(sf, "_capture", return_value="/home/user/go"),
        mock.patch.object(sf, "_run", return_value=True) as run_mock,
    ):
        result = sf.format_go(str(file_path))
    assert result == "goimports"
    run_mock.assert_called_once()
    argv = run_mock.call_args[0][0]
    assert argv[0].endswith("goimports")
    assert "-local" in argv
    assert "example.com/foo" in argv
    assert "-w" in argv
    assert str(file_path) in argv


def test_uses_gopath_when_available(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/bar\n", encoding="utf-8")
    file_path = tmp_path / "bar.go"
    file_path.touch()
    with (
        mock.patch.object(sf, "_capture", return_value="/opt/go"),
        mock.patch.object(sf, "_run", return_value=True) as run_mock,
    ):
        sf.format_go(str(file_path))
    argv = run_mock.call_args[0][0]
    assert argv[0] == "/opt/go/bin/goimports"


def test_falls_back_to_bare_goimports_when_gopath_empty(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/baz\n", encoding="utf-8")
    file_path = tmp_path / "baz.go"
    file_path.touch()
    with (
        mock.patch.object(sf, "_capture", return_value=None),
        mock.patch.object(sf, "_run", return_value=True) as run_mock,
    ):
        sf.format_go(str(file_path))
    argv = run_mock.call_args[0][0]
    assert argv[0] == "goimports"


def test_falls_back_when_gopath_is_empty_string(tmp_path: Path) -> None:
    # _capture strips output; an empty GOPATH would return "" which is falsy.
    (tmp_path / "go.mod").write_text("module example.com/baz\n", encoding="utf-8")
    file_path = tmp_path / "baz.go"
    file_path.touch()
    with (
        mock.patch.object(sf, "_capture", return_value=""),
        mock.patch.object(sf, "_run", return_value=True) as run_mock,
    ):
        sf.format_go(str(file_path))
    argv = run_mock.call_args[0][0]
    assert argv[0] == "goimports"


def test_returns_none_when_goimports_fails(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/x\n", encoding="utf-8")
    file_path = tmp_path / "x.go"
    file_path.touch()
    with (
        mock.patch.object(sf, "_capture", return_value=None),
        mock.patch.object(sf, "_run", return_value=False),
    ):
        result = sf.format_go(str(file_path))
    assert result is None


def test_finds_gomod_in_ancestor(tmp_path: Path) -> None:
    # go.mod may be several levels above the file.
    nested = tmp_path / "pkg" / "sub"
    nested.mkdir(parents=True)
    (tmp_path / "go.mod").write_text("module example.com/nested\n", encoding="utf-8")
    file_path = nested / "util.go"
    file_path.touch()
    with (
        mock.patch.object(sf, "_capture", return_value=None),
        mock.patch.object(sf, "_run", return_value=True) as run_mock,
    ):
        result = sf.format_go(str(file_path))
    assert result == "goimports"
    argv = run_mock.call_args[0][0]
    assert "example.com/nested" in argv


# --- format_python ----------------------------------------------------------


def test_returns_ruff_when_both_succeed() -> None:
    with mock.patch.object(sf, "_run", return_value=True):
        assert sf.format_python("/any/file.py") == "ruff"


def test_returns_check_only_when_check_succeeds_format_fails() -> None:
    with mock.patch.object(sf, "_run", side_effect=[True, False]):
        assert sf.format_python("/any/file.py") == "ruff (check only)"


def test_returns_format_only_when_check_fails_format_succeeds() -> None:
    with mock.patch.object(sf, "_run", side_effect=[False, True]):
        assert sf.format_python("/any/file.py") == "ruff (format only)"


def test_returns_none_when_both_fail() -> None:
    with mock.patch.object(sf, "_run", return_value=False):
        assert sf.format_python("/any/file.py") is None


def test_calls_ruff_check_first_then_format() -> None:
    calls: list[list[str]] = []

    def capture_call(argv: list[str], **_: object) -> bool:
        calls.append(argv[:3])
        return True

    with mock.patch.object(sf, "_run", side_effect=capture_call):
        sf.format_python("/any/file.py")
    assert calls[0] == ["ruff", "check", "--fix"]
    assert calls[1] == ["ruff", "format", "--quiet"]


def test_always_runs_both_stages_independently() -> None:
    # Both ruff calls must be made regardless of first result.
    with mock.patch.object(sf, "_run", return_value=False) as run_mock:
        sf.format_python("/any/file.py")
    assert run_mock.call_count == 2


def test_log_line_emitted_once_per_file_via_main(tmp_path: Path) -> None:
    # One [stop-format] line per file, not one per ruff stage.
    tmp = tmp_path / "foo.py"
    tmp.touch()
    stderr_capture = io.StringIO()
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "_run", return_value=True),
        mock.patch.object(sys, "stdin", io.StringIO("")),
        mock.patch.object(sys, "stderr", stderr_capture),
    ):
        sf.main()
    lines = [ln for ln in stderr_capture.getvalue().splitlines() if "[stop-format]" in ln]
    assert len(lines) == 1


def test_log_line_emitted_once_when_check_only_succeeds(tmp_path: Path) -> None:
    # check=True, format=False → tool="ruff (check only)" → exactly one log line.
    tmp = tmp_path / "foo.py"
    tmp.touch()
    stderr_capture = io.StringIO()
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "_run", side_effect=[True, False]),
        mock.patch.object(sys, "stdin", io.StringIO("")),
        mock.patch.object(sys, "stderr", stderr_capture),
    ):
        sf.main()
    lines = [ln for ln in stderr_capture.getvalue().splitlines() if "[stop-format]" in ln]
    assert len(lines) == 1


def test_log_line_emitted_once_when_format_only_succeeds(tmp_path: Path) -> None:
    # check=False, format=True → tool="ruff (format only)" → exactly one log line.
    tmp = tmp_path / "foo.py"
    tmp.touch()
    stderr_capture = io.StringIO()
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "_run", side_effect=[False, True]),
        mock.patch.object(sys, "stdin", io.StringIO("")),
        mock.patch.object(sys, "stderr", stderr_capture),
    ):
        sf.main()
    lines = [ln for ln in stderr_capture.getvalue().splitlines() if "[stop-format]" in ln]
    assert len(lines) == 1


def test_no_log_when_both_stages_fail(tmp_path: Path) -> None:
    # Neither ruff stage succeeds → format_python returns None → no log line.
    tmp = tmp_path / "foo.py"
    tmp.touch()
    stderr_capture = io.StringIO()
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "_run", return_value=False),
        mock.patch.object(sys, "stdin", io.StringIO("")),
        mock.patch.object(sys, "stderr", stderr_capture),
    ):
        sf.main()
    lines = [ln for ln in stderr_capture.getvalue().splitlines() if "[stop-format]" in ln]
    assert len(lines) == 0


# --- format_prettier --------------------------------------------------------


def test_returns_none_when_no_prettier_marker_found(tmp_path: Path) -> None:
    file_path = tmp_path / "app.ts"
    file_path.touch()
    assert sf.format_prettier(str(file_path)) is None


def test_returns_prettier_when_prettierrc_found(tmp_path: Path) -> None:
    (tmp_path / ".prettierrc").touch()
    file_path = tmp_path / "app.ts"
    file_path.touch()
    with mock.patch.object(sf, "_run", return_value=True):
        assert sf.format_prettier(str(file_path)) == "prettier"


def test_returns_prettier_when_package_json_found(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    file_path = tmp_path / "index.js"
    file_path.touch()
    with mock.patch.object(sf, "_run", return_value=True):
        assert sf.format_prettier(str(file_path)) == "prettier"


def test_finds_marker_in_ancestor(tmp_path: Path) -> None:
    nested = tmp_path / "src" / "components"
    nested.mkdir(parents=True)
    (tmp_path / ".prettierrc").touch()
    file_path = nested / "Button.tsx"
    file_path.touch()
    with mock.patch.object(sf, "_run", return_value=True) as run_mock:
        result = sf.format_prettier(str(file_path))
    assert result == "prettier"
    _, kwargs = run_mock.call_args
    assert kwargs.get("cwd") == str(tmp_path)


def test_returns_none_when_npx_prettier_fails(tmp_path: Path) -> None:
    (tmp_path / ".prettierrc").touch()
    file_path = tmp_path / "app.tsx"
    file_path.touch()
    with mock.patch.object(sf, "_run", return_value=False):
        assert sf.format_prettier(str(file_path)) is None


def test_passes_file_path_to_prettier(tmp_path: Path) -> None:
    (tmp_path / ".prettierrc").touch()
    file_path = tmp_path / "app.ts"
    file_path.touch()
    with mock.patch.object(sf, "_run", return_value=True) as run_mock:
        sf.format_prettier(str(file_path))
    argv = run_mock.call_args[0][0]
    assert "prettier" in argv
    assert "--write" in argv
    assert str(file_path) in argv


@pytest.mark.parametrize(
    "marker",
    [
        ".prettierrc",
        ".prettierrc.json",
        ".prettierrc.js",
        "prettier.config.js",
        "package.json",
    ],
)
def test_all_prettier_marker_filenames_trigger_discovery(marker: str, tmp_path: Path) -> None:
    (tmp_path / marker).write_text("{}", encoding="utf-8")
    file_path = tmp_path / "f.ts"
    file_path.touch()
    with mock.patch.object(sf, "_run", return_value=True):
        assert sf.format_prettier(str(file_path)) == "prettier"


# --- _run / _capture: error handling ----------------------------------------


def test_run_returns_false_on_oserror() -> None:
    with mock.patch("subprocess.run", side_effect=OSError("no binary")):
        assert sf._run(["nonexistent"]) is False


def test_run_returns_false_on_timeout() -> None:
    with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 15)):
        assert sf._run(["slow-formatter"]) is False


def test_run_returns_false_on_nonzero_exit() -> None:
    proc = mock.MagicMock()
    proc.returncode = 1
    with mock.patch("subprocess.run", return_value=proc):
        assert sf._run(["formatter", "--bad"]) is False


def test_run_returns_true_on_zero_exit() -> None:
    proc = mock.MagicMock()
    proc.returncode = 0
    with mock.patch("subprocess.run", return_value=proc):
        assert sf._run(["formatter", "--ok"]) is True


def test_capture_returns_none_on_oserror() -> None:
    with mock.patch("subprocess.check_output", side_effect=OSError("no binary")):
        assert sf._capture(["nonexistent"]) is None


def test_capture_returns_none_on_called_process_error() -> None:
    with mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "cmd")):
        assert sf._capture(["cmd", "--bad"]) is None


def test_capture_returns_none_on_timeout() -> None:
    with mock.patch("subprocess.check_output", side_effect=subprocess.TimeoutExpired("cmd", 15)):
        assert sf._capture(["cmd"]) is None


def test_capture_strips_trailing_whitespace() -> None:
    with mock.patch("subprocess.check_output", return_value="/home/user/go\n"):
        assert sf._capture(["go", "env", "GOPATH"]) == "/home/user/go"


# --- main: integration ------------------------------------------------------


def _make_patched_formatters(
    calls: dict[str, list[str]], return_values: dict[str, str | None]
) -> dict[str, Callable[[str], str | None]]:
    """Build a FORMATTERS dict that records calls and returns configured values."""

    def _make(key: str) -> Callable[[str], str | None]:
        def fmt(path: str) -> str | None:
            calls[key].append(path)
            return return_values.get(key)

        return fmt

    return {
        ".go": _make(".go"),
        ".py": _make(".py"),
        ".ts": _make(".ts"),
        ".tsx": _make(".tsx"),
        ".js": _make(".js"),
        ".jsx": _make(".jsx"),
    }


def test_mixed_extensions_call_correct_formatters(tmp_path: Path) -> None:
    go_file = tmp_path / "main.go"
    py_file = tmp_path / "util.py"
    ts_file = tmp_path / "app.ts"
    md_file = tmp_path / "README.md"
    for p in (go_file, py_file, ts_file, md_file):
        p.touch()

    calls: dict[str, list[str]] = {
        ".go": [],
        ".py": [],
        ".ts": [],
        ".tsx": [],
        ".js": [],
        ".jsx": [],
    }
    ret: dict[str, str | None] = {".go": "goimports", ".py": "ruff", ".ts": "prettier"}
    patched = _make_patched_formatters(calls, ret)

    with (
        mock.patch.object(
            sf,
            "_git_modified_files",
            return_value=[str(go_file), str(py_file), str(ts_file), str(md_file)],
        ),
        mock.patch.object(sf, "FORMATTERS", patched),
        mock.patch.object(sys, "stdin", io.StringIO('{"type":"stop"}')),
    ):
        result = sf.main()

    assert result == 0
    assert calls[".go"] == [str(go_file)]
    assert calls[".py"] == [str(py_file)]
    assert calls[".ts"] == [str(ts_file)]


def test_stderr_log_format(tmp_path: Path) -> None:
    tmp = tmp_path / "foo.py"
    tmp.touch()
    stderr_capture = io.StringIO()
    calls: dict[str, list[str]] = {
        ".go": [],
        ".py": [],
        ".ts": [],
        ".tsx": [],
        ".js": [],
        ".jsx": [],
    }
    patched = _make_patched_formatters(calls, {".py": "ruff"})
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "FORMATTERS", patched),
        mock.patch.object(sys, "stdin", io.StringIO("")),
        mock.patch.object(sys, "stderr", stderr_capture),
    ):
        sf.main()
    assert f"[stop-format] ruff → {tmp.name}" in stderr_capture.getvalue()


def test_no_log_when_formatter_returns_none(tmp_path: Path) -> None:
    tmp = tmp_path / "foo.py"
    tmp.touch()
    stderr_capture = io.StringIO()
    calls: dict[str, list[str]] = {
        ".go": [],
        ".py": [],
        ".ts": [],
        ".tsx": [],
        ".js": [],
        ".jsx": [],
    }
    patched = _make_patched_formatters(calls, {".py": None})
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[str(tmp)]),
        mock.patch.object(sf, "FORMATTERS", patched),
        mock.patch.object(sys, "stdin", io.StringIO("")),
        mock.patch.object(sys, "stderr", stderr_capture),
    ):
        sf.main()
    assert stderr_capture.getvalue() == ""


def test_main_always_returns_zero_in_integration() -> None:
    with (
        mock.patch.object(sf, "_git_modified_files", return_value=[]),
        mock.patch.object(sys, "stdin", io.StringIO("")),
    ):
        assert sf.main() == 0
