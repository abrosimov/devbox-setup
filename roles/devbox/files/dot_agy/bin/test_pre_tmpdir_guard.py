from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_tmpdir_guard
from _claude_lib import proc


@pytest.fixture(autouse=True)
def _clear_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    # Most tests want a clean env so stdin JSON drives behaviour. Tests that
    # exercise the env-var protocol set the vars explicitly via ``monkeypatch.setenv``.
    monkeypatch.delenv("CC_BASH_COMMAND", raising=False)
    monkeypatch.delenv("CC_TOOL_INPUT_FILE_PATH", raising=False)
    # Default TMPDIR off so allowlist tests get deterministic state. Individual
    # tests that exercise $TMPDIR allowlisting set it explicitly.
    monkeypatch.delenv("TMPDIR", raising=False)


def test_is_blocked_path_detects_tmp_substring() -> None:
    assert pre_tmpdir_guard.is_blocked_path("ls /tmp/foo")
    assert pre_tmpdir_guard.is_blocked_path("cp file /var/tmp/here")


def test_is_blocked_path_allows_unrelated_path() -> None:
    # Preserves the legacy substring match: `case "$cmd" in */tmp/*)` blocks any
    # command containing "/tmp/" anywhere. The project-local "tmp/" form has no
    # leading slash and therefore is not blocked.
    assert not pre_tmpdir_guard.is_blocked_path("ls tmp/foo")
    assert not pre_tmpdir_guard.is_blocked_path("echo hi")
    assert not pre_tmpdir_guard.is_blocked_path("")


def test_is_blocked_file_target_strict_prefix() -> None:
    assert pre_tmpdir_guard.is_blocked_file_target("/tmp/foo.txt")
    assert pre_tmpdir_guard.is_blocked_file_target("/var/tmp/log")
    assert not pre_tmpdir_guard.is_blocked_file_target("project/tmp/foo")
    assert not pre_tmpdir_guard.is_blocked_file_target("")


def test_evaluate_blocks_bash_command_with_tmp() -> None:
    payload: dict[str, object] = {
        "tool_input": {"command": "rm /tmp/foo"},
    }
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert blocked
    assert target == "rm /tmp/foo"


def test_evaluate_blocks_write_to_tmp_file() -> None:
    payload: dict[str, object] = {
        "tool_input": {"file_path": "/tmp/example.log"},
    }
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert blocked
    assert target == "/tmp/example.log"


def test_evaluate_allows_clean_payload() -> None:
    payload: dict[str, object] = {
        "tool_input": {"command": "ls", "file_path": "src/x.py"},
    }
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert not blocked
    assert target is None


def test_evaluate_handles_missing_tool_input() -> None:
    blocked, target = pre_tmpdir_guard.evaluate({})
    assert not blocked
    assert target is None


def test_evaluate_handles_non_dict_tool_input() -> None:
    payload: dict[str, object] = {"tool_input": "not a dict"}
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert not blocked
    assert target is None


def test_evaluate_handles_non_string_command() -> None:
    payload: dict[str, object] = {"tool_input": {"command": 123}}
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert not blocked
    assert target is None


def test_ensure_tmp_dir_creates_directory(tmp_path: Path) -> None:
    result = pre_tmpdir_guard.ensure_tmp_dir(tmp_path)
    assert result == tmp_path / "tmp"
    assert result.is_dir()


def test_ensure_tmp_dir_idempotent(tmp_path: Path) -> None:
    (tmp_path / "tmp").mkdir()
    result = pre_tmpdir_guard.ensure_tmp_dir(tmp_path)
    assert result.is_dir()


def test_ensure_gitignore_creates_when_absent(tmp_path: Path) -> None:
    pre_tmpdir_guard.ensure_gitignore(tmp_path)
    gitignore = tmp_path / ".gitignore"
    assert gitignore.exists()
    assert "tmp/" in gitignore.read_text(encoding="utf-8")


def test_ensure_gitignore_appends_when_missing_entry(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("dist/\nnode_modules/\n", encoding="utf-8")
    pre_tmpdir_guard.ensure_gitignore(tmp_path)
    content = gitignore.read_text(encoding="utf-8")
    assert "dist/" in content
    assert "tmp/" in content


def test_ensure_gitignore_no_op_when_entry_present(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("dist/\ntmp/\n", encoding="utf-8")
    pre_tmpdir_guard.ensure_gitignore(tmp_path)
    content = gitignore.read_text(encoding="utf-8")
    assert content.count("tmp/") == 1


def test_ensure_gitignore_appends_newline_when_missing_trailing(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("dist/", encoding="utf-8")
    pre_tmpdir_guard.ensure_gitignore(tmp_path)
    content = gitignore.read_text(encoding="utf-8")
    assert "dist/\ntmp/\n" in content


def test_find_project_root_returns_git_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert pre_tmpdir_guard.find_project_root(nested) == tmp_path


def test_find_project_root_falls_back_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        proc,
        "run_cmd",
        lambda *_a, **_kw: proc.CmdResult(stdout="", stderr="", returncode=1, timed_out=False),
    )
    assert pre_tmpdir_guard.find_project_root(tmp_path) == tmp_path


def test_main_passes_on_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert pre_tmpdir_guard.main() == 0


def test_main_passes_on_clean_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "ls -la"}})),
    )
    assert pre_tmpdir_guard.main() == 0


def test_main_blocks_and_initialises_project_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PWD", str(tmp_path))
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "touch /tmp/x"}})),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_tmpdir_guard.main() == 2
    assert (tmp_path / "tmp").is_dir()
    assert "tmp/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "BLOCKED" in err.getvalue()


# Env-var protocol: matches the original bash hook contract
# (``CC_BASH_COMMAND`` / ``CC_TOOL_INPUT_FILE_PATH``).


def test_evaluate_uses_env_command_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_BASH_COMMAND", "rm /tmp/foo")
    blocked, target = pre_tmpdir_guard.evaluate({})
    assert blocked
    assert target == "rm /tmp/foo"


def test_evaluate_uses_env_file_path_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_TOOL_INPUT_FILE_PATH", "/tmp/example.log")
    blocked, target = pre_tmpdir_guard.evaluate({})
    assert blocked
    assert target == "/tmp/example.log"


def test_evaluate_env_clean_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CC_BASH_COMMAND", "ls -la")
    monkeypatch.setenv("CC_TOOL_INPUT_FILE_PATH", "src/x.py")
    blocked, target = pre_tmpdir_guard.evaluate({})
    assert not blocked
    assert target is None


def test_evaluate_env_takes_priority_when_env_blocks_stdin_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CC_BASH_COMMAND", "rm /tmp/foo")
    payload: dict[str, object] = {"tool_input": {"command": "ls", "file_path": "src/x.py"}}
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert blocked
    assert target == "rm /tmp/foo"


def test_evaluate_env_takes_priority_when_env_allows_stdin_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Env vars are set (env_command non-empty) so stdin is ignored even when
    # only the file-path env is set to a benign string. This matches the bash
    # hook semantics: env vars are the canonical source when present.
    monkeypatch.setenv("CC_BASH_COMMAND", "ls")
    monkeypatch.setenv("CC_TOOL_INPUT_FILE_PATH", "src/x.py")
    payload: dict[str, object] = {"tool_input": {"command": "rm /tmp/foo"}}
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert not blocked
    assert target is None


def test_evaluate_falls_back_to_stdin_when_env_empty() -> None:
    # No env vars set (autouse fixture deletes them) — stdin JSON drives behaviour.
    payload: dict[str, object] = {"tool_input": {"command": "rm /tmp/foo"}}
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert blocked
    assert target == "rm /tmp/foo"


def test_evaluate_both_empty_allows() -> None:
    blocked, target = pre_tmpdir_guard.evaluate({})
    assert not blocked
    assert target is None


# Allowlist: sandbox-namespaced tmp dirs (/tmp/claude/, /private/tmp/claude/) and $TMPDIR.


def test_is_blocked_path_allows_tmp_claude_namespace() -> None:
    assert not pre_tmpdir_guard.is_blocked_path("ls /tmp/claude/uv-cache")
    assert not pre_tmpdir_guard.is_blocked_path("cp foo /tmp/claude/x/y")


def test_is_blocked_path_allows_private_tmp_claude_namespace() -> None:
    # macOS resolves /tmp to /private/tmp; both forms must be allowlisted.
    assert not pre_tmpdir_guard.is_blocked_path("ls /private/tmp/claude/uv-cache")


def test_is_blocked_path_still_blocks_general_tmp() -> None:
    # The allowlist only covers the sandbox namespace, not all of /tmp.
    assert pre_tmpdir_guard.is_blocked_path("ls /tmp/random.txt")
    assert pre_tmpdir_guard.is_blocked_path("cp file /var/tmp/here")


def test_is_blocked_path_blocks_when_mixed_allowed_and_disallowed() -> None:
    # Any single non-allowlisted /tmp/ token in the command poisons the whole command.
    assert pre_tmpdir_guard.is_blocked_path("cat /tmp/claude/ok /tmp/other")


def test_is_blocked_path_allows_diff_against_sandbox_tmp() -> None:
    # The user's original complaint: `diff foo /tmp/claude/bar` was being blocked.
    assert not pre_tmpdir_guard.is_blocked_path("diff src/x.py /tmp/claude/x.py")


def test_is_blocked_file_target_allows_sandbox_namespace() -> None:
    assert not pre_tmpdir_guard.is_blocked_file_target("/tmp/claude/log")
    assert not pre_tmpdir_guard.is_blocked_file_target("/private/tmp/claude/log")


def test_is_blocked_file_target_still_blocks_general_tmp() -> None:
    assert pre_tmpdir_guard.is_blocked_file_target("/tmp/foo.txt")
    assert pre_tmpdir_guard.is_blocked_file_target("/var/tmp/log")


def test_tmpdir_env_subdirectory_is_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sandbox sets TMPDIR to a namespaced subdir; that path must pass.
    monkeypatch.setenv("TMPDIR", "/var/folders/abc/T/")
    assert not pre_tmpdir_guard.is_blocked_file_target("/var/folders/abc/T/scratch")
    # And the macOS canonical form should remain unaffected (no /tmp/ substring).
    assert not pre_tmpdir_guard.is_blocked_path("touch /var/folders/abc/T/scratch")


def test_tmpdir_env_pointing_at_bare_tmp_does_not_collapse_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # If TMPDIR=/tmp (Linux default), honouring it would defeat the guard. Refuse.
    monkeypatch.setenv("TMPDIR", "/tmp")
    assert pre_tmpdir_guard.is_blocked_file_target("/tmp/foo.txt")
    assert pre_tmpdir_guard.is_blocked_path("touch /tmp/foo.txt")


def test_evaluate_allows_command_in_sandbox_namespace() -> None:
    payload: dict[str, object] = {"tool_input": {"command": "cat /tmp/claude/log"}}
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert not blocked
    assert target is None


def test_evaluate_allows_write_to_sandbox_namespace() -> None:
    payload: dict[str, object] = {"tool_input": {"file_path": "/tmp/claude/scratch.txt"}}
    blocked, target = pre_tmpdir_guard.evaluate(payload)
    assert not blocked
    assert target is None


def test_main_blocks_via_env_protocol(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PWD", str(tmp_path))
    monkeypatch.setenv("CC_BASH_COMMAND", "touch /tmp/x")
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_tmpdir_guard.main() == 2
    assert (tmp_path / "tmp").is_dir()
    assert "BLOCKED" in err.getvalue()
