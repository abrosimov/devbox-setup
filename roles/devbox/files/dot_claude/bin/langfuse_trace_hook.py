#!/usr/bin/env python3
"""Credential-safe Claude Langfuse hook with a durable local retry intent."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import MutableMapping

# Operator API credentials are never exported through the unauthenticated edge.
SHADOWING_VARIABLES: Final[tuple[str, ...]] = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_HOST",
)
VENDORED_HOOK: Final[Path] = Path(__file__).resolve().parent / "vendor" / "langfuse_hook.py"
REPLAY_ENV: Final = "CC_LANGFUSE_PENDING_REPLAY"


def scrub_shadowing_credentials(environment: MutableMapping[str, str]) -> None:
    for name in SHADOWING_VARIABLES:
        environment.pop(name, None)


def pending_root() -> Path:
    state = Path(os.environ.get("CC_LANGFUSE_STATE_DIR") or Path.home() / ".claude/state")
    return state.expanduser() / "langfuse_pending"


def pending_key(session_id: str, transcript_path: Path) -> str:
    return hashlib.sha256(f"{session_id}::{transcript_path}".encode()).hexdigest()


def fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as out:
            temporary.chmod(0o600)
            json.dump(value, out, sort_keys=True)
            out.flush()
            os.fsync(out.fileno())
        temporary.replace(path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def durable_snapshot(source: Path, destination: Path) -> None:
    """Keep a replayable transcript even if Claude rotates/removes its original."""
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        # APFS clonefile avoids copying multi-megabyte transcripts on each Stop.
        if sys.platform == "darwin":
            try:
                subprocess.run(
                    ["/bin/cp", "-c", str(source), str(temporary)],
                    check=True, capture_output=True, timeout=30,
                )
            except (OSError, subprocess.SubprocessError):
                shutil.copyfile(source, temporary)
        else:
            shutil.copyfile(source, temporary)
        os.chmod(temporary, 0o600)
        with temporary.open("rb") as copied:
            os.fsync(copied.fileno())
        temporary.replace(destination)
        fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def hook_identity(payload: dict) -> tuple[str, Path] | None:
    session_id = payload.get("session_id") or payload.get("sessionId")
    path = payload.get("transcript_path") or payload.get("transcriptPath")
    if not isinstance(session_id, str) or not isinstance(path, str):
        return None
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        return None
    return session_id, source


def register_pending(payload: dict) -> tuple[Path, str, Path] | None:
    identity = hook_identity(payload)
    if identity is None:
        return None
    session_id, source = identity
    key = pending_key(session_id, source)
    nonce = uuid.uuid4().hex
    root = pending_root()
    snapshot = root / f"{key}.{nonce}" / source.name
    durable_snapshot(source, snapshot)
    marker = root / f"{key}.json"
    record = {
        "schema_version": 1,
        "nonce": nonce,
        "session_id": session_id,
        "transcript_path": str(source),
        "snapshot_path": str(snapshot),
        "hook_event_name": payload.get("hook_event_name") or payload.get("hookEventName") or "Stop",
        "environment": os.environ.get("LANGFUSE_TRACING_ENVIRONMENT", ""),
        "user_id": os.environ.get("LANGFUSE_USER_ID", ""),
        "trace_tags": os.environ.get("CC_LANGFUSE_TRACE_TAGS", ""),
        "trace_seed": os.environ.get("CC_LANGFUSE_TRACE_SEED", ""),
        "traceparent": os.environ.get("CC_LANGFUSE_TRACEPARENT", ""),
    }
    durable_json(marker, record)
    return marker, nonce, snapshot


def complete_pending(marker: Path, nonce: str, snapshot: Path) -> None:
    """Do not delete a newer Stop's marker while an older hook is finishing."""
    try:
        current = json.loads(marker.read_text(encoding="utf-8"))
        if current.get("nonce") == nonce:
            marker.unlink()
            fsync_directory(marker.parent)
    except FileNotFoundError:
        pass
    # Every registration owns a distinct immutable snapshot.
    snapshot.unlink(missing_ok=True)
    with contextlib.suppress(OSError):
        snapshot.parent.rmdir()


def main() -> None:
    scrub_shadowing_credentials(os.environ)
    # The replay runner supplies a minimal, known hook payload through stdin.
    try:
        raw = sys.stdin.read()
    except OSError:
        raw = ""
    payload = {}
    if raw:
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                payload = obj
        except ValueError:
            pass

    pending = None
    if not os.environ.get(REPLAY_ENV) and payload:
        pending = register_pending(payload)

    sys.path[0] = str(VENDORED_HOOK.parent)
    original_stdin = sys.stdin
    try:
        if raw:
            sys.stdin = io.StringIO(raw)
        try:
            runpy.run_path(str(VENDORED_HOOK), run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise
        if pending is not None:
            marker, nonce, snapshot = pending
            record = json.loads(marker.read_text(encoding="utf-8"))
            if Path(record["transcript_path"]).is_file():
                complete_pending(marker, nonce, snapshot)
            # An original removed during export may make the vendored hook
            # return without processing; retain its durable snapshot for replay.
    finally:
        sys.stdin = original_stdin


if __name__ == "__main__":
    main()
