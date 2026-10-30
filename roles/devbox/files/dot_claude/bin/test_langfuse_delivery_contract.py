# ruff: noqa: ARG005
"""Executable, currently failing delivery invariants for the vendored Langfuse hook.

These are strict xfails until the transport handoff has a durable ACK boundary.
They exercise the actual upstream functions with injected failures, not a copy
of their implementation. Do not mark them passing by weakening assertions.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).parent / "vendor" / "langfuse_hook.py"
HOOK_RUN_DRIVER = Path(__file__).parent / "testdata" / "langfuse_hook_run.py"


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
        def __init__(self, target, daemon):
            assert callable(target)
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


def test_closed_turn_emit_failure_is_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed closed turn cannot be marked emitted and committed."""
    m = hook()
    turn = m.Turn(
        user_msg={"uuid": "turn-one"},
        assistant_msgs=[],
        tool_results_by_id={},
        tool_use_timestamps_by_id={},
        injected_by_tool_id={},
        rows=[],
    )
    state = m.SessionState(turn_numbers={"turn-one": 1})

    def broken_emit(*_args, **_kwargs):
        message = "injected observation serialization failure"
        raise ValueError(message)

    monkeypatch.setattr(m, "emit_turn", broken_emit)
    with pytest.raises(ValueError, match="injected observation"):
        m.emit_and_close_ready_turns(
            object(),
            "session",
            Path("session.jsonl"),
            [turn],
            state,
            user_id=None,
            subagent_transcripts_by_tool_use_id={},
        )


def test_open_turn_emit_failure_is_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    """An open turn cannot silently proceed to commit after emission fails."""
    m = hook()
    turn = m.Turn(
        user_msg={"uuid": "turn-one"},
        assistant_msgs=[],
        tool_results_by_id={},
        tool_use_timestamps_by_id={},
        injected_by_tool_id={},
        rows=[],
    )
    state = m.SessionState(
        open_turn={"rows": [{"type": "user", "uuid": "turn-one"}]},
        turn_numbers={"turn-one": 1},
    )

    def broken_emit(*_args, **_kwargs):
        message = "injected open-turn emission failure"
        raise ValueError(message)

    monkeypatch.setattr(m, "assemble_turns", lambda *_: ([], turn, []))
    monkeypatch.setattr(m, "turn_has_unresolved_async_activity", lambda *_: False)
    monkeypatch.setattr(m, "emit_turn", broken_emit)
    with pytest.raises(ValueError, match="injected open-turn"):
        m.emit_ready_observations_of_open_turn(
            object(),
            "session",
            Path("session.jsonl"),
            state,
            {},
            user_id=None,
            subagent_transcripts_by_tool_use_id={},
        )


def run_hook_scenario(
    tmp_path: Path, scenario: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    pytest.importorskip("langfuse")
    state = tmp_path / "state"
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("", encoding="utf-8")
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("LANGFUSE_")
    }
    environment |= {
        "CC_LANGFUSE_STATE_DIR": str(state),
        "CC_LANGFUSE_PUBLIC_KEY": "pk-lf-hook-run",
        "CC_LANGFUSE_SECRET_KEY": "sk-lf-hook-run",
        "CC_LANGFUSE_BASE_URL": "http://127.0.0.1:9",
    }
    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_RUN_DRIVER), str(SOURCE.parent), str(transcript), scenario],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"Hook process did not exit after the {scenario} run")
    return result, state


def test_run_failing_on_turn_k_leaves_nothing_in_the_spool(tmp_path: Path) -> None:
    """The checkpoint stays put, so replay re-emits earlier turns; spooling them duplicates."""
    result, state = run_hook_scenario(tmp_path, "emission")
    assert result.returncode == 1, result.stderr
    assert not list(state.rglob("*.otlp"))


def test_flush_timeout_discards_queued_spans_and_exits(tmp_path: Path) -> None:
    result, state = run_hook_scenario(tmp_path, "flush-timeout")
    assert result.returncode == 1, result.stderr
    assert not list((state / "langfuse_otlp_spool").glob("*.otlp"))


def test_successful_run_commits_every_turn_to_the_spool(tmp_path: Path) -> None:
    result, state = run_hook_scenario(tmp_path, "success")
    assert result.returncode == 0, result.stderr
    assert list((state / "langfuse_otlp_spool").glob("*.otlp"))
    assert not list((state / "langfuse_otlp_spool").rglob(".staging/*/*.otlp"))
