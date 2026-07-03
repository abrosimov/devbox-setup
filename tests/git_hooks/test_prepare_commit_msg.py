"""Tests for the global prepare-commit-msg hook.

The hook is deployed to ~/.config/git/hooks/prepare-commit-msg and invoked by git
with (msg_file, commit_source, ...). These tests exercise the real artifact end
to end: a throwaway git repo, a branch set via symbolic-ref, and the hook run as
a subprocess — the same way git runs it.
"""

from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = (
    Path(__file__).resolve().parents[2] / "roles/devbox/files/.config/git/hooks/prepare-commit-msg"
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway git repo with a deterministic identity."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.co"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, check=True)
    return tmp_path


def set_branch(repo: Path, branch: str) -> None:
    """Point HEAD at an (unborn) branch without needing a commit."""
    subprocess.run(
        ["git", "symbolic-ref", "HEAD", f"refs/heads/{branch}"],
        cwd=repo,
        check=True,
    )


def run_hook(
    repo: Path,
    message: str,
    *,
    source: str = "",
    position: str | None = None,
) -> str:
    """Run the hook against `message`; return the resulting file content."""
    if position is not None:
        subprocess.run(["git", "config", "jira.keyPosition", position], cwd=repo, check=True)
    msg_file = repo / "COMMIT_EDITMSG"
    msg_file.write_text(message, encoding="utf-8")
    argv = [sys.executable, str(HOOK), str(msg_file)]
    if source:
        argv.append(source)
    subprocess.run(argv, cwd=repo, check=True)
    return msg_file.read_text(encoding="utf-8")


# --- key injection ----------------------------------------------------------


@pytest.mark.parametrize(
    ("branch", "expected_key"),
    [
        ("ABC-123_login", "ABC-123"),
        ("feature/PROJ-4567-x", "PROJ-4567"),
        ("bugfix/AB-1", "AB-1"),
    ],
)
def test_prefix_injects_key(repo: Path, branch: str, expected_key: str) -> None:
    set_branch(repo, branch)
    assert run_hook(repo, "add login") == f"[{expected_key}]: add login\n"


def test_suffix_position(repo: Path) -> None:
    set_branch(repo, "ABC-123_login")
    assert run_hook(repo, "add login", position="suffix") == "add login [ABC-123]\n"


def test_multiline_body_preserved(repo: Path) -> None:
    set_branch(repo, "ABC-123_x")
    out = run_hook(repo, "subject\n\nbody line\n")
    assert out == "[ABC-123]: subject\n\nbody line\n"


# --- no-op guards -----------------------------------------------------------


def test_no_key_branch_is_noop(repo: Path) -> None:
    set_branch(repo, "fish-git-shortcuts-47k8")
    assert run_hook(repo, "personal work") == "personal work"


def test_main_branch_is_noop(repo: Path) -> None:
    set_branch(repo, "main")
    assert run_hook(repo, "chore: bump") == "chore: bump"


def test_already_tagged_is_noop(repo: Path) -> None:
    set_branch(repo, "ABC-123_login")
    assert run_hook(repo, "[ABC-123]: done") == "[ABC-123]: done"


@pytest.mark.parametrize("source", ["merge", "squash"])
def test_machine_sources_skipped(repo: Path, source: str) -> None:
    set_branch(repo, "ABC-123_login")
    assert run_hook(repo, "Merge branch x", source=source) == "Merge branch x"


def test_detached_head_is_noop(repo: Path) -> None:
    set_branch(repo, "ABC-123_x")
    (repo / "f").write_text("x")
    subprocess.run(["git", "add", "f"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-q", sha], cwd=repo, check=True)  # detach
    assert run_hook(repo, "detached work") == "detached work"


# --- deployability ----------------------------------------------------------


def test_hook_is_executable_python() -> None:
    """Deployed as a runnable hook: executable bit + python3 shebang."""
    assert HOOK.stat().st_mode & stat.S_IXUSR, "hook must be executable"
    assert HOOK.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3")
