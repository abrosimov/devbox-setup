from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_bash_cache_env as hook

if TYPE_CHECKING:
    import pytest


def test_sanitise_session_id_alphanumeric_passthrough() -> None:
    assert hook.sanitise_session_id("abc-123_ghi") == "abc-123_ghi"


def test_sanitise_session_id_replaces_dot() -> None:
    # Dots are dropped to defeat `..` traversal — safer than trying to detect
    # only the malicious form.
    assert hook.sanitise_session_id("abc.def") == "abc-def"


def test_sanitise_session_id_replaces_traversal() -> None:
    assert hook.sanitise_session_id("../../etc/passwd") == "etc-passwd"


def test_sanitise_session_id_empty_falls_back() -> None:
    assert hook.sanitise_session_id("") == hook.UNKNOWN_SESSION
    assert hook.sanitise_session_id("///") == hook.UNKNOWN_SESSION


def test_compute_session_cache_covers_all_vars(tmp_path: Path) -> None:
    cache = hook.compute_session_cache("sess1", sessions_root=tmp_path)
    for name in hook.CACHE_VARS:
        assert name in cache.variables
        assert cache.variables[name].startswith(str(tmp_path / "sess1"))


def test_ensure_cache_dirs_creates_all(tmp_path: Path) -> None:
    cache = hook.compute_session_cache("sess1", sessions_root=tmp_path)
    hook.ensure_cache_dirs(cache)
    for path in cache.variables.values():
        assert Path(path).is_dir()


def test_build_env_prefix_includes_all_vars(tmp_path: Path) -> None:
    cache = hook.compute_session_cache("s", sessions_root=tmp_path)
    prefix = hook.build_env_prefix(cache)
    assert prefix.startswith("export ")
    assert prefix.endswith(";")
    for name in hook.CACHE_VARS:
        assert f"{name}=" in prefix


def test_wrap_command_prepends_prefix(tmp_path: Path) -> None:
    cache = hook.compute_session_cache("s", sessions_root=tmp_path)
    wrapped = hook.wrap_command("uv run pytest", cache)
    assert "export UV_CACHE_DIR=" in wrapped
    assert wrapped.endswith(" uv run pytest")


def test_should_skip_gh_and_git_log() -> None:
    assert hook.should_skip("gh pr view 1")
    assert hook.should_skip("gh")
    assert hook.should_skip("git log --oneline")
    assert hook.should_skip("git show HEAD")
    assert hook.should_skip("git blame README.md")


def test_should_skip_leaves_other_commands() -> None:
    assert not hook.should_skip("uv run pytest")
    assert not hook.should_skip("git status")
    assert not hook.should_skip("git diff")
    assert not hook.should_skip("ghosthound start")


def test_prune_stale_sessions_removes_old(tmp_path: Path) -> None:
    old = tmp_path / "old"
    fresh = tmp_path / "fresh"
    old.mkdir()
    fresh.mkdir()
    now = time.time()
    old_time = now - hook.SESSION_TTL_SECONDS - 100
    import os

    os.utime(old, (old_time, old_time))
    hook.prune_stale_sessions(sessions_root=tmp_path, now=now)
    assert not old.exists()
    assert fresh.exists()


def test_prune_stale_sessions_keeps_current(tmp_path: Path) -> None:
    current = tmp_path / "current"
    current.mkdir()
    import os

    old_time = time.time() - hook.SESSION_TTL_SECONDS - 100
    os.utime(current, (old_time, old_time))
    hook.prune_stale_sessions(
        sessions_root=tmp_path, keep_session_id="current", now=time.time(),
    )
    assert current.exists()


def test_prune_stale_sessions_missing_root_noop(tmp_path: Path) -> None:
    hook.prune_stale_sessions(sessions_root=tmp_path / "does-not-exist")


def test_main_no_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert hook.main() == 0
    assert out.getvalue() == ""


def test_main_skips_gh_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(hook, "SESSIONS_ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps({"session_id": "s1", "tool_input": {"command": "gh pr view"}}),
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert hook.main() == 0
    assert out.getvalue() == ""


def test_main_wraps_uv_run_pytest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(hook, "SESSIONS_ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {"session_id": "sess-abc", "tool_input": {"command": "uv run pytest"}},
            ),
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert hook.main() == 0
    payload = json.loads(out.getvalue())
    updated = payload["hookSpecificOutput"]["updatedInput"]["command"]
    assert "export UV_CACHE_DIR=" in updated
    assert str(tmp_path / "sess-abc" / "uv-cache") in updated
    assert updated.endswith(" uv run pytest")
    assert (tmp_path / "sess-abc" / "uv-cache").is_dir()


def test_main_sanitises_path_traversal_in_session_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(hook, "SESSIONS_ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "../../escape",
                    "tool_input": {"command": "uv run pytest"},
                },
            ),
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert hook.main() == 0
    payload = json.loads(out.getvalue())
    updated = payload["hookSpecificOutput"]["updatedInput"]["command"]
    assert "/../.." not in updated
    assert "escape" in updated


def test_main_handles_missing_session_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(hook, "SESSIONS_ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "uv run pytest"}})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert hook.main() == 0
    payload = json.loads(out.getvalue())
    updated = payload["hookSpecificOutput"]["updatedInput"]["command"]
    assert hook.UNKNOWN_SESSION in updated


def test_main_handles_non_string_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(hook, "SESSIONS_ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"session_id": "s", "tool_input": {"command": 42}})),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert hook.main() == 0
    assert out.getvalue() == ""
