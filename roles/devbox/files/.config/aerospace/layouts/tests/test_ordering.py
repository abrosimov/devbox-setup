from __future__ import annotations

from aerospace_layouts.aerospace import AerospaceClient
from aerospace_layouts.cli import apply_layout, focused_windows
from aerospace_layouts.ordering import (
    DfsProbeOrdering,
    IdentityOrdering,
    dfs_index_map,
    order_by_dfs_map,
)
from aerospace_layouts.planner import plan_layout

from .conftest import FakeWm, make_windows


def test_identity_preserves_order():
    windows = make_windows(3)
    assert IdentityOrdering().order(windows) == windows


def test_dfs_index_map_probes_every_index_in_order():
    dfs_by_index = {0: 12, 1: 10, 2: 11}
    assert dfs_index_map(lambda i: dfs_by_index[i], 3) == [(0, 12), (1, 10), (2, 11)]


def test_order_by_dfs_map_orders_and_drops_missing_ids():
    windows = make_windows(3)  # ids 10, 11, 12
    dfs_map: list[tuple[int, int | None]] = [(0, 12), (1, 99), (2, 10)]  # 99 not in the set
    assert [w.window_id for w in order_by_dfs_map(windows, dfs_map)] == [12, 10]


def test_dfs_probe_reorders_by_resolved_index():
    windows = make_windows(3)  # ids 10, 11, 12
    dfs_by_index = {0: 12, 1: 10, 2: 11}
    ordering = DfsProbeOrdering(resolve_dfs_index=lambda i: dfs_by_index[i])
    ordered_ids = [w.window_id for w in ordering.order(windows)]
    assert ordered_ids == [12, 10, 11]


def test_dfs_probe_skips_unknown_ids():
    windows = make_windows(2)  # ids 10, 11
    ordering = DfsProbeOrdering(resolve_dfs_index=lambda i: {0: 99, 1: 10}[i])
    ordered_ids = [w.window_id for w in ordering.order(windows)]
    assert ordered_ids == [10]


def test_scrambled_array_order_tile_targets_true_dfs_windows():
    # Regression for the live smoke failure: list-windows array order != dfs. The visually
    # leftmost window (dfs-0) must be the master and never a join target -- it has no left
    # neighbour, which is exactly the "No windows in the specified direction" error.
    dfs = [1779, 2000, 2001]
    array = [2000, 1779, 2001]
    client = AerospaceClient(FakeWm(dfs_ids=dfs, array_ids=array, focused=2000))
    orderer = DfsProbeOrdering(resolve_dfs_index=client.focus_dfs_index)

    windows = orderer.order(client.list_windows("3"))
    assert [w.window_id for w in windows] == dfs

    joins = [c for c in plan_layout("tile", windows, "3") if c.args[0] == "join-with"]
    assert [c.window_id for c in joins] == [2001]
    assert all(c.window_id != 1779 for c in joins)


def test_focused_windows_restores_focus_after_probing():
    wm = FakeWm(dfs_ids=[10, 11, 12], array_ids=[12, 10, 11], focused=11)
    client = AerospaceClient(wm)
    orderer = DfsProbeOrdering(resolve_dfs_index=client.focus_dfs_index)

    focused, windows = focused_windows(client, orderer, "3")
    assert focused == 11
    assert wm.focused == 11
    assert [w.window_id for w in windows] == [10, 11, 12]


def test_apply_layout_orders_against_post_flatten_tree_not_stale_pre_flatten():
    # Regression for the second live failure: the dfs probe ran on the stale pre-flatten
    # tree. There 163 sits last (a stack slot, so it would be joined -- the reported
    # "join-with left --window-id 163" error), but after flatten 163 is the true leftmost
    # (dfs-0). apply_layout must flatten FIRST, then probe, so 163 becomes the master and is
    # never a join target.
    wm = FakeWm(
        dfs_ids=[2000, 2001, 163],
        post_flatten_dfs=[163, 2000, 2001],
        array_ids=[2000, 2001, 163],
        focused=163,
    )
    client = AerospaceClient(wm)

    apply_layout(client, "tile", "3")

    assert wm.mutations[0][:1] == ["flatten-workspace-tree"]
    assert wm.joined_ids() == ["2001"]
    assert "163" not in wm.joined_ids()
