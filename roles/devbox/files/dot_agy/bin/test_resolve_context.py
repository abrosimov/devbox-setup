from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import resolve_context
from _claude_lib import proc

if TYPE_CHECKING:
    import pytest


def _ok(stdout: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _err(stderr: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout="", stderr=stderr, returncode=128, timed_out=False)


def test_resolve_valid_branch() -> None:
    ctx = resolve_context.resolve("PROJ-123_add_user_auth", "docs/implementation_plans")
    assert ctx is not None
    assert ctx.jira_issue == "PROJ-123"
    assert ctx.branch_name == "add_user_auth"
    assert ctx.branch == "PROJ-123_add_user_auth"
    assert ctx.project_dir == "docs/implementation_plans/PROJ-123/add_user_auth"


def test_resolve_custom_plans_dir() -> None:
    ctx = resolve_context.resolve("ABC-9_feature", "custom/plans")
    assert ctx is not None
    assert ctx.project_dir == "custom/plans/ABC-9/feature"


def test_resolve_rejects_non_jira_prefix() -> None:
    assert resolve_context.resolve("feature_branch_only", "p") is None


def test_resolve_rejects_lowercase_prefix() -> None:
    assert resolve_context.resolve("abc-1_x", "p") is None


def test_resolve_rejects_missing_underscore_payload() -> None:
    assert resolve_context.resolve("PROJ-1", "p") is None


def test_resolve_rejects_empty_branch() -> None:
    assert resolve_context.resolve("", "p") is None


def test_to_json_round_trip() -> None:
    ctx = resolve_context.resolve("PROJ-1_x", "plans")
    assert ctx is not None
    payload = json.loads(ctx.to_json())
    assert payload == {
        "JIRA_ISSUE": "PROJ-1",
        "BRANCH_NAME": "x",
        "BRANCH": "PROJ-1_x",
        "PROJECT_DIR": "plans/PROJ-1/x",
    }


def test_parse_args_defaults() -> None:
    parsed = resolve_context.parse_args([])
    assert parsed is not None
    assert parsed.plans_dir == "docs/implementation_plans"
    assert not parsed.show_help


def test_parse_args_help_flag() -> None:
    parsed = resolve_context.parse_args(["--help"])
    assert parsed is not None
    assert parsed.show_help


def test_parse_args_plans_dir_override() -> None:
    parsed = resolve_context.parse_args(["--plans-dir", "my/plans"])
    assert parsed is not None
    assert parsed.plans_dir == "my/plans"


def test_parse_args_plans_dir_requires_value(monkeypatch: pytest.MonkeyPatch) -> None:
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.parse_args(["--plans-dir"]) is None
    assert "requires a value" in err.getvalue()


def test_parse_args_unknown_option(monkeypatch: pytest.MonkeyPatch) -> None:
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.parse_args(["--no-such-flag"]) is None
    assert "Unknown option" in err.getvalue()


def test_main_help_writes_usage_to_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert resolve_context.main(["--help"]) == 0
    assert "Usage:" in out.getvalue()


def _stub_run_cmd(monkeypatch: pytest.MonkeyPatch, responses: dict[str, proc.CmdResult]) -> None:
    def fake(cmd: list[str], **_kwargs: object) -> proc.CmdResult:
        key = " ".join(cmd)
        for prefix, result in responses.items():
            if key.startswith(prefix):
                return result
        return _err()

    monkeypatch.setattr(proc, "run_cmd", fake)


def test_main_not_in_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run_cmd(monkeypatch, {"git rev-parse --is-inside-work-tree": _err()})
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.main([]) == 1
    assert "not inside a git repository" in err.getvalue()


def test_main_detached_head(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run_cmd(
        monkeypatch,
        {
            "git rev-parse --is-inside-work-tree": _ok("true\n"),
            "git branch --show-current": _ok(""),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.main([]) == 2
    assert "detached HEAD" in err.getvalue()


def test_main_non_convention_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run_cmd(
        monkeypatch,
        {
            "git rev-parse --is-inside-work-tree": _ok("true\n"),
            "git branch --show-current": _ok("master\n"),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.main([]) == 2
    assert "PROJ-123_description convention" in err.getvalue()


def test_main_writes_json_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run_cmd(
        monkeypatch,
        {
            "git rev-parse --is-inside-work-tree": _ok("true\n"),
            "git branch --show-current": _ok("PROJ-123_feature_name\n"),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert resolve_context.main([]) == 0
    payload = json.loads(out.getvalue())
    assert payload["JIRA_ISSUE"] == "PROJ-123"
    assert payload["BRANCH_NAME"] == "feature_name"
    assert payload["PROJECT_DIR"] == "docs/implementation_plans/PROJ-123/feature_name"


def test_main_respects_plans_dir_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run_cmd(
        monkeypatch,
        {
            "git rev-parse --is-inside-work-tree": _ok("true\n"),
            "git branch --show-current": _ok("X-1_y\n"),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert resolve_context.main(["--plans-dir", "alt/plans"]) == 0
    payload = json.loads(out.getvalue())
    assert payload["PROJECT_DIR"] == "alt/plans/X-1/y"
