from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aerospace_layouts.aerospace import AerospaceClient
from aerospace_layouts.cli import apply_layout, main

from .conftest import FakeWm

WS = "3"


class RecordingRunner:
    def __init__(self, inner: FakeWm) -> None:
        self.inner = inner
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        return self.inner(argv)

    def count_prefix(self, prefix: list[str]) -> int:
        return sum(1 for call in self.calls if call[: len(prefix)] == prefix)


def _recording_client() -> tuple[AerospaceClient, RecordingRunner]:
    runner = RecordingRunner(FakeWm(dfs_ids=[10, 11, 12]))
    return AerospaceClient(runner), runner


@pytest.mark.parametrize("name", ["columns", "max"])
def test_order_agnostic_layouts_flatten_without_dfs_probe(name: str):
    client, runner = _recording_client()
    apply_layout(client, name, WS)
    assert runner.count_prefix(["flatten-workspace-tree"]) == 1
    assert runner.count_prefix(["focus", "--dfs-index"]) == 0


@pytest.mark.parametrize("name", ["tile", "fair"])
def test_order_sensitive_layouts_probe_dfs_order(name: str):
    client, runner = _recording_client()
    apply_layout(client, name, WS)
    assert runner.count_prefix(["flatten-workspace-tree"]) == 1
    assert runner.count_prefix(["focus", "--dfs-index"]) > 0


def _drive_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, argv: list[str], focused: int | None = None
) -> RecordingRunner:
    runner = RecordingRunner(FakeWm(dfs_ids=[10, 11, 12], focused=focused, workspace=WS))
    monkeypatch.setattr("aerospace_layouts.cli._make_client", lambda: AerospaceClient(runner))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert main(argv) == 0
    return runner


@pytest.mark.parametrize("name", ["columns", "max", "tile", "fair"])
def test_apply_emits_exactly_one_eval_call_for_the_mutation_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str
):
    runner = _drive_main(monkeypatch, tmp_path, ["apply", name])
    assert runner.count_prefix(["eval"]) == 1


def test_promote_emits_exactly_one_eval_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    runner = _drive_main(monkeypatch, tmp_path, ["promote"], focused=12)
    assert runner.count_prefix(["eval"]) == 1


def test_demote_emits_exactly_one_eval_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    runner = _drive_main(monkeypatch, tmp_path, ["demote"], focused=10)
    assert runner.count_prefix(["eval"]) == 1


def test_adjust_master_emits_exactly_one_eval_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    runner = _drive_main(monkeypatch, tmp_path, ["adjust-master", "+"], focused=10)
    assert runner.count_prefix(["eval"]) == 1
