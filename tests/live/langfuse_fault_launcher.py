"""Run the deployed Langfuse hook wrapper with one injected crash or pause.

Runs under the deployed hook venv, stdlib only on this side.
Usage: langfuse_fault_launcher.py <deployed-bin> <fault> <signal-dir>

  kill-mid-export     SIGKILL right after the first batch is staged, before commit
  kill-after-commit   SIGKILL after the batches reach the spool, before the checkpoint
  pause-after-commit  hold the session lock after commit until <signal-dir>/release
"""

from __future__ import annotations

import importlib
import os
import runpy
import signal
import sys
import time
from pathlib import Path
from typing import Final

PAUSE_LIMIT_SECONDS: Final = 120.0
POLL_SECONDS: Final = 0.05
FAULTS: Final = ("kill-mid-export", "kill-after-commit", "pause-after-commit")


def die() -> None:
    os.kill(os.getpid(), signal.SIGKILL)


def pause(signals: Path) -> None:
    (signals / "paused").touch()
    deadline = time.monotonic() + PAUSE_LIMIT_SECONDS
    while not (signals / "release").exists():
        if time.monotonic() > deadline:
            die()
        time.sleep(POLL_SECONDS)


def inject(exporter: type, fault: str, signals: Path) -> None:
    if fault == "kill-mid-export":
        export = exporter.export

        def export_then_die(self: object, spans: object) -> object:
            export(self, spans)
            die()
            return None

        exporter.export = export_then_die
        return
    commit = exporter.commit

    def commit_then_fault(self: object) -> None:
        commit(self)
        if fault == "kill-after-commit":
            die()
        pause(signals)

    exporter.commit = commit_then_fault


def main() -> None:
    deployed, fault, signals = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    if fault not in FAULTS:
        message = f"unknown fault {fault!r}; expected one of {FAULTS}"
        raise SystemExit(message)
    sys.path.insert(0, str(deployed / "vendor"))
    # The vendored hook imports this module by the same name and gets the patched class.
    module = importlib.import_module("durable_otel_exporter")
    inject(module.DurableSpoolExporter, fault, signals)
    wrapper = deployed / "langfuse_trace_hook.py"
    sys.argv = [str(wrapper)]
    runpy.run_path(str(wrapper), run_name="__main__")


if __name__ == "__main__":
    main()
