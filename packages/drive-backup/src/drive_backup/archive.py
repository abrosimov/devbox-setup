"""Write one directory as a zstd-compressed tar stream.

The source directories belong to tools that may still be running, so the walk is
tolerant: a file that vanishes is skipped, and a file that changes size while it is
read is stored at the size it had when its header was written (short reads are
zero-padded) so the tar stream is never corrupted. Every such event is reported.

A stream larger than ``max_part_bytes`` is cut on the fly into ``<dest>.part-001``,
``.part-002``, …: a plain byte split, so the parts concatenated in order are the
``.tar.zst``. A stream that fits in one part is written as ``<dest>`` itself.
"""

from __future__ import annotations

import os
import stat
import tarfile
from collections.abc import Callable, Iterator
from compression import zstd
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import TracebackType
from typing import BinaryIO

from .config import DirSpec


@dataclass
class ArchiveResult:
    dest: Path
    parts: list[Path] = field(default_factory=list[Path])
    files: int = 0
    bytes_in: int = 0
    warnings: list[str] = field(default_factory=list[str])

    @property
    def bytes_out(self) -> int:
        return sum(part.stat().st_size for part in self.parts)


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


class PartWriter:
    """Spread a byte stream over hidden ``.partial`` files of at most ``max_part_bytes``.

    ``publish`` renames them to their final names; ``discard`` removes what is left.
    """

    def __init__(self, dest: Path, max_part_bytes: int) -> None:
        if max_part_bytes <= 0:
            raise ValueError(f"max_part_bytes must be positive, got {max_part_bytes}")
        self._dest = dest
        self._max = max_part_bytes
        self._partials: list[Path] = []
        self._room = 0
        self._fh: BinaryIO | None = None
        # The first part is opened eagerly so every stream yields at least one file,
        # later ones lazily so an exact multiple of the part size leaves no empty part.
        self._open_next()

    def __enter__(self) -> PartWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _open_next(self) -> BinaryIO:
        self.close()
        index = len(self._partials) + 1
        partial = self._dest.with_name(f".{self._dest.name}.part-{index:03d}.partial")
        self._partials.append(partial)
        fh = partial.open("wb")
        self._fh, self._room = fh, self._max
        return fh

    def _current(self) -> BinaryIO:
        fh = self._fh
        if fh is None:
            raise ValueError(f"write to closed part writer for {self._dest}")
        if self._room == 0:
            fh = self._open_next()
        return fh

    def write(self, data: bytes) -> int:
        view = memoryview(data).cast("B")
        while view:
            fh = self._current()
            chunk, view = view[: self._room], view[self._room :]
            fh.write(chunk)
            self._room -= len(chunk)
        return len(data)

    def flush(self) -> None:
        if self._fh is not None:
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def final_paths(self) -> list[Path]:
        if len(self._partials) == 1:
            return [self._dest]
        return [
            self._dest.with_name(f"{self._dest.name}.part-{i:03d}")
            for i in range(1, len(self._partials) + 1)
        ]

    def publish(self) -> list[Path]:
        self.close()
        finals = self.final_paths()
        done: list[Path] = []
        try:
            for partial, final in zip(self._partials, finals, strict=True):
                partial.replace(final)
                done.append(final)
        except BaseException:
            for final in done:
                final.unlink(missing_ok=True)
            raise
        return finals

    def discard(self) -> None:
        self.close()
        for partial in self._partials:
            partial.unlink(missing_ok=True)


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


def write_archive(
    spec: DirSpec,
    dest: Path,
    level: int,
    max_part_bytes: int,
    approve: Callable[[Path], None] | None = None,
) -> ArchiveResult:
    """Archive ``spec.path`` into ``dest`` or its parts, atomically (temp files + rename).

    ``approve`` sees every final path before any is renamed into place; raising from
    it leaves nothing behind.
    """
    if not spec.path.is_dir():
        raise FileNotFoundError(f"{spec.name}: {spec.path} is not a directory")
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = ArchiveResult(dest=dest)
    # Entries are rooted at the directory's own name (".claude/...") so an archive
    # unpacks next to, not over, whatever is in the current directory.
    root = spec.path.name
    parts = PartWriter(dest, max_part_bytes)
    try:
        with (
            parts,
            zstd.ZstdFile(parts, "wb", level=level) as zf,
            tarfile.open(fileobj=zf, mode="w|", format=tarfile.PAX_FORMAT) as tar,
        ):
            tar.addfile(tar.gettarinfo(str(spec.path), root))
            for src, rel in _walk(spec, result):
                _add_entry(tar, src, f"{root}/{rel}", result)
        if approve is not None:
            for final in parts.final_paths():
                approve(final)
        result.parts = parts.publish()
    finally:
        parts.discard()
    return result
