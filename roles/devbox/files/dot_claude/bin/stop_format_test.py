#!/usr/bin/env python3
"""Tests for stop-format.

Run from any directory:
    python3 bin/stop_format_test.py
or via unittest discovery:
    python3 -m unittest bin.stop_format_test
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stop_format as sf


class TestStdinHandling(unittest.TestCase):
    """main() stdin parsing behaviour."""

    def _run_main(self, stdin_text: str) -> int:
        with mock.patch.object(sf, "_git_modified_files", return_value=[]):
            with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)):
                return sf.main()

    def test_valid_json_proceeds(self):
        with mock.patch.object(sf, "_git_modified_files", return_value=[]) as m:
            with mock.patch.object(sys, "stdin", io.StringIO('{"type":"stop"}')):
                result = sf.main()
        self.assertEqual(result, 0)
        m.assert_called_once()

    def test_empty_stdin_proceeds(self):
        with mock.patch.object(sf, "_git_modified_files", return_value=[]) as m:
            with mock.patch.object(sys, "stdin", io.StringIO("")):
                result = sf.main()
        self.assertEqual(result, 0)
        m.assert_called_once()

    def test_whitespace_only_stdin_proceeds(self):
        with mock.patch.object(sf, "_git_modified_files", return_value=[]) as m:
            with mock.patch.object(sys, "stdin", io.StringIO("   \n  ")):
                result = sf.main()
        self.assertEqual(result, 0)
        m.assert_called_once()

    def test_invalid_json_warns_and_continues(self):
        stderr_cap = io.StringIO()
        with mock.patch.object(sf, "_git_modified_files", return_value=[]) as m:
            with mock.patch.object(sys, "stdin", io.StringIO("{not json")):
                with mock.patch.object(sys, "stderr", stderr_cap):
                    result = sf.main()
        self.assertEqual(result, 0)
        m.assert_called_once()
        self.assertIn(
            "[stop-format] warning: invalid stdin JSON, formatting anyway",
            stderr_cap.getvalue(),
        )

    def test_always_returns_zero(self):
        result = self._run_main('{"ok": true}')
        self.assertEqual(result, 0)


class TestGitDiscovery(unittest.TestCase):
    """_git_modified_files() path resolution and filtering."""

    def test_returns_empty_on_git_failure(self):
        import subprocess

        with mock.patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(128, "git")
        ):
            self.assertEqual(sf._git_modified_files(), [])

    def test_returns_empty_on_oserror(self):
        with mock.patch("subprocess.check_output", side_effect=OSError("no git")):
            self.assertEqual(sf._git_modified_files(), [])

    def test_returns_empty_on_timeout(self):
        import subprocess

        with mock.patch(
            "subprocess.check_output", side_effect=subprocess.TimeoutExpired("git", 15)
        ):
            self.assertEqual(sf._git_modified_files(), [])

    def test_returns_empty_when_diff_is_empty(self):
        with mock.patch("subprocess.check_output", return_value=""):
            self.assertEqual(sf._git_modified_files(), [])

    def test_resolves_relative_paths_to_absolute(self):
        with tempfile.NamedTemporaryFile(suffix=".go", delete=False) as f:
            tmp = f.name
        try:
            parent = os.path.dirname(tmp)
            basename = os.path.basename(tmp)
            # Give git a relative path and mock cwd to parent so os.path.join resolves correctly.
            with mock.patch("subprocess.check_output", return_value=basename + "\n"):
                with mock.patch.object(sf.os, "getcwd", return_value=parent):
                    result = sf._git_modified_files()
            self.assertEqual(result, [tmp])
        finally:
            os.unlink(tmp)

    def test_filters_out_files_that_do_not_exist(self):
        with mock.patch("subprocess.check_output", return_value="ghost/file.go\n"):
            with mock.patch("os.getcwd", return_value="/some/repo"):
                result = sf._git_modified_files()
        self.assertEqual(result, [])

    def test_skips_blank_lines(self):
        with mock.patch("subprocess.check_output", return_value="\n\n\n"):
            result = sf._git_modified_files()
        self.assertEqual(result, [])


class TestFormatDispatch(unittest.TestCase):
    """main() routes file extensions to the correct formatter.

    FORMATTERS is a module-level dict holding direct function references.
    Patching the module attribute alone doesn't update the dict, so we
    patch sf.FORMATTERS directly to intercept dispatch.
    """

    def _run_with_extension(self, ext: str) -> tuple[dict[str, list[str]], str]:
        called: dict[str, list] = {"go": [], "py": [], "pr": []}

        def fake_go(p):
            called["go"].append(p)

        def fake_py(p):
            called["py"].append(p)

        def fake_pr(p):
            called["pr"].append(p)

        patched = {
            ".go": fake_go,
            ".py": fake_py,
            ".ts": fake_pr,
            ".tsx": fake_pr,
            ".js": fake_pr,
            ".jsx": fake_pr,
        }

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            tmp = f.name
        try:
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "FORMATTERS", patched):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        sf.main()
            return called, tmp
        finally:
            os.unlink(tmp)

    def test_go_routes_to_format_go(self):
        called, tmp = self._run_with_extension(".go")
        self.assertEqual(called["go"], [tmp])
        self.assertEqual(called["py"], [])
        self.assertEqual(called["pr"], [])

    def test_py_routes_to_format_python(self):
        called, tmp = self._run_with_extension(".py")
        self.assertEqual(called["py"], [tmp])
        self.assertEqual(called["go"], [])
        self.assertEqual(called["pr"], [])

    def test_ts_routes_to_format_prettier(self):
        called, tmp = self._run_with_extension(".ts")
        self.assertEqual(called["pr"], [tmp])
        self.assertEqual(called["go"], [])
        self.assertEqual(called["py"], [])

    def test_tsx_routes_to_format_prettier(self):
        called, tmp = self._run_with_extension(".tsx")
        self.assertEqual(called["pr"], [tmp])

    def test_js_routes_to_format_prettier(self):
        called, tmp = self._run_with_extension(".js")
        self.assertEqual(called["pr"], [tmp])

    def test_jsx_routes_to_format_prettier(self):
        called, tmp = self._run_with_extension(".jsx")
        self.assertEqual(called["pr"], [tmp])

    def test_unknown_extension_no_formatter_invoked(self):
        called, _ = self._run_with_extension(".rb")
        self.assertEqual(called["go"], [])
        self.assertEqual(called["py"], [])
        self.assertEqual(called["pr"], [])

    def test_no_extension_no_formatter_invoked(self):
        # Files without extension (e.g. Makefile) are silently skipped.
        with tempfile.NamedTemporaryFile(suffix="", delete=False, prefix="Makefile") as f:
            tmp = f.name
        try:
            called: list = []

            def spy(p):
                called.append(p)

            patched = {".go": spy, ".py": spy, ".ts": spy, ".tsx": spy, ".js": spy, ".jsx": spy}
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "FORMATTERS", patched):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        sf.main()
            self.assertEqual(called, [])
        finally:
            os.unlink(tmp)

    def test_extension_matching_is_case_insensitive(self):
        # main() lowercases the extension before lookup — .GO must route to format_go.
        with tempfile.NamedTemporaryFile(suffix=".GO", delete=False) as f:
            tmp = f.name
        try:
            called: list = []

            def spy(p):
                called.append(p)

            patched = {".go": spy, ".py": spy, ".ts": spy, ".tsx": spy, ".js": spy, ".jsx": spy}
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "FORMATTERS", patched):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        sf.main()
            self.assertEqual(called, [tmp])
        finally:
            os.unlink(tmp)


class TestFormatGo(unittest.TestCase):
    """format_go() finds go.mod, reads module name, builds goimports argv."""

    def test_returns_none_when_no_gomod(self):
        with tempfile.TemporaryDirectory() as d:
            file_path = os.path.join(d, "main.go")
            Path(file_path).touch()
            result = sf.format_go(file_path)
        self.assertIsNone(result)

    def test_returns_none_when_gomod_has_no_module_line(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, "go.mod")).write_text("go 1.21\n", encoding="utf-8")
            file_path = os.path.join(d, "main.go")
            Path(file_path).touch()
            result = sf.format_go(file_path)
        self.assertIsNone(result)

    def test_returns_goimports_on_success(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, "go.mod")).write_text(
                "module example.com/foo\n\ngo 1.21\n", encoding="utf-8"
            )
            file_path = os.path.join(d, "main.go")
            Path(file_path).touch()
            with mock.patch.object(sf, "_capture", return_value="/home/user/go"):
                with mock.patch.object(sf, "_run", return_value=True) as run_mock:
                    result = sf.format_go(file_path)
        self.assertEqual(result, "goimports")
        run_mock.assert_called_once()
        argv = run_mock.call_args[0][0]
        self.assertTrue(argv[0].endswith("goimports"))
        self.assertIn("-local", argv)
        self.assertIn("example.com/foo", argv)
        self.assertIn("-w", argv)
        self.assertIn(file_path, argv)

    def test_uses_gopath_when_available(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, "go.mod")).write_text("module example.com/bar\n", encoding="utf-8")
            file_path = os.path.join(d, "bar.go")
            Path(file_path).touch()
            with mock.patch.object(sf, "_capture", return_value="/opt/go"):
                with mock.patch.object(sf, "_run", return_value=True) as run_mock:
                    sf.format_go(file_path)
        argv = run_mock.call_args[0][0]
        self.assertEqual(argv[0], "/opt/go/bin/goimports")

    def test_falls_back_to_bare_goimports_when_gopath_empty(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, "go.mod")).write_text("module example.com/baz\n", encoding="utf-8")
            file_path = os.path.join(d, "baz.go")
            Path(file_path).touch()
            with mock.patch.object(sf, "_capture", return_value=None):
                with mock.patch.object(sf, "_run", return_value=True) as run_mock:
                    sf.format_go(file_path)
        argv = run_mock.call_args[0][0]
        self.assertEqual(argv[0], "goimports")

    def test_falls_back_when_gopath_is_empty_string(self):
        # _capture strips output; an empty GOPATH would return "" which is falsy.
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, "go.mod")).write_text("module example.com/baz\n", encoding="utf-8")
            file_path = os.path.join(d, "baz.go")
            Path(file_path).touch()
            with mock.patch.object(sf, "_capture", return_value=""):
                with mock.patch.object(sf, "_run", return_value=True) as run_mock:
                    sf.format_go(file_path)
        argv = run_mock.call_args[0][0]
        self.assertEqual(argv[0], "goimports")

    def test_returns_none_when_goimports_fails(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, "go.mod")).write_text("module example.com/x\n", encoding="utf-8")
            file_path = os.path.join(d, "x.go")
            Path(file_path).touch()
            with mock.patch.object(sf, "_capture", return_value=None):
                with mock.patch.object(sf, "_run", return_value=False):
                    result = sf.format_go(file_path)
        self.assertIsNone(result)

    def test_finds_gomod_in_ancestor(self):
        # go.mod may be several levels above the file.
        with tempfile.TemporaryDirectory() as root:
            nested = os.path.join(root, "pkg", "sub")
            os.makedirs(nested)
            Path(os.path.join(root, "go.mod")).write_text(
                "module example.com/nested\n", encoding="utf-8"
            )
            file_path = os.path.join(nested, "util.go")
            Path(file_path).touch()
            with mock.patch.object(sf, "_capture", return_value=None):
                with mock.patch.object(sf, "_run", return_value=True) as run_mock:
                    result = sf.format_go(file_path)
        self.assertEqual(result, "goimports")
        argv = run_mock.call_args[0][0]
        self.assertIn("example.com/nested", argv)


class TestFormatPython(unittest.TestCase):
    """format_python() runs ruff check and ruff format independently."""

    def test_returns_ruff_when_both_succeed(self):
        with mock.patch.object(sf, "_run", return_value=True):
            result = sf.format_python("/any/file.py")
        self.assertEqual(result, "ruff")

    def test_returns_check_only_when_check_succeeds_format_fails(self):
        with mock.patch.object(sf, "_run", side_effect=[True, False]):
            result = sf.format_python("/any/file.py")
        self.assertEqual(result, "ruff (check only)")

    def test_returns_format_only_when_check_fails_format_succeeds(self):
        with mock.patch.object(sf, "_run", side_effect=[False, True]):
            result = sf.format_python("/any/file.py")
        self.assertEqual(result, "ruff (format only)")

    def test_returns_none_when_both_fail(self):
        with mock.patch.object(sf, "_run", return_value=False):
            result = sf.format_python("/any/file.py")
        self.assertIsNone(result)

    def test_calls_ruff_check_first_then_format(self):
        calls = []

        def capture_call(argv, **_):
            calls.append(argv[:3])
            return True

        with mock.patch.object(sf, "_run", side_effect=capture_call):
            sf.format_python("/any/file.py")
        self.assertEqual(calls[0], ["ruff", "check", "--fix"])
        self.assertEqual(calls[1], ["ruff", "format", "--quiet"])

    def test_always_runs_both_stages_independently(self):
        # Both ruff calls must be made regardless of first result.
        with mock.patch.object(sf, "_run", return_value=False) as run_mock:
            sf.format_python("/any/file.py")
        self.assertEqual(run_mock.call_count, 2)

    def test_log_line_emitted_once_per_file_via_main(self):
        # One [stop-format] line per file, not one per ruff stage.
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            tmp = f.name
        try:
            stderr_capture = io.StringIO()
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "_run", return_value=True):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        with mock.patch.object(sys, "stderr", stderr_capture):
                            sf.main()
            lines = [l for l in stderr_capture.getvalue().splitlines() if "[stop-format]" in l]
            self.assertEqual(len(lines), 1)
        finally:
            os.unlink(tmp)

    def test_log_line_emitted_once_when_check_only_succeeds(self):
        # check=True, format=False → tool="ruff (check only)" → exactly one log line.
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            tmp = f.name
        try:
            stderr_capture = io.StringIO()
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "_run", side_effect=[True, False]):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        with mock.patch.object(sys, "stderr", stderr_capture):
                            sf.main()
            lines = [l for l in stderr_capture.getvalue().splitlines() if "[stop-format]" in l]
            self.assertEqual(len(lines), 1)
        finally:
            os.unlink(tmp)

    def test_log_line_emitted_once_when_format_only_succeeds(self):
        # check=False, format=True → tool="ruff (format only)" → exactly one log line.
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            tmp = f.name
        try:
            stderr_capture = io.StringIO()
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "_run", side_effect=[False, True]):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        with mock.patch.object(sys, "stderr", stderr_capture):
                            sf.main()
            lines = [l for l in stderr_capture.getvalue().splitlines() if "[stop-format]" in l]
            self.assertEqual(len(lines), 1)
        finally:
            os.unlink(tmp)

    def test_no_log_when_both_stages_fail(self):
        # Neither ruff stage succeeds → format_python returns None → no log line.
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            tmp = f.name
        try:
            stderr_capture = io.StringIO()
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "_run", return_value=False):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        with mock.patch.object(sys, "stderr", stderr_capture):
                            sf.main()
            lines = [l for l in stderr_capture.getvalue().splitlines() if "[stop-format]" in l]
            self.assertEqual(len(lines), 0)
        finally:
            os.unlink(tmp)


class TestFormatPrettier(unittest.TestCase):
    """format_prettier() walks ancestors for a config marker, runs npx prettier."""

    def test_returns_none_when_no_prettier_marker_found(self):
        with tempfile.TemporaryDirectory() as d:
            file_path = os.path.join(d, "app.ts")
            Path(file_path).touch()
            result = sf.format_prettier(file_path)
        self.assertIsNone(result)

    def test_returns_prettier_when_prettierrc_found(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, ".prettierrc")).touch()
            file_path = os.path.join(d, "app.ts")
            Path(file_path).touch()
            with mock.patch.object(sf, "_run", return_value=True):
                result = sf.format_prettier(file_path)
        self.assertEqual(result, "prettier")

    def test_returns_prettier_when_package_json_found(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, "package.json")).write_text("{}", encoding="utf-8")
            file_path = os.path.join(d, "index.js")
            Path(file_path).touch()
            with mock.patch.object(sf, "_run", return_value=True):
                result = sf.format_prettier(file_path)
        self.assertEqual(result, "prettier")

    def test_finds_marker_in_ancestor(self):
        with tempfile.TemporaryDirectory() as root:
            nested = os.path.join(root, "src", "components")
            os.makedirs(nested)
            Path(os.path.join(root, ".prettierrc")).touch()
            file_path = os.path.join(nested, "Button.tsx")
            Path(file_path).touch()
            with mock.patch.object(sf, "_run", return_value=True) as run_mock:
                result = sf.format_prettier(file_path)
        self.assertEqual(result, "prettier")
        _, kwargs = run_mock.call_args
        self.assertEqual(kwargs.get("cwd"), root)

    def test_returns_none_when_npx_prettier_fails(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, ".prettierrc")).touch()
            file_path = os.path.join(d, "app.tsx")
            Path(file_path).touch()
            with mock.patch.object(sf, "_run", return_value=False):
                result = sf.format_prettier(file_path)
        self.assertIsNone(result)

    def test_passes_file_path_to_prettier(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, ".prettierrc")).touch()
            file_path = os.path.join(d, "app.ts")
            Path(file_path).touch()
            with mock.patch.object(sf, "_run", return_value=True) as run_mock:
                sf.format_prettier(file_path)
        argv = run_mock.call_args[0][0]
        self.assertIn("prettier", argv)
        self.assertIn("--write", argv)
        self.assertIn(file_path, argv)

    def test_all_prettier_marker_filenames_trigger_discovery(self):
        markers = [
            ".prettierrc",
            ".prettierrc.json",
            ".prettierrc.js",
            "prettier.config.js",
            "package.json",
        ]
        for marker in markers:
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as d:
                Path(os.path.join(d, marker)).write_text("{}", encoding="utf-8")
                file_path = os.path.join(d, "f.ts")
                Path(file_path).touch()
                with mock.patch.object(sf, "_run", return_value=True):
                    result = sf.format_prettier(file_path)
                self.assertEqual(result, "prettier")


class TestErrorHandling(unittest.TestCase):
    """_run() and _capture() swallow every subprocess exception and return safe defaults."""

    def test_run_returns_false_on_oserror(self):
        with mock.patch("subprocess.run", side_effect=OSError("no binary")):
            self.assertFalse(sf._run(["nonexistent"]))

    def test_run_returns_false_on_timeout(self):
        import subprocess

        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 15)):
            self.assertFalse(sf._run(["slow-formatter"]))

    def test_run_returns_false_on_nonzero_exit(self):
        proc = mock.MagicMock()
        proc.returncode = 1
        with mock.patch("subprocess.run", return_value=proc):
            self.assertFalse(sf._run(["formatter", "--bad"]))

    def test_run_returns_true_on_zero_exit(self):
        proc = mock.MagicMock()
        proc.returncode = 0
        with mock.patch("subprocess.run", return_value=proc):
            self.assertTrue(sf._run(["formatter", "--ok"]))

    def test_capture_returns_none_on_oserror(self):
        with mock.patch("subprocess.check_output", side_effect=OSError("no binary")):
            self.assertIsNone(sf._capture(["nonexistent"]))

    def test_capture_returns_none_on_called_process_error(self):
        import subprocess

        with mock.patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "cmd")
        ):
            self.assertIsNone(sf._capture(["cmd", "--bad"]))

    def test_capture_returns_none_on_timeout(self):
        import subprocess

        with mock.patch(
            "subprocess.check_output", side_effect=subprocess.TimeoutExpired("cmd", 15)
        ):
            self.assertIsNone(sf._capture(["cmd"]))

    def test_capture_strips_trailing_whitespace(self):
        with mock.patch("subprocess.check_output", return_value="/home/user/go\n"):
            result = sf._capture(["go", "env", "GOPATH"])
        self.assertEqual(result, "/home/user/go")


class TestMainIntegration(unittest.TestCase):
    """End-to-end: correct formatters called, log format verified.

    FORMATTERS holds direct function references so we patch sf.FORMATTERS
    to intercept dispatch rather than the individual format_* attributes.
    """

    def _make_patched_formatters(self, calls: dict, return_values: dict):
        """Build a FORMATTERS dict that records calls and returns configured values."""

        def _make(key):
            def fmt(path):
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

    def test_mixed_extensions_call_correct_formatters(self):
        with tempfile.TemporaryDirectory() as d:
            go_file = os.path.join(d, "main.go")
            py_file = os.path.join(d, "util.py")
            ts_file = os.path.join(d, "app.ts")
            md_file = os.path.join(d, "README.md")
            for p in [go_file, py_file, ts_file, md_file]:
                Path(p).touch()

            calls: dict = {".go": [], ".py": [], ".ts": [], ".tsx": [], ".js": [], ".jsx": []}
            ret = {".go": "goimports", ".py": "ruff", ".ts": "prettier"}
            patched = self._make_patched_formatters(calls, ret)

            with (
                mock.patch.object(
                    sf, "_git_modified_files", return_value=[go_file, py_file, ts_file, md_file]
                ),
                mock.patch.object(sf, "FORMATTERS", patched),
            ):
                with mock.patch.object(sys, "stdin", io.StringIO('{"type":"stop"}')):
                    result = sf.main()

        self.assertEqual(result, 0)
        self.assertEqual(calls[".go"], [go_file])
        self.assertEqual(calls[".py"], [py_file])
        self.assertEqual(calls[".ts"], [ts_file])

    def test_stderr_log_format(self):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            tmp = f.name
        try:
            stderr_capture = io.StringIO()
            calls: dict = {".go": [], ".py": [], ".ts": [], ".tsx": [], ".js": [], ".jsx": []}
            patched = self._make_patched_formatters(calls, {".py": "ruff"})
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "FORMATTERS", patched):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        with mock.patch.object(sys, "stderr", stderr_capture):
                            sf.main()
            output = stderr_capture.getvalue()
            basename = os.path.basename(tmp)
            self.assertIn(f"[stop-format] ruff → {basename}", output)
        finally:
            os.unlink(tmp)

    def test_no_log_when_formatter_returns_none(self):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            tmp = f.name
        try:
            stderr_capture = io.StringIO()
            calls: dict = {".go": [], ".py": [], ".ts": [], ".tsx": [], ".js": [], ".jsx": []}
            patched = self._make_patched_formatters(calls, {".py": None})
            with mock.patch.object(sf, "_git_modified_files", return_value=[tmp]):
                with mock.patch.object(sf, "FORMATTERS", patched):
                    with mock.patch.object(sys, "stdin", io.StringIO("")):
                        with mock.patch.object(sys, "stderr", stderr_capture):
                            sf.main()
            self.assertEqual(stderr_capture.getvalue(), "")
        finally:
            os.unlink(tmp)

    def test_main_always_returns_zero(self):
        with mock.patch.object(sf, "_git_modified_files", return_value=[]):
            with mock.patch.object(sys, "stdin", io.StringIO("")):
                self.assertEqual(sf.main(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
