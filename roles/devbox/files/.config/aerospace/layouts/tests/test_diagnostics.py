from __future__ import annotations

from aerospace_layouts.aerospace import AerospaceClient
from aerospace_layouts.cli import diagnose
from aerospace_layouts.diagnostics import (
    format_commands,
    format_dfs_map,
    format_diagnosis,
    format_window_line,
)
from aerospace_layouts.model import Window, floating_windows, join_with

from .conftest import FakeWm


def _win(window_id: int, layout: str | None = "h_tiles") -> Window:
    return Window(window_id, f"App{window_id}", f"t{window_id}", parent_layout=layout)


def test_format_window_line_shows_layout():
    expected = "id=163 layout=floating app='App163' title='t163'"
    assert format_window_line(_win(163, "floating")) == expected


def test_floating_windows_filters_by_parent_layout():
    windows = [_win(10, "h_tiles"), _win(163, "floating"), _win(11, "v_tiles")]
    assert [w.window_id for w in floating_windows(windows)] == [163]


def test_format_dfs_map_marks_missing_as_none():
    assert format_dfs_map([(0, 163), (1, None)]) == ["dfs[0] -> 163", "dfs[1] -> <none>"]


def test_format_commands_renders_argv():
    assert format_commands([join_with("left", 12)]) == ["join-with left --window-id 12"]


def test_format_diagnosis_flags_floating_and_shows_tiled_set():
    raw = [_win(163, "floating"), _win(10), _win(11)]
    ordered = [_win(163, "floating"), _win(10), _win(11)]
    dfs_map: list[tuple[int, int | None]] = [(0, 163), (1, 10), (2, 11)]
    lines = format_diagnosis(raw, dfs_map, ordered, [join_with("left", 11)])
    assert any("floating window(s) NOT in the tiling tree: 163" in line for line in lines)
    assert any("tiling set (floating excluded, master first): 10, 11" in line for line in lines)


def test_diagnose_excludes_floating_and_plans_without_executing_joins():
    wm = FakeWm(
        dfs_ids=[2000, 2001, 200, 163],
        post_flatten_dfs=[163, 2000, 2001, 200],
        array_ids=[2000, 2001, 200, 163],
        focused=163,
        layouts={163: "floating"},
    )
    client = AerospaceClient(wm)

    commands = diagnose(client, "tile", "3")

    assert wm.mutations == [["flatten-workspace-tree", "--workspace", "3"]]
    assert wm.joined_ids() == []
    assert any(c.args[:1] == ("join-with",) for c in commands)
    assert all(c.window_id != 163 for c in commands)
    assert wm.focused == 163
