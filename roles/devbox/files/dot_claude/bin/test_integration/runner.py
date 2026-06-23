"""Subprocess runner for the integration harness.

Builds a hardened ``env`` (deterministic ``$HOME``, ``$TMPDIR``, ``$PATH``,
masked sandbox-specific variables) and invokes the script via its shebang —
``subprocess.run([str(path), ...])``. If the path is not executable, the
return result carries ``permission_denied`` and the caller surfaces it as a
failure rather than crashing.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_SECONDS: int = 30


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    permission_denied: bool = False
    error: str | None = None


@dataclass(frozen=True)
class RunRequest:
    script_path: Path
    argv: tuple[str, ...] = ()
    stdin: str = ""
    env_overrides: dict[str, str] = field(default_factory=dict)
    cwd: Path | None = None
    timeout: int = DEFAULT_TIMEOUT_SECONDS


def _placeholder_home(tmp_root: Path) -> Path:
    home = tmp_root / "home"
    home.mkdir(parents=True, exist_ok=True)
    return home


def _placeholder_tmpdir(tmp_root: Path) -> Path:
    tmpdir = tmp_root / "tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    return tmpdir


def build_env(
    overrides: dict[str, str],
    home: Path,
    tmpdir: Path,
) -> dict[str, str]:
    safe_env: dict[str, str] = {
        "HOME": str(home),
        "TMPDIR": str(tmpdir),
        "PATH": os.environ.get(
            "PATH",
            "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
        ),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        # Make sure shared lib bootstrapping doesn't crash when looking for
        # standard helper directories.
        "XDG_CACHE_HOME": str(tmpdir / "cache"),
    }
    # Whitelist a few env vars the scripts genuinely require if present.
    for inherited in ("USER", "SHELL", "LOGNAME"):
        value = os.environ.get(inherited)
        if value is not None:
            safe_env[inherited] = value
    safe_env.update(overrides)
    return safe_env


def _resolve_placeholders(value: str, home: Path, tmpdir: Path) -> str:
    out = value.replace("<HOME>", str(home))
    return out.replace("<TMPDIR>", str(tmpdir))


def materialise_payload(
    raw: Any,
    home: Path,
    tmpdir: Path,
) -> Any:
    if isinstance(raw, str):
        return _resolve_placeholders(raw, home, tmpdir)
    if isinstance(raw, list):
        return [materialise_payload(item, home, tmpdir) for item in raw]
    if isinstance(raw, dict):
        return {key: materialise_payload(value, home, tmpdir) for key, value in raw.items()}
    return raw


def run_script(request: RunRequest, tmp_root: Path) -> RunResult:
    if not request.script_path.exists():
        return RunResult(
            returncode=-1,
            stdout="",
            stderr="",
            error=f"script missing: {request.script_path}",
        )
    if not os.access(request.script_path, os.X_OK):
        return RunResult(
            returncode=-1,
            stdout="",
            stderr="",
            permission_denied=True,
            error=f"not executable: {request.script_path}",
        )

    home = _placeholder_home(tmp_root)
    tmpdir = _placeholder_tmpdir(tmp_root)
    env_overrides = {
        key: _resolve_placeholders(value, home, tmpdir)
        for key, value in request.env_overrides.items()
    }
    env = build_env(env_overrides, home, tmpdir)
    stdin = _resolve_placeholders(request.stdin, home, tmpdir)
    argv = [
        str(request.script_path),
        *[_resolve_placeholders(arg, home, tmpdir) for arg in request.argv],
    ]
    cwd: Path | str | None
    if request.cwd is None:
        cwd = home
    else:
        cwd = Path(_resolve_placeholders(str(request.cwd), home, tmpdir))
        if not cwd.exists():
            cwd.mkdir(parents=True, exist_ok=True)

    try:
        completed = subprocess.run(
            argv,
            input=stdin,
            env=env,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=request.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return RunResult(
            returncode=-1,
            stdout=exc.stdout if isinstance(exc.stdout, str) else "",
            stderr=exc.stderr if isinstance(exc.stderr, str) else "",
            timed_out=True,
            error=f"timeout after {request.timeout}s",
        )
    except OSError as exc:
        return RunResult(
            returncode=-1,
            stdout="",
            stderr="",
            error=f"oserror: {exc}",
        )
    return RunResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def parse_stdin_fixture(
    fixture: dict[str, Any],
) -> tuple[str, dict[str, str], list[str], str | None]:
    """Return (stdin, env_overrides, argv, cwd) for a CLI-style fixture.

    Recorded hook fixtures (PreToolUse / PostToolUse / PermissionRequest /
    Stop / PreCompact) lack the ``argv`` / ``env`` / ``stdin`` envelope —
    they are the raw stdin payload. Hand-crafted CLI fixtures use the
    envelope shape with optional ``cwd``.
    """
    if isinstance(fixture, dict) and "argv" in fixture:
        argv_value = fixture.get("argv", [])
        argv: list[str] = [str(item) for item in argv_value] if isinstance(argv_value, list) else []
        stdin_value = fixture.get("stdin", "")
        stdin = stdin_value if isinstance(stdin_value, str) else ""
        env_value = fixture.get("env", {})
        env: dict[str, str] = (
            {str(k): str(v) for k, v in env_value.items()} if isinstance(env_value, dict) else {}
        )
        cwd_value = fixture.get("cwd")
        cwd = cwd_value if isinstance(cwd_value, str) else None
        return stdin, env, argv, cwd
    # Recorded hook payload — feed verbatim as stdin.
    return json.dumps(fixture, ensure_ascii=False), {}, [], None
