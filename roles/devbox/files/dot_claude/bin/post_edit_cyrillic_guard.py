#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unicodedata
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks

ALLOWLIST_FRAGMENTS: Final[tuple[str, ...]] = (
    "/testdata/",
    "/fixtures/",
    "/__fixtures__/",
    "/memory/",
)


def is_allowlisted(file_path: str) -> bool:
    if not file_path:
        return False
    return any(fragment in file_path for fragment in ALLOWLIST_FRAGMENTS)


def count_cyrillic(text: str) -> int:
    if not text:
        return 0
    total = 0
    for ch in text:
        try:
            name = unicodedata.name(ch)
        except ValueError:
            continue
        if "CYRILLIC" in name:
            total += 1
    return total


def collect_text() -> str:
    parts: list[str] = []
    for var in ("CC_TOOL_INPUT_NEW_STRING", "CC_TOOL_INPUT_CONTENT", "CC_TOOL_INPUT_NEW_SOURCE"):
        value = os.environ.get(var, "")
        if value:
            parts.append(value)
    return "".join(parts)


def maybe_read_file(file_path: str) -> str:
    if not file_path:
        return ""
    target = Path(file_path)
    if not target.is_file():
        return ""
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def main() -> int:
    env.setup()
    file_path = os.environ.get("CC_TOOL_INPUT_FILE_PATH", "")
    if is_allowlisted(file_path):
        return hooks.ALLOW

    text = collect_text()
    if not text and file_path:
        text = maybe_read_file(file_path)
    if not text:
        return hooks.ALLOW

    count = count_cyrillic(text)
    if count > 0:
        sys.stderr.write(
            f"WARNING: Cyrillic characters detected ({count}) in {file_path}. "
            "Project policy: written artifacts must be British English. Replace "
            "Cyrillic content with British English before committing. See "
            "CLAUDE.md > Language Policy.\n",
        )
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
