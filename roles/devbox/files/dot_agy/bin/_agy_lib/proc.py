from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class CmdResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def run_cmd(
    cmd: list[str] | str,
    *,
    timeout: int = 30,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> CmdResult:
    argv: list[str] = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
    cwd_arg = str(cwd) if cwd is not None else None

    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd_arg,
            env=env,
            input=input_text,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CmdResult(stdout=stdout, stderr=stderr, returncode=-1, timed_out=True)
    except FileNotFoundError as exc:
        return CmdResult(stdout="", stderr=str(exc), returncode=127, timed_out=False)
    except OSError as exc:
        return CmdResult(stdout="", stderr=str(exc), returncode=126, timed_out=False)

    return CmdResult(
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        returncode=completed.returncode,
        timed_out=False,
    )
