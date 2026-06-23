from __future__ import annotations

from typing import Final

RESET: Final[str] = "\x1b[0m"
BOLD: Final[str] = "\x1b[1m"
DIM: Final[str] = "\x1b[2m"
ITALIC: Final[str] = "\x1b[3m"
UNDERLINE: Final[str] = "\x1b[4m"


def _clamp(value: int) -> int:
    if value < 0:
        return 0
    if value > 255:
        return 255
    return value


def fg_rgb(r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{_clamp(r)};{_clamp(g)};{_clamp(b)}m"


def bg_rgb(r: int, g: int, b: int) -> str:
    return f"\x1b[48;2;{_clamp(r)};{_clamp(g)};{_clamp(b)}m"


def style(text: str, *codes: str) -> str:
    if not codes:
        return text
    return "".join(codes) + text + RESET
