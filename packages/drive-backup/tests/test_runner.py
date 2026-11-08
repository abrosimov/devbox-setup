from __future__ import annotations

import io
import logging
import shutil
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from drive_backup.config import Config, DirSpec, parse
from drive_backup.gitrepo import UNPUSHED_PREFIX, WORKTREE_DIR, GitRepo, Worktree
from drive_backup.runner import (
    Backup,
    LockedError,
    RunOptions,
    RunReport,
    Runtime,
    archive_name,
    archive_taken,
    run_lock,
)

from .conftest import clone, git

NOW = datetime(2026, 9, 26, 3, 0, tzinfo=timezone(timedelta(hours=3)))


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t


def _runtime(clock: FakeClock) -> Runtime:
    return Runtime(now=lambda: NOW, monotonic=clock.monotonic)


def _config(repo: Path, *specs: DirSpec, max_part_bytes: int = 2**31) -> Config:
    return Config(repo_dir=repo, dirs=specs, zstd_level=1, max_part_bytes=max_part_bytes)


def _backup(cfg: Config, *, branch: str | None = None, push_attempts: int = 3) -> Backup:
    gitrepo = GitRepo(cfg.repo_dir, lfs=False, push_attempts=push_attempts, branch=branch)
    return Backup(cfg, RunOptions(profile="work"), gitrepo, _runtime(FakeClock()))


def _run(cfg: Config, rt: Runtime, *, push: bool = True) -> RunReport:
    options = RunOptions(profile="work", push=push)
    backup = Backup(cfg, options, GitRepo(cfg.repo_dir, lfs=False), rt)
    return backup.run(io.StringIO("log line\n"))


def _files(remote: Path, branch: str = "master") -> list[str]:
    return git(remote, "ls-tree", "-r", "--name-only", branch).splitlines()


def _unpushed(repo: Path) -> list[str]:
    return git(repo, "for-each-ref", "--format=%(refname)", UNPUSHED_PREFIX).splitlines()


def _checkout_state(repo: Path) -> dict[str, bytes]:
    state = {
        str(p.relative_to(repo)): p.read_bytes()
        for p in sorted(repo.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    }
    for name in ("HEAD", "index"):
        state[f".git/{name}"] = (repo / ".git" / name).read_bytes()
    state["refs/heads"] = git(repo, "for-each-ref", "refs/heads").encode()
    return state


def _assert_no_backup_worktree(repo: Path) -> None:
    assert not (repo / ".git" / WORKTREE_DIR).exists()
    assert git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


def _after_archiving(
    backup: Backup, monkeypatch: pytest.MonkeyPatch, hook: Callable[[], object]
) -> None:
    real = backup.archive_all

    def archive_then_hook(tree: Worktree, report: RunReport) -> None:
        real(tree, report)
        hook()

    monkeypatch.setattr(backup, "archive_all", archive_then_hook)


def _push_from(other: Path, rel: str, text: str) -> None:
    path = other / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    git(other, "add", rel)
    git(other, "commit", "-qm", f"other: {rel}")
    git(other, "push", "-q")


def test_archive_name_suffixes_reruns() -> None:
    taken = {"work_claude_2026-09-26.tar.zst", "work_claude_2026-09-26-2.tar.zst"}
    assert archive_name("work", "claude", "2026-09-26", taken.__contains__) == (
        "work_claude_2026-09-26-3.tar.zst"
    )


def test_existing_parts_take_the_archive_name(tmp_path: Path) -> None:
    (tmp_path / "work_claude_2026-09-26.tar.zst.part-001").write_bytes(b"x")
    (tmp_path / "work_claude_2026-09-26.tar.zst.part-002").write_bytes(b"x")

    def taken(name: str) -> bool:
        return archive_taken(tmp_path, name)

    assert archive_name("work", "claude", "2026-09-26", taken) == "work_claude_2026-09-26-2.tar.zst"
    assert not archive_taken(tmp_path, "work_codex_2026-09-26.tar.zst")


def test_large_archive_is_committed_as_parts(
    repo: Path, remote: Path, source: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="drive_backup")
    cfg = _config(repo, DirSpec("claude", source), max_part_bytes=64)
    report = _run(cfg, _runtime(FakeClock()))

    assert report.ok
    parts = report.archives[0].parts
    assert len(parts) > 1
    files = git(remote, "ls-tree", "-r", "--name-only", "master").splitlines()
    assert sorted(files) == sorted(
        [".gitattributes", "2026-09/work_backup_2026-09-26.log"]
        + [f"2026-09/{p.name}" for p in parts]
    )
    subject = git(remote, "log", "-1", "--format=%s", "master")
    assert subject == (
        f"backup(work): 2026-09-26: work_claude_2026-09-26.tar.zst.part-001..{len(parts):03d}"
    )
    assert f"split work_claude_2026-09-26.tar.zst into {len(parts)} parts" in caplog.text


def test_same_day_rerun_after_parts_gets_suffix(repo: Path, remote: Path, source: Path) -> None:
    cfg = _config(repo, DirSpec("claude", source), max_part_bytes=64)
    _run(cfg, _runtime(FakeClock()))
    report = _run(cfg, _runtime(FakeClock()))

    assert report.ok
    assert report.archives[0].parts[0].name == "work_claude_2026-09-26-2.tar.zst.part-001"


def test_parts_outside_lfs_are_refused_and_not_committed(
    repo: Path, remote: Path, source: Path
) -> None:
    (repo / ".gitattributes").write_text("*.tar.zst filter=lfs diff=lfs merge=lfs -text\n")
    git(repo, "commit", "-qam", "no part pattern")
    git(repo, "push", "-q")
    cfg = _config(repo, DirSpec("claude", source), max_part_bytes=64)
    report = _run(cfg, _runtime(FakeClock()))

    assert "part-001 is not tracked by LFS" in str(report.error)
    assert [f for f in _files(remote) if f.startswith("2026-09/")] == [
        "2026-09/work_backup_2026-09-26.log"
    ]


def test_unpushed_commit_from_no_push_run_is_replayed_and_pushed(
    repo: Path, remote: Path, source: Path, tmp_path: Path
) -> None:
    cfg = _config(repo, DirSpec("claude", source))
    _run(cfg, _runtime(FakeClock()), push=False)
    _push_from(clone(remote, tmp_path / "other"), "personal.txt", "p")

    report = _run(cfg, _runtime(FakeClock()))

    assert report.ok, report.error
    assert {
        "personal.txt",
        "2026-09/work_claude_2026-09-26.tar.zst",
        "2026-09/work_claude_2026-09-26-2.tar.zst",
    } <= set(_files(remote))
    assert _unpushed(repo) == []


def test_happy_path_commits_archives_and_log_and_pushes(
    repo: Path, remote: Path, source: Path, tmp_path: Path
) -> None:
    other = tmp_path / "home" / ".codex"
    other.mkdir()
    (other / "a").write_text("a")
    cfg = _config(repo, DirSpec("claude", source), DirSpec("codex", other))
    before = _checkout_state(repo)
    report = _run(cfg, _runtime(FakeClock()))

    assert report.ok
    assert sorted(_files(remote)) == [
        ".gitattributes",
        "2026-09/work_backup_2026-09-26.log",
        "2026-09/work_claude_2026-09-26.tar.zst",
        "2026-09/work_codex_2026-09-26.tar.zst",
    ]
    subject = git(remote, "log", "-1", "--format=%s", "master")
    assert subject.startswith("backup(work): 2026-09-26: work_claude_2026-09-26.tar.zst")
    assert _checkout_state(repo) == before
    _assert_no_backup_worktree(repo)


def test_same_day_rerun_adds_suffixed_archive_and_appends_log(
    repo: Path, remote: Path, source: Path
) -> None:
    cfg = _config(repo, DirSpec("claude", source))
    _run(cfg, _runtime(FakeClock()))
    _run(cfg, _runtime(FakeClock()))
    assert "2026-09/work_claude_2026-09-26-2.tar.zst" in _files(remote)
    run_log = git(remote, "show", "master:2026-09/work_backup_2026-09-26.log")
    assert run_log.count("log line") == 2


def test_legacy_deferral_config_archives_without_waiting(repo: Path, source: Path) -> None:
    cfg = parse(
        {
            "repo_dir": str(repo),
            "defer": {"interval_minutes": 15, "max_wait_minutes": 180},
            "dir": [{"name": "claude", "path": str(source), "busy": ["python"]}],
            "zstd_level": 1,
        },
        {},
    )
    report = _run(cfg, _runtime(FakeClock()), push=False)
    assert report.ok
    assert [[p.name for p in result.parts] for result in report.archives] == [
        ["work_claude_2026-09-26.tar.zst"]
    ]


def test_failure_commits_log_and_completed_archives_to_the_default_branch(
    repo: Path, remote: Path, source: Path, tmp_path: Path
) -> None:
    git(repo, "checkout", "-qb", "feature")
    cfg = _config(repo, DirSpec("claude", source), DirSpec("gone", tmp_path / "missing"))
    report = _run(cfg, _runtime(FakeClock()))

    assert not report.ok
    files = _files(remote)
    assert "2026-09/work_claude_2026-09-26.tar.zst" in files
    assert "2026-09/work_backup_2026-09-26.log" in files
    assert "FAILED" in git(remote, "log", "-1", "--format=%s", "master")
    assert git(remote, "for-each-ref", "--format=%(refname)", "refs/heads") == "refs/heads/master"
    assert git(repo, "symbolic-ref", "--short", "HEAD") == "feature"
    _assert_no_backup_worktree(repo)


def test_missing_repo_fails_without_writing(tmp_path: Path, source: Path) -> None:
    cfg = _config(tmp_path / "nope", DirSpec("claude", source))
    report = _run(cfg, _runtime(FakeClock()))
    assert "does not exist" in str(report.error)
    assert not (tmp_path / "nope").exists()


def test_unreachable_remote_fails_and_leaves_no_worktree(
    repo: Path, source: Path, tmp_path: Path
) -> None:
    git(repo, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))

    assert "git fetch" in str(report.error)
    _assert_no_backup_worktree(repo)


def test_feature_branch_with_deleted_upstream_backs_up_to_the_default_branch(
    repo: Path, remote: Path, source: Path
) -> None:
    git(repo, "checkout", "-qb", "pin_renovate_config")
    git(repo, "push", "-qu", "origin", "pin_renovate_config")
    git(repo, "push", "-q", "origin", "--delete", "pin_renovate_config")
    before = _checkout_state(repo)

    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))

    assert report.ok, report.error
    assert "2026-09/work_claude_2026-09-26.tar.zst" in _files(remote)
    assert git(remote, "for-each-ref", "--format=%(refname)", "refs/heads") == "refs/heads/master"
    assert _checkout_state(repo) == before


def test_dirty_checkout_is_left_byte_for_byte_untouched(
    repo: Path, remote: Path, source: Path
) -> None:
    # The modified .gitattributes also drops the LFS patterns: only the target branch's count.
    (repo / ".gitattributes").write_text("changed\n")
    (repo / "staged.txt").write_text("staged\n")
    git(repo, "add", "staged.txt")
    (repo / "untracked.txt").write_text("untracked\n")
    before = _checkout_state(repo)

    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))

    assert report.ok, report.error
    files = _files(remote)
    assert "2026-09/work_claude_2026-09-26.tar.zst" in files
    assert not {"staged.txt", "untracked.txt"} & set(files)
    assert git(remote, "show", "master:.gitattributes") != "changed"
    assert _checkout_state(repo) == before


def test_detached_head_is_left_alone(repo: Path, remote: Path, source: Path) -> None:
    git(repo, "checkout", "-q", "--detach")
    before = _checkout_state(repo)

    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))

    assert report.ok, report.error
    assert "2026-09/work_claude_2026-09-26.tar.zst" in _files(remote)
    assert _checkout_state(repo) == before


def test_default_branch_is_asked_from_the_remote_without_origin_head(
    repo: Path, remote: Path, source: Path
) -> None:
    git(remote, "branch", "main", "master")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    git(repo, "remote", "set-head", "origin", "--delete")

    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))

    assert report.ok, report.error
    assert "2026-09/work_claude_2026-09-26.tar.zst" in _files(remote, "main")
    assert _files(remote, "master") == [".gitattributes"]


def test_configured_branch_overrides_the_default(repo: Path, remote: Path, source: Path) -> None:
    git(remote, "branch", "backups", "master")
    backup = _backup(_config(repo, DirSpec("claude", source)), branch="backups")

    assert backup.run(io.StringIO()).ok
    assert "2026-09/work_claude_2026-09-26.tar.zst" in _files(remote, "backups")
    assert _files(remote, "master") == [".gitattributes"]


@pytest.mark.parametrize("leave_directory", [True, False])
def test_stale_worktree_from_a_crashed_run_is_removed_first(
    repo: Path, remote: Path, source: Path, leave_directory: bool
) -> None:
    stale = repo / ".git" / WORKTREE_DIR
    git(repo, "worktree", "add", "-q", "--detach", str(stale))
    if leave_directory:
        (stale / "2026-09").mkdir()
        (stale / "2026-09" / "work_claude_2026-09-26.tar.zst").write_bytes(b"half-written")
    else:
        shutil.rmtree(stale)

    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))

    assert report.ok, report.error
    assert "2026-09/work_claude_2026-09-26.tar.zst" in _files(remote)
    _assert_no_backup_worktree(repo)


def test_archive_outside_lfs_is_refused(repo: Path, remote: Path, source: Path) -> None:
    (repo / ".gitattributes").unlink()
    git(repo, "commit", "-qam", "drop lfs")
    git(repo, "push", "-q")
    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))
    assert "not tracked by LFS" in str(report.error)
    assert not [f for f in _files(remote) if f.endswith(".tar.zst")]


def test_push_race_is_rebased(
    repo: Path,
    remote: Path,
    source: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    other = clone(remote, remote.parent / "other")
    backup = _backup(_config(repo, DirSpec("claude", source)))
    _after_archiving(backup, monkeypatch, lambda: _push_from(other, "personal.txt", "p"))

    assert backup.run(io.StringIO()).ok
    assert {"personal.txt", "2026-09/work_claude_2026-09-26.tar.zst"} <= set(_files(remote))
    assert "push attempt 1 failed" in caplog.text
    _assert_no_backup_worktree(repo)


def test_conflicting_race_is_aborted_and_later_runs_still_succeed(
    repo: Path,
    remote: Path,
    source: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    other = clone(remote, remote.parent / "other")
    cfg = _config(repo, DirSpec("claude", source))
    backup = _backup(cfg)
    log_rel = "2026-09/work_backup_2026-09-26.log"
    _after_archiving(backup, monkeypatch, lambda: _push_from(other, log_rel, "other\n"))

    report = backup.run(io.StringIO("ours\n"))

    assert "git rebase" in str(report.error)
    assert len(_unpushed(repo)) == 1
    _assert_no_backup_worktree(repo)

    assert _run(cfg, _runtime(FakeClock())).ok
    assert "2026-09/work_claude_2026-09-26.tar.zst" in _files(remote)
    assert "cannot replay" in caplog.text
    assert len(_unpushed(repo)) == 1


def test_failed_push_keeps_the_commit_for_the_next_run(
    repo: Path, remote: Path, source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _config(repo, DirSpec("claude", source))
    backup = _backup(cfg, push_attempts=1)
    hidden = tmp_path / "hidden.git"
    _after_archiving(backup, monkeypatch, lambda: remote.rename(hidden))

    report = backup.run(io.StringIO())

    assert "push to origin/master failed" in str(report.error)
    assert len(_unpushed(repo)) == 1
    hidden.rename(remote)

    assert _run(cfg, _runtime(FakeClock())).ok
    assert {
        "2026-09/work_claude_2026-09-26.tar.zst",
        "2026-09/work_claude_2026-09-26-2.tar.zst",
    } <= set(_files(remote))
    assert _unpushed(repo) == []


def test_no_push_keeps_the_commit_off_every_branch(repo: Path, remote: Path, source: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()), push=False)

    [kept] = _unpushed(repo)
    assert git(repo, "log", "-1", "--format=%s", kept).startswith("backup(work)")
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(remote, "log", "-1", "--format=%s", "master") == "init"
    _assert_no_backup_worktree(repo)


@pytest.mark.skipif(shutil.which("git-lfs") is None, reason="git-lfs is not installed")
def test_lfs_objects_are_pushed_from_the_worktree(repo: Path, remote: Path, source: Path) -> None:
    git(repo, "lfs", "install", "--local", "--skip-repo")
    cfg = _config(repo, DirSpec("claude", source))
    backup = Backup(cfg, RunOptions(profile="work"), GitRepo(repo), _runtime(FakeClock()))

    report = backup.run(io.StringIO())

    assert report.ok, report.error
    pointer = git(remote, "show", "master:2026-09/work_claude_2026-09-26.tar.zst")
    oid = pointer.split("oid sha256:")[1].split()[0]
    assert (remote / "lfs" / "objects" / oid[:2] / oid[2:4] / oid).is_file()


def test_lock_is_exclusive(tmp_path: Path) -> None:
    lock = tmp_path / "state" / "run.lock"
    with run_lock(lock), pytest.raises(LockedError), run_lock(lock):
        pass
