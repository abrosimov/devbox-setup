from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aerospace_layouts.layouts.tile import tile_layout
from aerospace_layouts.model import MasterSide

from .conftest import argv_strings, make_windows

WS = "3"


def test_master_left_three_windows_builds_vertical_stack_on_right():
    commands = tile_layout(make_windows(3), MasterSide.LEFT, WS)
    assert argv_strings(commands) == [
        "layout h_tiles --window-id 10",
        "join-with left --window-id 12",
        "layout v_tiles --window-id 11",
        "balance-sizes --workspace 3",
    ]


def test_master_extent_emits_single_absolute_width_resize_not_smart_nudges():
    commands = tile_layout(make_windows(3), MasterSide.LEFT, WS, master_extent=960)
    strings = argv_strings(commands)
    assert strings == [
        "layout h_tiles --window-id 10",
        "join-with left --window-id 12",
        "layout v_tiles --window-id 11",
        "balance-sizes --workspace 3",
        "resize width 960 --window-id 10",
    ]
    assert not any("resize smart" in s for s in strings)


def test_master_extent_resizes_height_for_horizontal_master():
    commands = tile_layout(make_windows(3), MasterSide.BOTTOM, WS, master_extent=540)
    assert argv_strings(commands)[-1] == "resize height 540 --window-id 10"


def test_single_window_emits_no_joins_and_no_resize():
    commands = tile_layout(make_windows(1), MasterSide.LEFT, WS, master_extent=960)
    strings = argv_strings(commands)
    assert strings == ["layout h_tiles --window-id 10"]
    assert not any("join-with" in s or "resize" in s for s in strings)


def test_two_windows_no_join_no_stack_reorient():
    commands = tile_layout(make_windows(2), MasterSide.LEFT, WS, master_extent=960)
    assert argv_strings(commands) == [
        "layout h_tiles --window-id 10",
        "balance-sizes --workspace 3",
        "resize width 960 --window-id 10",
    ]


def test_five_windows_joins_all_stack_windows_towards_anchor():
    commands = tile_layout(make_windows(5), MasterSide.LEFT, WS)
    assert argv_strings(commands) == [
        "layout h_tiles --window-id 10",
        "join-with left --window-id 12",
        "join-with left --window-id 13",
        "join-with left --window-id 14",
        "layout v_tiles --window-id 11",
        "balance-sizes --workspace 3",
    ]


def test_master_right_relocates_master_after_stack():
    commands = tile_layout(make_windows(3), MasterSide.RIGHT, WS)
    assert argv_strings(commands) == [
        "layout h_tiles --window-id 10",
        "join-with left --window-id 12",
        "layout v_tiles --window-id 11",
        "move right --window-id 10",
        "balance-sizes --workspace 3",
    ]


def test_master_bottom_uses_vertical_root_and_up_joins_and_moves_down():
    commands = tile_layout(make_windows(3), MasterSide.BOTTOM, WS)
    assert argv_strings(commands) == [
        "layout v_tiles --window-id 10",
        "join-with up --window-id 12",
        "layout h_tiles --window-id 11",
        "move down --window-id 10",
        "balance-sizes --workspace 3",
    ]


def test_master_top_uses_vertical_root_no_relocate():
    commands = tile_layout(make_windows(3), MasterSide.TOP, WS)
    assert argv_strings(commands) == [
        "layout v_tiles --window-id 10",
        "join-with up --window-id 12",
        "layout h_tiles --window-id 11",
        "balance-sizes --workspace 3",
    ]


def test_layout_commands_tolerate_nonzero_but_joins_and_resizes_do_not():
    commands = tile_layout(make_windows(3), MasterSide.LEFT, WS, master_extent=960)
    by_head = {cmd.args[0]: cmd.tolerate_nonzero for cmd in commands}
    assert by_head["layout"] is True
    assert by_head["join-with"] is False
    assert by_head["resize"] is False


@pytest.mark.parametrize("side", list(MasterSide))
@given(n=st.integers(min_value=1, max_value=8))
def test_join_count_is_n_minus_two_and_never_targets_master(side: MasterSide, n: int):
    windows = make_windows(n)
    master_id = windows[0].window_id
    commands = tile_layout(windows, side, WS)
    joins = [cmd for cmd in commands if cmd.args[0] == "join-with"]
    assert len(joins) == max(0, n - 2)
    assert all(cmd.window_id != master_id for cmd in joins)


@pytest.mark.parametrize("side", list(MasterSide))
@given(n=st.integers(min_value=1, max_value=8))
def test_joins_cover_post_anchor_windows_exactly_once(side: MasterSide, n: int):
    # The only per-window placement is joining each window after the anchor into the
    # stack, exactly once (no window joined twice); the master and anchor are never joined.
    windows = make_windows(n)
    commands = tile_layout(windows, side, WS)
    joined = [cmd.window_id for cmd in commands if cmd.args[0] == "join-with"]
    expected = [w.window_id for w in windows[2:]]
    assert joined == expected
    assert len(joined) == len(set(joined))
