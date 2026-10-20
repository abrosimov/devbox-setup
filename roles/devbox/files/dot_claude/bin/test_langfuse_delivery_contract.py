# ruff: noqa: ARG005
"""Executable, currently failing delivery invariants for the vendored Langfuse hook.

These are strict xfails until the transport handoff has a durable ACK boundary.
They exercise the actual upstream functions with injected failures, not a copy
of their implementation. Do not mark them passing by weakening assertions.
"""

from __future__ import annotations

import importlib.util
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).parent / "vendor" / "langfuse_hook.py"


def hook():
    pytest.importorskip("langfuse")
    spec = importlib.util.spec_from_file_location("langfuse_delivery_contract_under_test", SOURCE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_unacknowledged_observations_are_not_checkpointed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Even a crash after enqueue must leave its logical event replayable."""
    m = hook()
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("", encoding="utf-8")
    saved = []
    state = m.SessionState(open_turn={"rows": [{"type": "user"}]})
    monkeypatch.setattr(m, "FileLock", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(m, "load_hook_state", dict)
    monkeypatch.setattr(m, "get_session_state", lambda *_: state)
    monkeypatch.setattr(m, "get_subagent_transcripts_by_tool_use_id", lambda *_: {})
    monkeypatch.setattr(m, "WorkflowAgentTranscriptsByRunId", lambda *_: None)
    monkeypatch.setattr(m, "get_new_turns_from_transcript", lambda *args, **kwargs: ([], state))
    monkeypatch.setattr(m, "build_session_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(m, "get_task_id_to_tool_use_id", lambda *_: {})
    monkeypatch.setattr(
        m,
        "emit_ready_observations_of_open_turn",
        lambda *args, **kwargs: state.turn_progress.update(
            {"turn-one": {"emitted_keys": ["generation:1"], "trace_id": "a" * 32}}
        ),
    )
    monkeypatch.setattr(
        m,
        "save_session_state",
        lambda _global_state, _key, session_state: saved.append(dict(session_state.turn_progress)),
    )
    class BrokenClient:
        def flush(self):
            message = "collector unavailable"
            raise OSError(message)

        def shutdown(self):
            pass

    with pytest.raises(OSError, match="collector unavailable"):
        m.emit_new_turns_from_transcript(
        BrokenClient(),
        SimpleNamespace(user_id="test", trace_seed=None, parent_context=None),
        "session",
        transcript,
        )
    # No flush or durable collector acknowledgement happened, so the
    # persisted checkpoint must NOT declare the event sent.
    assert not saved


def test_failed_flush_must_be_observable_to_delivery_caller() -> None:
    """A flush failure must not look identical to a confirmed durable handoff."""
    m = hook()

    class BrokenClient:
        def flush(self):
            message = "injected collector connection failure"
            raise OSError(message)

        def shutdown(self):
            pass

    # Never call the network; the SDK itself raises deterministically.
    with pytest.raises(OSError, match="injected collector"):
        m.flush_and_shutdown_langfuse_client(BrokenClient())


def test_hanging_flush_must_not_report_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate an SDK worker which cannot finish inside the hook's budget."""
    m = hook()

    class FakeThread:
        def __init__(self, _target, daemon):
            assert daemon

        def start(self):
            pass

        def join(self, timeout):
            assert timeout == 5.0

        def is_alive(self):
            return True

    monkeypatch.setattr(m.threading, "Thread", FakeThread)
    with pytest.raises(TimeoutError):
        m.flush_and_shutdown_langfuse_client(SimpleNamespace())


def test_turn_trace_id_is_deterministic_for_replay() -> None:
    m = hook()
    first = m.derive_turn_trace_id("stable-session", 1)
    second = m.derive_turn_trace_id("stable-session", 1)
    assert first == second
    assert m._is_valid_trace_id_hex(first)
