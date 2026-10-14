#!/usr/bin/env python3
"""
Universal event logger for Claude Code and Antigravity CLI.
Logs all hook events (PreToolUse, PostToolUse, etc.) as JSONL.
"""

import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path

# Deployed artefacts whose content decides the engine's behaviour. Their digests
# are stamped on every SessionStart record so a session can be attributed to the
# exact rules it ran under; the same digest is emitted as a Langfuse trace tag by
# settings.json's CC_LANGFUSE_TRACE_TAGS (via ai-config's file_sha256), so the
# two records join on it.
STAMPED_ARTEFACTS: dict[str, str] = {
    "rules_sha256": "CLAUDE.md",
    "settings_sha256": "settings.json",
}
STAMPED_EVENTS = frozenset({"SessionStart"})


def sha256_of(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def version_stamp(config_root: Path, payload: dict[str, object]) -> dict[str, object]:
    stamp: dict[str, object] = {
        name: sha256_of(config_root / relative) for name, relative in STAMPED_ARTEFACTS.items()
    }
    stamp["model"] = payload.get("model")
    return stamp


def build_log_entry(
    event_name: str, payload: dict[str, object], config_root: Path
) -> dict[str, object]:
    env_metadata = {
        "CC_TOOL_NAME": os.environ.get("CC_TOOL_NAME"),
        "CC_BASH_COMMAND": os.environ.get("CC_BASH_COMMAND"),
        "TOOL_COUNT": os.environ.get("TOOL_COUNT"),
        "SESSION_ID": os.environ.get("SESSION_ID"),
    }
    entry: dict[str, object] = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "event": event_name,
        "env": {k: v for k, v in env_metadata.items() if v is not None},
        "payload": payload,
        "cwd": str(Path.cwd()),
    }
    if event_name in STAMPED_EVENTS:
        entry["stamp"] = version_stamp(config_root, payload)
    return entry


def main() -> None:
    event_name = sys.argv[1] if len(sys.argv) > 1 else "UnknownEvent"

    raw_stdin = sys.stdin.read().strip()
    try:
        payload = json.loads(raw_stdin) if raw_stdin else {}
    except json.JSONDecodeError:
        payload = {"raw_unparsed": raw_stdin}

    # Automatically determine the config root (.claude or .gemini/antigravity-cli)
    script_path = Path(__file__).resolve()
    config_root = script_path.parent.parent
    log_entry = build_log_entry(event_name, payload, config_root)
    state_dir = config_root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    log_file = state_dir / "hook_events.jsonl"
    lock_file = state_dir / "hook_events.lock"

    with lock_file.open("w") as lck:
        fcntl.flock(lck, fcntl.LOCK_EX)
        try:
            # Rotate log if it exceeds 500 MB
            max_size = 500 * 1024 * 1024
            if log_file.exists() and log_file.stat().st_size >= max_size:
                ts = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
                rotated_file = state_dir / f"hook_events.{ts}.jsonl"
                with contextlib.suppress(OSError):
                    log_file.rename(rotated_file)

            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        finally:
            fcntl.flock(lck, fcntl.LOCK_UN)

    sys.exit(0)


if __name__ == "__main__":
    main()
