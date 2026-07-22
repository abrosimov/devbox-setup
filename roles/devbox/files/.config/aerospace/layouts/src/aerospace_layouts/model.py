from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

FLOATING_LAYOUT: Final = "floating"


@dataclass(frozen=True)
class Window:
    window_id: int
    app_name: str
    window_title: str
    # `%{window-parent-container-layout}` from list-windows: "floating" means the window is
    # NOT in the tiling tree (join-with has no neighbour for it). None when not probed.
    parent_layout: str | None = None


def floating_windows(windows: list[Window]) -> list[Window]:
    return [w for w in windows if w.parent_layout == FLOATING_LAYOUT]


def tiled_windows(windows: list[Window]) -> list[Window]:
    # awesome skips floating clients in tile/fair/max; they stay floating above the tiled
    # area. Excluding them keeps join-with/resize/layout off windows with no tiling neighbour.
    return [w for w in windows if w.parent_layout != FLOATING_LAYOUT]


@dataclass(frozen=True)
class Command:
    args: tuple[str, ...]
    window_id: int | None = None
    # `layout` exits non-zero when the requested layout is already in effect (a no-op).
    # Such commands set this so the executor treats the non-zero exit as "already there".
    tolerate_nonzero: bool = False

    def to_argv(self) -> list[str]:
        argv = list(self.args)
        if self.window_id is not None:
            argv += ["--window-id", str(self.window_id)]
        return argv


class MasterSide(Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


def flatten(workspace: str) -> Command:
    return Command(("flatten-workspace-tree", "--workspace", workspace))


def set_layout(mode: str, window_id: int) -> Command:
    return Command(("layout", mode), window_id=window_id, tolerate_nonzero=True)


def float_window(window_id: int) -> Command:
    return Command(("layout", "floating"), window_id=window_id, tolerate_nonzero=True)


def join_with(direction: str, window_id: int) -> Command:
    return Command(("join-with", direction), window_id=window_id)


def move(direction: str, window_id: int) -> Command:
    return Command(("move", direction), window_id=window_id)


def swap(direction: str, window_id: int) -> Command:
    return Command(("swap", direction), window_id=window_id)


def balance_sizes(workspace: str) -> Command:
    return Command(("balance-sizes", "--workspace", workspace))


def resize_smart(delta: int, window_id: int) -> Command:
    return Command(("resize", "smart", f"{delta:+d}"), window_id=window_id)


def resize_to(axis: str, extent: int, window_id: int) -> Command:
    return Command(("resize", axis, str(extent)), window_id=window_id)
