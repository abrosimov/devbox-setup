"""The in-process span queue between the Langfuse SDK and the durable spool.

A span the OpenTelemetry batch processor drops never reaches the spool, so the
queue must hold a whole firing, and a firing that still loses one must fail
without advancing its checkpoint, leaving the turn to the next firing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from opentelemetry.proto.collector.trace.v1 import trace_service_pb2 as trace_service

BIN = Path(__file__).parent
GATED_RUN = BIN / "testdata" / "langfuse_gated_run.py"
SESSION_ID = "0c9b6e2a-5d1f-4b8e-9a37-2f4c6d8e0001"
SDK_DEFAULT_QUEUE_SIZE = 2048
SDK_DEFAULT_EXPORT_BATCH = 512


@dataclass(frozen=True)
class Home:
    path: Path

    @property
    def state(self) -> Path:
        return self.path / ".claude" / "state"

    @property
    def spool(self) -> Path:
        return self.state / "langfuse_otlp_spool"

    @property
    def checkpoint(self) -> Path:
        return self.state / "langfuse_state.json"


def turn_rows(turn: int, tool_calls: int) -> list[dict[str, object]]:
    prefix = f"t{turn}"
    minute = f"2026-11-01T17:{20 + turn}"
    rows: list[dict[str, object]] = [
        {
            "type": "user",
            "uuid": f"{prefix}-prompt",
            "sessionId": SESSION_ID,
            "timestamp": f"{minute}:00.000Z",
            "message": {"role": "user", "content": f"Survey every module, pass {turn}"},
        }
    ]
    for call in range(tool_calls):
        tool_use_id = f"toolu_{prefix}_{call:06d}"
        rows.extend(
            [
                {
                    "type": "assistant",
                    "uuid": f"{prefix}-a-{call:06d}",
                    "sessionId": SESSION_ID,
                    "timestamp": f"{minute}:01.000Z",
                    "message": {
                        "id": f"msg_{prefix}_{call:06d}",
                        "role": "assistant",
                        "model": "claude-test",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": tool_use_id,
                                "name": "Read",
                                "input": {"file_path": f"/src/module_{call}.py"},
                            }
                        ],
                    },
                },
                {
                    "type": "user",
                    "uuid": f"{prefix}-r-{call:06d}",
                    "sessionId": SESSION_ID,
                    "timestamp": f"{minute}:02.000Z",
                    "message": {
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}
                        ],
                    },
                },
            ]
        )
    rows.append(
        {
            "type": "assistant",
            "uuid": f"{prefix}-final",
            "sessionId": SESSION_ID,
            "timestamp": f"{minute}:03.000Z",
            "message": {
                "id": f"msg_{prefix}_final",
                "role": "assistant",
                "model": "claude-test",
                "content": [{"type": "text", "text": "Every module surveyed."}],
            },
        }
    )
    return rows


def spans_of_turn(tool_calls: int) -> int:
    # The turn itself, one generation per assistant message and one span per tool call.
    return 1 + (tool_calls + 1) + tool_calls


def append_turn(transcript: Path, turn: int, tool_calls: int) -> None:
    transcript.parent.mkdir(parents=True, exist_ok=True)
    with transcript.open("a", encoding="utf-8") as out:
        out.writelines(json.dumps(row) + "\n" for row in turn_rows(turn, tool_calls))


def fire(
    home: Home, transcript: Path, entry: str, **extra: str
) -> subprocess.CompletedProcess[str]:
    ambient = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("LANGFUSE_", "CC_LANGFUSE_", "OTEL_"))
    }
    edge = {
        "HOME": str(home.path),
        "CC_LANGFUSE_BASE_URL": "http://127.0.0.1:9",
        "CC_LANGFUSE_PUBLIC_KEY": "pk-lf-span-queue",
        "CC_LANGFUSE_SECRET_KEY": "sk-lf-span-queue",
    }
    payload = {
        "session_id": SESSION_ID,
        "transcript_path": str(transcript),
        "hook_event_name": "Stop",
    }
    return subprocess.run(
        [sys.executable, str(GATED_RUN), str(BIN), entry],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
        env=ambient | edge | extra,
    )


def hook_log(home: Home) -> str:
    log = home.state / "langfuse_hook.log"
    return log.read_text(encoding="utf-8") if log.is_file() else ""


def spooled_spans(home: Home) -> int:
    total = 0
    for batch in home.spool.glob("*.otlp"):
        request = trace_service.ExportTraceServiceRequest.FromString(batch.read_bytes())
        total += sum(
            len(scope.spans)
            for resource in request.resource_spans
            for scope in resource.scope_spans
        )
    return total


def staged_batches(home: Home) -> list[Path]:
    return sorted(home.spool.glob(".staging/*/*.otlp"))


def test_turn_larger_than_the_sdk_default_queue_is_spooled_whole(tmp_path: Path) -> None:
    home = Home(tmp_path / "home")
    transcript = tmp_path / "projects" / f"{SESSION_ID}.jsonl"
    # Beyond the default queue plus the batch the held export worker has already taken.
    tool_calls = (SDK_DEFAULT_QUEUE_SIZE + SDK_DEFAULT_EXPORT_BATCH) // 2 + 100
    append_turn(transcript, 1, tool_calls)

    result = fire(home, transcript, "wrapper")

    assert result.returncode == 0, f"{result.stderr[-2000:]}\n{hook_log(home)}"
    assert spooled_spans(home) == spans_of_turn(tool_calls)
    assert not staged_batches(home)


def test_dropped_span_fails_the_firing_and_the_next_firing_re_emits_the_turn(
    tmp_path: Path,
) -> None:
    home = Home(tmp_path / "home")
    transcript = tmp_path / "projects" / f"{SESSION_ID}.jsonl"
    append_turn(transcript, 1, tool_calls=1)
    first = fire(home, transcript, "vendored")
    assert first.returncode == 0, f"{first.stderr}\n{hook_log(home)}"
    checkpoint = home.checkpoint.read_bytes()
    spooled = spooled_spans(home)
    append_turn(transcript, 2, tool_calls=3)

    overflowing = fire(
        home, transcript, "vendored", OTEL_BSP_MAX_QUEUE_SIZE="1", LANGFUSE_FLUSH_AT="1"
    )

    assert overflowing.returncode == 1, f"{overflowing.stderr}\n{hook_log(home)}"
    assert "lost a span" in overflowing.stderr
    assert "SpanLossError" in hook_log(home)
    assert home.checkpoint.read_bytes() == checkpoint
    assert spooled_spans(home) == spooled
    assert not staged_batches(home)

    retried = fire(home, transcript, "vendored")

    assert retried.returncode == 0, f"{retried.stderr}\n{hook_log(home)}"
    assert home.checkpoint.read_bytes() != checkpoint
    assert spooled_spans(home) == spooled + spans_of_turn(3)
