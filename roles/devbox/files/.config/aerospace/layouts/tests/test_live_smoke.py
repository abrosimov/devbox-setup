from __future__ import annotations

import os

import pytest

from aerospace_layouts.aerospace import AerospaceClient, subprocess_runner
from aerospace_layouts.cli import apply_layout

LIVE = os.environ.get("AEROSPACE_LAYOUTS_LIVE") == "1"

pytestmark = pytest.mark.skipif(
    not LIVE, reason="set AEROSPACE_LAYOUTS_LIVE=1 to run against the real WM"
)


@pytest.mark.live
def test_tile_master_left_builds_master_plus_stack():
    """Drive the real AeroSpace WM and verify the tile master+stack tree by eye.

    HOW TO RUN (from a normal terminal, AeroSpace running):
        1. Open exactly THREE windows on one workspace (e.g. a browser + two
           terminals). `apply_layout` flattens FIRST, then probes the post-flatten
           left-to-right order, so the master is the true leftmost window.
        2. Focus that workspace, then run:
               AEROSPACE_LAYOUTS_LIVE=1 uv run pytest -m live -s
        3. WATCH THE SCREEN as the commands run.

    WHAT TO OBSERVE (this is what the test cannot assert -- you confirm it):
        - The master window occupies a single full-height column on the LEFT.
        - The other two windows form ONE vertical stack on the RIGHT (top/bottom),
          NOT a further-nested pair and NOT a horizontal row.
        - The master occupies ~50% of the monitor width (Design A absolute resize);
          the tile gap is not subtracted, so accept a small deviation from an exact half.

    IF THE STACK IS WRONG, this pins the exact `join-with` semantics to fix in
    layouts/tile.py:
        - If the second stack window ended up nested INSIDE a sub-container with
          the first (i.e. `[master, [w1, [w2]]]` rather than `[master, [w1,w2]]`),
          then `join-with left` on w2 did not merge into w1's container as assumed
          -- adjust the anchor/direction so all stack windows share one parent.
        - If `join-with` failed with "No windows in the specified direction", the
          join axis did not match the window's position -- flip cfg.join_dir.
        - If the whole workspace flipped orientation, the root-orientation `layout`
          call targeted the wrong container -- it must hit the root (master at
          dfs-index 0), not the stack.

    FAIR (`apply fair`): with four+ windows, observe TWO vertical columns of roughly
    equal width, the odd window (odd count) landing in the LEFT column. The join-with
    merge-vs-nest semantics are identical to tile: each column's non-anchor windows must
    share ONE parent container, not nest pairwise.

    ADDITIONAL LIVE CHECKS (require AeroSpace >= 0.21, eval-batched mutations):
        (a) Cycle tile <-> fair (and around the cycle). Each step should feel near-instant
            with NO intermediate flash -- the whole arrange sequence is one double-buffered
            `aerospace eval`, not a visible series of joins/resizes.
        (b) After `apply tile`, the master lands at ~50% of the monitor width (Design A).
        (c) `promote` a stack window: it pulls onto the master half AND takes the ~50%
            proportion in one gesture. `demote` the master: the new master takes ~50%.
        (d) The eval batch applies atomically -- you never see a half-built tree between
            the flatten and the final arranged layout.
    """
    client = AerospaceClient(subprocess_runner(os.environ.get("AEROSPACE_BIN", "aerospace")))
    workspace = client.focused_workspace()
    if len(client.list_windows(workspace)) < 3:
        pytest.skip("open at least three windows on the focused workspace first")

    apply_layout(client, "tile", workspace)
