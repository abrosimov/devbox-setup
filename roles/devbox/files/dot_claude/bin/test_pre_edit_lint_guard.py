from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_edit_lint_guard

if TYPE_CHECKING:
    import pytest


def test_file_extension_returns_lower() -> None:
    assert pre_edit_lint_guard.file_extension("x.PY") == "py"
    assert pre_edit_lint_guard.file_extension("/tmp/foo.ts") == "ts"
    assert pre_edit_lint_guard.file_extension("no-ext") == ""
    assert pre_edit_lint_guard.file_extension("") == ""


def test_patterns_for_ext_handles_tsx_alias() -> None:
    tsx_patterns = pre_edit_lint_guard.patterns_for_ext("tsx")
    ts_patterns = pre_edit_lint_guard.patterns_for_ext("ts")
    assert tsx_patterns == ts_patterns


def test_detect_suppression_finds_noqa() -> None:
    findings = pre_edit_lint_guard.detect_suppression("x = 1  # noqa", "", is_edit=False)
    assert any(f.directive == "# noqa" for f in findings)


def test_detect_suppression_skips_when_already_present() -> None:
    findings = pre_edit_lint_guard.detect_suppression(
        "x = 1  # noqa: F401",
        "x = 0  # noqa: F401",
        is_edit=True,
    )
    assert findings == []


def test_detect_suppression_catches_eslint_disable() -> None:
    findings = pre_edit_lint_guard.detect_suppression("// eslint-disable", "", is_edit=False)
    assert any(f.directive == "eslint-disable" for f in findings)


def test_detect_suppression_catches_pyrefly_ignore() -> None:
    # Verbatim output of `pyrefly suppress`: the space before the bracket is what
    # the tool writes, so the pattern must not require `ignore[`.
    findings = pre_edit_lint_guard.detect_suppression(
        "    return None  # pyrefly: ignore [bad-return]",
        "",
        is_edit=False,
    )
    assert any(f.directive == "# pyrefly: ignore" for f in findings)


def test_detect_suppression_catches_pyrefly_unspaced_and_blanket_forms() -> None:
    # The hand-written unspaced variant and the file-level blanket are the two
    # other shapes the same directive takes.
    unspaced = pre_edit_lint_guard.detect_suppression(
        "x = 1  # pyrefly:ignore[bad-assignment]",
        "",
        is_edit=False,
    )
    blanket = pre_edit_lint_guard.detect_suppression(
        "# pyrefly: ignore-errors\n",
        "",
        is_edit=False,
    )
    assert any(f.directive == "# pyrefly: ignore" for f in unspaced)
    assert any(f.directive == "# pyrefly: ignore" for f in blanket)


def test_is_self_referential_covers_only_the_guard_and_its_test() -> None:
    assert pre_edit_lint_guard.is_self_referential("/repo/bin/pre_edit_lint_guard.py")
    assert pre_edit_lint_guard.is_self_referential("/repo/bin/test_pre_edit_lint_guard.py")
    assert not pre_edit_lint_guard.is_self_referential("/repo/bin/bash_decision_gate.py")
    assert not pre_edit_lint_guard.is_self_referential("/repo/bin/pre_bash_toolchain_guard.py")
    assert not pre_edit_lint_guard.is_self_referential("")


def test_detect_lazy_types_python_any() -> None:
    findings = pre_edit_lint_guard.detect_lazy_types("def f() -> Any: ...", "", "py", is_edit=False)
    assert findings


def test_detect_lazy_types_typescript_any() -> None:
    findings = pre_edit_lint_guard.detect_lazy_types("const x: any = 1", "", "ts", is_edit=False)
    assert findings


def test_detect_lazy_types_go_empty_interface() -> None:
    findings = pre_edit_lint_guard.detect_lazy_types("var x interface{}", "", "go", is_edit=False)
    assert findings


def test_detect_lazy_types_skips_when_in_old_text() -> None:
    findings = pre_edit_lint_guard.detect_lazy_types(
        "def f() -> Any: pass",
        "def f() -> Any: ...",
        "py",
        is_edit=True,
    )
    assert findings == []


def test_main_allows_unknown_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "# noqa"},
                }
            )
        ),
    )
    assert pre_edit_lint_guard.main() == 0


def test_main_blocks_suppression(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": "/tmp/x.py", "content": "import os  # noqa: F401"},
                }
            )
        ),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_edit_lint_guard.main() == 2
    assert "Lint suppression" in err.getvalue()


def test_main_allows_suppression_literal_in_the_guards_own_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A pattern entry necessarily contains the directive it blocks, so without
    # the exemption the list could never gain another entry.
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "/repo/bin/pre_edit_lint_guard.py",
                        "content": '_sup(r"# pyrefly:\\s*ignore", "Python", "# pyrefly: ignore"),',
                    },
                }
            )
        ),
    )
    assert pre_edit_lint_guard.main() == 0


def test_main_allows_suppression_literal_in_the_guards_own_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "/repo/bin/test_pre_edit_lint_guard.py",
                        "content": 'assert detect("x  # pyrefly: ignore [bad-return]")',
                    },
                }
            )
        ),
    )
    assert pre_edit_lint_guard.main() == 0


def test_main_still_blocks_suppression_in_a_sibling_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The exemption is keyed on the two file names, not on the directory they
    # live in: the guards alongside this one stay covered.
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "/repo/bin/bash_decision_gate.py",
                        "content": "x = 1  # pyrefly: ignore [bad-assignment]",
                    },
                }
            )
        ),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_edit_lint_guard.main() == 2
    assert "Lint suppression" in err.getvalue()


def test_main_blocks_lazy_typing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": "/tmp/x.py", "content": "def f() -> Any: pass"},
                }
            )
        ),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_edit_lint_guard.main() == 2
    assert "Lazy typing" in err.getvalue()


def test_self_referential_exemption_does_not_cover_lazy_typing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Only the suppression check is exempted. Nothing about maintaining the
    # pattern list requires the guard's own source to carry lazy annotations.
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "/repo/bin/pre_edit_lint_guard.py",
                        "content": "def f() -> Any: pass",
                    },
                }
            )
        ),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_edit_lint_guard.main() == 2
    assert "Lazy typing" in err.getvalue()


def test_main_allows_clean_edit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Edit",
                    "tool_input": {
                        "file_path": "/tmp/x.py",
                        "old_string": "x = 1",
                        "new_string": "x: int = 1",
                    },
                }
            )
        ),
    )
    assert pre_edit_lint_guard.main() == 0


_safe_alphabet = st.characters(
    blacklist_categories=("Cs",),
    blacklist_characters=("\x00",),
)


@given(
    prefix=st.text(alphabet=_safe_alphabet, max_size=50),
    suffix=st.text(alphabet=_safe_alphabet, max_size=50),
    directive=st.sampled_from(
        [
            "# noqa",
            "# NOQA",
            "# noqa: F401",
            "# type: ignore",
            "# type:ignore",
            "# pyrefly: ignore [bad-return]",
            "# pyrefly:ignore[bad-return]",
            "# pyrefly: ignore-errors",
            "//nolint",
            "// nolint:errcheck",
            "@ts-ignore",
            "@ts-expect-error",
            "eslint-disable",
            "eslint-disable-next-line",
            "@SuppressWarnings",
            '@SuppressWarnings("all")',
        ]
    ),
)
def test_suppression_always_detected(prefix: str, directive: str, suffix: str) -> None:
    prefix = prefix.replace("\x00", "")
    suffix = suffix.replace("\x00", "")
    content = f"{prefix}{directive}{suffix}"
    findings = pre_edit_lint_guard.detect_suppression(content, "", is_edit=False)
    assert findings, f"missed: {directive!r} in {content!r}"


@given(content=st.text(alphabet=_safe_alphabet, max_size=200))
def test_detector_never_crashes_on_arbitrary_input(content: str) -> None:
    suppression = pre_edit_lint_guard.detect_suppression(content, "", is_edit=False)
    lazy = pre_edit_lint_guard.detect_lazy_types(content, "", "py", is_edit=False)
    assert isinstance(suppression, list)
    assert isinstance(lazy, list)
