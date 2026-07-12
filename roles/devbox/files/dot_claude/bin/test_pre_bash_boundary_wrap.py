from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_bash_boundary_wrap as bw

if TYPE_CHECKING:
    import pytest


def test_needs_wrapping_gh_pr_view() -> None:
    assert bw.needs_wrapping("gh pr view 123")


def test_needs_wrapping_gh_alone() -> None:
    assert bw.needs_wrapping("gh")


def test_needs_wrapping_git_log() -> None:
    assert bw.needs_wrapping("git log --oneline -10")


def test_needs_wrapping_git_show() -> None:
    assert bw.needs_wrapping("git show HEAD")


def test_needs_wrapping_git_blame() -> None:
    assert bw.needs_wrapping("git blame README.md")


def test_does_not_wrap_git_status() -> None:
    assert not bw.needs_wrapping("git status")


def test_does_not_wrap_git_diff() -> None:
    assert not bw.needs_wrapping("git diff")


def test_does_not_wrap_other_command() -> None:
    assert not bw.needs_wrapping("ls -la")


def test_does_not_wrap_command_containing_gh_substring() -> None:
    assert not bw.needs_wrapping("ghosthound start")


def test_build_wrap_uses_token_in_tag() -> None:
    wrap = bw.build_wrap("gh pr view 1", "deadbeefcafebabe")
    assert wrap.tag == "untrusted-content-deadbeefcafebabe"
    assert wrap.token == "deadbeefcafebabe"  # noqa: S105
    assert wrap.tag in wrap.additional_context


def test_build_wrap_additional_context_mentions_untrusted() -> None:
    wrap = bw.build_wrap("git log", "tok")
    assert "UNTRUSTED" in wrap.additional_context
    assert wrap.tag in wrap.additional_context


def test_main_no_wrapping_for_clean_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "ls -la"}})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert bw.main(token_factory=lambda: "fixed") == 0
    assert out.getvalue() == ""


def test_main_wraps_gh_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "gh pr view 1"}})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert bw.main(token_factory=lambda: "abcdef01") == 0
    payload = json.loads(out.getvalue())
    hook = payload["hookSpecificOutput"]
    assert hook["hookEventName"] == "PreToolUse"
    assert "updatedInput" not in hook
    assert "untrusted-content-abcdef01" in hook["additionalContext"]


def test_main_wraps_git_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "git log HEAD"}})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert bw.main(token_factory=lambda: "tok123ff") == 0
    payload = json.loads(out.getvalue())
    hook = payload["hookSpecificOutput"]
    assert "updatedInput" not in hook
    assert "untrusted-content-tok123ff" in hook["additionalContext"]


def test_main_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert bw.main() == 0
    assert out.getvalue() == ""


def test_main_handles_non_dict_tool_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_input": "not a dict"})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert bw.main() == 0
    assert out.getvalue() == ""


def test_main_handles_non_string_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_input": {"command": 42}})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert bw.main() == 0
    assert out.getvalue() == ""
