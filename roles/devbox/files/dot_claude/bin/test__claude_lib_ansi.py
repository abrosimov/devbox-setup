from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import ansi


def test_reset_sequence() -> None:
    assert ansi.RESET == "\x1b[0m"


def test_fg_rgb_format() -> None:
    assert ansi.fg_rgb(255, 128, 0) == "\x1b[38;2;255;128;0m"


def test_bg_rgb_format() -> None:
    assert ansi.bg_rgb(0, 0, 0) == "\x1b[48;2;0;0;0m"


@pytest.mark.parametrize(
    ("inp", "expected"),
    [(-1, 0), (0, 0), (255, 255), (256, 255), (1000, 255)],
)
def test_rgb_components_are_clamped(inp: int, expected: int) -> None:
    code = ansi.fg_rgb(inp, inp, inp)
    match = re.match(r"\x1b\[38;2;(\d+);(\d+);(\d+)m", code)
    assert match is not None
    assert int(match.group(1)) == expected
    assert int(match.group(2)) == expected
    assert int(match.group(3)) == expected


def test_style_wraps_with_codes_and_reset() -> None:
    out = ansi.style("hi", ansi.BOLD, ansi.fg_rgb(255, 0, 0))
    assert out.startswith(ansi.BOLD)
    assert out.endswith(ansi.RESET)
    assert "hi" in out


def test_style_no_codes_returns_text_unchanged() -> None:
    assert ansi.style("hi") == "hi"


def test_truecolor_escape_starts_with_csi() -> None:
    assert ansi.fg_rgb(1, 2, 3).startswith("\x1b[")
    assert ansi.bg_rgb(1, 2, 3).startswith("\x1b[")
