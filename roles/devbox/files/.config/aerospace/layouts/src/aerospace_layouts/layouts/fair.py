from __future__ import annotations

from aerospace_layouts.model import (
    Command,
    Window,
    balance_sizes,
    join_with,
    set_layout,
)


def fair_layout(windows: list[Window], workspace: str) -> list[Command]:
    # Balanced two-column split: left = windows[:k], right = windows[k:], odd extra goes LEFT.
    # Precondition: the CLI has already flattened the workspace and probed the dfs order; this
    # emits only the post-flatten arrange sequence. The merge-vs-nest join-with behaviour is the
    # SAME as tile (each stack window joins towards its column anchor) and must be live-verified
    # -- see tests/test_live_smoke.py and layouts/tile.py.
    if not windows:
        return []
    n = len(windows)
    commands: list[Command] = [set_layout("h_tiles", windows[0].window_id)]
    if n < 2:
        return commands

    k = (n + 1) // 2
    left = windows[:k]
    right = windows[k:]

    for window in left[1:]:
        commands.append(join_with("left", window.window_id))
    if len(left) >= 2:
        commands.append(set_layout("v_tiles", left[0].window_id))

    for window in right[1:]:
        commands.append(join_with("left", window.window_id))
    if len(right) >= 2:
        commands.append(set_layout("v_tiles", right[0].window_id))

    commands.append(balance_sizes(workspace))
    return commands
