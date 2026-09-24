"""Detect live sessions that are still writing into an archived directory."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class Process:
    pid: int
    args: str

    def names(self) -> set[str]:
        """Executable names this process can be recognised by.

        argv[0] covers native binaries (``claude``, ``codex``); argv[1] covers
        interpreter-launched CLIs (``node /opt/homebrew/bin/gemini``).
        """
        tokens = self.args.split()
        return {PurePosixPath(t).name for t in tokens[:2]}


ProcessLister = Callable[[], Iterable[Process]]


def list_processes() -> list[Process]:
    # `ps -axo pid=,args=` has the same meaning on macOS and procps.
    out = subprocess.run(
        ["ps", "-axo", "pid=,args="], capture_output=True, text=True, check=True
    ).stdout
    processes: list[Process] = []
    for line in out.splitlines():
        pid, _, args = line.strip().partition(" ")
        if pid.isdigit():
            processes.append(Process(int(pid), args.strip()))
    return processes


def find_busy(
    names: Iterable[str], lister: ProcessLister = list_processes, own_pid: int | None = None
) -> list[Process]:
    wanted = set(names)
    if not wanted:
        return []
    me = os.getpid() if own_pid is None else own_pid
    return [p for p in lister() if p.pid != me and p.names() & wanted]
