#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks

SESSIONS_ROOT: Final[Path] = Path("/tmp/claude/sessions")  # noqa: S108
SESSION_TTL_SECONDS: Final[int] = 7 * 24 * 60 * 60
UNKNOWN_SESSION: Final[str] = "unknown"

CACHE_VARS: Final[dict[str, str]] = {
    "UV_CACHE_DIR": "uv-cache",
    "RUFF_CACHE_DIR": "ruff-cache",
    "MYPY_CACHE_DIR": "mypy-cache",
    "PYTEST_CACHE_DIR": "pytest-cache",
    "GOCACHE": "go-build-cache",
    "GOMODCACHE": "go-mod-cache",
    "NPM_CONFIG_CACHE": "npm-cache",
}

SAFE_SESSION_RE: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9_-]+")
DASH_RUN_RE: Final[re.Pattern[str]] = re.compile(r"-{2,}")

# boundary_wrap owns rewriting of these commands (adds untrusted-content tags).
# Cache env vars are irrelevant for gh/git-log/show/blame — skip to avoid
# clobbering boundary_wrap's updatedInput.
BOUNDARY_WRAP_TRIGGERS_RE: Final[re.Pattern[str]] = re.compile(
    r"^(gh(\s|$)|git\s+(log|show|blame)(\s|$))",
)


@dataclass(frozen=True)
class SessionCache:
    session_id: str
    root: Path
    variables: dict[str, str]


def sanitise_session_id(session_id: str) -> str:
    replaced = SAFE_SESSION_RE.sub("-", session_id)
    collapsed = DASH_RUN_RE.sub("-", replaced).strip("-")
    return collapsed or UNKNOWN_SESSION


def compute_session_cache(
    session_id: str, sessions_root: Path | None = None,
) -> SessionCache:
    safe = sanitise_session_id(session_id)
    base = sessions_root if sessions_root is not None else SESSIONS_ROOT
    root = base / safe
    variables = {name: str(root / subdir) for name, subdir in CACHE_VARS.items()}
    return SessionCache(session_id=safe, root=root, variables=variables)


def ensure_cache_dirs(cache: SessionCache) -> None:
    for path in cache.variables.values():
        Path(path).mkdir(parents=True, exist_ok=True)


def prune_stale_sessions(
    sessions_root: Path | None = None,
    keep_session_id: str | None = None,
    now: float | None = None,
) -> None:
    base = sessions_root if sessions_root is not None else SESSIONS_ROOT
    if not base.exists():
        return
    cutoff = (now if now is not None else time.time()) - SESSION_TTL_SECONDS
    try:
        entries = list(os.scandir(base))
    except OSError:
        return
    for entry in entries:
        if keep_session_id is not None and entry.name == keep_session_id:
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry.path, ignore_errors=True)
        except OSError:
            continue


def build_env_prefix(cache: SessionCache) -> str:
    assignments = " ".join(
        f"{name}={value}" for name, value in cache.variables.items()
    )
    return f"export {assignments};"


def wrap_command(cmd: str, cache: SessionCache) -> str:
    return f"{build_env_prefix(cache)} {cmd}"


def should_skip(cmd: str) -> bool:
    return bool(BOUNDARY_WRAP_TRIGGERS_RE.match(cmd))


def emit_updated_command(updated: str) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {"command": updated},
        },
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW

    tool_input_value = data.get("tool_input", {})
    if not isinstance(tool_input_value, dict):
        return hooks.ALLOW
    command_value = tool_input_value.get("command", "")
    cmd = command_value if isinstance(command_value, str) else ""
    if not cmd or should_skip(cmd):
        return hooks.ALLOW

    session_value = data.get("session_id", UNKNOWN_SESSION)
    session_id = session_value if isinstance(session_value, str) else UNKNOWN_SESSION

    cache = compute_session_cache(session_id)
    ensure_cache_dirs(cache)
    prune_stale_sessions(keep_session_id=cache.session_id)
    emit_updated_command(wrap_command(cmd, cache))
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
