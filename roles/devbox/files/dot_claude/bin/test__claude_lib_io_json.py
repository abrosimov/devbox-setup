from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import io_json


def test_load_json_reads_object(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    target.write_text('{"a": 1, "b": "two"}', encoding="utf-8")
    assert io_json.load_json(target) == {"a": 1, "b": "two"}


def test_load_json_rejects_non_object(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    target.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(TypeError):
        io_json.load_json(target)


def test_dump_json_writes_pretty(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    io_json.dump_json(target, {"a": 1, "b": [1, 2]})
    text = target.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert '"a": 1' in text


def test_dump_json_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    original: dict[str, object] = {"a": 1, "nested": {"k": [1, 2, 3]}, "flag": True}
    io_json.dump_json(target, original)
    assert io_json.load_json(target) == original


def test_safe_load_json_default_on_empty() -> None:
    assert io_json.safe_load_json("") == {}


def test_safe_load_json_default_on_invalid() -> None:
    assert io_json.safe_load_json("not json") == {}


def test_safe_load_json_default_on_non_object() -> None:
    assert io_json.safe_load_json("[1, 2]") == {}


def test_safe_load_json_uses_supplied_default() -> None:
    sentinel: dict[str, object] = {"fallback": True}
    assert io_json.safe_load_json("bad", default=sentinel) == sentinel


def test_safe_load_json_returns_parsed_object() -> None:
    assert io_json.safe_load_json('{"k": 1}') == {"k": 1}


@given(
    st.dictionaries(
        st.text(min_size=1, max_size=20).filter(lambda s: "\x00" not in s),
        st.one_of(
            st.integers(min_value=-(10**9), max_value=10**9),
            st.text(max_size=50).filter(lambda s: "\x00" not in s),
            st.booleans(),
            st.none(),
        ),
        max_size=10,
    ),
)
def test_safe_load_json_roundtrip_property(data: dict[str, object]) -> None:
    encoded = json.dumps(data)
    assert io_json.safe_load_json(encoded) == data
