from __future__ import annotations

import json
import sys
from typing import Final, Literal

# Exit codes Claude Code expects from hook scripts.
# ALLOW: pass through silently.
# BLOCK: deny the tool call. PreToolUse hooks may also use this to abort the
# upcoming action; the stderr stream is surfaced to the user.
ALLOW: Final[int] = 0
BLOCK: Final[int] = 2


def read_hook_input() -> dict[str, object]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def write_additional_context(message: str) -> None:
    payload = {"additionalContext": message}
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def write_decision(behavior: Literal["allow", "deny"], reason: str | None = None) -> None:
    hook_output: dict[str, object] = {"permissionDecision": behavior}
    if reason is not None:
        hook_output["permissionDecisionReason"] = reason
    payload = {"hookSpecificOutput": hook_output}
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


# PermissionRequest is a distinct hook lifecycle from PreToolUse. The shapes diverge:
# PreToolUse uses ``hookSpecificOutput.permissionDecision``; PermissionRequest nests
# under ``hookSpecificOutput.decision.behavior`` and requires ``hookEventName``.
def write_permission_request_decision(behavior: Literal["allow", "deny"]) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": behavior},
        },
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()
