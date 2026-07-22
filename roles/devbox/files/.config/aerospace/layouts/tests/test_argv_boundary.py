from __future__ import annotations

import subprocess

import pytest

from aerospace_layouts.aerospace import WINDOW_FORMAT, AerospaceClient, AerospaceError
from aerospace_layouts.model import Command, join_with, set_layout

from .conftest import FakeRunner, FakeWm


def _completed(
    argv: list[str], returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def _list_windows_argv(workspace: str) -> list[str]:
    return ["list-windows", "--workspace", workspace, "--format", WINDOW_FORMAT, "--json"]


def test_command_to_argv_appends_window_id():
    assert join_with("right", 42).to_argv() == ["join-with", "right", "--window-id", "42"]
    assert " ".join(join_with("right", 42).to_argv()) == "join-with right --window-id 42"


def test_resize_uses_signed_delta():
    assert Command(("resize", "smart", "+50"), window_id=10).to_argv() == [
        "resize",
        "smart",
        "+50",
        "--window-id",
        "10",
    ]


def test_execute_raises_on_strict_nonzero():
    argv = ["join-with", "right", "--window-id", "42"]
    runner = FakeRunner(
        {tuple(argv): _completed(argv, 1, stderr="No windows in the specified direction")}
    )
    client = AerospaceClient(runner)
    with pytest.raises(AerospaceError, match="No windows"):
        client.execute(join_with("right", 42))


def test_execute_tolerates_nonzero_layout():
    argv = ["layout", "h_tiles", "--window-id", "10"]
    runner = FakeRunner({tuple(argv): _completed(argv, 1, stderr="already h_tiles")})
    AerospaceClient(runner).execute(set_layout("h_tiles", 10))


def test_list_windows_parses_json():
    payload = (
        '[{"app-name": "Zen", "window-id": 7, "window-title": "home"}, '
        '{"app-name": "Term", "window-id": 8, "window-title": "sh"}]'
    )
    argv = _list_windows_argv("3")
    client = AerospaceClient(FakeRunner({tuple(argv): _completed(argv, 0, stdout=payload)}))
    windows = client.list_windows("3")
    assert [(w.window_id, w.app_name) for w in windows] == [(7, "Zen"), (8, "Term")]


def test_list_windows_coerces_string_window_id():
    payload = '[{"app-name": "Zen", "window-id": "7", "window-title": "home"}]'
    argv = _list_windows_argv("3")
    client = AerospaceClient(FakeRunner({tuple(argv): _completed(argv, 0, stdout=payload)}))
    assert client.list_windows("3")[0].window_id == 7


def test_list_windows_parses_floating_parent_layout():
    payload = (
        '[{"app-name": "kitty", "window-id": 163, "window-title": "sh", '
        '"window-parent-container-layout": "floating"}]'
    )
    argv = _list_windows_argv("3")
    client = AerospaceClient(FakeRunner({tuple(argv): _completed(argv, 0, stdout=payload)}))
    assert client.list_windows("3")[0].parent_layout == "floating"


def test_focused_workspace_parses_json():
    payload = '[{"workspace": "5"}]'
    argv = ["list-workspaces", "--focused", "--json"]
    client = AerospaceClient(FakeRunner({tuple(argv): _completed(argv, 0, stdout=payload)}))
    assert client.focused_workspace() == "5"


def test_focused_window_id_returns_none_when_empty():
    argv = ["list-windows", "--focused", "--json"]
    client = AerospaceClient(FakeRunner({tuple(argv): _completed(argv, 0, stdout="[]")}))
    assert client.focused_window_id() is None


_MONITOR_ARGV = [
    "list-monitors",
    "--focused",
    "--json",
    "--format",
    "%{monitor-appkit-nsscreen-screens-id}",
]


def test_focused_monitor_appkit_id_parses_one_based_index():
    payload = '[{"monitor-appkit-nsscreen-screens-id": 2}]'
    client = AerospaceClient(
        FakeRunner({tuple(_MONITOR_ARGV): _completed(_MONITOR_ARGV, 0, payload)})
    )
    assert client.focused_monitor_appkit_id() == 2


def test_focused_monitor_appkit_id_degrades_to_none_on_query_failure():
    client = AerospaceClient(
        FakeRunner({tuple(_MONITOR_ARGV): _completed(_MONITOR_ARGV, 1, stderr="x")})
    )
    assert client.focused_monitor_appkit_id() is None


def test_focused_monitor_appkit_id_degrades_to_none_on_empty_output():
    client = AerospaceClient(
        FakeRunner({tuple(_MONITOR_ARGV): _completed(_MONITOR_ARGV, 0, stdout="")})
    )
    assert client.focused_monitor_appkit_id() is None


def test_query_raises_on_nonzero():
    argv = ["list-workspaces", "--focused", "--json"]
    client = AerospaceClient(FakeRunner({tuple(argv): _completed(argv, 1, stderr="socket error")}))
    with pytest.raises(AerospaceError, match="socket error"):
        client.focused_workspace()


def test_focus_dfs_index_returns_window_that_landed_there():
    client = AerospaceClient(FakeWm(dfs_ids=[10, 11, 12]))
    assert client.focus_dfs_index(0) == 10
    assert client.focus_dfs_index(2) == 12


def test_focus_dfs_index_out_of_range_returns_none():
    assert AerospaceClient(FakeWm(dfs_ids=[10])).focus_dfs_index(5) is None


def test_focus_window_sets_focus():
    wm = FakeWm(dfs_ids=[10, 11], focused=11)
    AerospaceClient(wm).focus_window(10)
    assert wm.focused == 10
