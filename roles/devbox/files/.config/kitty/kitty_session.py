"""Snapshot the focused kitty OS window as a kitty session file.

Runs under kitty's bundled interpreter (`kitty +launch kitty_session.py`) and is
imported by the `quit_confirm.py` kitten, so it must stay stdlib-only.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping, Sequence

SESSION_FILE: Final = Path.home() / ".config" / "kitty" / "last-session.conf"
CLAUDE_SESSIONS_DIR: Final = Path.home() / ".claude" / "sessions"
KITTY_LS_TIMEOUT_SECONDS: Final = 2
DEFAULT_TAB_TITLE: Final = "shell"
RESTORED_SHELL: Final = "fish"

# The session id is spliced into a fish command line, so only plain id characters pass.
_SESSION_ID: Final = re.compile(r"[A-Za-z0-9_-]+")
_LAYOUT_NAME: Final = re.compile(r"[a-z_]+")


class SnapshotError(Exception):
    pass


@dataclass(frozen=True)
class ClaudeSession:
    session_id: str
    cwd: str


@dataclass(frozen=True)
class RenderedSession:
    text: str
    tab_count: int


type ClaudeSessionLookup = Callable[[int], ClaudeSession | None]


def read_os_windows() -> list[object]:
    try:
        result = subprocess.run(
            ["kitty", "@", "ls"],
            capture_output=True,
            text=True,
            timeout=KITTY_LS_TIMEOUT_SECONDS,
            check=True,
        )
        data: object = json.loads(result.stdout)
    except (subprocess.SubprocessError, OSError, ValueError) as err:
        msg = "'kitty @ ls' failed — is allow_remote_control = yes in kitty.conf?"
        raise SnapshotError(msg) from err
    if not isinstance(data, list):
        msg = "'kitty @ ls' did not return a list of OS windows"
        raise SnapshotError(msg)
    return data


def focused_os_window(os_windows: Sequence[object]) -> Mapping[str, object] | None:
    candidates = [window for window in os_windows if isinstance(window, dict)]
    for window in candidates:
        if window.get("is_focused") is True:
            return window
    return candidates[0] if candidates else None


def read_claude_session(pid: int, sessions_dir: Path = CLAUDE_SESSIONS_DIR) -> ClaudeSession | None:
    try:
        record: object = json.loads((sessions_dir / f"{pid}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or record.get("pid") != pid:
        return None
    if record.get("kind") != "interactive":
        return None
    session_id = record.get("sessionId")
    cwd = record.get("cwd")
    if not isinstance(session_id, str) or _SESSION_ID.fullmatch(session_id) is None:
        return None
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return None
    return ClaudeSession(session_id=session_id, cwd=cwd)


def render_session(
    os_windows: Sequence[object],
    claude_session_of: ClaudeSessionLookup,
    home: str,
) -> RenderedSession:
    os_window = focused_os_window(os_windows)
    if os_window is None:
        msg = "'kitty @ ls' reported no OS windows"
        raise SnapshotError(msg)
    lines: list[str] = []
    tab_count = 0
    for tab in mappings(os_window.get("tabs")):
        launches = [
            _launch_line(window, claude_session_of, home) for window in _restorable_windows(tab)
        ]
        if not launches:
            continue
        tab_count += 1
        lines.append(f"new_tab {_tab_title(tab)}")
        layout = tab.get("layout")
        if isinstance(layout, str) and _LAYOUT_NAME.fullmatch(layout):
            lines.append(f"layout {layout}")
        lines.extend(launches)
        lines.append("")
    if tab_count == 0:
        msg = "the focused OS window has no tabs to save"
        raise SnapshotError(msg)
    return RenderedSession(text="\n".join(lines), tab_count=tab_count)


def write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def save_snapshot(path: Path = SESSION_FILE) -> int:
    rendered = render_session(read_os_windows(), read_claude_session, str(Path.home()))
    try:
        write_atomically(path, rendered.text)
    except OSError as err:
        msg = f"cannot write {path}: {err}"
        raise SnapshotError(msg) from err
    return rendered.tab_count


def mappings(value: object) -> Iterator[Mapping[str, object]]:
    if isinstance(value, list):
        yield from (item for item in value if isinstance(item, dict))


def _restorable_windows(tab: Mapping[str, object]) -> list[Mapping[str, object]]:
    windows = list(mappings(tab.get("windows")))
    by_id = {
        window_id: window for window in windows if isinstance(window_id := window.get("id"), int)
    }
    # Overlays (such as the quit_confirm kitten) stack on top of the first window of
    # their group, so restoring each group's first window drops them.
    group_heads = [
        by_id[head]
        for group in mappings(tab.get("groups"))
        if "dock" not in group
        and isinstance(group_windows := group.get("windows"), list)
        and group_windows
        and isinstance(head := group_windows[0], int)
        and head in by_id
    ]
    return group_heads or windows


def _tab_title(tab: Mapping[str, object]) -> str:
    title = tab.get("title")
    if not isinstance(title, str):
        return DEFAULT_TAB_TITLE
    flattened = " ".join(title.split())
    return flattened or DEFAULT_TAB_TITLE


def _launch_line(
    window: Mapping[str, object],
    claude_session_of: ClaudeSessionLookup,
    home: str,
) -> str:
    processes = list(mappings(window.get("foreground_processes")))
    for process in processes:
        pid = process.get("pid")
        if not isinstance(pid, int):
            continue
        claude = claude_session_of(pid)
        if claude is not None and _is_single_line(claude.cwd):
            return shlex.join(
                [
                    "launch",
                    "--cwd",
                    claude.cwd,
                    RESTORED_SHELL,
                    "-C",
                    f"claude --resume {claude.session_id}",
                ]
            )
    return shlex.join(["launch", "--cwd", _window_cwd(window, processes, home), RESTORED_SHELL])


def _window_cwd(
    window: Mapping[str, object],
    processes: Sequence[Mapping[str, object]],
    home: str,
) -> str:
    for candidate in [*(process.get("cwd") for process in processes), window.get("cwd")]:
        if isinstance(candidate, str) and _is_single_line(candidate):
            return candidate
    return home


# kitty reads a session file with str.splitlines(), so any line break it splits on
# would turn the rest of the value into a new directive.
def _is_single_line(value: str) -> bool:
    return value.splitlines() == [value]


def main() -> int:
    try:
        tab_count = save_snapshot()
    except SnapshotError as err:
        print(f"kitty-save-session: {err}", file=sys.stderr)
        return 1
    print(f"Saved {tab_count} tab(s) to {SESSION_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
