from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import git_safe_merge as gsm
from _claude_lib import proc

if TYPE_CHECKING:
    import pytest


def _ok(stdout: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _err(stderr: str = "fatal") -> proc.CmdResult:
    return proc.CmdResult(stdout="", stderr=stderr, returncode=1, timed_out=False)


def test_parse_args_minimal() -> None:
    result = gsm.parse_args(["feature/x"])
    assert isinstance(result, gsm.ParsedArgs)
    assert result.source == "feature/x"
    assert result.target_override is None


def test_parse_args_with_into() -> None:
    result = gsm.parse_args(["feature/x", "--into", "develop"])
    assert isinstance(result, gsm.ParsedArgs)
    assert result.target_override == "develop"


def test_parse_args_into_before_source() -> None:
    result = gsm.parse_args(["--into", "develop", "feature/x"])
    assert isinstance(result, gsm.ParsedArgs)
    assert result.source == "feature/x"
    assert result.target_override == "develop"


def test_parse_args_missing_source() -> None:
    result = gsm.parse_args([])
    assert isinstance(result, gsm.ParseFailure)
    assert result.show_usage


def test_parse_args_into_without_value() -> None:
    result = gsm.parse_args(["feature/x", "--into"])
    assert isinstance(result, gsm.ParseFailure)
    assert "--into requires" in result.reason


def test_parse_args_unknown_flag() -> None:
    result = gsm.parse_args(["--foo"])
    assert isinstance(result, gsm.ParseFailure)
    assert "Unknown flag" in result.reason


def test_parse_args_extra_positional() -> None:
    result = gsm.parse_args(["a", "b"])
    assert isinstance(result, gsm.ParseFailure)
    assert "Unexpected positional" in result.reason


def _setup(
    monkeypatch: pytest.MonkeyPatch, responses: dict[str, proc.CmdResult]
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake(cmd: list[str], **_kwargs: object) -> proc.CmdResult:
        calls.append(list(cmd))
        key = " ".join(cmd)
        for prefix, response in responses.items():
            if key.startswith(prefix):
                return response
        return _ok()

    monkeypatch.setattr(proc, "run_cmd", fake)
    return calls


def test_run_no_source_prints_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, {"git config --get claude.integrationBranch": _err()})
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsm.run([]) == 1
    assert "Usage:" in err.getvalue()


def test_run_blocks_merge_into_main(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, {"git config --get claude.integrationBranch": _err()})
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsm.run(["feature/x", "--into", "main"]) == 1
    assert "Cannot merge into 'main'" in err.getvalue()


def test_run_blocks_merge_into_master(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, {"git config --get claude.integrationBranch": _err()})
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsm.run(["feature/x", "--into", "master"]) == 1
    assert "master" in err.getvalue()


def test_run_blocks_when_source_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(
        monkeypatch,
        {
            "git config --get claude.integrationBranch": _err(),
            "git rev-parse --verify feature/x": _err(),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsm.run(["feature/x"]) == 1
    assert "Source branch 'feature/x' does not exist" in err.getvalue()


def test_run_blocks_when_target_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(
        monkeypatch,
        {
            "git config --get claude.integrationBranch": _err(),
            "git rev-parse --verify feature/x": _ok(),
            "git rev-parse --verify build/stable": _err(),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsm.run(["feature/x"]) == 1
    assert "Target branch 'build/stable' does not exist" in err.getvalue()


def test_run_nothing_to_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(
        monkeypatch,
        {
            "git config --get claude.integrationBranch": _err(),
            "git rev-parse --verify feature/x": _ok(),
            "git rev-parse --verify build/stable": _ok(),
            "git merge-base feature/x build/stable": _ok("abc123\n"),
            "git rev-list --count build/stable..feature/x": _ok("0\n"),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert gsm.run(["feature/x"]) == 0
    assert "Nothing to merge" in out.getvalue()


def test_run_successful_ff(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(
        monkeypatch,
        {
            "git config --get claude.integrationBranch": _err(),
            "git rev-parse --verify feature/x": _ok(),
            "git rev-parse --verify build/stable": _ok(),
            "git merge-base": _ok("abc\n"),
            "git rev-list --count": _ok("3\n"),
            "git branch --show-current": _ok("feature/x\n"),
            "git diff --quiet": _ok(),
            "git diff --cached --quiet": _ok(),
            "git switch build/stable": _ok(),
            "git merge --ff-only feature/x": _ok("Fast-forward\n"),
            "git switch feature/x": _ok(),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert gsm.run(["feature/x"]) == 0
    assert "Merged 'feature/x' into 'build/stable' (fast-forward)" in out.getvalue()


def test_run_ff_fails_diverged(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(
        monkeypatch,
        {
            "git config --get claude.integrationBranch": _err(),
            "git rev-parse --verify feature/x": _ok(),
            "git rev-parse --verify build/stable": _ok(),
            "git merge-base": _ok("abc\n"),
            "git rev-list --count": _ok("3\n"),
            "git branch --show-current": _ok("feature/x\n"),
            "git diff --quiet": _ok(),
            "git diff --cached --quiet": _ok(),
            "git switch build/stable": _ok(),
            "git merge --ff-only feature/x": _err("Not possible"),
            "git switch feature/x": _ok(),
        },
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert gsm.run(["feature/x"]) == 1
    assert "Fast-forward merge not possible" in err.getvalue()
    assert "Rebase source onto target" in err.getvalue()


def test_run_uses_into_target_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(
        monkeypatch,
        {
            "git config --get claude.integrationBranch": _err(),
            "git rev-parse --verify feature/x": _ok(),
            "git rev-parse --verify develop": _ok(),
            "git merge-base": _ok("abc\n"),
            "git rev-list --count": _ok("3\n"),
            "git branch --show-current": _ok("feature/x\n"),
            "git diff --quiet": _ok(),
            "git diff --cached --quiet": _ok(),
            "git switch develop": _ok(),
            "git merge --ff-only feature/x": _ok(),
            "git switch feature/x": _ok(),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert gsm.run(["feature/x", "--into", "develop"]) == 0
    assert "develop" in out.getvalue()


def test_run_uses_custom_integration_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(
        monkeypatch,
        {
            "git config --get claude.integrationBranch": _ok("integration\n"),
            "git rev-parse --verify feature/x": _ok(),
            "git rev-parse --verify integration": _ok(),
            "git merge-base": _ok("abc\n"),
            "git rev-list --count": _ok("3\n"),
            "git branch --show-current": _ok("feature/x\n"),
            "git diff --quiet": _ok(),
            "git diff --cached --quiet": _ok(),
            "git switch integration": _ok(),
            "git merge --ff-only feature/x": _ok(),
            "git switch feature/x": _ok(),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert gsm.run(["feature/x"]) == 0
    assert "integration" in out.getvalue()


def test_run_stashes_uncommitted(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _setup(
        monkeypatch,
        {
            "git config --get claude.integrationBranch": _err(),
            "git rev-parse --verify feature/x": _ok(),
            "git rev-parse --verify build/stable": _ok(),
            "git merge-base": _ok("abc\n"),
            "git rev-list --count": _ok("3\n"),
            "git branch --show-current": _ok("feature/x\n"),
            "git diff --quiet": _err(),
            "git diff --cached --quiet": _ok(),
            "git stash push": _ok(),
            "git switch build/stable": _ok(),
            "git merge --ff-only feature/x": _ok(),
            "git switch feature/x": _ok(),
            "git stash pop": _ok(),
        },
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert gsm.run(["feature/x"]) == 0
    assert "Stashing uncommitted changes" in out.getvalue()
    stash_pushes = [c for c in calls if c[:3] == ["git", "stash", "push"]]
    assert stash_pushes
    stash_pops = [c for c in calls if c[:3] == ["git", "stash", "pop"]]
    assert stash_pops
