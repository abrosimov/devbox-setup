#!/usr/bin/env python3
"""Merge a repo-owned Codex TOML fragment into app-owned config.toml.

The managed fragment owns its top-level scalar keys and complete top-level
tables. All other root keys and tables from the live file are preserved.
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import tempfile
import tomllib
from pathlib import Path

ROOT_BEGIN = "# BEGIN devbox managed Codex root settings"
ROOT_END = "# END devbox managed Codex root settings"
TABLES_BEGIN = "# BEGIN devbox managed Codex tables"
TABLES_END = "# END devbox managed Codex tables"

_MANAGED_MARKER_LABELS = (
    "managed Codex root settings",
    "managed Codex tables",
    "otelcol-edge telemetry",
    "otelbox edge telemetry",
)
_MARKER_BLOCK_RE = re.compile(
    r"^# BEGIN devbox (?P<label>"
    + "|".join(re.escape(label) for label in _MANAGED_MARKER_LABELS)
    + r")\s*$\n.*?^# END devbox (?P=label)\s*$\n?",
    re.MULTILINE | re.DOTALL,
)
_TABLE_HEADER_RE = re.compile(r"^\s*\[\[?(?P<name>[^\[\]\r\n]+)\]\]?\s*(?:#.*)?$", re.MULTILINE)
_ROOT_KEY_RE = re.compile(r"^\s*(?P<name>[A-Za-z0-9_-]+)\s*=")


class ReconcileError(ValueError):
    """Raised when either TOML document cannot be reconciled safely."""


def _parse_toml(text: str, source: str) -> dict[str, object]:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        message = f"invalid TOML in {source}: {exc}"
        raise ReconcileError(message) from exc


def _split_managed_fragment(text: str) -> tuple[str, str, set[str], set[str]]:
    parsed = _parse_toml(text, "managed fragment")
    root_keys = {key for key, value in parsed.items() if not isinstance(value, dict)}
    table_names = {key for key, value in parsed.items() if isinstance(value, dict)}

    first_table = _TABLE_HEADER_RE.search(text)
    if first_table is None or not table_names:
        message = "managed fragment must declare at least one TOML table"
        raise ReconcileError(message)

    root_text = text[: first_table.start()].strip()
    tables_text = text[first_table.start() :].strip()
    if not root_keys:
        message = "managed fragment must declare at least one root scalar"
        raise ReconcileError(message)
    return root_text, tables_text, root_keys, table_names


def _strip_managed_blocks(text: str) -> str:
    return _MARKER_BLOCK_RE.sub("", text)


def _table_is_owned(table_name: str, owned_tables: set[str]) -> bool:
    normalized = table_name.strip()
    return any(normalized == name or normalized.startswith(f"{name}.") for name in owned_tables)


def _split_live_document(text: str, owned_tables: set[str]) -> tuple[str, str]:
    headers = list(_TABLE_HEADER_RE.finditer(text))
    if not headers:
        return text, ""

    root_text = text[: headers[0].start()]
    kept_tables: list[str] = []
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        if not _table_is_owned(header.group("name"), owned_tables):
            kept_tables.append(text[header.start() : end])
    return root_text, "".join(kept_tables)


def _remove_owned_root_keys(text: str, owned_keys: set[str]) -> str:
    kept_lines: list[str] = []
    for line in text.splitlines():
        match = _ROOT_KEY_RE.match(line)
        if match is None or match.group("name") not in owned_keys:
            kept_lines.append(line)
    return "\n".join(kept_lines).strip()


def reconcile(managed_text: str, live_text: str) -> str:
    """Return a valid merged TOML document without touching the filesystem."""
    managed_root, managed_tables, owned_keys, owned_tables = _split_managed_fragment(managed_text)
    _parse_toml(live_text, "live config")

    unmarked_live = _strip_managed_blocks(live_text)
    live_root, live_tables = _split_live_document(unmarked_live, owned_tables)
    live_root = _remove_owned_root_keys(live_root, owned_keys)
    live_tables = live_tables.strip()

    parts = [f"{ROOT_BEGIN}\n{managed_root}\n{ROOT_END}"]
    if live_root:
        parts.append(live_root)
    if live_tables:
        parts.append(live_tables)
    parts.append(f"{TABLES_BEGIN}\n{managed_tables}\n{TABLES_END}")

    result = "\n\n".join(parts).rstrip() + "\n"
    _parse_toml(result, "reconciled config")
    return result


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", text=True
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.chmod(0o600)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _mode_is_private(path: Path) -> bool:
    return path.exists() and stat.S_IMODE(path.stat().st_mode) == 0o600


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--managed", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument(
        "--check", action="store_true", help="report drift without changing the target"
    )
    args = parser.parse_args()

    managed_text = args.managed.read_text(encoding="utf-8")
    live_text = args.target.read_text(encoding="utf-8") if args.target.exists() else ""
    result = reconcile(managed_text, live_text)
    changed = result != live_text or not _mode_is_private(args.target)

    if args.check:
        print("changed" if changed else "unchanged")
        return int(changed)
    if changed:
        _write_atomic(args.target, result)
    print("changed" if changed else "unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
