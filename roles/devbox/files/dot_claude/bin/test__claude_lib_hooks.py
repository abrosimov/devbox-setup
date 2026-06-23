from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import hooks

if TYPE_CHECKING:
    import pytest


def test_read_hook_input_parses_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"tool_name": "Bash", "ok": true}'))
    parsed = hooks.read_hook_input()
    assert parsed == {"tool_name": "Bash", "ok": True}


def test_read_hook_input_returns_empty_on_empty_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert hooks.read_hook_input() == {}


def test_read_hook_input_returns_empty_on_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("   \n\t "))
    assert hooks.read_hook_input() == {}


def test_read_hook_input_returns_empty_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json {"))
    assert hooks.read_hook_input() == {}


def test_read_hook_input_returns_empty_on_non_object_top_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("[1, 2, 3]"))
    assert hooks.read_hook_input() == {}


def test_write_additional_context_emits_json(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    hooks.write_additional_context("hello world")
    payload = json.loads(out.getvalue())
    assert payload == {"additionalContext": "hello world"}


def test_write_decision_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    hooks.write_decision("allow")
    payload = json.loads(out.getvalue())
    assert payload == {"hookSpecificOutput": {"permissionDecision": "allow"}}


def test_write_decision_deny_with_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    hooks.write_decision("deny", reason="not allowed")
    payload = json.loads(out.getvalue())
    assert payload == {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": "not allowed",
        },
    }


def test_exit_code_constants() -> None:
    assert hooks.ALLOW == 0
    assert hooks.BLOCK == 2


def test_write_permission_request_decision_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    hooks.write_permission_request_decision("allow")
    payload = json.loads(out.getvalue())
    assert payload == {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "allow"},
        },
    }


def test_write_permission_request_decision_deny(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    hooks.write_permission_request_decision("deny")
    payload = json.loads(out.getvalue())
    assert payload == {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "deny"},
        },
    }


def test_write_permission_request_decision_exact_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    hooks.write_permission_request_decision("allow")
    payload = json.loads(out.getvalue())
    # The PermissionRequest shape must use ``decision.behavior`` (nested), NOT
    # the PreToolUse ``permissionDecision`` (flat). Guard against accidental
    # regression to the PreToolUse shape.
    hook_specific = payload["hookSpecificOutput"]
    assert "permissionDecision" not in hook_specific
    assert "decision" in hook_specific
    assert hook_specific["decision"] == {"behavior": "allow"}
    assert hook_specific["hookEventName"] == "PermissionRequest"


def test_write_permission_request_decision_distinct_from_write_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pre_out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", pre_out)
    hooks.write_decision("allow")
    pre_payload = json.loads(pre_out.getvalue())

    perm_out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", perm_out)
    hooks.write_permission_request_decision("allow")
    perm_payload = json.loads(perm_out.getvalue())

    assert pre_payload != perm_payload
    assert pre_payload["hookSpecificOutput"].get("permissionDecision") == "allow"
    assert perm_payload["hookSpecificOutput"]["decision"]["behavior"] == "allow"
