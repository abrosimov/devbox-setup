from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
import resolve_context
from _claude_lib import proc


def _ok(stdout: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _err(stderr: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout="", stderr=stderr, returncode=128, timed_out=False)


# --- profile -----------------------------------------------------------------


def test_profile_unset_is_an_error_with_the_remedy() -> None:
    with pytest.raises(resolve_context.ContextError, match="make personal"):
        resolve_context.read_profile({})


def test_profile_unknown_value_is_an_error() -> None:
    with pytest.raises(resolve_context.ContextError, match="not one of"):
        resolve_context.read_profile({"MNEMOSYNE_PERISTASEOS": "lab"})


@pytest.mark.parametrize("profile", ["personal", "work"])
def test_profile_known_values_pass(profile: str) -> None:
    assert resolve_context.read_profile({"MNEMOSYNE_PERISTASEOS": profile}) == profile


# --- vault -------------------------------------------------------------------


def test_personal_child_directory(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    assert resolve_context.resolve_vault("personal", tmp_path, "docs\n") == tmp_path / "docs"


def test_personal_missing_marker_names_the_expected_form(tmp_path: Path) -> None:
    with pytest.raises(resolve_context.ContextError, match="child directory such as `docs`"):
        resolve_context.resolve_vault("personal", tmp_path, None)


def test_personal_rejects_an_external_path(tmp_path: Path) -> None:
    with pytest.raises(resolve_context.ContextError, match="inside the repository"):
        resolve_context.resolve_vault("personal", tmp_path, "/srv/vaults/x")


@pytest.mark.parametrize("declared", ["a/b", ".docs", ""])
def test_personal_rejects_non_child_forms(tmp_path: Path, declared: str) -> None:
    with pytest.raises(resolve_context.ContextError):
        resolve_context.resolve_vault("personal", tmp_path, declared)


def test_personal_rejects_a_missing_or_symlinked_child(tmp_path: Path) -> None:
    with pytest.raises(resolve_context.ContextError, match="not a directory"):
        resolve_context.resolve_vault("personal", tmp_path, "docs")
    (tmp_path / "real").mkdir()
    (tmp_path / "docs").symlink_to(tmp_path / "real")
    with pytest.raises(resolve_context.ContextError, match="symlinks"):
        resolve_context.resolve_vault("personal", tmp_path, "docs")


def test_work_external_absolute_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vaults" / "repo"
    repo.mkdir()
    vault.mkdir(parents=True)
    assert resolve_context.resolve_vault("work", repo, f"{vault}\n") == vault.resolve()


def test_work_tilde_path_is_expanded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    repo = tmp_path / "repo"
    vault = tmp_path / "vaults" / "repo"
    repo.mkdir()
    vault.mkdir(parents=True)
    assert resolve_context.resolve_vault("work", repo, "~/vaults/repo") == vault.resolve()


def test_work_missing_marker_names_the_expected_form(tmp_path: Path) -> None:
    with pytest.raises(resolve_context.ContextError, match="absolute path outside"):
        resolve_context.resolve_vault("work", tmp_path, None)


def test_work_rejects_a_child_name(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    with pytest.raises(resolve_context.ContextError, match="outside the repository"):
        resolve_context.resolve_vault("work", tmp_path, "docs")


def test_work_rejects_a_path_inside_the_repository(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    with pytest.raises(resolve_context.ContextError, match="lies inside"):
        resolve_context.resolve_vault("work", tmp_path, str(tmp_path / "docs"))


def test_work_rejects_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(resolve_context.ContextError, match="not a directory"):
        resolve_context.resolve_vault("work", tmp_path, str(tmp_path / "nowhere"))


# --- branch ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("PROJ-123_add_user_auth", ("PROJ-123", "add_user_auth")),
        ("ABC-9_feature", ("ABC-9", "feature")),
        ("feature_branch_only", (None, "feature_branch_only")),
        ("abc-1_x", (None, "abc-1_x")),
        ("PROJ-1", (None, "PROJ-1")),
        ("master", (None, "master")),
        ("", (None, "")),
    ],
)
def test_split_branch(branch: str, expected: tuple[str | None, str]) -> None:
    assert resolve_context.split_branch(branch) == expected


def test_to_json_carries_a_null_issue(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    ctx = resolve_context.resolve("personal", tmp_path, "docs", "feature/login")
    payload = json.loads(ctx.to_json())
    assert payload == {
        "PROFILE": "personal",
        "VAULT": str(tmp_path / "docs"),
        "BRANCH": "feature/login",
        "JIRA_ISSUE": None,
        "BRANCH_NAME": "feature/login",
    }


# --- main --------------------------------------------------------------------


def _stub_git(monkeypatch: pytest.MonkeyPatch, toplevel: Path, branch: str) -> None:
    responses = {
        "git rev-parse --is-inside-work-tree": _ok("true\n"),
        "git rev-parse --show-toplevel": _ok(f"{toplevel}\n"),
        "git branch --show-current": _ok(f"{branch}\n"),
    }

    def fake(cmd: list[str], **_kwargs: object) -> proc.CmdResult:
        return responses.get(" ".join(cmd), _err())

    monkeypatch.setattr(proc, "run_cmd", fake)


def test_main_help_writes_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert resolve_context.main(["--help"]) == 0
    assert "Usage:" in out.getvalue()


def test_main_unknown_option(monkeypatch: pytest.MonkeyPatch) -> None:
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.main(["--plans-dir", "x"]) == 1
    assert "Unknown option" in err.getvalue()


def test_main_profile_is_read_before_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MNEMOSYNE_PERISTASEOS", raising=False)
    monkeypatch.setattr(proc, "run_cmd", lambda *_a, **_k: _ok("true\n"))
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.main([]) == 1
    assert "MNEMOSYNE_PERISTASEOS is not set" in err.getvalue()


def test_main_not_in_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MNEMOSYNE_PERISTASEOS", "personal")
    monkeypatch.setattr(proc, "run_cmd", lambda *_a, **_k: _err())
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.main([]) == 1
    assert "not inside a git repository" in err.getvalue()


def test_main_personal_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MNEMOSYNE_PERISTASEOS", "personal")
    (tmp_path / "docs").mkdir()
    (tmp_path / ".vault-root").write_text("docs\n", encoding="utf-8")
    _stub_git(monkeypatch, tmp_path, "PROJ-123_feature_name")
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert resolve_context.main([]) == 0
    payload = json.loads(out.getvalue())
    assert payload["PROFILE"] == "personal"
    assert payload["VAULT"] == str(tmp_path / "docs")
    assert payload["JIRA_ISSUE"] == "PROJ-123"
    assert payload["BRANCH_NAME"] == "feature_name"


def test_main_work_success_without_an_issue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MNEMOSYNE_PERISTASEOS", "work")
    repo = tmp_path / "repo"
    vault = tmp_path / "vaults" / "repo"
    repo.mkdir()
    vault.mkdir(parents=True)
    (repo / ".vault-root").write_text(f"{vault}\n", encoding="utf-8")
    _stub_git(monkeypatch, repo, "master")
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert resolve_context.main([]) == 0
    payload = json.loads(out.getvalue())
    assert payload["VAULT"] == str(vault.resolve())
    assert payload["JIRA_ISSUE"] is None
    assert payload["BRANCH_NAME"] == "master"


def test_main_missing_marker_is_exit_1_with_hint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MNEMOSYNE_PERISTASEOS", "personal")
    _stub_git(monkeypatch, tmp_path, "PROJ-1_x")
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert resolve_context.main([]) == 1
    assert ".vault-root is missing" in err.getvalue()
