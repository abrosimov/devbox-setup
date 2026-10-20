#!/usr/bin/env python3
"""Replay unfinished Claude Langfuse sessions from the durable pending registry.

Run using ~/.claude/bin/.venv/bin/python, independently of Claude Code. The
registry stores sanitized session metadata and a transcript snapshot, never
project secrets or user prompts in a LaunchAgent configuration.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import langfuse_trace_hook as hook
from vendor.durable_otel_exporter import drain_spool

SETTINGS = Path.home() / ".claude" / "settings.json"
WRAPPER = Path(__file__).resolve().parent / "langfuse_trace_hook.py"
REQUIRED = ("CC_LANGFUSE_PUBLIC_KEY", "CC_LANGFUSE_SECRET_KEY", "CC_LANGFUSE_BASE_URL")
REPLAY_SETTINGS = (*REQUIRED, "CC_LANGFUSE_CAPTURE_IMAGES", "CC_LANGFUSE_DEBUG",
                   "CC_LANGFUSE_STATE_DIR")


def replay_environment() -> dict[str, str]:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    configured = settings.get("env", {})
    if not isinstance(configured, dict):
        message = "Claude settings.env must be an object"
        raise TypeError(message)
    if any(not isinstance(configured.get(name), str) or not configured[name]
           for name in REQUIRED):
        message = "Missing local-edge Langfuse runtime configuration"
        raise ValueError(message)
    url = configured["CC_LANGFUSE_BASE_URL"]
    if not url.startswith(("http://127.0.0.1:", "http://localhost:")):
        message = "Replay exporter must target a loopback collector"
        raise ValueError(message)
    environment = dict(os.environ)
    for key in REPLAY_SETTINGS:
        if isinstance(configured.get(key), str):
            environment[key] = configured[key]
    environment[hook.REPLAY_ENV] = "1"
    return environment


def replay_one(marker: Path, base_env: dict[str, str]) -> bool:
    record = json.loads(marker.read_text(encoding="utf-8"))
    if record.get("schema_version") != 1 or not isinstance(record.get("nonce"), str):
        message = "Unsupported pending marker format"
        raise ValueError(message)
    session_id = record["session_id"]
    original = Path(record["transcript_path"])
    snapshot = Path(record["snapshot_path"])
    if not snapshot.is_file():
        message = f"Pending transcript snapshot missing: {marker.name}"
        raise FileNotFoundError(message)
    transcript = original if original.is_file() else snapshot
    payload = {
        "session_id": session_id,
        "transcript_path": str(transcript),
        "hook_event_name": record["hook_event_name"],
    }
    environment = dict(base_env)
    environment["LANGFUSE_USER_ID"] = record.get("user_id", "")
    environment["LANGFUSE_TRACING_ENVIRONMENT"] = record.get("environment", "")
    environment["CC_LANGFUSE_TRACE_TAGS"] = record.get("trace_tags", "")
    environment["CC_LANGFUSE_TRACE_SEED"] = record.get("trace_seed", "")
    environment["CC_LANGFUSE_TRACEPARENT"] = record.get("traceparent", "")
    if transcript != original:
        environment["CC_LANGFUSE_STATE_IDENTITY_PATH"] = str(original)

    result = subprocess.run(
        [sys.executable, str(WRAPPER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
        env=environment,
    )
    if result.returncode != 0:
        return False
    # Re-read the marker to avoid deleting a newer Stop/SessionEnd registration.
    try:
        latest = json.loads(marker.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return True
    if latest.get("nonce") == record["nonce"]:
        hook.complete_pending(marker, record["nonce"], snapshot)
    return True


def main() -> int:
    try:
        environment = replay_environment()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Langfuse replay configuration unavailable: {type(exc).__name__}", file=sys.stderr)
        return 1

    base_url = environment["CC_LANGFUSE_BASE_URL"]
    # Deliver batches which were already fsynced before replaying transcripts;
    # an unavailable edge never deletes local OTLP payloads.
    sent_before, _pending_before = drain_spool(base_url)

    root = hook.pending_root()
    attempted = failed = 0
    for marker in sorted(root.glob("*.json")) if root.exists() else []:
        attempted += 1
        try:
            if not replay_one(marker, environment):
                failed += 1
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
            print(f"Replay still pending: {marker.name} ({type(exc).__name__})", file=sys.stderr)
            failed += 1
    sent_after, pending_batches = drain_spool(base_url)
    print(
        f"Langfuse replay: sessions_attempted={attempted}, "
        f"sessions_pending={failed}, otlp_sent={sent_before + sent_after}, "
        f"otlp_pending={pending_batches}"
    )
    return 1 if failed or pending_batches else 0


if __name__ == "__main__":
    raise SystemExit(main())
