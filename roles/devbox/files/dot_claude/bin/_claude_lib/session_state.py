from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable

SESSION_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
EDITED_PATHS_FILE: Final[str] = "edited_paths.jsonl"
SEEN_KEYS_FILE: Final[str] = "seen_keys.jsonl"
RETENTION_SECONDS: Final[int] = 30 * 24 * 60 * 60


def state_root() -> Path:
    return Path.home() / ".claude" / "state" / "sessions"


def prune_stale_sessions(root: Path, *, now: float | None = None) -> None:
    cutoff = (time.time() if now is None else now) - RETENTION_SECONDS
    try:
        entries = list(root.iterdir())
    except OSError:
        return
    for entry in entries:
        try:
            stale = entry.is_dir() and not entry.is_symlink() and entry.stat().st_mtime < cutoff
        except OSError:
            continue
        if stale:
            shutil.rmtree(entry, ignore_errors=True)


# Append-only JSON lines: concurrent hooks of one session (parallel tool calls)
# each append a single short line, so no lock is needed.
@dataclass(frozen=True)
class SessionState:
    directory: Path

    @classmethod
    def from_hook_input(
        cls,
        data: dict[str, object],
        root: Path | None = None,
    ) -> SessionState | None:
        session_id = data.get("session_id")
        if not isinstance(session_id, str) or not SESSION_ID_RE.match(session_id):
            return None
        return cls((root or state_root()) / session_id)

    def record_edit(self, path: Path) -> None:
        if not self.directory.exists():
            prune_stale_sessions(self.directory.parent)
        self.__append(EDITED_PATHS_FILE, [str(path.resolve())])

    def edited_paths(self) -> tuple[Path, ...]:
        return tuple(Path(entry) for entry in dict.fromkeys(self.__read(EDITED_PATHS_FILE)))

    def seen_keys(self) -> frozenset[str]:
        return frozenset(self.__read(SEEN_KEYS_FILE))

    def mark_seen(self, keys: Iterable[str]) -> None:
        self.__append(SEEN_KEYS_FILE, list(keys))

    def __read(self, name: str) -> list[str]:
        try:
            text = (self.directory / name).read_text(encoding="utf-8")
        except OSError:
            return []
        entries: list[str] = []
        for line in text.splitlines():
            try:
                value: object = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, str):
                entries.append(value)
        return entries

    def __append(self, name: str, entries: list[str]) -> None:
        if not entries:
            return
        payload = "".join(json.dumps(entry) + "\n" for entry in entries)
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with (self.directory / name).open("a", encoding="utf-8") as handle:
                handle.write(payload)
        except OSError:
            return
