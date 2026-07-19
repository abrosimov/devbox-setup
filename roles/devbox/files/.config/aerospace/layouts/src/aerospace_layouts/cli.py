from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from aerospace_layouts.aerospace import AerospaceClient, AerospaceError, subprocess_runner
from aerospace_layouts.diagnostics import (
    format_commands,
    format_dfs_map,
    format_diagnosis,
    format_window_line,
)
from aerospace_layouts.executor import run_commands
from aerospace_layouts.model import Command, Window, flatten, floating_windows
from aerospace_layouts.ordering import (
    DfsProbeOrdering,
    WindowOrderer,
    dfs_index_map,
    order_by_dfs_map,
)
from aerospace_layouts.planner import (
    CYCLE,
    FLATTENING_LAYOUTS,
    advance_index,
    layout_names,
    plan_adjust_master,
    plan_demote,
    plan_layout,
    plan_promote,
    record_layout_name,
)
from aerospace_layouts.state import default_state_path, get_index, load_state, save_state

logger = logging.getLogger("aerospace_layouts")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aerospace-layouts", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    cycle = sub.add_parser("cycle", help="advance to the next layout in the cycle and apply it")
    cycle.add_argument("--reverse", action="store_true", help="step to the previous layout")

    apply_p = sub.add_parser("apply", help="apply a named layout")
    apply_p.add_argument("name", choices=sorted(layout_names()))

    sub.add_parser("reapply", help="re-apply the current stored layout without advancing")

    adjust = sub.add_parser("adjust-master", help="nudge the master size larger (+) or smaller (-)")
    adjust.add_argument("direction", choices=["+", "-"])

    sub.add_parser("promote", help="swap the focused window into the master slot (dfs-index 0)")

    sub.add_parser(
        "demote",
        help="swap the focused window toward the tail of the stack (inverse of promote)",
    )

    diag = sub.add_parser(
        "diagnose",
        help="print what the tool sees (windows, dfs order, planned commands); executes no joins",
    )
    diag.add_argument("name", nargs="?", default="tile", choices=sorted(layout_names()))
    return parser


def _make_client() -> AerospaceClient:
    return AerospaceClient(subprocess_runner(os.environ.get("AEROSPACE_BIN", "aerospace")))


def _log_windows(workspace: str, windows: list[Window]) -> None:
    logger.info("workspace %s has %d window(s):", workspace, len(windows))
    for window in windows:
        logger.info("  %s", format_window_line(window))
    floating = floating_windows(windows)
    if floating:
        ids = ", ".join(str(w.window_id) for w in floating)
        logger.warning("%d floating window(s) NOT in the tiling tree: %s", len(floating), ids)


def _flatten_and_probe(
    client: AerospaceClient, workspace: str
) -> tuple[list[tuple[int, int | None]], list[Window]]:
    # Flatten MUST execute before the dfs probe: it linearises the tree, so the window->slot
    # order the join sequence assumes is only valid when read from the flattened tree. Capture
    # focus first and restore it after probing so the keybinding does not displace focus.
    focused = client.focused_window_id()
    client.execute(flatten(workspace))
    windows = client.list_windows(workspace)
    dfs_map = dfs_index_map(client.focus_dfs_index, len(windows))
    ordered = order_by_dfs_map(windows, dfs_map)
    if focused is not None:
        client.focus_window(focused)
    return dfs_map, ordered


def focused_windows(
    client: AerospaceClient, orderer: WindowOrderer, workspace: str
) -> tuple[int | None, list[Window]]:
    # promote / adjust-master operate on the CURRENT tree (no flatten). DfsProbeOrdering moves
    # focus while probing; capture and restore it so the keybinding does not displace focus.
    focused = client.focused_window_id()
    windows = orderer.order(client.list_windows(workspace))
    if focused is not None:
        client.focus_window(focused)
    return focused, windows


def apply_layout(client: AerospaceClient, name: str, workspace: str) -> None:
    windows = client.list_windows(workspace)
    _log_windows(workspace, windows)
    if name in FLATTENING_LAYOUTS:
        dfs_map, windows = _flatten_and_probe(client, workspace)
        for line in format_dfs_map(dfs_map):
            logger.info("  %s", line)
        excluded = floating_windows(windows)
        if excluded:
            logger.info(
                "excluding %d floating window(s) from tiling: %s",
                len(excluded),
                [w.window_id for w in excluded],
            )
    logger.info("ordered (master first): %s", [w.window_id for w in windows])
    commands = plan_layout(name, windows, workspace)
    logger.info("planned %d command(s): %s", len(commands), format_commands(commands))
    run_commands(client, commands)


def diagnose(client: AerospaceClient, name: str, workspace: str) -> list[Command]:
    raw = client.list_windows(workspace)
    dfs_map, ordered = _flatten_and_probe(client, workspace)
    commands = plan_layout(name, ordered, workspace)
    for line in format_diagnosis(raw, dfs_map, ordered, commands):
        print(line)
    return commands


def _apply_named(client: AerospaceClient, name: str, state_path: Path) -> None:
    workspace = client.focused_workspace()
    apply_layout(client, name, workspace)
    state = load_state(state_path)
    record_layout_name(state, workspace, name)
    save_state(state_path, state)


def _cycle(client: AerospaceClient, state_path: Path, *, reverse: bool) -> None:
    workspace = client.focused_workspace()
    state = load_state(state_path)
    index = advance_index(state, workspace, reverse=reverse)
    apply_layout(client, CYCLE[index], workspace)
    save_state(state_path, state)


def _reapply(client: AerospaceClient, state_path: Path) -> None:
    workspace = client.focused_workspace()
    index = get_index(load_state(state_path), workspace)
    apply_layout(client, CYCLE[index], workspace)


def _promote(client: AerospaceClient, orderer: WindowOrderer) -> None:
    workspace = client.focused_workspace()
    focused, windows = focused_windows(client, orderer, workspace)
    run_commands(client, plan_promote(windows, focused))


def _demote(client: AerospaceClient, orderer: WindowOrderer) -> None:
    workspace = client.focused_workspace()
    focused, windows = focused_windows(client, orderer, workspace)
    run_commands(client, plan_demote(windows, focused))


def _adjust_master(client: AerospaceClient, orderer: WindowOrderer, *, grow: bool) -> None:
    workspace = client.focused_workspace()
    _, windows = focused_windows(client, orderer, workspace)
    run_commands(client, plan_adjust_master(windows, grow))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("AEROSPACE_LAYOUTS_LOG", "WARNING").upper(),
        format="%(levelname)s %(message)s",
    )
    args = _build_parser().parse_args(argv)
    client = _make_client()
    orderer: WindowOrderer = DfsProbeOrdering(resolve_dfs_index=client.focus_dfs_index)
    state_path = default_state_path()

    try:
        match args.command:
            case "cycle":
                _cycle(client, state_path, reverse=args.reverse)
            case "apply":
                _apply_named(client, args.name, state_path)
            case "reapply":
                _reapply(client, state_path)
            case "adjust-master":
                _adjust_master(client, orderer, grow=args.direction == "+")
            case "promote":
                _promote(client, orderer)
            case "demote":
                _demote(client, orderer)
            case "diagnose":
                diagnose(client, args.name, client.focused_workspace())
            case _:  # unreachable: subparsers are required
                return 2
    except AerospaceError:
        logger.exception("aerospace command failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
