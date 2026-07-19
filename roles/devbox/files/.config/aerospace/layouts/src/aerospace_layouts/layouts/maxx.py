from __future__ import annotations

from aerospace_layouts.model import Command, Window, set_layout


def max_layout(windows: list[Window]) -> list[Command]:
    # Approximation of awesome's `max` (monocle). AeroSpace has no "only the focused
    # window is visible" mode; v_accordion collapses the siblings into a stacked
    # accordion where the focused one expands, which is the closest native behaviour.
    # Precondition: the CLI has already flattened the workspace.
    if not windows:
        return []
    return [set_layout("v_accordion", windows[0].window_id)]
