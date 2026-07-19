from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from aerospace_layouts.model import Command, Window

logger = logging.getLogger("aerospace_layouts")

Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

_QUERY_TIMEOUT_S = 10.0

# `--format` combines with `--json` (each %{var} becomes a JSON key). We request the parent
# container layout so callers can see which windows are floating (not in the tiling tree).
WINDOW_FORMAT = "%{window-id} %{app-name} %{window-title} %{window-parent-container-layout}"


class AerospaceError(RuntimeError):
    pass


def subprocess_runner(binary: str = "aerospace") -> Runner:
    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [binary, *argv],
            capture_output=True,
            text=True,
            timeout=_QUERY_TIMEOUT_S,
            check=False,
        )

    return run


@dataclass
class AerospaceClient:
    run_argv: Runner

    def _query(self, argv: list[str]) -> str:
        result = self.run_argv(argv)
        logger.debug("query rc=%d argv=%s", result.returncode, " ".join(argv))
        if result.returncode != 0:
            raise AerospaceError(
                f"{' '.join(argv)} exited {result.returncode}: {result.stderr.strip()}"
            )
        return result.stdout

    def list_windows(self, workspace: str) -> list[Window]:
        payload = self._query(
            ["list-windows", "--workspace", workspace, "--format", WINDOW_FORMAT, "--json"]
        )
        return _parse_windows(payload)

    def focused_workspace(self) -> str:
        payload = self._query(["list-workspaces", "--focused", "--json"])
        rows = _parse_rows(payload)
        if not rows:
            raise AerospaceError("no focused workspace reported")
        value = rows[0].get("workspace")
        if not isinstance(value, str):
            raise AerospaceError("focused workspace payload missing 'workspace'")
        return value

    def focused_window_id(self) -> int | None:
        payload = self._query(["list-windows", "--focused", "--json"])
        windows = _parse_windows(payload)
        return windows[0].window_id if windows else None

    def focus_dfs_index(self, index: int) -> int | None:
        # Side-effecting probe: move focus to the dfs position, then read back which window
        # landed there. Returns None if the index is out of range (focus exits non-zero).
        if self.run_argv(["focus", "--dfs-index", str(index)]).returncode != 0:
            return None
        return self.focused_window_id()

    def focus_window(self, window_id: int) -> None:
        self.run_argv(["focus", "--window-id", str(window_id)])

    def execute(self, command: Command) -> None:
        argv = command.to_argv()
        result = self.run_argv(argv)
        logger.info("exec rc=%d argv=%s", result.returncode, " ".join(argv))
        if result.returncode != 0 and result.stderr.strip():
            logger.info("  stderr: %s", result.stderr.strip())
        if result.returncode == 0:
            return
        if command.tolerate_nonzero:
            # `layout` reports non-zero when already in the requested state; the tree is
            # in the desired shape, so continue the sequence rather than aborting.
            return
        raise AerospaceError(
            f"{' '.join(argv)} exited {result.returncode}: {result.stderr.strip()}"
        )


def _parse_rows(payload: str) -> list[dict[str, object]]:
    data: object = json.loads(payload)
    if not isinstance(data, list):
        raise AerospaceError("expected a JSON array")
    items = cast("list[object]", data)
    return [cast("dict[str, object]", item) for item in items if isinstance(item, dict)]


def _parse_windows(payload: str) -> list[Window]:
    windows: list[Window] = []
    for row in _parse_rows(payload):
        window_id = _coerce_window_id(row.get("window-id"))
        if window_id is None:
            continue
        layout = row.get("window-parent-container-layout")
        windows.append(
            Window(
                window_id,
                str(row.get("app-name", "")),
                str(row.get("window-title", "")),
                parent_layout=str(layout) if isinstance(layout, str) else None,
            )
        )
    return windows


def _coerce_window_id(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
