from __future__ import annotations

from aerospace_layouts.model import Command, Window, balance_sizes, set_layout


def columns_layout(windows: list[Window], workspace: str) -> list[Command]:
    # Even horizontal row, zero nesting -- the robust fallback layout.
    # Precondition: the CLI has already flattened the workspace.
    if not windows:
        return []
    return [set_layout("h_tiles", windows[0].window_id), balance_sizes(workspace)]
