"""Fault-injection contracts for persistent Langfuse hook emission state.

Expected failures are strict: an implementation that repairs a defect must
also promote that scenario into an ordinary passing test.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).parent / "vendor" / "langfuse_hook.py"


def load_hook():
    pytest.importorskip("langfuse")
    spec = importlib.util.spec_from_file_location("langfuse_durable_state_under_test", SOURCE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.xfail(strict=True, reason="Upstream swallows state persistence errors")
def test_checkpoint_storage_failure_is_not_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failed checkpoint must never be mistaken for a durable state commit."""
    module = load_hook()
    monkeypatch.setattr(module, "STATE_DIR", tmp_path)
    monkeypatch.setattr(module, "STATE_FILE", tmp_path / "state.json")

    def reject_replace(*_args, **_kwargs) -> None:
        message = "injected persistent volume write failure"
        raise OSError(message)

    monkeypatch.setattr(module.os, "replace", reject_replace)
    with pytest.raises(OSError, match="injected persistent volume"):
        module.save_hook_state({"session": {"offset": 23}})


@pytest.mark.xfail(strict=True, reason="Upstream atomically renames but does not fsync checkpoint")
def test_checkpoint_calls_fsync_before_returning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A successful checkpoint should persist file data and rename metadata."""
    module = load_hook()
    monkeypatch.setattr(module, "STATE_DIR", tmp_path)
    monkeypatch.setattr(module, "STATE_FILE", tmp_path / "state.json")
    fsync_calls: list[int] = []
    original_fsync = module.os.fsync

    def capture_fsync(fd: int) -> None:
        fsync_calls.append(fd)
        original_fsync(fd)

    monkeypatch.setattr(module.os, "fsync", capture_fsync)
    module.save_hook_state({"session": {"offset": 23}})
    assert (tmp_path / "state.json").exists()
    assert len(fsync_calls) >= 2


def test_checkpoint_state_contains_replay_cursor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The persisted state format carries the per-turn emission cursor."""
    module = load_hook()
    monkeypatch.setattr(module, "STATE_DIR", tmp_path)
    monkeypatch.setattr(module, "STATE_FILE", tmp_path / "state.json")
    session_state = module.SessionState(
        offset=42,
        turn_progress={"turn-uuid": {"trace_id": "a" * 32, "emitted_keys": ["tool:1"]}},
    )
    global_state: dict = {}
    module.save_session_state(global_state, "session-key", session_state)
    loaded = module.get_session_state(module.load_hook_state(), "session-key")
    assert loaded.offset == 42
    assert loaded.turn_progress["turn-uuid"]["emitted_keys"] == ["tool:1"]
