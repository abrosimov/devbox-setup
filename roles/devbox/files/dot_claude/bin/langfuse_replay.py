#!/usr/bin/env python3
"""Replay unfinished Claude Langfuse sessions from the durable pending registry.

Run using ~/.claude/bin/.venv/bin/python, independently of Claude Code. The
registry stores sanitized session metadata and a transcript snapshot, never
project secrets or user prompts in a LaunchAgent configuration.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import langfuse_trace_hook as hook

SETTINGS = Path.home() / ".claude" / "settings.json"
WRAPPER = Path(__file__).resolve().parent / "langfuse_trace_hook.py"
REQUIRED = ("CC_LANGFUSE_PUBLIC_KEY", "CC_LANGFUSE_SECRET_KEY", "CC_LANGFUSE_BASE_URL")
REPLAY_SETTINGS = (
    *REQUIRED,
    "CC_LANGFUSE_CAPTURE_IMAGES",
    "CC_LANGFUSE_DEBUG",
    "CC_LANGFUSE_STATE_DIR",
    "CC_LANGFUSE_SPOOL_MAX_BYTES",
    "CC_LANGFUSE_PENDING_MAX_BYTES",
)
LEGACY_MARKER_FIELDS = {
    "CC_LANGFUSE_TRACE_SEED": "trace_seed",
    "CC_LANGFUSE_TRACEPARENT": "traceparent",
}
LOOPBACK_PREFIXES = ("http://127.0.0.1:", "http://localhost:")


def replay_environment() -> dict[str, str]:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    configured = settings.get("env", {})
    if not isinstance(configured, dict):
        message = "Claude settings.env must be an object"
        raise TypeError(message)
    if any(not isinstance(configured.get(name), str) or not configured[name] for name in REQUIRED):
        message = "Missing local-edge Langfuse runtime configuration"
        raise ValueError(message)
    url = configured["CC_LANGFUSE_BASE_URL"]
    if not url.startswith(LOOPBACK_PREFIXES):
        message = "Replay exporter must target a loopback collector"
        raise ValueError(message)
    environment = dict(os.environ)
    # Run-scoped settings only reach a replay whose marker predates run_environment.
    for key in (*REPLAY_SETTINGS, *hook.RUN_SCOPED_VARIABLES):
        if isinstance(configured.get(key), str):
            environment[key] = configured[key]
    environment[hook.REPLAY_ENV] = "1"
    return environment


def restore_run_environment(environment: dict[str, str], record: dict[str, object]) -> None:
    recorded = record.get("run_environment")
    if not isinstance(recorded, dict):
        # Legacy marker: it carried these two; the rest stay as settings.json gives them.
        for name, field in LEGACY_MARKER_FIELDS.items():
            value = record.get(field, "")
            environment[name] = value if isinstance(value, str) else ""
        return
    # The marker records what the run had, absence included, so settings.json cannot override it.
    for name in hook.RUN_SCOPED_VARIABLES:
        value = recorded.get(name)
        if isinstance(value, str):
            environment[name] = value
        else:
            environment.pop(name, None)


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
    restore_run_environment(environment, record)
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
    # A full spool or a quarantined span is named on the hook's stderr; the LaunchAgent log
    # is its only witness, on success as well as on failure.
    if result.stderr:
        sys.stderr.write(result.stderr)
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


def codex_spool() -> Path:
    # The vendored Codex hook resolves its configuration and spool from HOME the same way.
    return Path.home() / ".codex" / "langfuse_state" / "langfuse_otlp_spool"


def codex_base_url() -> str:
    config = json.loads((Path.home() / ".codex" / "langfuse.json").read_text(encoding="utf-8"))
    url = config.get("base_url") if isinstance(config, dict) else None
    if not isinstance(url, str) or not url.startswith(LOOPBACK_PREFIXES):
        message = "Codex Langfuse base_url must target a loopback collector"
        raise ValueError(message)
    return url


def drain_codex_spool() -> tuple[int, int]:
    spool = codex_spool()
    if not spool.is_dir():
        return 0, 0
    try:
        base_url = codex_base_url()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Codex Langfuse spool not drained: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0, len(list(spool.glob("*.otlp")))
    exporter = importlib.import_module("vendor.durable_otel_exporter")
    return exporter.drain_spool(base_url, directory=spool)


def main() -> int:
    # The Codex spool needs nothing from Claude's settings, so their absence does not hold it up.
    codex_sent, codex_pending = drain_codex_spool()
    try:
        environment = replay_environment()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Langfuse replay configuration unavailable: {type(exc).__name__}", file=sys.stderr)
        return 1

    base_url = environment["CC_LANGFUSE_BASE_URL"]
    # Deliver batches which were already fsynced before replaying transcripts;
    # an unavailable edge never deletes local OTLP payloads.
    from vendor.durable_otel_exporter import drain_spool  # noqa: PLC0415

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
        f"otlp_pending={pending_batches}, codex_otlp_sent={codex_sent}, "
        f"codex_otlp_pending={codex_pending}"
    )
    return 1 if failed or pending_batches or codex_pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
