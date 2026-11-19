"""Cmd+Q handler for kitty.

Triggered by `map cmd+q kitten quit_confirm.py` in kitty.conf. Scans the
focused OS window for tabs running anything other than an idle shell. If
none are busy, closes the OS window immediately. If any are busy, shows a
confirmation prompt listing tab name + foreground process; left unanswered,
it closes the window once its countdown runs out, so an unattended quit
still completes.

Scope is intentionally limited to the CURRENT OS window — quitting one
window does not affect other kitty OS windows. Before the window closes, it is
snapshotted to the session file kitty restores on its next launch.
"""

from __future__ import annotations

import importlib
import json
import logging
import math
import subprocess
import time
from typing import TYPE_CHECKING, Final, Protocol

from kittens.tui.handler import Handler, result_handler
from kittens.tui.loop import Loop

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from types import ModuleType

IDLE_SHELLS = frozenset({"fish", "bash", "zsh", "sh", "dash", "ksh"})
KITTY_LS_TIMEOUT_SECONDS: Final = 2
CONFIRM_TIMEOUT_SECONDS: Final = 300
_LOGGER: Final = logging.getLogger(__name__)


def _load_kitty_session() -> ModuleType | None:
    try:
        return importlib.import_module("kitty_session")
    except Exception:
        _LOGGER.exception("kitty_session failed to load; Cmd+Q closes without a snapshot")
        return None


# kitty puts this file's directory on sys.path only while it executes the module
# body, so the sibling module must be loaded here, not inside a function.
_KITTY_SESSION: Final = _load_kitty_session()


# Duck-typed slices of the kitty API surface — kitty does not ship type stubs
# we depend on, so we describe the minimum we use as Protocols.
class _KeyEvent(Protocol):
    def matches(self, name: str) -> bool: ...


class _TimerHandle(Protocol):
    def cancel(self) -> None: ...


class _Window(Protocol):
    os_window_id: int


class _Boss(Protocol):
    window_id_map: dict[int, _Window]

    def close_os_window(self, os_window_id: int) -> None: ...


def _mappings(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _foreground_command(window: Mapping[str, object]) -> tuple[str, str] | None:
    """Return (short_name, display_cmd) of the first non-idle foreground
    process inside a kitty window, or None if everything is idle."""
    for proc in _mappings(window.get("foreground_processes")):
        raw_cmdline = proc.get("cmdline")
        if not isinstance(raw_cmdline, list) or not raw_cmdline:
            continue
        cmdline = [str(arg) for arg in raw_cmdline]
        short = cmdline[0].rsplit("/", 1)[-1]
        if short in IDLE_SHELLS:
            continue
        display = " ".join(cmdline) if len(cmdline) > 1 else short
        return short, display
    return None


def _busy_tabs_in_focused_window() -> list[tuple[str, str]]:
    """Return a list of (tab_label, foreground_command_display) for tabs in
    the focused OS window where the foreground command is not just an idle
    shell."""
    try:
        result = subprocess.run(
            ["kitty", "@", "ls"],
            capture_output=True,
            text=True,
            timeout=KITTY_LS_TIMEOUT_SECONDS,
            check=True,
        )
        data: object = json.loads(result.stdout)
    except (subprocess.SubprocessError, ValueError, OSError):
        return []

    os_windows = _mappings(data)
    focused = next((ow for ow in os_windows if ow.get("is_focused") is True), None)
    if focused is None and os_windows:
        focused = os_windows[0]
    if focused is None:
        return []

    busy: list[tuple[str, str]] = []
    for tab in _mappings(focused.get("tabs")):
        tab_label = str(tab.get("title") or f"tab {tab.get('id')}")
        for window in _mappings(tab.get("windows")):
            found = _foreground_command(window)
            if found is not None:
                busy.append((tab_label, found[1]))
                break  # one busy entry per tab is enough
    return busy


class QuitDialog(Handler):
    """Minimal yes/no overlay that lists busy sessions."""

    def __init__(
        self,
        busy: list[tuple[str, str]],
        timeout_seconds: float = CONFIRM_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self.busy = busy
        self.answer = "cancel"
        # Name-mangled so they cannot collide with kitty's own Handler attributes.
        self.__timeout_seconds = timeout_seconds
        self.__clock = clock
        self.__deadline = 0.0
        self.__tick_handle: _TimerHandle | None = None
        self.__answered = False

    def initialize(self) -> None:
        self.cmd.set_window_title("Confirm close")
        self.__deadline = self.__clock() + self.__timeout_seconds
        self.__tick()

    def __tick(self) -> None:
        # A tick already dequeued by the event loop survives cancel(), so check first.
        if self.__answered:
            return
        remaining = self.__deadline - self.__clock()
        if remaining <= 0:
            self.__finish("close")
            return
        shown_seconds = math.ceil(remaining)
        self._draw(shown_seconds)
        # Wake up exactly when the displayed whole second changes.
        delay = remaining - (shown_seconds - 1)
        self.__tick_handle = self.asyncio_loop.call_later(delay, self.__tick)

    def __finish(self, answer: str) -> None:
        if self.__answered:
            return
        self.__answered = True
        if self.__tick_handle is not None:
            self.__tick_handle.cancel()
            self.__tick_handle = None
        self.answer = answer
        self.quit_loop(0)

    def _draw(self, seconds_left: int) -> None:
        minutes, seconds = divmod(seconds_left, 60)
        self.cmd.clear_screen()
        self.print("Active sessions in this window:\r\n\r\n")
        for label, cmd in self.busy:
            self.print(f"  {label}: {cmd}\r\n")
        self.print(f"\r\nClosing automatically in {minutes}:{seconds:02d}\r\n")
        self.print("Close this window anyway? [y/N]: ")

    # Signature is dictated by the kitty Handler API — positional `text` and a
    # positional `in_bracketed_paste` bool are part of the contract, so FBT001
    # and FBT002 do not apply.
    def on_text(self, text: str, in_bracketed_paste: bool = False) -> None:  # noqa: FBT001, FBT002
        _ = in_bracketed_paste  # part of kitty Handler API contract
        self.__finish("close" if text in ("y", "Y") else "cancel")

    def on_key(self, key_event: _KeyEvent) -> None:
        if key_event.matches("esc") or key_event.matches("ctrl+c"):
            self.__finish("cancel")


def main(args: list[str]) -> str:
    _ = args  # part of kitten main() API contract
    busy = _busy_tabs_in_focused_window()
    if busy:
        loop = Loop()
        dialog = QuitDialog(busy)
        loop.loop(dialog)
        if dialog.answer != "close":
            return dialog.answer
    _save_snapshot()
    return "close"


# Saved from main, not handle_result: that runs inside kitty's event loop, which
# would have to answer the snapshot's own `kitty @ ls`.
def _save_snapshot() -> None:
    if _KITTY_SESSION is None:
        return
    try:
        _KITTY_SESSION.save_snapshot()
    except Exception:
        _LOGGER.exception("kitty session snapshot failed; closing without it")


# Signature is fixed by kitty's @result_handler decorator contract.
@result_handler(no_ui=False)
def handle_result(
    args: list[str],
    answer: str,
    target_window_id: int,
    boss: _Boss,
) -> None:
    _ = args  # part of @result_handler API contract
    if answer != "close":
        return
    window = boss.window_id_map.get(target_window_id)
    if window is None:
        return
    boss.close_os_window(window.os_window_id)
