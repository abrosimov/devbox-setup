from __future__ import annotations

import io
import tarfile
from compression import zstd
from pathlib import Path

import pytest

from drive_backup.archive import ExactSizeReader, write_archive
from drive_backup.config import DirSpec


def _members(path: Path) -> dict[str, tarfile.TarInfo]:
    with zstd.ZstdFile(path) as zf, tarfile.open(fileobj=zf, mode="r|") as tar:
        return {m.name: m for m in tar}


def test_roundtrip_with_excludes(source: Path, tmp_path: Path) -> None:
    spec = DirSpec(name="claude", path=source, exclude=("bin/.venv",))
    dest = tmp_path / "out" / "a.tar.zst"
    result = write_archive(spec, dest, level=3)

    members = _members(dest)
    assert ".claude/projects/p1/s.jsonl" in members
    assert ".claude/bin/tool.py" in members
    assert not any(".venv" in name for name in members)
    assert members[".claude/link"].issym()
    assert members[".claude"].isdir()
    assert result.files == 3
    assert result.warnings == []
    assert not list(dest.parent.glob(".*.partial"))


def test_extracts_to_identical_content(source: Path, tmp_path: Path) -> None:
    dest = tmp_path / "a.tar.zst"
    write_archive(DirSpec(name="claude", path=source), dest, level=1)
    out = tmp_path / "x"
    with zstd.ZstdFile(dest) as zf, tarfile.open(fileobj=zf, mode="r|") as tar:
        tar.extractall(out, filter="data")
    assert (out / ".claude/projects/p1/s.jsonl").read_text() == '{"a": 1}\n' * 100


def test_special_files_are_skipped(source: Path, tmp_path: Path) -> None:
    import os

    os.mkfifo(source / "fifo")
    result = write_archive(DirSpec(name="c", path=source), tmp_path / "a.tar.zst", level=1)
    assert any("special" in w for w in result.warnings)


def test_missing_source_leaves_nothing_behind(tmp_path: Path) -> None:
    dest = tmp_path / "a.tar.zst"
    with pytest.raises(FileNotFoundError):
        write_archive(DirSpec(name="c", path=tmp_path / "nope"), dest, level=1)
    assert list(tmp_path.iterdir()) == []


def test_exact_size_reader_pads_and_truncates() -> None:
    short = ExactSizeReader(io.BytesIO(b"abc"), 5)
    assert short.read(10) == b"abc\0\0"
    assert short.padded == 2
    assert short.read() == b""
    long = ExactSizeReader(io.BytesIO(b"abcdef"), 4)
    assert long.read() == b"abcd"
    assert long.padded == 0
