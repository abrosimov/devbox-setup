from __future__ import annotations

from typing import Final

from aerospace_layouts.layouts import (
    columns_layout,
    fair_layout,
    floating_layout,
    max_layout,
    tile_layout,
)
from aerospace_layouts.model import (
    Command,
    MasterSide,
    Window,
    resize_smart,
    swap,
    tiled_windows,
)
from aerospace_layouts.state import State, get_index, set_index

# Single source of truth for the cycle order. Edit this list to change what the
# `cycle` keybinding steps through.
CYCLE: Final[tuple[str, ...]] = (
    "floating",
    "tile",
    "tile.left",
    "tile.top",
    "tile.bottom",
    "fair",
    "max",
    "columns",
)

# awesome-wm names its tile variants by the side the STACK occupies, not the master:
# `tile` (== tile.right) is master-LEFT/stack-RIGHT, `tile.left` mirrors it (master-RIGHT),
# `tile.bottom` is master-TOP/stack-BOTTOM, `tile.top` is master-BOTTOM/stack-TOP. Keeping
# those names and translating to the master side reproduces awesome muscle memory and gives
# all four distinct master sides across the four names. Flip a value here to make a name
# refer to the master side instead.
_TILE_MASTER_SIDE: Final[dict[str, MasterSide]] = {
    "tile": MasterSide.LEFT,
    "tile.left": MasterSide.RIGHT,
    "tile.top": MasterSide.BOTTOM,
    "tile.bottom": MasterSide.TOP,
}

ADJUST_MASTER_STEP: Final = 50

# Layouts that rebuild the tree from a flat state. The CLI must execute
# `flatten-workspace-tree` and re-probe the dfs order BEFORE building these, so the join
# sequence operates on the real post-flatten row. `floating` reflows nothing, so it is
# excluded.
FLATTENING_LAYOUTS: Final[frozenset[str]] = frozenset(
    {*_TILE_MASTER_SIDE, "fair", "max", "columns"}
)


class UnknownLayoutError(ValueError):
    pass


def layout_names() -> tuple[str, ...]:
    return (*_TILE_MASTER_SIDE.keys(), "floating", "fair", "max", "columns")


def plan_layout(name: str, windows: list[Window], workspace: str) -> list[Command]:
    side = _TILE_MASTER_SIDE.get(name)
    if side is not None:
        return tile_layout(tiled_windows(windows), side, workspace)
    if name == "floating":
        return floating_layout(windows)
    if name == "fair":
        return fair_layout(tiled_windows(windows), workspace)
    if name == "max":
        return max_layout(tiled_windows(windows))
    if name == "columns":
        return columns_layout(tiled_windows(windows), workspace)
    raise UnknownLayoutError(name)


def plan_promote(windows: list[Window], focused_id: int | None) -> list[Command]:
    if focused_id is None:
        return []
    index = next((i for i, w in enumerate(windows) if w.window_id == focused_id), None)
    if index is None or index == 0:
        return []
    # Bubble the focused window to dfs-index 0 (master) one neighbour at a time.
    return [swap("dfs-prev", focused_id) for _ in range(index)]


def plan_demote(windows: list[Window], focused_id: int | None) -> list[Command]:
    if focused_id is None:
        return []
    index = next((i for i, w in enumerate(windows) if w.window_id == focused_id), None)
    if index is None or index == len(windows) - 1:
        return []
    # Bubble the focused window to the last dfs slot one neighbour at a time.
    return [swap("dfs-next", focused_id) for _ in range(len(windows) - 1 - index)]


def plan_adjust_master(
    windows: list[Window], grow: bool, step: int = ADJUST_MASTER_STEP
) -> list[Command]:
    if not windows:
        return []
    delta = step if grow else -step
    return [resize_smart(delta, windows[0].window_id)]


def advance_index(state: State, workspace: str, *, reverse: bool = False) -> int:
    current = get_index(state, workspace)
    step = -1 if reverse else 1
    nxt = (current + step) % len(CYCLE)
    set_index(state, workspace, nxt)
    return nxt


def record_layout_name(state: State, workspace: str, name: str) -> None:
    if name in CYCLE:
        set_index(state, workspace, CYCLE.index(name))
