#!/usr/bin/env python3
"""Tests for pre-write-existing-guard.

Run from any directory:
    python3 bin/pre_write_existing_guard_test.py
or via unittest discovery:
    python3 -m unittest bin.pre_write_existing_guard_test
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

import pre_write_existing_guard as guard


class TestExtractFilePath(unittest.TestCase):
    """_extract_file_path() parses the PreToolUse event JSON."""

    def _extract(self, raw: str):
        return guard._extract_file_path(raw)

    def test_returns_path_from_valid_event(self):
        raw = '{"tool_input": {"file_path": "/tmp/foo.py"}}'
        self.assertEqual(self._extract(raw), "/tmp/foo.py")

    def test_returns_none_on_empty_string(self):
        self.assertIsNone(self._extract(""))

    def test_returns_none_on_whitespace_only(self):
        self.assertIsNone(self._extract("   \n  "))

    def test_returns_none_on_invalid_json(self):
        self.assertIsNone(self._extract("{not json"))

    def test_returns_none_when_event_is_not_dict(self):
        self.assertIsNone(self._extract('["list", "not", "dict"]'))

    def test_returns_none_when_tool_input_missing(self):
        self.assertIsNone(self._extract('{"other_key": "value"}'))

    def test_returns_none_when_tool_input_is_not_dict(self):
        self.assertIsNone(self._extract('{"tool_input": "a string"}'))

    def test_returns_none_when_tool_input_is_null(self):
        self.assertIsNone(self._extract('{"tool_input": null}'))

    def test_returns_none_when_file_path_missing(self):
        self.assertIsNone(self._extract('{"tool_input": {"other": "x"}}'))

    def test_returns_none_when_file_path_is_not_string(self):
        self.assertIsNone(self._extract('{"tool_input": {"file_path": 42}}'))

    def test_returns_none_when_file_path_is_null(self):
        self.assertIsNone(self._extract('{"tool_input": {"file_path": null}}'))

    def test_returns_none_when_file_path_is_empty_string(self):
        self.assertIsNone(self._extract('{"tool_input": {"file_path": ""}}'))

    def test_returns_none_when_file_path_is_false(self):
        self.assertIsNone(self._extract('{"tool_input": {"file_path": false}}'))

    def test_accepts_path_with_spaces(self):
        raw = '{"tool_input": {"file_path": "/home/user/my file.py"}}'
        self.assertEqual(self._extract(raw), "/home/user/my file.py")

    def test_extra_keys_are_ignored(self):
        raw = '{"tool_name": "Write", "tool_input": {"file_path": "/x.py", "content": "..."}}'
        self.assertEqual(self._extract(raw), "/x.py")


class TestIsBlocking(unittest.TestCase):
    """_is_blocking() returns True only for existing non-empty files."""

    def test_true_for_existing_non_empty_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"content")
            tmp = f.name
        try:
            self.assertTrue(guard._is_blocking(tmp))
        finally:
            os.unlink(tmp)

    def test_false_for_missing_file(self):
        # OSError must be swallowed, not propagated.
        self.assertFalse(guard._is_blocking("/no/such/path/file.py"))

    def test_false_for_empty_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp = f.name
        try:
            self.assertFalse(guard._is_blocking(tmp))
        finally:
            os.unlink(tmp)

    def test_true_for_single_byte_file(self):
        # Boundary: size == 1 must block.
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x")
            tmp = f.name
        try:
            self.assertTrue(guard._is_blocking(tmp))
        finally:
            os.unlink(tmp)

    def test_true_for_file_with_only_newline(self):
        # Newline-only files have size > 0 — must block.
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\n")
            tmp = f.name
        try:
            self.assertTrue(guard._is_blocking(tmp))
        finally:
            os.unlink(tmp)


class TestIsBlockingErrorHandling(unittest.TestCase):
    """_is_blocking() fails open (returns False) for all OSError variants."""

    def test_false_when_getsize_raises_oserror(self):
        with mock.patch("os.path.getsize", side_effect=OSError("permission denied")):
            self.assertFalse(guard._is_blocking("/some/path.py"))

    def test_false_when_getsize_raises_permission_error(self):
        # PermissionError is a subclass of OSError.
        with mock.patch("os.path.getsize", side_effect=PermissionError("denied")):
            self.assertFalse(guard._is_blocking("/root/secret.py"))

    def test_false_when_getsize_raises_file_not_found(self):
        # FileNotFoundError is a subclass of OSError — explicit mock for clarity.
        with mock.patch("os.path.getsize", side_effect=FileNotFoundError("missing")):
            self.assertFalse(guard._is_blocking("/missing.py"))

    def test_main_exit_0_when_getsize_raises_oserror(self):
        # Fail-open: any getsize error must not block the write.
        raw = '{"tool_input": {"file_path": "/some/file.py"}}'
        with mock.patch("os.path.getsize", side_effect=OSError("disk error")):
            with mock.patch.object(sys, "stdin", io.StringIO(raw)):
                with mock.patch.object(sys, "stderr", io.StringIO()):
                    result = guard.main()
        self.assertEqual(result, 0)


class TestMain(unittest.TestCase):
    """End-to-end via stdin mock and exit-code capture."""

    def _run(self, stdin_text: str) -> tuple[int, str]:
        stderr_cap = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)):
            with mock.patch.object(sys, "stderr", stderr_cap):
                exit_code = guard.main()
        return exit_code, stderr_cap.getvalue()

    def test_exit_0_when_no_file_path(self):
        code, err = self._run('{"tool_input": {}}')
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_exit_0_when_file_path_missing_on_disk(self):
        raw = '{"tool_input": {"file_path": "/no/such/file.py"}}'
        code, err = self._run(raw)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_exit_0_when_file_exists_but_is_empty(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp = f.name
        try:
            raw = f'{{"tool_input": {{"file_path": "{tmp}"}}}}'
            code, err = self._run(raw)
            self.assertEqual(code, 0)
            self.assertEqual(err, "")
        finally:
            os.unlink(tmp)

    def test_exit_2_when_file_exists_non_empty(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"existing content")
            tmp = f.name
        try:
            raw = f'{{"tool_input": {{"file_path": "{tmp}"}}}}'
            code, _ = self._run(raw)
            self.assertEqual(code, 2)
        finally:
            os.unlink(tmp)

    def test_stderr_contains_blocked_prefix_on_exit_2(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            raw = f'{{"tool_input": {{"file_path": "{tmp}"}}}}'
            _, err = self._run(raw)
            self.assertTrue(err.startswith("BLOCKED [pre-write-existing-guard]:"))
        finally:
            os.unlink(tmp)

    def test_stderr_contains_file_path_on_exit_2(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            raw = f'{{"tool_input": {{"file_path": "{tmp}"}}}}'
            _, err = self._run(raw)
            self.assertIn(tmp, err)
        finally:
            os.unlink(tmp)

    def test_stderr_suggests_edit_alternative_on_exit_2(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            raw = f'{{"tool_input": {{"file_path": "{tmp}"}}}}'
            _, err = self._run(raw)
            self.assertIn("Edit", err)
            self.assertIn("MultiEdit", err)
        finally:
            os.unlink(tmp)

    def test_exit_0_on_empty_stdin(self):
        code, err = self._run("")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_exit_0_on_invalid_json(self):
        code, err = self._run("{bad json")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
