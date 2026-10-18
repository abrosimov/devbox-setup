from __future__ import annotations

import io
import os
import tarfile
from compression import zstd
from pathlib import Path

import pytest

from drive_backup import archive
from drive_backup.archive import ExactSizeReader, PartWriter, write_archive
from drive_backup.config import DirSpec

BIG = 2**31


def _members(path: Path) -> dict[str, tarfile.TarInfo]:
    with zstd.ZstdFile(path) as zf, tarfile.open(fileobj=zf, mode="r|") as tar:
        return {m.name: m for m in tar}


def _extract(stream: bytes, out: Path) -> None:
    with zstd.ZstdFile(io.BytesIO(stream)) as zf, tarfile.open(fileobj=zf, mode="r|") as tar:
        tar.extractall(out, filter="data")


def _tree(root: Path) -> dict[str, bytes | str]:
    return {
        str(p.relative_to(root)): str(p.readlink()) if p.is_symlink() else p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_symlink() or p.is_file()
    }


def _leftovers(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


def test_roundtrip_with_excludes(source: Path, tmp_path: Path) -> None:
    spec = DirSpec(name="claude", path=source, exclude=("bin/.venv",))
    dest = tmp_path / "out" / "a.tar.zst"
    result = write_archive(spec, dest, level=3, max_part_bytes=BIG)

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
    write_archive(DirSpec(name="claude", path=source), dest, level=1, max_part_bytes=BIG)
    out = tmp_path / "x"
    with zstd.ZstdFile(dest) as zf, tarfile.open(fileobj=zf, mode="r|") as tar:
        tar.extractall(out, filter="data")
    assert (out / ".claude/projects/p1/s.jsonl").read_text() == '{"a": 1}\n' * 100


def test_special_files_are_skipped(source: Path, tmp_path: Path) -> None:
    os.mkfifo(source / "fifo")
    result = write_archive(
        DirSpec(name="c", path=source), tmp_path / "a.tar.zst", level=1, max_part_bytes=BIG
    )
    assert any("special" in w for w in result.warnings)


def test_missing_source_leaves_nothing_behind(tmp_path: Path) -> None:
    dest = tmp_path / "a.tar.zst"
    with pytest.raises(FileNotFoundError):
        write_archive(DirSpec(name="c", path=tmp_path / "nope"), dest, level=1, max_part_bytes=BIG)
    assert list(tmp_path.iterdir()) == []


def test_exact_size_reader_pads_and_truncates() -> None:
    short = ExactSizeReader(io.BytesIO(b"abc"), 5)
    assert short.read(10) == b"abc\0\0"
    assert short.padded == 2
    assert short.read() == b""
    long = ExactSizeReader(io.BytesIO(b"abcdef"), 4)
    assert long.read() == b"abcd"
    assert long.padded == 0


def test_output_that_fits_one_part_is_a_single_tar_zst(source: Path, tmp_path: Path) -> None:
    spec = DirSpec(name="claude", path=source)
    reference = write_archive(spec, tmp_path / "ref" / "a.tar.zst", level=1, max_part_bytes=BIG)
    size = reference.bytes_out

    dest = tmp_path / "out" / "a.tar.zst"
    result = write_archive(spec, dest, level=1, max_part_bytes=size)

    assert result.parts == [dest]
    assert _leftovers(dest.parent) == ["a.tar.zst"]
    assert dest.read_bytes() == reference.dest.read_bytes()


def test_output_one_byte_over_the_part_size_splits_in_two(source: Path, tmp_path: Path) -> None:
    spec = DirSpec(name="claude", path=source)
    reference = write_archive(spec, tmp_path / "ref" / "a.tar.zst", level=1, max_part_bytes=BIG)
    size = reference.bytes_out

    dest = tmp_path / "out" / "a.tar.zst"
    result = write_archive(spec, dest, level=1, max_part_bytes=size - 1)

    assert [p.name for p in result.parts] == ["a.tar.zst.part-001", "a.tar.zst.part-002"]
    assert [p.stat().st_size for p in result.parts] == [size - 1, 1]
    assert _leftovers(dest.parent) == ["a.tar.zst.part-001", "a.tar.zst.part-002"]
    assert b"".join(p.read_bytes() for p in result.parts) == reference.dest.read_bytes()


def test_tiny_parts_concatenate_to_the_original_tree(source: Path, tmp_path: Path) -> None:
    dest = tmp_path / "out" / "a.tar.zst"
    result = write_archive(DirSpec(name="claude", path=source), dest, level=1, max_part_bytes=64)

    assert len(result.parts) > 3
    assert [p.name for p in result.parts] == [
        f"a.tar.zst.part-{i:03d}" for i in range(1, len(result.parts) + 1)
    ]
    assert all(p.stat().st_size == 64 for p in result.parts[:-1])
    assert 0 < result.parts[-1].stat().st_size <= 64
    assert not dest.exists()
    assert result.bytes_out == sum(p.stat().st_size for p in result.parts)

    out = tmp_path / "x"
    _extract(b"".join(p.read_bytes() for p in result.parts), out)
    assert _tree(out / ".claude") == _tree(source)


@pytest.mark.parametrize(
    ("writes", "max_part_bytes", "expected"),
    [
        ([b"abcdef"], 3, [b"abc", b"def"]),
        ([b"ab", b"cd", b"ef"], 2, [b"ab", b"cd", b"ef"]),
        ([b"abcdefg"], 3, [b"abc", b"def", b"g"]),
        ([b"abc"], 3, [b"abc"]),
        ([b"a", b"bcdefgh"], 4, [b"abcd", b"efgh"]),
    ],
)
def test_part_writer_cuts_at_exact_boundaries(
    tmp_path: Path, writes: list[bytes], max_part_bytes: int, expected: list[bytes]
) -> None:
    dest = tmp_path / "a.tar.zst"
    with PartWriter(dest, max_part_bytes) as parts:
        for data in writes:
            assert parts.write(data) == len(data)
        finals = parts.publish()

    assert [p.read_bytes() for p in finals] == expected
    assert _leftovers(tmp_path) == sorted(p.name for p in finals)


def test_part_writer_rejects_non_positive_size(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        PartWriter(tmp_path / "a.tar.zst", 0)


def test_rejected_part_leaves_nothing_behind(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    seen: list[str] = []

    def reject_second(path: Path) -> None:
        seen.append(path.name)
        if path.name.endswith("part-002"):
            raise RuntimeError("not tracked")

    with pytest.raises(RuntimeError, match="not tracked"):
        write_archive(
            DirSpec(name="claude", path=source),
            out / "a.tar.zst",
            level=1,
            max_part_bytes=64,
            approve=reject_second,
        )
    assert seen[:2] == ["a.tar.zst.part-001", "a.tar.zst.part-002"]
    assert _leftovers(out) == []


def test_failure_mid_stream_leaves_no_parts(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_add = archive._add_entry
    calls: list[str] = []

    def fail_late(
        tar: tarfile.TarFile, src: Path, arcname: str, result: archive.ArchiveResult
    ) -> None:
        calls.append(arcname)
        if len(calls) == 6:
            raise OSError("disk full")
        real_add(tar, src, arcname, result)

    monkeypatch.setattr(archive, "_add_entry", fail_late)
    out = tmp_path / "out"
    with pytest.raises(OSError, match="disk full"):
        write_archive(DirSpec(name="claude", path=source), out / "a.tar.zst", 1, 64)
    assert _leftovers(out) == []


def test_failed_rename_rolls_back_published_parts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = Path.replace
    renamed: list[str] = []

    def fail_second(self: Path, target: Path) -> Path:
        renamed.append(self.name)
        if len(renamed) == 2:
            raise OSError("rename failed")
        return real_replace(self, target)

    parts = PartWriter(tmp_path / "a.tar.zst", 2)
    parts.write(b"abcdef")
    monkeypatch.setattr(Path, "replace", fail_second)
    with pytest.raises(OSError, match="rename failed"):
        parts.publish()
    monkeypatch.undo()
    parts.discard()
    assert _leftovers(tmp_path) == []
