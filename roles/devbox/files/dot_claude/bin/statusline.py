#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import ansi, env, hooks

# Kanagawa Paper Ink palette — kept in sync with the fish/Tide prompt.
C_GOLD: Final[str] = ansi.fg_rgb(196, 178, 138)
C_TEAL: Final[str] = ansi.fg_rgb(142, 164, 158)
C_BLUE: Final[str] = ansi.fg_rgb(105, 138, 155)
C_GREEN: Final[str] = ansi.fg_rgb(105, 148, 105)
C_YELLOW: Final[str] = ansi.fg_rgb(212, 193, 150)
C_RED: Final[str] = ansi.fg_rgb(196, 116, 110)
C_MUTED: Final[str] = ansi.fg_rgb(158, 155, 147)

SEP: Final[str] = f"{C_MUTED}│{ansi.RESET}"

BAR_WIDTH: Final[int] = 10
CTX_OK_THRESHOLD: Final[int] = 50
CTX_WARN_THRESHOLD: Final[int] = 20
FPF_CRITICAL_THRESHOLD: Final[int] = 200


@dataclass(frozen=True)
class StatuslineInput:
    cwd: str
    model: str
    remaining: int | None


def _str_field(payload: Mapping[str, object], *path: str, default: str = "?") -> str:
    current: object = payload
    for key in path:
        if not isinstance(current, Mapping):
            return default
        nxt = current.get(key)
        if nxt is None:
            return default
        current = nxt
    if isinstance(current, str):
        return current
    return default


def _int_field(payload: Mapping[str, object], *path: str) -> int | None:
    current: object = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        nxt = current.get(key)
        if nxt is None:
            return None
        current = nxt
    return _coerce_int(current)


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def parse_input(payload: Mapping[str, object]) -> StatuslineInput:
    cwd = _str_field(payload, "cwd")
    if cwd == "?":
        cwd = _str_field(payload, "workspace", "current_dir")
    model = _str_field(payload, "model", "display_name")
    remaining = _int_field(payload, "context_window", "remaining_percentage")
    return StatuslineInput(cwd=cwd, model=model, remaining=remaining)


def shorten_path(cwd: str, home: str) -> str:
    if not home:
        return cwd
    if cwd == home:
        return "~"
    prefix = home if home.endswith("/") else home + "/"
    if cwd.startswith(prefix):
        return "~/" + cwd[len(prefix) :]
    return cwd


def context_color(remaining: int) -> str:
    if remaining >= CTX_OK_THRESHOLD:
        return C_GREEN
    if remaining >= CTX_WARN_THRESHOLD:
        return C_YELLOW
    return C_RED


def context_bar(remaining: int) -> str:
    bounded = max(0, min(100, remaining))
    filled = bounded // BAR_WIDTH
    empty = BAR_WIDTH - filled
    return ("▪" * filled) + ("·" * empty)


def context_segment(remaining: int | None) -> str:
    if remaining is None:
        return f"{C_MUTED}ctx —"
    colour = context_color(remaining)
    bar = context_bar(remaining)
    return f"{C_BLUE}ctx {colour}{remaining}%{C_MUTED} {bar}"


def git_branch(cwd: str) -> str | None:
    if not cwd or not Path(cwd).is_dir():
        return None
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", cwd, "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if completed.returncode != 0:
        return None
    branch = (completed.stdout or "").strip()
    return branch or None


def git_segment(branch: str | None) -> str:
    if branch is None:
        return ""
    return f"{C_MUTED} {SEP} {C_GOLD} {branch}"


def fpf_state_path() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME") or ""
    if xdg:
        base = Path(xdg)
    else:
        home = os.environ.get("HOME") or str(Path.home())
        base = Path(home) / ".cache"
    return base / "devbox-setup" / "fpf-drift"


def fpf_drift_value(state_path: Path) -> int | None:
    if not state_path.is_file():
        return None
    try:
        raw = state_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _fpf_doc_path(cwd: str) -> Path | None:
    if not cwd:
        return None
    candidate = Path(cwd) / "roles" / "devbox" / "files" / "dot_claude" / "docs" / "FPF-Spec.md"
    if candidate.is_file():
        return candidate
    return None


def trigger_fpf_refresh(local_spec: Path) -> None:
    home = os.environ.get("HOME") or str(Path.home())
    script = Path(home) / ".claude" / "bin" / "fpf_drift_check.py"
    if not script.is_file():
        return
    try:
        subprocess.Popen(
            [str(script), "--local", str(local_spec)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except (OSError, FileNotFoundError):
        return


def fpf_segment(drift: int | None) -> str:
    if drift is None or drift <= 0:
        return ""
    colour = C_RED if drift > FPF_CRITICAL_THRESHOLD else C_YELLOW
    return f"{C_MUTED} {SEP} {colour}FPF Δ{drift}"


def render(parsed: StatuslineInput, home: str, fpf_drift: int | None) -> str:
    short_cwd = shorten_path(parsed.cwd, home)
    pieces: list[str] = [
        f"{C_TEAL}{short_cwd}{ansi.RESET}",
        f" {SEP} ",
        f"{context_segment(parsed.remaining)}{ansi.RESET}",
    ]
    branch = git_branch(parsed.cwd)
    git_part = git_segment(branch)
    if git_part:
        pieces.append(f"{git_part}{ansi.RESET}")
    fpf_part = fpf_segment(fpf_drift)
    if fpf_part:
        pieces.append(f"{fpf_part}{ansi.RESET}")
    pieces.append(f" {SEP} ")
    pieces.append(f"{C_MUTED}{parsed.model}{ansi.RESET}")
    return "".join(pieces)


def run() -> int:
    payload = hooks.read_hook_input()
    parsed = parse_input(payload)
    home = os.environ.get("HOME") or ""

    local_spec = _fpf_doc_path(parsed.cwd)
    if local_spec is not None:
        trigger_fpf_refresh(local_spec)

    fpf_drift = fpf_drift_value(fpf_state_path())

    line = render(parsed, home, fpf_drift)
    sys.stdout.write(line + "\n")
    return 0


def main() -> int:
    env.setup()
    return run()


if __name__ == "__main__":
    sys.exit(main())
