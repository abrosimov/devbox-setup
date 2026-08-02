from __future__ import annotations

import json
from pathlib import Path

from . import paths


def load_json(path: Path) -> dict[str, object]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"expected object at top level of {path}, got {type(data).__name__}"
        raise TypeError(msg)
    return data


def dump_json(path: Path, data: dict[str, object], *, indent: int = 2) -> None:
    rendered = json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=False)
    paths.atomic_write(Path(path), rendered + "\n")


def safe_load_json(text: str, *, default: dict[str, object] | None = None) -> dict[str, object]:
    fallback: dict[str, object] = {} if default is None else dict(default)
    if not text.strip():
        return fallback
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return fallback
    if not isinstance(parsed, dict):
        return fallback
    return parsed
