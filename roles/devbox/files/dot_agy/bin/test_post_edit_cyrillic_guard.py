from __future__ import annotations

import io
import sys
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import post_edit_cyrillic_guard as guard

if TYPE_CHECKING:
    import pytest


def test_count_cyrillic_zero_for_latin() -> None:
    assert guard.count_cyrillic("Hello, world!") == 0


def test_count_cyrillic_counts_only_cyrillic() -> None:
    assert guard.count_cyrillic("Привет") == 6
    assert guard.count_cyrillic("Привет world") == 6


def test_count_cyrillic_handles_empty() -> None:
    assert guard.count_cyrillic("") == 0


def test_count_cyrillic_handles_mixed_unicode() -> None:
    assert guard.count_cyrillic("中文 plus Кир plus emoji") == 3


def test_count_cyrillic_handles_unnamed_codepoints() -> None:
    text = "Hello\x00\x01\x02"
    assert guard.count_cyrillic(text) == 0


def test_is_allowlisted_testdata() -> None:
    assert guard.is_allowlisted("/x/y/testdata/sample.txt")


def test_is_allowlisted_fixtures() -> None:
    assert guard.is_allowlisted("/x/fixtures/data.json")
    assert guard.is_allowlisted("/x/__fixtures__/data.json")


def test_is_allowlisted_memory() -> None:
    assert guard.is_allowlisted("/x/memory/note.md")


def test_is_allowlisted_false_for_source() -> None:
    assert not guard.is_allowlisted("/src/main.py")


def test_is_allowlisted_empty() -> None:
    assert not guard.is_allowlisted("")


def test_collect_text_combines_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_TOOL_INPUT_NEW_STRING", "abc")
    monkeypatch.setenv("CC_TOOL_INPUT_CONTENT", "def")
    monkeypatch.setenv("CC_TOOL_INPUT_NEW_SOURCE", "ghi")
    assert guard.collect_text() == "abcdefghi"


def test_collect_text_handles_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CC_TOOL_INPUT_NEW_STRING", raising=False)
    monkeypatch.delenv("CC_TOOL_INPUT_CONTENT", raising=False)
    monkeypatch.delenv("CC_TOOL_INPUT_NEW_SOURCE", raising=False)
    assert guard.collect_text() == ""


def test_maybe_read_file_reads_existing(tmp_path: Path) -> None:
    target = tmp_path / "doc.md"
    target.write_text("Привет", encoding="utf-8")
    assert guard.maybe_read_file(str(target)) == "Привет"


def test_maybe_read_file_returns_empty_for_missing(tmp_path: Path) -> None:
    assert guard.maybe_read_file(str(tmp_path / "missing")) == ""


def test_maybe_read_file_returns_empty_for_directory(tmp_path: Path) -> None:
    assert guard.maybe_read_file(str(tmp_path)) == ""


def test_main_allow_when_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_TOOL_INPUT_FILE_PATH", "/x/testdata/file.md")
    monkeypatch.setenv("CC_TOOL_INPUT_CONTENT", "Привет")
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert guard.main() == 0
    assert err.getvalue() == ""


def test_main_no_warning_when_no_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_TOOL_INPUT_FILE_PATH", "/x/src.py")
    monkeypatch.delenv("CC_TOOL_INPUT_NEW_STRING", raising=False)
    monkeypatch.delenv("CC_TOOL_INPUT_CONTENT", raising=False)
    monkeypatch.delenv("CC_TOOL_INPUT_NEW_SOURCE", raising=False)
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert guard.main() == 0
    assert err.getvalue() == ""


def test_main_warns_when_cyrillic_in_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_TOOL_INPUT_FILE_PATH", "/src/main.py")
    monkeypatch.setenv("CC_TOOL_INPUT_NEW_STRING", "комментарий")
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert guard.main() == 0
    output = err.getvalue()
    assert "WARNING" in output
    assert "Cyrillic" in output
    assert "/src/main.py" in output


def test_main_reads_file_when_env_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "src.py"
    target.write_text("Hi комм", encoding="utf-8")
    monkeypatch.setenv("CC_TOOL_INPUT_FILE_PATH", str(target))
    monkeypatch.delenv("CC_TOOL_INPUT_NEW_STRING", raising=False)
    monkeypatch.delenv("CC_TOOL_INPUT_CONTENT", raising=False)
    monkeypatch.delenv("CC_TOOL_INPUT_NEW_SOURCE", raising=False)
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert guard.main() == 0
    assert "WARNING" in err.getvalue()


def test_main_no_warning_when_purely_latin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_TOOL_INPUT_FILE_PATH", "/src/main.py")
    monkeypatch.setenv("CC_TOOL_INPUT_NEW_STRING", "def hello():\n    return 1")
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert guard.main() == 0
    assert err.getvalue() == ""


# --- Hypothesis fuzz: detector never crashes on arbitrary unicode -------------

_unicode_chars = st.characters(blacklist_categories=("Cs",))


@given(st.text(alphabet=_unicode_chars, max_size=200))
def test_count_cyrillic_never_crashes(text: str) -> None:
    result = guard.count_cyrillic(text)
    assert result >= 0
    assert isinstance(result, int)


_cyrillic_chars = st.sampled_from(
    [chr(c) for c in range(0x0410, 0x044F + 1) if "CYRILLIC" in (unicodedata.name(chr(c), ""))]
)


@given(st.lists(_cyrillic_chars, min_size=1, max_size=50))
def test_count_cyrillic_matches_input_length_for_pure_cyrillic(chars: list[str]) -> None:
    text = "".join(chars)
    assert guard.count_cyrillic(text) == len(text)


@given(st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu"), max_codepoint=0x007A)))
def test_count_cyrillic_zero_for_pure_latin(text: str) -> None:
    assert guard.count_cyrillic(text) == 0
