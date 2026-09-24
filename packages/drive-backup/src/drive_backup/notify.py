"""Best-effort desktop notification; a scheduled job has no terminal to fail into."""

from __future__ import annotations

import shutil
import subprocess
import sys


def notify(title: str, message: str) -> None:
    if sys.platform != "darwin" or not (osascript := shutil.which("osascript")):
        return

    # AppleScript string literals escape backslash and double quote only.
    def quote(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    script = f"display notification {quote(message[:200])} with title {quote(title)}"
    subprocess.run([osascript, "-e", script], check=False, capture_output=True)
