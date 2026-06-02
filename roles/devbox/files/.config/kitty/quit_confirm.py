"""Cmd+Q handler for kitty.

Triggered by `map cmd+q kitten quit_confirm.py` in kitty.conf. Scans the
focused OS window for tabs running anything other than an idle shell. If
none are busy, closes the OS window immediately. If any are busy, shows a
confirmation prompt listing tab name + foreground process.

Scope is intentionally limited to the CURRENT OS window — quitting one
window does not affect other kitty OS windows.
"""

import json
import subprocess
from typing import List, Optional, Tuple

from kittens.tui.handler import Handler, result_handler
from kittens.tui.loop import Loop


IDLE_SHELLS = frozenset({"fish", "bash", "zsh", "sh", "dash", "ksh"})


def _foreground_command(window: dict) -> Optional[Tuple[str, str]]:
    """Return (short_name, display_cmd) of the first non-idle foreground
    process inside a kitty window, or None if everything is idle."""
    for proc in window.get("foreground_processes", []) or []:
        cmdline = proc.get("cmdline") or []
        if not cmdline:
            continue
        short = cmdline[0].rsplit("/", 1)[-1]
        if short in IDLE_SHELLS:
            continue
        display = " ".join(cmdline) if len(cmdline) > 1 else short
        return short, display
    return None


def _busy_tabs_in_focused_window() -> List[Tuple[str, str]]:
    """Return a list of (tab_label, foreground_command_display) for tabs in
    the focused OS window where the foreground command is not just an idle
    shell."""
    try:
        result = subprocess.run(
            ["kitty", "@", "ls"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        data = json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return []

    focused = next((ow for ow in data if ow.get("is_focused")), None)
    if focused is None and data:
        focused = data[0]
    if focused is None:
        return []

    busy: List[Tuple[str, str]] = []
    for tab in focused.get("tabs", []):
        tab_label = tab.get("title") or f"tab {tab.get('id')}"
        for window in tab.get("windows", []):
            found = _foreground_command(window)
            if found is not None:
                busy.append((tab_label, found[1]))
                break  # one busy entry per tab is enough
    return busy


class QuitDialog(Handler):
    """Minimal yes/no overlay that lists busy sessions."""

    def __init__(self, busy: List[Tuple[str, str]]):
        super().__init__()
        self.busy = busy
        self.answer = "cancel"

    def initialize(self) -> None:
        self.cmd.set_window_title("Confirm close")
        self._draw()

    def _draw(self) -> None:
        self.cmd.clear_screen()
        self.print("Active sessions in this window:\r\n\r\n")
        for label, cmd in self.busy:
            self.print(f"  {label}: {cmd}\r\n")
        self.print("\r\nClose this window anyway? [y/N]: ")

    def on_text(self, text: str, in_bracketed_paste: bool = False) -> None:
        _ = in_bracketed_paste  # part of kitty Handler API contract
        self.answer = "close" if text in ("y", "Y") else "cancel"
        self.quit_loop(0)

    def on_key(self, key_event) -> None:
        if key_event.matches("esc") or key_event.matches("ctrl+c"):
            self.answer = "cancel"
            self.quit_loop(0)


def main(args: List[str]) -> str:
    _ = args  # part of kitten main() API contract
    busy = _busy_tabs_in_focused_window()
    if not busy:
        return "close"
    loop = Loop()
    dialog = QuitDialog(busy)
    loop.loop(dialog)
    return dialog.answer


@result_handler(no_ui=False)
def handle_result(args, answer, target_window_id, boss) -> None:  # type: ignore[no-untyped-def]
    _ = args  # part of @result_handler API contract
    if answer != "close":
        return
    window = boss.window_id_map.get(target_window_id)
    if window is None:
        return
    boss.close_os_window(window.os_window_id)
