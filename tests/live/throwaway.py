"""Throwaway home directories for tests that run a real engine binary.

Every path an engine test writes passes `assert_throwaway` first. The guard is
load-bearing, not ceremonial: a live reconcile against `~/.claude` rewrites
repository-owned files, and the engines resolve `~` from `HOME`, so a single
mistaken path would target the operator's real configuration.
"""

from __future__ import annotations

import os
import pwd
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# Read from the password database rather than `Path.home()`: the tests set HOME
# to the throwaway, so an env-derived answer would make the guard agree with
# whatever mistake put it there.
REAL_HOME: Final = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()


class UnsafeHomeError(RuntimeError):
    pass


def temporary_root() -> Path:
    return Path(tempfile.gettempdir()).resolve()


def assert_throwaway(path: Path) -> Path:
    """Return `path` resolved, or refuse if it is not disposable.

    Resolution is what makes this more than a prefix check: a symlink inside the
    temporary tree that points at the real home resolves out of the temporary
    root and is refused.
    """
    resolved = Path(path).resolve()
    root = temporary_root()
    if resolved == root or root not in resolved.parents:
        message = f"refusing to touch {resolved}: not inside the temporary root {root}"
        raise UnsafeHomeError(message)
    if resolved == REAL_HOME or REAL_HOME in resolved.parents or resolved in REAL_HOME.parents:
        message = f"refusing to touch {resolved}: it overlaps the real home {REAL_HOME}"
        raise UnsafeHomeError(message)
    return resolved


@dataclass(frozen=True, slots=True)
class ThrowawayHome:
    path: Path

    @classmethod
    def create(cls, path: Path) -> ThrowawayHome:
        root = assert_throwaway(path)
        root.mkdir(parents=True, exist_ok=True)
        return cls(path=root)

    def resolve(self, relative: str) -> Path:
        candidate = assert_throwaway(self.path / relative)
        if candidate != self.path and self.path not in candidate.parents:
            message = f"refusing to touch {candidate}: it escapes the throwaway home {self.path}"
            raise UnsafeHomeError(message)
        return candidate

    def directory(self, relative: str) -> Path:
        target = self.resolve(relative)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def write(self, relative: str, content: str, *, mode: int = 0o600) -> Path:
        target = self.resolve(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        target.chmod(mode)
        return target

    def environment(self, **extra: str) -> dict[str, str]:
        redirected = {
            "HOME": str(self.path),
            "CLAUDE_CONFIG_DIR": str(self.path / ".claude"),
            "CODEX_HOME": str(self.path / ".codex"),
            "XDG_STATE_HOME": str(self.path / ".local" / "state"),
        }
        for value in redirected.values():
            assert_throwaway(Path(value))
        return {**os.environ, **redirected, **extra}
