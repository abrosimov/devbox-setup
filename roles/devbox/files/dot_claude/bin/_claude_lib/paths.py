from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

# Compared after resolving, so macOS /tmp lands here; on Linux gettempdir() is /tmp.
MACOS_SYSTEM_TEMP_DIR: Final[str] = "/private/tmp"


def temp_roots() -> tuple[Path, ...]:
    candidates = (os.environ.get("TMPDIR"), tempfile.gettempdir(), MACOS_SYSTEM_TEMP_DIR)
    return tuple(dict.fromkeys(Path(candidate).resolve() for candidate in candidates if candidate))


def is_within(path: Path, roots: Iterable[Path]) -> bool:
    resolved = path.resolve()
    return any(resolved.is_relative_to(root) for root in roots)


def is_temp_path(path: Path) -> bool:
    return is_within(path, temp_roots())


def find_project_root(
    start: Path,
    markers: Sequence[str],
    *,
    max_depth: int = 20,
) -> Path | None:
    current = start.resolve() if start.exists() else start
    if current.is_file():
        current = current.parent

    depth = 0
    while depth <= max_depth:
        for marker in markers:
            if (current / marker).exists():
                return current
        if current.parent == current:
            return None
        current = current.parent
        depth += 1
    return None


def find_git_root(start: Path) -> Path | None:
    return find_project_root(start, (".git",))


def atomic_write(target: Path, content: str, *, encoding: str = "utf-8") -> None:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        tmp_path.replace(target)
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
