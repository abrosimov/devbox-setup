from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import paths


def test_find_project_root_finds_marker_at_start(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/foo\n")
    assert paths.find_project_root(tmp_path, ("go.mod",)) == tmp_path


def test_find_project_root_walks_up_tree(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/foo\n")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert paths.find_project_root(nested, ("go.mod",)) == tmp_path


def test_find_project_root_returns_none_when_no_marker(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert paths.find_project_root(nested, ("nonexistent.marker",)) is None


def test_find_project_root_starts_from_file_parent(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    nested = tmp_path / "src" / "module.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("")
    assert paths.find_project_root(nested, ("pyproject.toml",)) == tmp_path


def test_find_project_root_first_marker_wins(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "pyproject.toml").write_text("")
    result = paths.find_project_root(tmp_path, ("package.json", "pyproject.toml"))
    assert result == tmp_path


def test_find_project_root_respects_max_depth(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("")
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    assert paths.find_project_root(deep, ("go.mod",), max_depth=2) is None


def test_find_git_root_finds_dot_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "pkg"
    nested.mkdir()
    assert paths.find_git_root(nested) == tmp_path


def test_atomic_write_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    paths.atomic_write(target, "hello\n")
    assert target.read_text() == "hello\n"


def test_atomic_write_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.write_text("old")
    paths.atomic_write(target, "new")
    assert target.read_text() == "new"


def test_atomic_write_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "out.txt"
    paths.atomic_write(target, "x")
    assert target.read_text() == "x"


def test_atomic_write_cleans_tmpfile_on_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "out.txt"
    sentinel = "simulated crash"

    def boom(self: Path, _target: Path) -> None:  # noqa: ARG001
        raise RuntimeError(sentinel)

    monkeypatch.setattr(Path, "replace", boom)
    with pytest.raises(RuntimeError, match=sentinel):
        paths.atomic_write(target, "doomed")

    # The final target must not exist as a half-written file.
    assert not target.exists()
    # No tmpfile orphans left behind.
    orphans = [p for p in tmp_path.iterdir() if p.name.startswith(".out.txt.")]
    assert orphans == []
