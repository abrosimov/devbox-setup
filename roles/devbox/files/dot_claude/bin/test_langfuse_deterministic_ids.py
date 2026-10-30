"""A re-emitted turn must carry the identities its first emission had.

Langfuse stores the OTel span id as the observation id and the trace id as the
trace id, with no deduplication on read, so replay after a crash or a lost
acknowledgement only stays idempotent if every identity is reproducible.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import langfuse_replay
import langfuse_trace_hook
import pytest

trace_service = pytest.importorskip("opentelemetry.proto.collector.trace.v1.trace_service_pb2")

BIN = Path(__file__).parent
WRAPPER = BIN / "langfuse_trace_hook.py"
VENDORED_HOOK = BIN / "vendor" / "langfuse_hook.py"
SESSION_ID = "0d9c4a52-6f0e-4f43-9a51-1d7bb0e7c001"
OTHER_SESSION_ID = "0d9c4a52-6f0e-4f43-9a51-1d7bb0e7c002"
ROOT_NAME = "Conversational Turn"
PARENT_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
PARENT_SPAN_ID = "00f067aa0ba902b7"
PER_RUN_VARIABLES = (
    "LANGFUSE_USER_ID",
    "LANGFUSE_TRACING_ENVIRONMENT",
    "CC_LANGFUSE_TRACE_TAGS",
    "CC_LANGFUSE_TRACE_SEED",
    "CC_LANGFUSE_TRACEPARENT",
)
FIRST_TURN_START = "2026-10-01T10:00:00.000Z"
UUIDLESS_TURN_FIRST_ROW = "2026-10-01T10:01:01.000Z"
LAST_TURN_START = "2026-10-01T10:02:00.000Z"


@dataclass(frozen=True, order=True)
class Identity:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: str
    start_time: int
    end_time: int


def nanoseconds(timestamp: str) -> int:
    return int(datetime.fromisoformat(timestamp).timestamp()) * 10**9


def user_row(
    session_id: str, uuid: str | None, timestamp: str | None, content: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "type": "user",
        "sessionId": session_id,
        "message": {"role": "user", "content": content},
    }
    if uuid is not None:
        row["uuid"] = uuid
    if timestamp is not None:
        row["timestamp"] = timestamp
    return row


def assistant_row(
    session_id: str, message_id: str | None, timestamp: str | None, content: list[object]
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "model": "claude-test", "content": content}
    if message_id is not None:
        message["id"] = message_id
    row: dict[str, object] = {"type": "assistant", "sessionId": session_id, "message": message}
    if timestamp is not None:
        row["timestamp"] = timestamp
    return row


def tool_result_row(session_id: str, tool_use_id: str, timestamp: str) -> dict[str, object]:
    content = [{"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}]
    return user_row(session_id, None, timestamp, content)


def text(value: str) -> dict[str, str]:
    return {"type": "text", "text": value}


def tool_use(tool_use_id: str, name: str, tool_input: dict[str, str]) -> dict[str, object]:
    return {"type": "tool_use", "id": tool_use_id, "name": name, "input": tool_input}


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def write_session(directory: Path, session_id: str, *, with_subagent: bool = True) -> Path:
    """Three turns: tools and a subagent, then one without uuid or user time, then an open one."""
    first_turn: list[dict[str, object]] = [
        user_row(session_id, "user-row-1", FIRST_TURN_START, "Read the notes"),
        assistant_row(
            session_id,
            "msg_1",
            "2026-10-01T10:00:01.000Z",
            [text("Reading"), tool_use("toolu_read", "Read", {"file_path": "notes.md"})],
        ),
        tool_result_row(session_id, "toolu_read", "2026-10-01T10:00:02.000Z"),
    ]
    if with_subagent:
        first_turn += [
            assistant_row(
                session_id,
                "msg_2",
                "2026-10-01T10:00:03.000Z",
                [tool_use("toolu_task", "Task", {"description": "Investigate", "prompt": "Go"})],
            ),
            tool_result_row(session_id, "toolu_task", "2026-10-01T10:00:10.000Z"),
        ]
    first_turn.append(
        assistant_row(session_id, "msg_3", "2026-10-01T10:00:11.000Z", [text("Done")])
    )
    uuidless_turn = [
        user_row(session_id, None, None, "And then?"),
        assistant_row(session_id, None, UUIDLESS_TURN_FIRST_ROW, [text("Thinking")]),
        assistant_row(session_id, None, None, [text("Finished")]),
    ]
    open_turn = [
        user_row(session_id, "user-row-3", LAST_TURN_START, "Thanks"),
        assistant_row(session_id, "msg_6", "2026-10-01T10:02:01.000Z", [text("Welcome")]),
    ]
    transcript = directory / f"{session_id}.jsonl"
    write_jsonl(transcript, first_turn + uuidless_turn + open_turn)
    if with_subagent:
        subagents = transcript.with_suffix("") / "subagents"
        meta = {"toolUseId": "toolu_task", "agentType": "general-purpose", "description": "Go"}
        subagents.mkdir(parents=True)
        (subagents / "agent-a1.meta.json").write_text(json.dumps(meta), encoding="utf-8")
        # Two prompts whose replies lack message ids collide on the gen:noid:0 key.
        write_jsonl(
            subagents / "agent-a1.jsonl",
            [
                user_row(session_id, "agent-row-1", "2026-10-01T10:00:04.000Z", "Investigate"),
                assistant_row(session_id, None, "2026-10-01T10:00:05.000Z", [text("Looking")]),
                user_row(session_id, "agent-row-2", "2026-10-01T10:00:06.000Z", "Continue"),
                assistant_row(session_id, None, "2026-10-01T10:00:07.000Z", [text("Found")]),
            ],
        )
    return transcript


def hook_environment(state: Path, **overrides: str) -> dict[str, str]:
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("LANGFUSE_", "CC_LANGFUSE_"))
    }
    environment |= {
        "CC_LANGFUSE_STATE_DIR": str(state),
        "CC_LANGFUSE_PUBLIC_KEY": "pk-lf-deterministic",
        "CC_LANGFUSE_SECRET_KEY": "sk-lf-deterministic",
        "CC_LANGFUSE_BASE_URL": "http://127.0.0.1:9",
    }
    return environment | overrides


def hook_log(state: Path) -> str:
    log = state / "langfuse_hook.log"
    return log.read_text(encoding="utf-8") if log.is_file() else ""


def spooled_identities(state: Path) -> list[Identity]:
    identities: list[Identity] = []
    for batch in sorted((state / "langfuse_otlp_spool").glob("*.otlp")):
        request = trace_service.ExportTraceServiceRequest.FromString(batch.read_bytes())
        for resource_spans in request.resource_spans:
            for scope_spans in resource_spans.scope_spans:
                identities.extend(
                    Identity(
                        span.name,
                        span.trace_id.hex(),
                        span.span_id.hex(),
                        span.parent_span_id.hex(),
                        span.start_time_unix_nano,
                        span.end_time_unix_nano,
                    )
                    for span in scope_spans.spans
                )
    assert identities, f"the hook spooled no observations\n{hook_log(state)}"
    return sorted(identities)


def run_live_hook(
    transcript: Path, session_id: str, state: Path, **overrides: str
) -> list[Identity]:
    payload = {
        "session_id": session_id,
        "transcript_path": str(transcript),
        "hook_event_name": "Stop",
    }
    result = subprocess.run(
        [sys.executable, str(WRAPPER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
        env=hook_environment(state, **overrides),
    )
    assert result.returncode == 0, f"{result.stderr}\n{hook_log(state)}"
    return spooled_identities(state)


def run_pending_replay(
    transcript: Path,
    session_id: str,
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    remove_original: bool = False,
) -> list[Identity]:
    monkeypatch.setenv("CC_LANGFUSE_STATE_DIR", str(state))
    for name in PER_RUN_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    payload = {
        "session_id": session_id,
        "transcript_path": str(transcript),
        "hook_event_name": "Stop",
    }
    registered = langfuse_trace_hook.register_pending(payload)
    assert registered is not None
    if remove_original:
        transcript.unlink()
    environment = hook_environment(state) | {langfuse_trace_hook.REPLAY_ENV: "1"}
    assert langfuse_replay.replay_one(registered[0], environment), hook_log(state)
    return spooled_identities(state)


def roots(identities: list[Identity]) -> list[Identity]:
    return [identity for identity in identities if identity.name == ROOT_NAME]


def is_nonzero_hex(value: str, length: int) -> bool:
    return len(value) == length and int(value, 16) != 0


def load_hook() -> ModuleType:
    pytest.importorskip("langfuse")
    spec = importlib.util.spec_from_file_location(
        "langfuse_deterministic_ids_under_test", VENDORED_HOOK
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reemitting_a_transcript_in_a_new_process_reproduces_every_identity(
    tmp_path: Path,
) -> None:
    transcript = write_session(tmp_path / "projects", SESSION_ID)
    first = run_live_hook(transcript, SESSION_ID, tmp_path / "first")
    second = run_live_hook(transcript, SESSION_ID, tmp_path / "second")
    assert second == first


def test_replay_of_a_pending_session_reproduces_the_live_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transcript = write_session(tmp_path / "projects", SESSION_ID)
    live = run_live_hook(transcript, SESSION_ID, tmp_path / "live")
    replayed = run_pending_replay(transcript, SESSION_ID, tmp_path / "replay", monkeypatch)
    assert replayed == live


def test_replay_from_the_snapshot_reproduces_the_live_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transcript = write_session(tmp_path / "projects", SESSION_ID, with_subagent=False)
    live = run_live_hook(transcript, SESSION_ID, tmp_path / "live")
    replayed = run_pending_replay(
        transcript, SESSION_ID, tmp_path / "replay", monkeypatch, remove_original=True
    )
    assert replayed == live


def test_each_turn_and_each_session_gets_its_own_trace(tmp_path: Path) -> None:
    session = run_live_hook(
        write_session(tmp_path / "a", SESSION_ID), SESSION_ID, tmp_path / "state-a"
    )
    other = run_live_hook(
        write_session(tmp_path / "b", OTHER_SESSION_ID), OTHER_SESSION_ID, tmp_path / "state-b"
    )
    turn_traces = [root.trace_id for root in roots(session)]
    assert len(turn_traces) == 3
    assert len(set(turn_traces)) == 3
    assert {i.trace_id for i in session}.isdisjoint({i.trace_id for i in other})


def test_observations_have_distinct_valid_ids_nested_under_emitted_parents(
    tmp_path: Path,
) -> None:
    identities = run_live_hook(
        write_session(tmp_path / "projects", SESSION_ID), SESSION_ID, tmp_path / "state"
    )
    span_ids = [identity.span_id for identity in identities]
    assert len(span_ids) == len(set(span_ids))
    assert sum(identity.name == "Subagent LLM Call" for identity in identities) == 2
    for identity in identities:
        assert is_nonzero_hex(identity.trace_id, 32)
        assert is_nonzero_hex(identity.span_id, 16)
        assert is_nonzero_hex(identity.parent_span_id, 16)
        if identity.name != ROOT_NAME:
            assert identity.parent_span_id in span_ids


def test_observation_times_come_from_the_transcript(tmp_path: Path) -> None:
    emitted_after = time.time_ns()
    identities = run_live_hook(
        write_session(tmp_path / "projects", SESSION_ID), SESSION_ID, tmp_path / "state"
    )
    assert {root.start_time for root in roots(identities)} == {
        nanoseconds(FIRST_TURN_START),
        nanoseconds(UUIDLESS_TURN_FIRST_ROW),
        nanoseconds(LAST_TURN_START),
    }
    for identity in identities:
        assert identity.start_time <= identity.end_time < emitted_after


def test_trace_seed_keeps_its_formula_and_its_span_ids(tmp_path: Path) -> None:
    transcript = write_session(tmp_path / "projects", SESSION_ID)
    seeded = run_live_hook(
        transcript, SESSION_ID, tmp_path / "first", CC_LANGFUSE_TRACE_SEED="external-seed"
    )
    assert {root.trace_id for root in roots(seeded)} == {
        hashlib.sha256(f"external-seed:{turn}".encode()).hexdigest()[:32] for turn in (1, 2, 3)
    }
    again = run_live_hook(
        transcript, SESSION_ID, tmp_path / "second", CC_LANGFUSE_TRACE_SEED="external-seed"
    )
    assert again == seeded


def test_attached_turns_nest_under_the_parent_with_reproducible_ids(tmp_path: Path) -> None:
    transcript = write_session(tmp_path / "projects", SESSION_ID)
    traceparent = f"00-{PARENT_TRACE_ID}-{PARENT_SPAN_ID}-01"
    attached = run_live_hook(
        transcript, SESSION_ID, tmp_path / "first", CC_LANGFUSE_TRACEPARENT=traceparent
    )
    assert {identity.trace_id for identity in attached} == {PARENT_TRACE_ID}
    assert {root.parent_span_id for root in roots(attached)} == {PARENT_SPAN_ID}
    assert len({identity.span_id for identity in attached}) == len(attached)
    again = run_live_hook(
        transcript, SESSION_ID, tmp_path / "second", CC_LANGFUSE_TRACEPARENT=traceparent
    )
    assert again == attached


def test_id_requests_without_a_transcript_pin_fail_instead_of_going_random() -> None:
    generator = load_hook().TranscriptIdGenerator()
    with pytest.raises(RuntimeError, match="pin"):
        generator.generate_span_id()
    with pytest.raises(RuntimeError, match="trace context"):
        generator.generate_trace_id()


def test_colliding_keys_resolve_to_the_same_distinct_ids_in_every_run() -> None:
    hook = load_hook()

    def issue_three_siblings() -> list[int]:
        generator = hook.TranscriptIdGenerator()
        issued = []
        for _ in range(3):
            with generator.pinned(int(PARENT_TRACE_ID, 16), int(PARENT_SPAN_ID, 16), "gen:noid:0"):
                issued.append(generator.generate_span_id())
        return issued

    first = issue_three_siblings()
    assert len(set(first)) == 3
    assert issue_three_siblings() == first


def test_client_whose_tracer_generates_random_ids_is_rejected() -> None:
    hook = load_hook()
    id_generators = importlib.import_module("opentelemetry.sdk.trace.id_generator")
    tracer = SimpleNamespace(id_generator=id_generators.RandomIdGenerator())
    with pytest.raises(RuntimeError, match="TranscriptIdGenerator"):
        hook._transcript_id_generator(SimpleNamespace(_otel_tracer=tracer))
