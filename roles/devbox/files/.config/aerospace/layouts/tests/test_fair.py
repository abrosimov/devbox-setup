from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from aerospace_layouts.layouts.fair import fair_layout

from .conftest import argv_strings, make_windows

WS = "3"


def test_four_windows_splits_into_two_vertical_columns():
    commands = fair_layout(make_windows(4), WS)
    assert argv_strings(commands) == [
        "layout h_tiles --window-id 10",
        "join-with left --window-id 11",
        "layout v_tiles --window-id 10",
        "join-with left --window-id 13",
        "layout v_tiles --window-id 12",
        "balance-sizes --workspace 3",
    ]


def test_five_windows_puts_odd_extra_in_left_column():
    commands = fair_layout(make_windows(5), WS)
    assert argv_strings(commands) == [
        "layout h_tiles --window-id 10",
        "join-with left --window-id 11",
        "join-with left --window-id 12",
        "layout v_tiles --window-id 10",
        "join-with left --window-id 14",
        "layout v_tiles --window-id 13",
        "balance-sizes --workspace 3",
    ]


def test_single_window_emits_only_root_force():
    commands = fair_layout(make_windows(1), WS)
    strings = argv_strings(commands)
    assert strings == ["layout h_tiles --window-id 10"]
    assert not any("join-with" in s for s in strings)


def test_two_windows_emit_root_force_and_balance_with_no_joins():
    commands = fair_layout(make_windows(2), WS)
    strings = argv_strings(commands)
    assert strings == [
        "layout h_tiles --window-id 10",
        "balance-sizes --workspace 3",
    ]
    assert not any("join-with" in s for s in strings)


def test_layout_commands_tolerate_nonzero_but_joins_do_not():
    commands = fair_layout(make_windows(4), WS)
    by_head = {cmd.args[0]: cmd.tolerate_nonzero for cmd in commands}
    assert by_head["layout"] is True
    assert by_head["join-with"] is False


@given(n=st.integers(min_value=1, max_value=8))
def test_join_count_is_n_minus_two_and_never_targets_a_column_anchor(n: int):
    windows = make_windows(n)
    k = (n + 1) // 2
    anchor_ids = {windows[0].window_id, windows[k].window_id} if k < n else {windows[0].window_id}
    commands = fair_layout(windows, WS)
    joins = [cmd for cmd in commands if cmd.args[0] == "join-with"]
    assert len(joins) == max(0, n - 2)
    assert all(cmd.window_id not in anchor_ids for cmd in joins)
