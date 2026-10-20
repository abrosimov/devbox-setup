from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import branch_name_guard as guard

BIN_DIR = Path(__file__).resolve().parent
COPIES = (
    BIN_DIR.parents[1] / "dot_codex" / "bin" / "branch_name_guard.py",
    BIN_DIR.parents[1] / "dot_agy" / "bin" / "branch_name_guard.py",
)


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("git checkout -b feat/login", "feat/login"),
        ("git checkout -B fix/x origin/main", "fix/x"),
        ("git checkout --orphan docs/site", "docs/site"),
        ("git switch -c feat/login", "feat/login"),
        ("git switch --create=feat/login", "feat/login"),
        ("git switch -C feat/login main", "feat/login"),
        ("git branch feat/login", "feat/login"),
        ("git branch --track feat/login origin/main", "feat/login"),
        ("git branch -m feat/login", "feat/login"),
        ("git branch -M old_name feat/login", "feat/login"),
        ("git -C /repo worktree add -b feat/login ../login main", "feat/login"),
        ("git push -u origin HEAD:feat/login", "feat/login"),
        ("git push origin HEAD:refs/heads/feat/login", "feat/login"),
        ("proj wt add feat/login", "feat/login"),
        ("proj wt fork fix/x", "fix/x"),
        ("git fetch && git checkout -b feat/login", "feat/login"),
        ("git status; git switch -c feat/login", "feat/login"),
        ("GIT_TRACE=1 git checkout -b feat/login", "feat/login"),
        ("bash -lc 'git checkout -b feat/login'", "feat/login"),
        ("fish -c 'proj wt add feat/login'", "feat/login"),
    ],
)
def test_denies_slashed_branch(cmd: str, expected: str) -> None:
    assert guard.slashed_branch(cmd) == expected


@pytest.mark.parametrize(
    "cmd",
    [
        "git checkout -b PROJ-123_add_login",
        "git checkout -b add_login origin/feat/upstream",
        "git switch -c add_login",
        "git switch feat/colleague",
        "git checkout feat/colleague",
        "git checkout -- src/app.py",
        "git branch",
        "git branch -a",
        "git branch -d feat/old",
        "git branch -D feat/old",
        "git branch --list 'feat/*'",
        "git branch -u origin/feat/x",
        "git branch --contains abc123",
        "git worktree add ../login add_login",
        "git worktree add -b add_login ../login origin/main",
        "git push -u origin add_login",
        "git push origin feat/colleague",
        "git push origin v1.0:refs/tags/release/v1.0",
        "proj wt add add_login --from origin/main",
        "echo git checkout -b feat/x",
        "git log --oneline origin/feat/x",
        "git checkout -b 'unterminated",
    ],
)
def test_allows(cmd: str) -> None:
    assert guard.slashed_branch(cmd) is None


def test_reason_suggests_flat_name() -> None:
    msg = guard.reason("feat/login")
    assert "'login'" in msg
    assert "PROJ-123_login" in msg


def _run(payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BIN_DIR / "branch_name_guard.py")],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )


def test_hook_blocks_with_exit_2() -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "git checkout -b feat/x"}}
    completed = _run(json.dumps(payload))
    assert completed.returncode == guard.BLOCK_EXIT
    assert "branch-name-slash" in completed.stderr


def test_hook_reads_argv_list_command() -> None:
    payload = {"tool_input": {"command": ["bash", "-lc", "git switch -c fix/y"]}}
    assert _run(json.dumps(payload)).returncode == guard.BLOCK_EXIT


@pytest.mark.parametrize(
    "payload",
    [
        "{",
        "[]",
        json.dumps({"tool_name": "apply_patch", "tool_input": {"patch": "x"}}),
        json.dumps({"tool_input": {"command": "git checkout -b add_login"}}),
    ],
)
def test_hook_allows_silently(payload: str) -> None:
    completed = _run(payload)
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""


@pytest.mark.parametrize("copy", COPIES, ids=lambda p: p.parts[-3])
def test_copies_are_byte_identical(copy: Path) -> None:
    assert copy.read_bytes() == (BIN_DIR / "branch_name_guard.py").read_bytes()
