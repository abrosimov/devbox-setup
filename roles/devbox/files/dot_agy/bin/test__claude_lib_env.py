from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    for var in (
        "PATH",
        "GOPATH",
        "GOTOOLCHAIN",
        "GOCACHE",
        "GOMODCACHE",
        "UV_CACHE_DIR",
        "RUFF_CACHE_DIR",
        "MYPY_CACHE_DIR",
        "NPM_CONFIG_CACHE",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    return tmp_path


def test_setup_sets_go_cache_under_tmpdir(clean_env: Path) -> None:
    env.setup()
    tmp = clean_env / "tmp"
    assert Path(env.os.environ["GOCACHE"]) == tmp / "go-build-cache"
    assert Path(env.os.environ["GOMODCACHE"]) == tmp / "go-mod-cache"
    assert env.os.environ["GOTOOLCHAIN"] == "local"


def test_setup_sets_python_cache_under_tmpdir(clean_env: Path) -> None:
    env.setup()
    tmp = clean_env / "tmp"
    assert Path(env.os.environ["UV_CACHE_DIR"]) == tmp / "uv-cache"
    assert Path(env.os.environ["RUFF_CACHE_DIR"]) == tmp / "ruff-cache"
    assert Path(env.os.environ["MYPY_CACHE_DIR"]) == tmp / "mypy-cache"


def test_setup_sets_npm_cache_under_tmpdir(clean_env: Path) -> None:
    env.setup()
    tmp = clean_env / "tmp"
    assert Path(env.os.environ["NPM_CONFIG_CACHE"]) == tmp / "npm-cache"


def test_setup_does_not_set_gopath(clean_env: Path) -> None:
    # GOPATH is not touched by env.setup(); it must be provided via
    # settings.json.env or fall back to Go's built-in $HOME/go default.
    assert clean_env.exists()
    env.setup()
    assert "GOPATH" not in env.os.environ


def test_setup_does_not_clobber_existing_values(
    clean_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert clean_env.exists()
    monkeypatch.setenv("GOCACHE", "/preexisting/cache")
    monkeypatch.setenv("UV_CACHE_DIR", "/preexisting/uv")
    env.setup()
    assert env.os.environ["GOCACHE"] == "/preexisting/cache"
    assert env.os.environ["UV_CACHE_DIR"] == "/preexisting/uv"


def test_harden_path_prepends_existing_directories(
    clean_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_bin = clean_env / ".local" / "bin"
    local_bin.mkdir(parents=True)
    monkeypatch.setenv("PATH", "/usr/bin")
    env.harden_path()
    parts = env.os.environ["PATH"].split(":")
    assert str(local_bin) in parts
    assert parts[-1] == "/usr/bin"


def test_harden_path_skips_nonexistent_directories(
    clean_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "/usr/bin")
    env.harden_path()
    parts = env.os.environ["PATH"].split(":")
    assert str(clean_env / ".cargo" / "bin") not in parts


def test_harden_path_does_not_duplicate_existing_entries(
    clean_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_bin = clean_env / ".local" / "bin"
    local_bin.mkdir(parents=True)
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")
    env.harden_path()
    parts = env.os.environ["PATH"].split(":")
    assert parts.count(str(local_bin)) == 1


def test_setup_is_idempotent(clean_env: Path) -> None:
    assert clean_env.exists()
    env.setup()
    first = dict(env.os.environ)
    env.setup()
    second = dict(env.os.environ)
    assert first == second
