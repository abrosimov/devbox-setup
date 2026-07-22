from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aerospace_layouts.model import MasterSide
from aerospace_layouts.planner import (
    CYCLE,
    FLATTENING_LAYOUTS,
    ORDER_SENSITIVE_LAYOUTS,
    UnknownLayoutError,
    advance_index,
    current_layout,
    layout_names,
    plan_adjust_master,
    plan_demote,
    plan_layout,
    plan_promote,
    record_layout_name,
)
from aerospace_layouts.state import State, get_index, load_state, save_state, set_index

from .conftest import argv_strings, make_windows

WS = "3"


def test_cycle_is_the_master_stack_layouts_without_columns_fair_floating():
    assert CYCLE == (
        "tile",
        "tile.left",
        "tile.top",
        "tile.bottom",
        "max",
    )
    for excluded in ("columns", "fair", "floating"):
        assert excluded not in CYCLE


def test_columns_and_fair_stay_apply_targets_outside_the_cycle():
    assert {"columns", "fair"} <= set(layout_names())
    assert plan_layout("columns", make_windows(3), WS)
    assert plan_layout("fair", make_windows(3), WS)


def test_floating_stays_a_named_apply_target_outside_the_cycle():
    assert "floating" in layout_names()
    assert argv_strings(plan_layout("floating", make_windows(3), WS)) == [
        "layout floating --window-id 10",
        "layout floating --window-id 11",
        "layout floating --window-id 12",
    ]


def test_current_layout_clamps_stale_out_of_range_index():
    stored = len(CYCLE) + 3
    state = State({WS: stored})
    name = current_layout(state, WS)
    assert name == CYCLE[stored % len(CYCLE)]
    assert name in layout_names()


def test_advance_wraps_modulo_cycle_length():
    state = State()
    seen = [advance_index(state, WS) for _ in range(len(CYCLE) + 1)]
    assert seen[: len(CYCLE)] == [*range(1, len(CYCLE)), 0]
    assert seen[len(CYCLE)] == 1


def test_advance_reverse_wraps_to_last():
    state = State()
    assert advance_index(state, WS, reverse=True) == len(CYCLE) - 1


def test_missing_workspace_defaults_to_index_zero_then_advances_to_one():
    state = State()
    assert get_index(state, "brand-new") == 0
    assert advance_index(state, "brand-new") == 1


def test_record_layout_name_sets_index_to_cycle_position():
    state = State()
    record_layout_name(state, WS, "tile.top")
    assert get_index(state, WS) == CYCLE.index("tile.top")


def test_record_out_of_cycle_name_leaves_index_untouched():
    state = State()
    set_index(state, WS, 2)
    record_layout_name(state, WS, "columns")
    assert get_index(state, WS) == 2


def test_record_unknown_name_leaves_index_untouched():
    state = State()
    set_index(state, WS, 4)
    record_layout_name(state, WS, "not-a-layout")
    assert get_index(state, WS) == 4


@given(n=st.integers(min_value=0, max_value=6))
def test_advance_is_always_in_range(n: int):
    state = State()
    for _ in range(n):
        idx = advance_index(state, WS)
        assert 0 <= idx < len(CYCLE)


def test_load_missing_file_returns_empty_state(tmp_path: Path):
    assert load_state(tmp_path / "absent.json") == State()


def test_load_corrupt_file_returns_empty_state(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text("{ not json", encoding="utf-8")
    assert load_state(path) == State()


def test_save_then_load_round_trips(tmp_path: Path):
    path = tmp_path / "nested" / "state.json"
    state = State({"1": 2, "work": 5})
    save_state(path, state)
    assert load_state(path) == state


def test_save_is_atomic_and_leaves_no_temp_file(tmp_path: Path):
    path = tmp_path / "state.json"
    save_state(path, State({"1": 1}))
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == {"workspaces": {"1": {"layout_index": 1}}}
    assert list(tmp_path.iterdir()) == [path]


def test_order_sensitive_layouts_are_the_tile_family_and_fair():
    expected = frozenset({"tile", "tile.left", "tile.top", "tile.bottom", "fair"})
    assert expected == ORDER_SENSITIVE_LAYOUTS


def test_order_sensitive_is_subset_of_flattening():
    assert ORDER_SENSITIVE_LAYOUTS <= FLATTENING_LAYOUTS


def test_max_and_columns_flatten_but_are_order_agnostic():
    assert {"max", "columns"} <= FLATTENING_LAYOUTS
    assert "max" not in ORDER_SENSITIVE_LAYOUTS
    assert "columns" not in ORDER_SENSITIVE_LAYOUTS


def test_plan_layout_unknown_name_raises():
    with pytest.raises(UnknownLayoutError):
        plan_layout("nope", make_windows(2), WS)


def test_plan_promote_bubbles_focused_to_master():
    windows = make_windows(4)
    focused = windows[3].window_id
    commands = plan_promote(windows, focused)
    assert argv_strings(commands) == [f"swap dfs-prev --window-id {focused}"] * 3


def test_plan_promote_focused_already_master_is_noop():
    windows = make_windows(4)
    assert plan_promote(windows, windows[0].window_id) == []


def test_plan_promote_no_focus_is_noop():
    assert plan_promote(make_windows(4), None) == []


def test_plan_demote_bubbles_master_to_tail():
    windows = make_windows(4)
    focused = windows[0].window_id
    commands = plan_demote(windows, focused)
    assert argv_strings(commands) == [f"swap dfs-next --window-id {focused}"] * 3


def test_plan_demote_focused_already_last_is_noop():
    windows = make_windows(4)
    assert plan_demote(windows, windows[-1].window_id) == []


def test_plan_demote_no_focus_is_noop():
    assert plan_demote(make_windows(4), None) == []


def test_plan_demote_from_middle_bubbles_remaining_distance():
    windows = make_windows(5)
    focused = windows[1].window_id
    commands = plan_demote(windows, focused)
    assert argv_strings(commands) == [f"swap dfs-next --window-id {focused}"] * 3


def test_plan_promote_appends_absolute_master_resize_on_promoted_window():
    windows = make_windows(4)
    focused = windows[3].window_id
    commands = plan_promote(windows, focused, master_extent=960, master_side=MasterSide.LEFT)
    assert argv_strings(commands) == [
        *([f"swap dfs-prev --window-id {focused}"] * 3),
        f"resize width 960 --window-id {focused}",
    ]


def test_plan_promote_without_extent_emits_no_resize():
    windows = make_windows(4)
    focused = windows[3].window_id
    assert (
        argv_strings(plan_promote(windows, focused)) == [f"swap dfs-prev --window-id {focused}"] * 3
    )


def test_plan_demote_reasserts_size_on_new_master_when_old_master_demoted():
    windows = make_windows(4)
    focused = windows[0].window_id
    commands = plan_demote(windows, focused, master_extent=540, master_side=MasterSide.BOTTOM)
    new_master = windows[1].window_id
    assert argv_strings(commands) == [
        *([f"swap dfs-next --window-id {focused}"] * 3),
        f"resize height 540 --window-id {new_master}",
    ]


def test_plan_demote_reasserts_size_on_untouched_master_when_stack_window_demoted():
    windows = make_windows(4)
    focused = windows[1].window_id
    commands = plan_demote(windows, focused, master_extent=960, master_side=MasterSide.LEFT)
    assert argv_strings(commands)[-1] == f"resize width 960 --window-id {windows[0].window_id}"


def test_plan_adjust_master_grows_and_shrinks_master():
    windows = make_windows(3)
    assert argv_strings(plan_adjust_master(windows, grow=True, step=50)) == [
        "resize smart +50 --window-id 10",
    ]
    assert argv_strings(plan_adjust_master(windows, grow=False, step=50)) == [
        "resize smart -50 --window-id 10",
    ]


def test_plan_adjust_master_empty_is_noop():
    assert plan_adjust_master([], grow=True) == []
