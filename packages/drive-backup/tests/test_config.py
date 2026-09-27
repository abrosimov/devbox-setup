from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from drive_backup.config import ConfigError, DirSpec, load, parse, resolve_path

ENV = {"HOME": "/home/u", "AION_AUTOPOIESEON": "/home/u/Work", "X": "/opt/x"}


def _cfg(**extra: object) -> dict[str, object]:
    return {"dir": [{"name": "claude", "path": "~/.claude"}], **extra}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("~/.claude", "/home/u/.claude"),
        ("~", "/home/u"),
        ("notes/obsidian", "/home/u/Work/notes/obsidian"),
        ("$X/data", "/opt/x/data"),
        ("${AION_AUTOPOIESEON}/a/../b", "/home/u/Work/b"),
        ("/abs/path", "/abs/path"),
    ],
)
def test_resolve_path(raw: str, expected: str) -> None:
    assert resolve_path(raw, ENV) == Path(expected)


def test_unset_variable_is_an_error() -> None:
    with pytest.raises(ConfigError, match=r"\$NOPE"):
        resolve_path("$NOPE/x", ENV)


def test_relative_path_needs_workspace() -> None:
    with pytest.raises(ConfigError, match="AION_AUTOPOIESEON"):
        resolve_path("notes", {"HOME": "/home/u"})


def test_defaults() -> None:
    cfg = parse(_cfg(), ENV)
    assert cfg.repo_dir == Path("/home/u/Work/drive/base")
    assert cfg.zstd_level == 9


def test_full_dir_table() -> None:
    cfg = parse(
        {
            "repo_dir": "~/drive",
            "zstd_level": 3,
            "dir": [
                {
                    "name": "claude",
                    "path": "~/.claude",
                    "exclude": ["bin/.venv"],
                },
                {"name": "notes", "path": "notes"},
            ],
        },
        ENV,
    )
    assert [d.name for d in cfg.dirs] == ["claude", "notes"]
    assert cfg.dirs[0].exclude == ("bin/.venv",)
    assert cfg.dirs[1].path == Path("/home/u/Work/notes")


def test_legacy_deferral_fields_are_validated_but_not_exposed() -> None:
    cfg = parse(
        {
            "defer": {"interval_minutes": 5, "max_wait_minutes": 60},
            "dir": [{"name": "claude", "path": "~/.claude", "busy": ["claude"]}],
        },
        ENV,
    )
    assert cfg.dirs == (DirSpec(name="claude", path=Path("/home/u/.claude")),)
    assert not hasattr(cfg, "defer")
    assert not hasattr(cfg.dirs[0], "busy")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({}, "at least one"),
        ({"dir": []}, "at least one"),
        (_cfg(bogus=1), "unknown key"),
        ({"dir": [{"name": "c", "path": "~/c", "typo": 1}]}, "unknown key"),
        ({"dir": [{"path": "~/c"}]}, "missing required key 'name'"),
        ({"dir": [{"name": "Bad_Name", "path": "~/c"}]}, "must match"),
        ({"dir": [{"name": "a", "path": "~/a"}, {"name": "a", "path": "~/b"}]}, "duplicate"),
        ({"dir": [{"name": "a", "path": "~/a", "exclude": "x"}]}, "must be list"),
        ({"dir": [{"name": "a", "path": "~/a", "exclude": ["../x"]}]}, "relative"),
        ({"dir": [{"name": "a", "path": "~/a", "busy": "claude"}]}, "must be list"),
        (_cfg(defer={"interval_minutes": 0}), "interval_minutes"),
        (_cfg(defer={"max_wait_minutes": -1}), "max_wait_minutes"),
        (_cfg(defer={"unknown": 1}), "unknown key"),
        (_cfg(zstd_level=0), "zstd_level"),
        (_cfg(zstd_level=True), "must be int"),
        # The repository must not be archived into itself, in either direction.
        ({"repo_dir": "~/.claude/drive", "dir": [{"name": "c", "path": "~/.claude"}]}, "overlaps"),
        ({"repo_dir": "~", "dir": [{"name": "c", "path": "~/.claude"}]}, "overlaps"),
    ],
)
def test_invalid(data: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse(data, ENV)


@pytest.mark.parametrize(
    ("pattern", "rel", "excluded"),
    [
        ("bin/.venv", "bin/.venv", True),
        ("bin/.venv", "bin/.venvx", False),
        ("bin/.venv", "other/bin/.venv", False),
        ("**/__pycache__", "a/b/__pycache__", True),
        ("**/__pycache__", "__pycache__", True),
        ("*.log", "x.log", True),
        ("*.log", "a/x.log", False),
        ("**/*.log", "a/x.log", True),
    ],
)
def test_exclude_matching(pattern: str, rel: str, excluded: bool) -> None:
    spec = DirSpec(name="x", path=Path("/x"), exclude=(pattern,))
    assert spec.is_excluded(PurePosixPath(rel)) is excluded


def test_load_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load(tmp_path / "missing.toml", ENV)
    bad = tmp_path / "bad.toml"
    bad.write_text("dir = [")
    with pytest.raises(ConfigError, match=r"bad\.toml"):
        load(bad, ENV)
