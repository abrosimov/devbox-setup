from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

GITATTRIBUTES = "*.tar.zst filter=lfs diff=lfs merge=lfs -text\n"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _identity(repo: Path) -> None:
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "master", str(bare)], check=True, capture_output=True
    )
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(bare), str(seed)], check=True, capture_output=True)
    _identity(seed)
    (seed / ".gitattributes").write_text(GITATTRIBUTES)
    git(seed, "add", ".gitattributes")
    git(seed, "commit", "-qm", "init")
    git(seed, "push", "-q", "origin", "master")
    return bare


def clone(remote: Path, dest: Path) -> Path:
    subprocess.run(["git", "clone", "-q", str(remote), str(dest)], check=True, capture_output=True)
    _identity(dest)
    return dest


@pytest.fixture
def repo(remote: Path, tmp_path: Path) -> Path:
    return clone(remote, tmp_path / "work" / "drive" / "base")


@pytest.fixture
def source(tmp_path: Path) -> Path:
    src = tmp_path / "home" / ".claude"
    (src / "projects" / "p1").mkdir(parents=True)
    (src / "projects" / "p1" / "s.jsonl").write_text('{"a": 1}\n' * 100)
    (src / "settings.json").write_text("{}")
    (src / "bin" / ".venv" / "lib").mkdir(parents=True)
    (src / "bin" / ".venv" / "lib" / "big.so").write_bytes(b"x" * 1000)
    (src / "bin" / "tool.py").write_text("print(1)\n")
    (src / "link").symlink_to("settings.json")
    return src
