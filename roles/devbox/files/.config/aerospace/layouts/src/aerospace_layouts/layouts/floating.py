from __future__ import annotations

from aerospace_layouts.model import Command, Window, float_window


def floating_layout(windows: list[Window]) -> list[Command]:
    return [float_window(window.window_id) for window in windows]
