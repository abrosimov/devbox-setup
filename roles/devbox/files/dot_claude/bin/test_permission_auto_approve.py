from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import permission_auto_approve as paa

if TYPE_CHECKING:
    import pytest


def test_is_simple_read_only_echo_plain() -> None:
    assert paa.is_simple_read_only("echo hello")
    assert paa.is_simple_read_only("echo")


def test_is_simple_read_only_printf_plain() -> None:
    assert paa.is_simple_read_only("printf 'x\\n'")


def test_is_simple_read_only_rejects_pipe_redirect() -> None:
    assert not paa.is_simple_read_only("echo hi | cat")
    assert not paa.is_simple_read_only("echo hi > file")


def test_is_existence_check_command_v() -> None:
    assert paa.is_existence_check("command -v ls")


def test_is_existence_check_type_hash() -> None:
    assert paa.is_existence_check("type ls")
    assert paa.is_existence_check("hash gcc")


def test_is_system_info_recognises_id_whoami() -> None:
    assert paa.is_system_info("id")
    assert paa.is_system_info("whoami")
    assert paa.is_system_info("hostname")
    assert paa.is_system_info("uname -a")


def test_is_system_info_recognises_sw_vers() -> None:
    assert paa.is_system_info("sw_vers")
    assert paa.is_system_info("sw_vers -productVersion")


def test_is_terminal_query_recognises_tput_locale() -> None:
    assert paa.is_terminal_query("tput cols")
    assert paa.is_terminal_query("locale")
    assert paa.is_terminal_query("stty -a")


def test_normalise_strips_cd_prefix() -> None:
    assert paa.normalise("cd /tmp && go build ./...") == "go build ./..."


def test_normalise_strips_env_vars() -> None:
    assert paa.normalise("FOO=bar BAR=baz pytest") == "pytest"


def test_normalise_strips_combined() -> None:
    assert paa.normalise("cd /x && FOO=bar pytest -k test") == "pytest -k test"


def test_normalise_strips_trailing_redirect() -> None:
    assert paa.normalise("cd /x && make test 2>&1") == "make test"


def test_normalise_no_change_when_no_prefix() -> None:
    assert paa.normalise("go build ./...") == "go build ./..."


def test_has_shell_metachars_detects_pipe_chain() -> None:
    assert paa.has_shell_metachars("a | b")
    assert paa.has_shell_metachars("a && b")
    assert paa.has_shell_metachars("a; b")
    assert paa.has_shell_metachars("$(echo x)")


def test_has_shell_metachars_clean() -> None:
    assert not paa.has_shell_metachars("go build ./...")


def test_is_safe_family_go_build() -> None:
    assert paa.is_safe_family("go build ./...")
    assert paa.is_safe_family("go test -run X")


def test_is_safe_family_uv_pytest() -> None:
    assert paa.is_safe_family("uv run pytest")
    assert paa.is_safe_family("pytest -k x")


def test_is_safe_family_rejects_unknown() -> None:
    assert not paa.is_safe_family("rm -rf /")


def test_should_allow_returns_false_for_non_bash() -> None:
    assert not paa.should_allow("Edit", {"command": "echo x"})


def test_should_allow_passes_echo() -> None:
    assert paa.should_allow("Bash", {"command": "echo hi"})


def test_should_allow_passes_cd_then_go_build() -> None:
    assert paa.should_allow("Bash", {"command": "cd /tmp && go build ./..."})


def test_should_allow_rejects_cd_then_unknown() -> None:
    assert not paa.should_allow("Bash", {"command": "cd /tmp && rm -rf foo"})


def test_should_allow_rejects_normalised_with_chain() -> None:
    assert not paa.should_allow("Bash", {"command": "cd /tmp && go build && make"})


def test_should_allow_handles_missing_command() -> None:
    assert not paa.should_allow("Bash", {})


def test_should_allow_handles_non_string_command() -> None:
    assert not paa.should_allow("Bash", {"command": 123})


def test_main_writes_allow_for_safe_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo ok"}})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert paa.main() == 0
    payload = json.loads(out.getvalue())
    # PermissionRequest hook shape: nested under ``decision.behavior``, with
    # explicit ``hookEventName``. Distinct from the PreToolUse ``permissionDecision``.
    assert payload == {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "allow"},
        },
    }


def test_main_writes_allow_for_normalised_cd_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {"tool_name": "Bash", "tool_input": {"command": "cd /tmp && go build ./..."}},
            ),
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert paa.main() == 0
    payload = json.loads(out.getvalue())
    assert payload["hookSpecificOutput"]["hookEventName"] == "PermissionRequest"
    assert payload["hookSpecificOutput"]["decision"]["behavior"] == "allow"


def test_main_no_output_for_unknown_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps({"tool_name": "Bash", "tool_input": {"command": "curl http://example"}})
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert paa.main() == 0
    assert out.getvalue() == ""


def test_main_empty_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert paa.main() == 0
    assert out.getvalue() == ""


def test_main_non_bash_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "/x"}})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert paa.main() == 0
    assert out.getvalue() == ""
