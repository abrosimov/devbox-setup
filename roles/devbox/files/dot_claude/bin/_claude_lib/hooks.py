from __future__ import annotations

import json
import sys
from typing import Final, Literal

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
    if not isinstance(parsed, dict):
        return {}

    # Agy payload adapter
    if "toolCall" in parsed and isinstance(parsed["toolCall"], dict):
        tool_call = parsed["toolCall"]
        if "name" in tool_call:
            parsed["tool_name"] = tool_call["name"]
        if "args" in tool_call:
            parsed["tool_input"] = tool_call["args"]

    return parsed


def write_additional_context(message: str) -> None:
    payload = {"additionalContext": message}
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def write_decision(
    behavior: Literal["allow", "deny", "ask", "defer"],
    reason: str | None = None,
) -> None:
    hook_output: dict[str, object] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": behavior,
    }
    if reason is not None:
        hook_output["permissionDecisionReason"] = reason
    payload = {
        "hookSpecificOutput": hook_output,
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def write_permission_request_decision(behavior: Literal["allow", "deny"]) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": behavior},
        },
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()
