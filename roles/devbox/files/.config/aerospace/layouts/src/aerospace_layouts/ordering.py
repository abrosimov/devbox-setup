from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from aerospace_layouts.model import Window


class WindowOrderer(Protocol):
    def order(self, windows: list[Window]) -> list[Window]: ...


def dfs_index_map(
    resolve_dfs_index: Callable[[int], int | None], count: int
) -> list[tuple[int, int | None]]:
    return [(index, resolve_dfs_index(index)) for index in range(count)]


def order_by_dfs_map(windows: list[Window], dfs_map: list[tuple[int, int | None]]) -> list[Window]:
    by_id = {window.window_id: window for window in windows}
    return [by_id[wid] for _, wid in dfs_map if wid is not None and wid in by_id]


class IdentityOrdering:
    # Trust the order `aerospace list-windows --json` returns. NOT dfs/visual order on the
    # probed CLI (that array is unsorted), so unsafe as the default -- kept only for tests
    # and for a future CLI that guarantees dfs array order.
    def order(self, windows: list[Window]) -> list[Window]:
        return list(windows)


@dataclass(frozen=True)
class DfsProbeOrdering:
    # Default strategy: the list-windows array is not dfs/visual order, so resolve each dfs
    # position to a window-id via `focus --dfs-index i` (the resolver captures the focused
    # id). Position 0 is then the true master and stack windows have the neighbours the
    # join sequence assumes.
    resolve_dfs_index: Callable[[int], int | None]

    def order(self, windows: list[Window]) -> list[Window]:
        return order_by_dfs_map(windows, dfs_index_map(self.resolve_dfs_index, len(windows)))
