from __future__ import annotations

import os
from pathlib import Path

# Hook scripts run as child processes that inherit Claude Code's environment.
# When Claude Code is launched from a GUI context (Spotlight, dock, IDE) rather
# than from a terminal, the process may lack paths configured by fish/bash
# profiles. This module augments PATH with known tool directories and redirects
# tool caches to $TMPDIR so they remain writable inside the sandbox.


def _home() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp"  # noqa: S108
    return Path(home)


def _tmpdir() -> Path:
    return Path(os.environ.get("TMPDIR") or "/tmp")  # noqa: S108


def _extra_paths(home: Path) -> list[Path]:
    return [
        Path("/opt/homebrew/bin"),
        Path("/opt/homebrew/sbin"),
        home / ".local" / "bin",
        home / ".programming" / "go" / "bin",
        home / ".cargo" / "bin",
        home / ".claude" / "bin",
        home / "bin",
        home / ".programming" / "ruby" / "gems" / "bin",
    ]


def harden_path() -> None:
    home = _home()
    current = os.environ.get("PATH", "")
    current_dirs = set(current.split(":"))
    missing = [p for p in _extra_paths(home) if str(p) not in current_dirs and p.exists()]
    if missing:
        os.environ["PATH"] = ":".join(str(p) for p in missing) + ":" + current


def setup_go(home: Path, tmp: Path) -> None:
    os.environ.setdefault("GOPATH", str(home / ".programming" / "go"))
    os.environ.setdefault("GOTOOLCHAIN", "local")
    os.environ.setdefault("GOCACHE", str(tmp / "go-build-cache"))
    os.environ.setdefault("GOMODCACHE", str(tmp / "go-mod-cache"))


def setup_python(tmp: Path) -> None:
    os.environ.setdefault("UV_CACHE_DIR", str(tmp / "uv-cache"))
    os.environ.setdefault("RUFF_CACHE_DIR", str(tmp / "ruff-cache"))
    os.environ.setdefault("MYPY_CACHE_DIR", str(tmp / "mypy-cache"))


def setup_node(tmp: Path) -> None:
    os.environ.setdefault("NPM_CONFIG_CACHE", str(tmp / "npm-cache"))


def setup() -> None:
    harden_path()
    home = _home()
    tmp = _tmpdir()
    setup_go(home, tmp)
    setup_python(tmp)
    setup_node(tmp)
