from __future__ import annotations

from dataclasses import dataclass

from aerospace_layouts.model import (
    Command,
    MasterSide,
    Window,
    balance_sizes,
    join_with,
    move,
    resize_smart,
    set_layout,
)

MASTER_WIDEN_STEP = 50
MASTER_WIDEN_STEPS = 2


@dataclass(frozen=True)
class _SideConfig:
    root_mode: str
    stack_mode: str
    join_dir: str
    relocate_dir: str | None


# Drives tile_layout. Precondition: `windows` is the post-flatten dfs order (the CLI
# flattens live, then probes order, before calling this). Force the root to `root_mode`,
# collapse the non-master windows into one `stack_mode` container by joining each towards
# the anchor along `join_dir`, then (RIGHT/BOTTOM only) relocate the master past the stack
# via `relocate_dir`. Reasserting the stack orientation makes the result independent of the
# monitor's default. See README "How the tile master+stack tree is built" for the rationale.
_CONFIG: dict[MasterSide, _SideConfig] = {
    MasterSide.LEFT: _SideConfig("h_tiles", "v_tiles", "left", None),
    MasterSide.RIGHT: _SideConfig("h_tiles", "v_tiles", "left", "right"),
    MasterSide.TOP: _SideConfig("v_tiles", "h_tiles", "up", None),
    MasterSide.BOTTOM: _SideConfig("v_tiles", "h_tiles", "up", "down"),
}


def tile_layout(
    windows: list[Window],
    master_side: MasterSide,
    workspace: str,
    widen_steps: int = MASTER_WIDEN_STEPS,
    widen_step: int = MASTER_WIDEN_STEP,
) -> list[Command]:
    if not windows:
        return []
    cfg = _CONFIG[master_side]
    master = windows[0]
    commands: list[Command] = [set_layout(cfg.root_mode, master.window_id)]

    stack = windows[1:]
    # Join each post-anchor window towards the anchor along the current axis: a neighbour
    # always exists there (join-with requires one) and the anchor is never joined, so the
    # master is never pulled into the stack.
    for window in stack[1:]:
        commands.append(join_with(cfg.join_dir, window.window_id))

    if len(stack) >= 2:
        commands.append(set_layout(cfg.stack_mode, stack[0].window_id))

    if len(windows) < 2:
        return commands

    if cfg.relocate_dir is not None:
        commands.append(move(cfg.relocate_dir, master.window_id))

    commands.append(balance_sizes(workspace))
    # Design R: after balancing, nudge the master larger by a fixed number of relative
    # steps. There is no percentage/points primitive in AeroSpace, so this is approximate.
    commands.extend(resize_smart(widen_step, master.window_id) for _ in range(widen_steps))
    return commands
