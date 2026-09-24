"""Write one directory as a zstd-compressed tar stream.

The source directories belong to tools that may still be running, so the walk is
tolerant: a file that vanishes is skipped, and a file that changes size while it is
read is stored at the size it had when its header was written (short reads are
zero-padded) so the tar stream is never corrupted. Every such event is reported.
"""

from __future__ import annotations

import os
import stat
import tarfile
from collections.abc import Iterator
from compression import zstd
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from .config import DirSpec


@dataclass
class ArchiveResult:
    path: Path
    files: int = 0
    bytes_in: int = 0
    warnings: list[str] = field(default_factory=list[str])

    @property
    def bytes_out(self) -> int:
        return self.path.stat().st_size


class ExactSizeReader:
    """Yield exactly ``size`` bytes: truncate growth, zero-pad shrinkage."""

    def __init__(self, fh: BinaryIO, size: int) -> None:
        self._fh = fh
        self._left = size
        self.padded = 0

    def read(self, n: int = -1) -> bytes:
        if self._left <= 0:
            return b""
        want = self._left if n < 0 else min(n, self._left)
        data = self._fh.read(want)
        if len(data) < want:
            pad = want - len(data)
            self.padded += pad
            data += b"\0" * pad
        self._left -= len(data)
        return data


def _walk(spec: DirSpec, result: ArchiveResult) -> Iterator[tuple[Path, PurePosixPath]]:
    def onerror(exc: OSError) -> None:
        result.warnings.append(f"cannot list {exc.filename}: {exc.strerror}")

    for top, dirnames, filenames in os.walk(spec.path, onerror=onerror):
        top_path = Path(top)
        rel_top = PurePosixPath(top_path.relative_to(spec.path).as_posix())
        kept: list[str] = []
        for name in sorted(dirnames):
            rel = rel_top / name
            if spec.is_excluded(rel):
                continue
            # os.walk does not descend into symlinked dirs; the link itself is stored.
            if not (top_path / name).is_symlink():
                kept.append(name)
            yield top_path / name, rel
        dirnames[:] = kept
        for name in sorted(filenames):
            rel = rel_top / name
            if not spec.is_excluded(rel):
                yield top_path / name, rel


def _add_entry(tar: tarfile.TarFile, src: Path, arcname: str, result: ArchiveResult) -> None:
    try:
        st = src.lstat()
    except FileNotFoundError:
        result.warnings.append(f"vanished: {src}")
        return
    mode = st.st_mode
    if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode)):
        result.warnings.append(f"skipped special file: {src}")
        return
    try:
        if not stat.S_ISREG(mode):
            tar.addfile(tar.gettarinfo(str(src), arcname))
            return
        with src.open("rb") as fh:
            info = tar.gettarinfo(arcname=arcname, fileobj=fh)
            reader = ExactSizeReader(fh, info.size)
            tar.addfile(info, reader)
    except FileNotFoundError:
        result.warnings.append(f"vanished: {src}")
        return
    except PermissionError as exc:
        result.warnings.append(f"permission denied: {src} ({exc.strerror})")
        return
    result.files += 1
    result.bytes_in += info.size
    if reader.padded:
        result.warnings.append(f"shrank while reading, zero-padded {reader.padded} B: {src}")


def write_archive(spec: DirSpec, dest: Path, level: int) -> ArchiveResult:
    """Archive ``spec.path`` into ``dest`` atomically (temp file + rename)."""
    if not spec.path.is_dir():
        raise FileNotFoundError(f"{spec.name}: {spec.path} is not a directory")
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(f".{dest.name}.partial")
    result = ArchiveResult(path=dest)
    # Entries are rooted at the directory's own name (".claude/...") so an archive
    # unpacks next to, not over, whatever is in the current directory.
    root = spec.path.name
    try:
        with (
            zstd.ZstdFile(partial, "wb", level=level) as zf,
            tarfile.open(fileobj=zf, mode="w|", format=tarfile.PAX_FORMAT) as tar,
        ):
            tar.addfile(tar.gettarinfo(str(spec.path), root))
            for src, rel in _walk(spec, result):
                _add_entry(tar, src, f"{root}/{rel}", result)
        partial.replace(dest)
    finally:
        partial.unlink(missing_ok=True)
    return result
