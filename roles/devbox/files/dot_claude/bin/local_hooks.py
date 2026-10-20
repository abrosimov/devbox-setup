#!/usr/bin/env python3
# Runs the machine-local hook commands listed in ~/.claude/local-hooks.json for one event.
# Fail-open by contract: always exits 0 and never writes stdout, so a local command can
# neither block the session nor inject a hook decision.
from __future__ import annotations

import contextlib
import json
import math
import os
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

CONFIG_PATH: Final[Path] = Path.home() / ".claude" / "local-hooks.json"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
SHELL: Final[str] = "/bin/sh"
STDERR_TAIL_CHARS: Final[int] = 200


@dataclass(frozen=True)
class LocalCommand:
    command: str
    timeout: float


def _log(message: str) -> None:
    sys.stderr.write(f"[local-hooks] {message}\n")


def _parse_entry(entry: object) -> LocalCommand | None:
    if not isinstance(entry, dict):
        return None
    command = entry.get("command")
    timeout = entry.get("timeout", DEFAULT_TIMEOUT_SECONDS)
    if not isinstance(command, str) or not command.strip():
        return None
    if isinstance(timeout, bool) or not isinstance(timeout, int | float):
        return None
    if not math.isfinite(timeout) or timeout <= 0:
        return None
    return LocalCommand(command=command, timeout=float(timeout))


def _read_config(config_path: Path) -> dict[str, object] | None:
    try:
        raw = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as err:
        _log(f"cannot read {config_path}: {err}")
        return None
    try:
        config: object = json.loads(raw)
    except json.JSONDecodeError as err:
        _log(f"malformed {config_path}: {err}")
        return None
    if not isinstance(config, dict):
        _log(f"{config_path} is not a JSON object")
        return None
    return config


def load_commands(config_path: Path, event: str) -> list[LocalCommand]:
    config = _read_config(config_path)
    if config is None:
        return []
    entries = config.get(event)
    if entries is None:
        return []
    if not isinstance(entries, list):
        _log(f"{event} in {config_path} is not a list")
        return []
    commands: list[LocalCommand] = []
    for index, entry in enumerate(entries):
        parsed = _parse_entry(entry)
        if parsed is None:
            _log(
                f'{event}[{index}] skipped: needs a non-empty "command" '
                'and an optional positive "timeout"',
            )
            continue
        commands.append(parsed)
    return commands


def _kill_group(process: subprocess.Popen[bytes]) -> None:
    # The shell's own children share its session, so the whole group goes, not just sh.
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def run_command(local: LocalCommand, payload: bytes) -> None:
    try:
        _run(local, payload)
    except OSError as err:
        _log(f"cannot run {local.command!r}: {err}")


def _run(local: LocalCommand, payload: bytes) -> None:
    # Files rather than pipes: a lingering grandchild holding a pipe could stall the wait.
    with tempfile.TemporaryFile() as stdin_file, tempfile.TemporaryFile() as stderr_file:
        stdin_file.write(payload)
        stdin_file.seek(0)
        process = subprocess.Popen(
            [SHELL, "-c", local.command],
            stdin=stdin_file,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=local.timeout)
        except subprocess.TimeoutExpired:
            _kill_group(process)
            _log(f"{local.command!r} timed out after {local.timeout:g}s")
            return
        if returncode != 0:
            stderr_file.seek(0)
            tail = stderr_file.read().decode(errors="replace").strip()[-STDERR_TAIL_CHARS:]
            suffix = f": {tail}" if tail else ""
            _log(f"{local.command!r} exited {returncode}{suffix}")


def dispatch(event: str, payload: bytes, config_path: Path) -> None:
    for local in load_commands(config_path, event):
        run_command(local, payload)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or not argv[1]:
        _log("usage: local_hooks.py <EventName>")
        return 0
    try:
        payload = sys.stdin.buffer.read()
    except OSError as err:
        _log(f"cannot read hook input: {err}")
        return 0
    dispatch(argv[1], payload, CONFIG_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
