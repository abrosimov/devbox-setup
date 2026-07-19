from __future__ import annotations

from aerospace_layouts.model import Command, Window, floating_windows, tiled_windows


def format_window_line(window: Window) -> str:
    layout = window.parent_layout or "?"
    return (
        f"id={window.window_id} layout={layout} "
        f"app={window.app_name!r} title={window.window_title!r}"
    )


def format_dfs_map(dfs_map: list[tuple[int, int | None]]) -> list[str]:
    return [f"dfs[{index}] -> {'<none>' if wid is None else wid}" for index, wid in dfs_map]


def format_commands(commands: list[Command]) -> list[str]:
    return [" ".join(command.to_argv()) for command in commands]


def format_diagnosis(
    raw_windows: list[Window],
    dfs_map: list[tuple[int, int | None]],
    ordered: list[Window],
    commands: list[Command],
) -> list[str]:
    lines = [f"windows on workspace: {len(raw_windows)}"]
    lines += [f"  {format_window_line(w)}" for w in raw_windows]

    floating = floating_windows(raw_windows)
    if floating:
        ids = ", ".join(str(w.window_id) for w in floating)
        lines.append(f"WARNING: {len(floating)} floating window(s) NOT in the tiling tree: {ids}")

    lines.append("dfs-index -> window-id (post-flatten):")
    lines += [f"  {line}" for line in format_dfs_map(dfs_map)]

    lines.append("probed order: " + ", ".join(str(w.window_id) for w in ordered))
    tiled = tiled_windows(ordered)
    lines.append("tiling set (floating excluded, master first): " + _ids(tiled))
    lines.append("planned commands (NOT executed):")
    lines += [f"  {line}" for line in format_commands(commands)]
    return lines


def _ids(windows: list[Window]) -> str:
    return ", ".join(str(w.window_id) for w in windows) or "<none>"
