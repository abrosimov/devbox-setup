from __future__ import annotations

from pathlib import Path

import pytest
from throwaway import REAL_HOME, ThrowawayHome, UnsafeHomeError, assert_throwaway, temporary_root


def test_a_path_under_the_temporary_root_is_accepted(tmp_path: Path) -> None:
    assert assert_throwaway(tmp_path / "home") == (tmp_path / "home").resolve()


@pytest.mark.parametrize(
    "candidate",
    [
        REAL_HOME,
        REAL_HOME / ".claude",
        REAL_HOME / ".codex" / "config.toml",
        REAL_HOME / ".gemini" / "antigravity-cli" / "settings.json",
        REAL_HOME.parent,
        Path("/"),
        Path(__file__).resolve().parents[2],
    ],
)
def test_a_path_outside_the_temporary_root_is_refused(candidate: Path) -> None:
    with pytest.raises(UnsafeHomeError):
        assert_throwaway(candidate)


def test_the_temporary_root_itself_is_refused() -> None:
    with pytest.raises(UnsafeHomeError):
        assert_throwaway(temporary_root())


def test_a_symlink_escaping_the_temporary_root_is_refused(tmp_path: Path) -> None:
    escape = tmp_path / "escape"
    escape.symlink_to(REAL_HOME)
    with pytest.raises(UnsafeHomeError):
        assert_throwaway(escape / ".claude")


def test_a_traversal_out_of_the_throwaway_home_is_refused(tmp_path: Path) -> None:
    home = ThrowawayHome.create(tmp_path / "home")
    with pytest.raises(UnsafeHomeError):
        home.resolve("../../../../../../.claude/settings.json")


def test_a_write_through_an_escaping_symlink_is_refused(tmp_path: Path) -> None:
    home = ThrowawayHome.create(tmp_path / "home")
    (home.path / "link").symlink_to(REAL_HOME)
    with pytest.raises(UnsafeHomeError):
        home.write("link/.claude/settings.json", "{}")


def test_a_write_inside_the_throwaway_home_lands_where_it_was_asked(tmp_path: Path) -> None:
    home = ThrowawayHome.create(tmp_path / "home")
    written = home.write(".claude/settings.json", '{"hooks": {}}')
    assert written.read_text(encoding="utf-8") == '{"hooks": {}}'
    assert home.path in written.parents


def test_the_environment_redirects_every_variable_an_engine_resolves_a_home_from(
    tmp_path: Path,
) -> None:
    home = ThrowawayHome.create(tmp_path / "home")
    environment = home.environment()
    for name in ("HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_STATE_HOME"):
        assert Path(environment[name]).resolve().is_relative_to(home.path)


def test_the_guard_ignores_a_hostile_home_variable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert Path.home() != REAL_HOME
    with pytest.raises(UnsafeHomeError):
        assert_throwaway(REAL_HOME / ".claude")
