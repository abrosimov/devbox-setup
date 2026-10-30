"""Disk budget of the OTLP spool and the transcript-snapshot store.

A full store refuses new data and fails the hook on stderr; it never deletes
undelivered data to make room, and replay keeps draining so it recovers.
"""

from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import langfuse_trace_hook
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

pytest.importorskip("langfuse")

BIN = Path(__file__).parent
WRAPPER = BIN / "langfuse_trace_hook.py"
REPLAY = BIN / "langfuse_replay.py"
SESSION_ID = "6b1d4c1e-2f53-4d1f-9a43-0c3a5e7d0001"
OTHER_SESSION_ID = "6b1d4c1e-2f53-4d1f-9a43-0c3a5e7d0002"
TRACES_PATH = "/api/public/otel/v1/traces"


@dataclass
class FakeEdge:
    base_url: str
    bodies: list[bytes] = field(default_factory=list)


@pytest.fixture
def fake_edge() -> Iterator[FakeEdge]:
    edge = FakeEdge(base_url="")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            status = 200 if self.path == TRACES_PATH else 404
            if status == 200:
                edge.bodies.append(body)
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    edge.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield edge
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


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
    def pending(self) -> Path:
        return self.state / "langfuse_pending"


def make_home(root: Path, base_url: str = "http://127.0.0.1:9") -> Home:
    settings = {
        "env": {
            "CC_LANGFUSE_BASE_URL": base_url,
            "CC_LANGFUSE_PUBLIC_KEY": "pk-lf-capacity",
            "CC_LANGFUSE_SECRET_KEY": "sk-lf-capacity",
        }
    }
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    return Home(root)


def write_transcript(directory: Path, session_id: str) -> Path:
    rows = [
        {
            "type": "user",
            "uuid": f"{session_id}-u1",
            "sessionId": session_id,
            "timestamp": "2026-10-01T10:00:00.000Z",
            "message": {"role": "user", "content": "Summarise the notes"},
        },
        {
            "type": "assistant",
            "sessionId": session_id,
            "timestamp": "2026-10-01T10:00:01.000Z",
            "message": {
                "id": f"{session_id}-m1",
                "role": "assistant",
                "model": "claude-test",
                "content": [{"type": "text", "text": "The notes say hello. " * 20}],
            },
        },
    ]
    transcript = directory / f"{session_id}.jsonl"
    directory.mkdir(parents=True, exist_ok=True)
    transcript.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return transcript


def ambient_environment() -> dict[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("LANGFUSE_", "CC_LANGFUSE_"))
    }


def run_hook(
    home: Home, transcript: Path, session_id: str, **extra: str
) -> subprocess.CompletedProcess[str]:
    settings = json.loads((home.path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    payload = {
        "session_id": session_id,
        "transcript_path": str(transcript),
        "hook_event_name": "Stop",
    }
    return subprocess.run(
        [sys.executable, str(WRAPPER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
        env=ambient_environment() | settings["env"] | {"HOME": str(home.path)} | extra,
    )


def run_replay(home: Home, **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPLAY)],
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
        env=ambient_environment() | {"HOME": str(home.path)} | extra,
    )


def hook_log(home: Home) -> str:
    log = home.state / "langfuse_hook.log"
    return log.read_text(encoding="utf-8") if log.is_file() else ""


def contents(directory: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def committed_batches(home: Home) -> list[Path]:
    return sorted(home.spool.glob("*.otlp"))


def fill_spool(home: Home, size: int) -> dict[str, bytes]:
    home.spool.mkdir(parents=True)
    (home.spool / f"{0:020d}-undelivered.otlp").write_bytes(b"\x0a" * size)
    return contents(home.spool)


def register_other_session(home: Home, transcript: Path) -> dict[str, bytes]:
    payload = {
        "session_id": OTHER_SESSION_ID,
        "transcript_path": str(transcript),
        "hook_event_name": "Stop",
    }
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CC_LANGFUSE_STATE_DIR", str(home.state))
        assert langfuse_trace_hook.register_pending(payload) is not None
    return contents(home.pending)


@pytest.fixture
def batch_bytes(tmp_path: Path) -> int:
    home = make_home(tmp_path / "reference")
    transcript = write_transcript(tmp_path / "reference-projects", SESSION_ID)
    result = run_hook(home, transcript, SESSION_ID)
    assert result.returncode == 0, f"{result.stderr}\n{hook_log(home)}"
    return sum(path.stat().st_size for path in committed_batches(home))


def test_full_spool_refuses_new_spans_and_fails_the_hook_naming_cap_and_path(
    tmp_path: Path, batch_bytes: int
) -> None:
    home = make_home(tmp_path / "home")
    # Replayed batches carry the marker's attributes, so leave headroom either way.
    undelivered = fill_spool(home, batch_bytes + batch_bytes // 2)
    cap = str(2 * batch_bytes)
    transcript = write_transcript(tmp_path / "projects", SESSION_ID)

    result = run_hook(home, transcript, SESSION_ID, CC_LANGFUSE_SPOOL_MAX_BYTES=cap)

    assert result.returncode != 0
    assert f"CC_LANGFUSE_SPOOL_MAX_BYTES={cap}" in result.stderr
    assert str(home.spool) in result.stderr
    committed = {name: data for name, data in contents(home.spool).items() if "/" not in name}
    assert committed == undelivered
    assert len(list(home.pending.glob("*.json"))) == 1


def test_replay_drains_a_full_spool_and_then_delivers_the_refused_session(
    tmp_path: Path, batch_bytes: int, fake_edge: FakeEdge
) -> None:
    home = make_home(tmp_path / "home", fake_edge.base_url)
    # Replayed batches carry the marker's attributes, so leave headroom either way.
    undelivered = fill_spool(home, batch_bytes + batch_bytes // 2)
    cap = str(2 * batch_bytes)
    transcript = write_transcript(tmp_path / "projects", SESSION_ID)
    refused = run_hook(home, transcript, SESSION_ID, CC_LANGFUSE_SPOOL_MAX_BYTES=cap)
    assert refused.returncode != 0

    replay = run_replay(home, CC_LANGFUSE_SPOOL_MAX_BYTES=cap)

    assert replay.returncode == 0, f"{replay.stdout}\n{replay.stderr}\n{hook_log(home)}"
    assert fake_edge.bodies[0] == next(iter(undelivered.values()))
    assert len(fake_edge.bodies) > 1
    assert not committed_batches(home)
    assert not list(home.pending.glob("*.json"))


def test_full_pending_store_refuses_the_snapshot_but_still_spools_the_turns(
    tmp_path: Path,
) -> None:
    home = make_home(tmp_path / "home")
    held = register_other_session(home, write_transcript(tmp_path / "projects", OTHER_SESSION_ID))
    transcript = write_transcript(tmp_path / "projects", SESSION_ID)
    cap = str(sum(map(len, held.values())) + transcript.stat().st_size - 1)

    result = run_hook(home, transcript, SESSION_ID, CC_LANGFUSE_PENDING_MAX_BYTES=cap)

    assert result.returncode == 1
    assert f"CC_LANGFUSE_PENDING_MAX_BYTES={cap}" in result.stderr
    assert str(home.pending) in result.stderr
    assert contents(home.pending) == held
    assert committed_batches(home), hook_log(home)


def test_pending_store_admits_snapshots_again_once_replay_clears_it(
    tmp_path: Path, fake_edge: FakeEdge
) -> None:
    home = make_home(tmp_path / "home", fake_edge.base_url)
    held = register_other_session(home, write_transcript(tmp_path / "projects", OTHER_SESSION_ID))
    transcript = write_transcript(tmp_path / "projects", SESSION_ID)
    cap = str(sum(map(len, held.values())) + transcript.stat().st_size - 1)
    assert run_hook(home, transcript, SESSION_ID, CC_LANGFUSE_PENDING_MAX_BYTES=cap).returncode

    replay = run_replay(home, CC_LANGFUSE_PENDING_MAX_BYTES=cap)
    assert replay.returncode == 0, f"{replay.stdout}\n{replay.stderr}\n{hook_log(home)}"
    again = run_hook(home, transcript, SESSION_ID, CC_LANGFUSE_PENDING_MAX_BYTES=cap)

    assert again.returncode == 0, f"{again.stderr}\n{hook_log(home)}"
    assert "CC_LANGFUSE_PENDING_MAX_BYTES" not in again.stderr
    assert not list(home.pending.glob("*.json"))


def test_re_registering_a_session_does_not_count_the_snapshot_it_replaces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CC_LANGFUSE_STATE_DIR", str(tmp_path / "state"))
    transcript = write_transcript(tmp_path / "projects", SESSION_ID)
    payload = {"session_id": SESSION_ID, "transcript_path": str(transcript)}
    first = langfuse_trace_hook.register_pending(payload)
    assert first is not None
    marker_bytes = first[0].stat().st_size
    monkeypatch.setenv(
        "CC_LANGFUSE_PENDING_MAX_BYTES", str(transcript.stat().st_size + marker_bytes)
    )

    second = langfuse_trace_hook.register_pending(payload)

    assert second is not None
    assert second[2].is_file()
    assert not first[2].exists()


def test_invalid_pending_cap_is_named_rather_than_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CC_LANGFUSE_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("CC_LANGFUSE_PENDING_MAX_BYTES", "two gigabytes")
    transcript = write_transcript(tmp_path / "projects", SESSION_ID)

    with pytest.raises(ValueError, match="CC_LANGFUSE_PENDING_MAX_BYTES"):
        langfuse_trace_hook.register_pending(
            {"session_id": SESSION_ID, "transcript_path": str(transcript)}
        )
