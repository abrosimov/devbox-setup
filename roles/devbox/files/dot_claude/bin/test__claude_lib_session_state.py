from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import session_state


@pytest.mark.parametrize("session_id", [None, "", "../escape", "a/b", ".hidden", 42])
def test_unusable_session_ids_yield_no_state(tmp_path: Path, session_id: object) -> None:
    data: dict[str, object] = {"session_id": session_id}
    assert session_state.SessionState.from_hook_input(data, tmp_path) is None


def test_edited_paths_are_resolved_unique_and_in_first_edit_order(tmp_path: Path) -> None:
    state = session_state.SessionState.from_hook_input({"session_id": "abc-123"}, tmp_path)
    assert state is not None
    first = tmp_path / "a.py"
    second = tmp_path / "b.py"
    for path in (first, second, first):
        state.record_edit(path)

    assert state.edited_paths() == (first.resolve(), second.resolve())


def test_paths_with_newlines_round_trip(tmp_path: Path) -> None:
    state = session_state.SessionState(tmp_path / "s")
    odd = tmp_path / "line\nbreak.py"
    state.record_edit(odd)
    assert state.edited_paths() == (odd.resolve(),)


def test_seen_keys_accumulate(tmp_path: Path) -> None:
    state = session_state.SessionState(tmp_path / "s")
    assert state.seen_keys() == frozenset()
    state.mark_seen(["k1"])
    state.mark_seen(["k2", "k1"])
    assert state.seen_keys() == frozenset({"k1", "k2"})


def test_unwritable_state_directory_degrades_to_empty(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("", encoding="utf-8")
    state = session_state.SessionState(blocker / "s")
    state.record_edit(tmp_path / "a.py")
    state.mark_seen(["k"])
    assert state.edited_paths() == ()
    assert state.seen_keys() == frozenset()


def test_new_session_prunes_stale_session_directories(tmp_path: Path) -> None:
    stale = tmp_path / "old-session"
    fresh = tmp_path / "recent-session"
    for directory in (stale, fresh):
        directory.mkdir()
    old = 1_000_000.0
    os.utime(stale, (old, old))

    session_state.SessionState(tmp_path / "new-session").record_edit(tmp_path / "a.py")

    assert not stale.exists()
    assert fresh.exists()
