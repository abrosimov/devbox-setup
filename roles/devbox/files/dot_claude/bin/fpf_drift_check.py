#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, paths, proc

UPSTREAM_URL: Final[str] = "https://raw.githubusercontent.com/ailev/FPF/main/FPF-Spec.md"
DEFAULT_TTL_HOURS: Final[int] = 168
LOCAL_RELATIVE_PATH: Final[str] = "roles/devbox/files/dot_claude/docs/FPF-Spec.md"

USAGE: Final[str] = (
    "Usage: fpf_drift_check.py [--force] [--local PATH]\n"
    "Writes drifted line count (or '0') to the state file.\n"
    "Skips network call when state file mtime is fresh, unless --force.\n"
)


@dataclass(frozen=True)
class ParsedArgs:
    force: bool
    local: str | None
    show_usage: bool


@dataclass(frozen=True)
class ParseFailure:
    message: str


def parse_args(argv: list[str]) -> ParsedArgs | ParseFailure:
    force = False
    local: str | None = None
    show_usage = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--force":
            force = True
            i += 1
            continue
        if arg == "--local":
            if i + 1 >= len(argv):
                return ParseFailure("--local requires a path argument.")
            local = argv[i + 1]
            i += 2
            continue
        if arg in ("-h", "--help"):
            show_usage = True
            i += 1
            continue
        return ParseFailure(f"Unknown argument '{arg}'.")
    return ParsedArgs(force=force, local=local, show_usage=show_usage)


def state_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME") or ""
    if xdg:
        base = Path(xdg)
    else:
        home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or str(Path.home())
        base = Path(home) / ".cache"
    return base / "devbox-setup"


def state_file() -> Path:
    return state_dir() / "fpf-drift"


def is_fresh(path: Path, ttl_hours: int) -> bool:
    if not path.is_file():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl_hours * 3600


def find_local_spec(start: Path) -> Path | None:
    current = start.resolve() if start.exists() else start
    if current.is_file():
        current = current.parent
    depth = 0
    while depth <= 20:
        candidate = current / LOCAL_RELATIVE_PATH
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent
        depth += 1
    return None


def download_upstream(target: Path, timeout: int = 10) -> bool:
    result = proc.run_cmd(
        [
            "curl",
            "-sfSL",
            "--max-time",
            str(timeout),
            UPSTREAM_URL,
            "-o",
            str(target),
        ],
        timeout=timeout + 5,
    )
    return result.success


def count_drift(upstream: Path, local: Path) -> int:
    result = proc.run_cmd(
        ["diff", str(upstream), str(local)],
        timeout=15,
    )
    if result.returncode not in (0, 1):
        return 0
    if not result.stdout:
        return 0
    count = 0
    for line in result.stdout.splitlines():
        if line.startswith(("<", ">")):
            count += 1
    return count


def write_state(value: int, target: Path) -> None:
    paths.atomic_write(target, f"{value}\n")


def run(argv: list[str]) -> int:
    parsed = parse_args(argv)
    if isinstance(parsed, ParseFailure):
        sys.stderr.write(f"{parsed.message}\n{USAGE}")
        return 2
    if parsed.show_usage:
        sys.stdout.write(USAGE)
        return 0

    state = state_file()
    state.parent.mkdir(parents=True, exist_ok=True)

    if not parsed.force and is_fresh(state, DEFAULT_TTL_HOURS):
        return 0

    if parsed.local:
        local_spec: Path | None = Path(parsed.local)
    else:
        cwd = Path(os.environ.get("PWD") or Path.cwd())
        local_spec = find_local_spec(cwd)

    if local_spec is None or not local_spec.is_file():
        return 1

    with tempfile.NamedTemporaryFile(delete=False, suffix=".fpf") as fh:
        tmp_path = Path(fh.name)
    try:
        if not download_upstream(tmp_path):
            return 0
        drift = count_drift(tmp_path, local_spec)
        write_state(drift, state)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    env.setup()
    return run(argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
