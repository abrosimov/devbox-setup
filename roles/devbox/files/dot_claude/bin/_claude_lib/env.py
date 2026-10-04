from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Hook scripts run as child processes that inherit Claude Code's environment.
# When Claude Code is launched from a GUI context (Spotlight, dock, IDE) rather
# than from a terminal, the process may lack paths configured by fish/bash
# profiles. This module augments PATH with known tool directories and redirects
# tool caches to $TMPDIR so they remain writable inside the sandbox.


def _tmpdir() -> Path:
    # TMPDIR is read directly instead of leaving it to tempfile.gettempdir():
    # gettempdir() caches its answer in a module global on the first call, so it
    # would not follow a TMPDIR that the session sets afterwards. gettempdir()
    # supplies the fallback because it checks each candidate directory for
    # writability, which a bare "/tmp" literal cannot do.
    return Path(os.environ.get("TMPDIR") or tempfile.gettempdir())


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
    home = Path.home()
    current = os.environ.get("PATH", "")
    current_dirs = set(current.split(":"))
    missing = [p for p in _extra_paths(home) if str(p) not in current_dirs and p.exists()]
    if missing:
        os.environ["PATH"] = ":".join(str(p) for p in missing) + ":" + current


def setup_go(home: Path, tmp: Path) -> None:
    # GOPATH is intentionally not set here: Go's built-in default of
    # $HOME/go is a sensible fallback on any machine, and settings.json.env
    # is the correct place to override it per-user.
    del home
    os.environ.setdefault("GOTOOLCHAIN", "local")
    os.environ.setdefault("GOCACHE", str(tmp / "go-build-cache"))
    os.environ.setdefault("GOMODCACHE", str(tmp / "go-mod-cache"))


def setup_python(tmp: Path) -> None:
    # No type-checker cache var: pyrefly exposes only PYREFLY_THREADS,
    # PYREFLY_CONFIG, PYREFLY_COLOR and PYREFLY_VERBOSE, so its `.pyrefly_cache`
    # cannot be relocated out of the project tree from the environment.
    os.environ.setdefault("UV_CACHE_DIR", str(tmp / "uv-cache"))
    os.environ.setdefault("RUFF_CACHE_DIR", str(tmp / "ruff-cache"))


def setup_node(tmp: Path) -> None:
    os.environ.setdefault("NPM_CONFIG_CACHE", str(tmp / "npm-cache"))


def setup() -> None:
    harden_path()
    home = Path.home()
    tmp = _tmpdir()
    setup_go(home, tmp)
    setup_python(tmp)
    setup_node(tmp)
