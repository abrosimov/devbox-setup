from __future__ import annotations

import json
import subprocess

import pytest

from aerospace_layouts.model import Command, Window


def make_windows(count: int) -> list[Window]:
    return [
        Window(window_id=10 + i, app_name=f"App{i}", window_title=f"title-{i}")
        for i in range(count)
    ]


def argv_strings(commands: list[Command]) -> list[str]:
    return [" ".join(cmd.to_argv()) for cmd in commands]


class FakeRunner:
    def __init__(
        self, responses: dict[tuple[str, ...], subprocess.CompletedProcess[str]] | None = None
    ) -> None:
        self.calls: list[list[str]] = []
        self._responses = responses or {}

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        response = self._responses.get(tuple(argv))
        if response is not None:
            return response
        return subprocess.CompletedProcess(argv, 0, "", "")

    @property
    def argv_strings(self) -> list[str]:
        return [" ".join(call) for call in self.calls]


class FakeWm:
    # Stateful runner modelling a workspace whose `list-windows` array order differs from
    # dfs/visual order. `focus --dfs-index i` resolves to dfs_ids[i]; `post_flatten_dfs`
    # models a tree whose dfs order changes once `flatten-workspace-tree` linearises it.
    # Non-query commands are recorded in `mutations` for sequence assertions.
    def __init__(
        self,
        dfs_ids: list[int],
        array_ids: list[int] | None = None,
        focused: int | None = None,
        post_flatten_dfs: list[int] | None = None,
        layouts: dict[int, str] | None = None,
    ) -> None:
        self.dfs_ids = dfs_ids
        self.array_ids = array_ids if array_ids is not None else dfs_ids
        self.focused: int | None = focused
        self.post_flatten_dfs = post_flatten_dfs
        self.layouts = layouts or {}
        self.mutations: list[list[str]] = []

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        if argv[:1] == ["list-windows"] and "--focused" in argv:
            ids = [self.focused] if self.focused is not None else []
            return subprocess.CompletedProcess(argv, 0, self._windows_json(ids), "")
        if argv[:1] == ["list-windows"] and "--workspace" in argv:
            return subprocess.CompletedProcess(argv, 0, self._windows_json(self.array_ids), "")
        if argv[:2] == ["focus", "--dfs-index"]:
            index = int(argv[2])
            if not 0 <= index < len(self.dfs_ids):
                return subprocess.CompletedProcess(argv, 1, "", "index out of range")
            self.focused = self.dfs_ids[index]
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:2] == ["focus", "--window-id"]:
            self.focused = int(argv[2])
            return subprocess.CompletedProcess(argv, 0, "", "")
        self.mutations.append(list(argv))
        if argv[:1] == ["flatten-workspace-tree"] and self.post_flatten_dfs is not None:
            self.dfs_ids = self.post_flatten_dfs
        return subprocess.CompletedProcess(argv, 0, "", "")

    def joined_ids(self) -> list[str]:
        return [m[m.index("--window-id") + 1] for m in self.mutations if m[:1] == ["join-with"]]

    def _windows_json(self, window_ids: list[int]) -> str:
        rows = [
            {
                "app-name": f"App{i}",
                "window-id": wid,
                "window-title": f"t{i}",
                "window-parent-container-layout": self.layouts.get(wid, "h_tiles"),
            }
            for i, wid in enumerate(window_ids)
        ]
        return json.dumps(rows)


@pytest.fixture
def fake_runner() -> FakeRunner:
    return FakeRunner()
