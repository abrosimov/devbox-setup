from __future__ import annotations

import pytest

from aerospace_layouts.layouts.columns import columns_layout
from aerospace_layouts.layouts.floating import floating_layout
from aerospace_layouts.layouts.maxx import max_layout
from aerospace_layouts.model import Window
from aerospace_layouts.planner import plan_layout

from .conftest import argv_strings, make_windows

WS = "3"


def _win(window_id: int, layout: str = "h_tiles") -> Window:
    return Window(window_id, f"App{window_id}", f"t{window_id}", parent_layout=layout)


def test_max_accordions_root():
    commands = max_layout(make_windows(3))
    assert argv_strings(commands) == ["layout v_accordion --window-id 10"]
    assert commands[0].tolerate_nonzero is True


def test_max_empty_workspace_is_noop():
    assert max_layout([]) == []


def test_columns_tiles_and_balances():
    commands = columns_layout(make_windows(3), WS)
    assert argv_strings(commands) == [
        "layout h_tiles --window-id 10",
        "balance-sizes --workspace 3",
    ]


def test_columns_empty_workspace_is_noop():
    assert columns_layout([], WS) == []


def test_columns_has_no_joins():
    assert not any(cmd.args[0] == "join-with" for cmd in columns_layout(make_windows(5), WS))


def test_floating_floats_every_window_and_does_not_flatten():
    commands = floating_layout(make_windows(3))
    assert argv_strings(commands) == [
        "layout floating --window-id 10",
        "layout floating --window-id 11",
        "layout floating --window-id 12",
    ]
    assert all(cmd.tolerate_nonzero for cmd in commands)


def test_floating_empty_is_noop():
    assert floating_layout([]) == []


@pytest.mark.parametrize("name", ["tile", "tile.left", "max", "columns"])
def test_tiling_layouts_exclude_floating_window(name: str):
    # 102 = leftmost tiled (master); 163 floating must never be touched by a tiling layout.
    windows = [_win(102), _win(163, "floating"), _win(200), _win(201)]
    commands = plan_layout(name, windows, WS)
    targeted = {c.window_id for c in commands if c.window_id is not None}
    assert 163 not in targeted
    assert 102 in targeted  # the leftmost tiled window is the master
    if name in {"tile", "tile.left"}:
        joins = [c for c in commands if c.args[0] == "join-with"]
        assert [c.window_id for c in joins] == [201]  # 200 anchor, 201 joined; 163 excluded


def test_tile_with_only_one_tiled_window_emits_no_joins():
    windows = [_win(163, "floating"), _win(102), _win(200, "floating")]
    commands = plan_layout("tile", windows, WS)
    assert not any(c.args[0] == "join-with" for c in commands)
    assert all(c.window_id != 163 and c.window_id != 200 for c in commands)
