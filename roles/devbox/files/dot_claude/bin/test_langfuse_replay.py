# ruff: noqa: ARG001
"""Persistent pending-session and independent replay tests (no network)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import langfuse_replay
import langfuse_trace_hook
import pytest


@pytest.fixture
def pending_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    state_dir = tmp_path / "state"
    monkeypatch.setenv("CC_LANGFUSE_STATE_DIR", str(state_dir))
    monkeypatch.setenv("LANGFUSE_USER_ID", "test-user")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "personal")
    monkeypatch.delenv(langfuse_trace_hook.REPLAY_ENV, raising=False)
    return state_dir


def sample_payload(tmp_path: Path) -> dict[str, str]:
    transcript = tmp_path / "session-001.jsonl"
    transcript.write_text('{"type":"user","message":"hello"}\n', encoding="utf-8")
    return {
        "session_id": "session-001",
        "transcript_path": str(transcript),
        "hook_event_name": "SessionEnd",
    }


def test_pending_registration_is_durable_and_recoverable(
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    record = langfuse_trace_hook.register_pending(sample_payload(tmp_path))
    assert record is not None
    marker, nonce, snapshot = record
    saved = json.loads(marker.read_text(encoding="utf-8"))
    assert saved["nonce"] == nonce
    assert saved["user_id"] == "test-user"
    assert saved["hook_event_name"] == "SessionEnd"
    assert snapshot.read_bytes() == Path(saved["transcript_path"]).read_bytes()
    assert snapshot.name == Path(saved["transcript_path"]).name
    langfuse_trace_hook.complete_pending(*record)
    assert not marker.exists()
    assert not snapshot.exists()


def test_old_hook_cannot_clear_a_newer_pending_session(
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)
    first = langfuse_trace_hook.register_pending(payload)
    second = langfuse_trace_hook.register_pending(payload)
    assert first is not None
    assert second is not None
    langfuse_trace_hook.complete_pending(*first)
    latest = json.loads(second[0].read_text(encoding="utf-8"))
    assert latest["nonce"] == second[1]
    assert second[2].is_file()


def test_failed_hook_keeps_its_pending_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    def failed_hook(*_args, **_kwargs):
        raise SystemExit(1)

    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", failed_hook)
    with pytest.raises(SystemExit) as exc:
        langfuse_trace_hook.main()
    assert exc.value.code == 1
    assert len(list((pending_environment / "langfuse_pending").glob("*.json"))) == 1


def test_repeated_failed_stops_keep_one_snapshot_per_session(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)

    def failed_hook(*_args, **_kwargs):
        raise SystemExit(1)

    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", failed_hook)
    for _ in range(3):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
        with pytest.raises(SystemExit):
            langfuse_trace_hook.main()

    root = pending_environment / "langfuse_pending"
    (marker,) = root.glob("*.json")
    record = json.loads(marker.read_text(encoding="utf-8"))
    snapshots = [path for path in root.iterdir() if path.is_dir()]
    assert snapshots == [Path(record["snapshot_path"]).parent]
    assert Path(record["snapshot_path"]).is_file()


def test_completed_hook_clears_its_pending_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(sample_payload(tmp_path))))
    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", lambda *_args, **_kwargs: None)
    langfuse_trace_hook.main()
    assert not list((pending_environment / "langfuse_pending").glob("*.json"))


def test_replay_uses_snapshot_when_original_transcript_was_removed(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)
    record = langfuse_trace_hook.register_pending(payload)
    assert record is not None
    marker, _, snapshot = record
    Path(payload["transcript_path"]).unlink()
    calls: list[dict] = []

    def fake_run(_args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(langfuse_replay.subprocess, "run", fake_run)
    env = {"CC_LANGFUSE_BASE_URL": "http://127.0.0.1:14318"}
    assert langfuse_replay.replay_one(marker, env)
    request = json.loads(calls[0]["input"])
    assert request["transcript_path"] == str(snapshot)
    assert calls[0]["env"]["CC_LANGFUSE_STATE_IDENTITY_PATH"] == payload["transcript_path"]
    assert not marker.exists()


def test_failed_replay_preserves_pending_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    record = langfuse_trace_hook.register_pending(sample_payload(tmp_path))
    assert record is not None
    marker, _, snapshot = record
    monkeypatch.setattr(
        langfuse_replay.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )
    assert not langfuse_replay.replay_one(marker, {})
    assert marker.is_file()
    assert snapshot.is_file()


def test_transcript_removed_during_hook_retains_pending_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)
    source = Path(payload["transcript_path"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    def remove_source(*_args, **_kwargs):
        source.unlink()

    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", remove_source)
    langfuse_trace_hook.main()
    markers = list((pending_environment / "langfuse_pending").glob("*.json"))
    assert len(markers) == 1
    record = json.loads(markers[0].read_text(encoding="utf-8"))
    assert Path(record["snapshot_path"]).is_file()
