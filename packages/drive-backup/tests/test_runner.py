from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from drive_backup.config import Config, DeferPolicy, DirSpec
from drive_backup.gitrepo import GitRepo
from drive_backup.processes import Process
from drive_backup.runner import (
    Backup,
    LockedError,
    RunOptions,
    RunReport,
    Runtime,
    archive_name,
    run_lock,
)

from .conftest import clone, git

NOW = datetime(2026, 9, 26, 3, 0, tzinfo=timezone(timedelta(hours=3)))


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


def _runtime(clock: FakeClock, procs: list[list[Process]] | None = None) -> Runtime:
    snapshots = iter(procs or [])
    last: list[Process] = []

    def lister() -> list[Process]:
        nonlocal last
        last = next(snapshots, last)
        return last

    return Runtime(now=lambda: NOW, sleep=clock.sleep, monotonic=clock.monotonic, processes=lister)


def _config(repo: Path, *specs: DirSpec, defer: DeferPolicy | None = None) -> Config:
    return Config(repo_dir=repo, dirs=specs, defer=defer or DeferPolicy(), zstd_level=1)


def _run(cfg: Config, rt: Runtime, *, defer: bool = True, push: bool = True) -> RunReport:
    options = RunOptions(profile="work", defer=defer, push=push)
    backup = Backup(cfg, options, GitRepo(cfg.repo_dir, lfs=False), rt)
    return backup.run(io.StringIO("log line\n"))


def test_archive_name_suffixes_reruns() -> None:
    taken = {"work_claude_2026-09-26.tar.zst", "work_claude_2026-09-26-2.tar.zst"}
    assert archive_name("work", "claude", "2026-09-26", taken.__contains__) == (
        "work_claude_2026-09-26-3.tar.zst"
    )


def test_happy_path_commits_archives_and_log_and_pushes(
    repo: Path, remote: Path, source: Path, tmp_path: Path
) -> None:
    other = tmp_path / "home" / ".codex"
    other.mkdir()
    (other / "a").write_text("a")
    cfg = _config(repo, DirSpec("claude", source), DirSpec("codex", other))
    report = _run(cfg, _runtime(FakeClock()))

    assert report.ok
    files = git(remote, "ls-tree", "-r", "--name-only", "master").splitlines()
    assert sorted(files) == [
        ".gitattributes",
        "2026-09/work_backup_2026-09-26.log",
        "2026-09/work_claude_2026-09-26.tar.zst",
        "2026-09/work_codex_2026-09-26.tar.zst",
    ]
    subject = git(remote, "log", "-1", "--format=%s", "master")
    assert subject.startswith("backup(work): 2026-09-26: work_claude_2026-09-26.tar.zst")
    assert git(repo, "status", "--porcelain") == ""


def test_same_day_rerun_adds_suffixed_archive_and_appends_log(
    repo: Path, remote: Path, source: Path
) -> None:
    cfg = _config(repo, DirSpec("claude", source))
    _run(cfg, _runtime(FakeClock()))
    _run(cfg, _runtime(FakeClock()))
    files = git(remote, "ls-tree", "-r", "--name-only", "master").splitlines()
    assert "2026-09/work_claude_2026-09-26-2.tar.zst" in files
    assert (repo / "2026-09/work_backup_2026-09-26.log").read_text().count("log line") == 2


def test_busy_dir_is_deferred_until_sessions_exit(repo: Path, source: Path) -> None:
    claude = Process(1, "claude")
    clock = FakeClock()
    rt = _runtime(clock, [[claude], [claude], []])
    cfg = _config(
        repo,
        DirSpec("claude", source, busy=("claude",)),
        defer=DeferPolicy(interval_minutes=10, max_wait_minutes=60),
    )
    report = _run(cfg, rt)
    assert report.ok
    assert clock.sleeps == [600, 600]
    assert report.forced == []


def test_busy_dir_is_forced_after_deadline(repo: Path, source: Path, tmp_path: Path) -> None:
    free = tmp_path / "free"
    free.mkdir()
    clock = FakeClock()
    rt = _runtime(clock, [[Process(1, "claude")]])
    cfg = _config(
        repo,
        DirSpec("claude", source, busy=("claude",)),
        DirSpec("free", free),
        defer=DeferPolicy(interval_minutes=40, max_wait_minutes=60),
    )
    report = _run(cfg, rt)
    assert report.ok
    assert report.forced == ["claude"]
    # The free dir is archived straight away; the wait is capped by the deadline.
    assert [r.path.name.split("_")[1] for r in report.archives] == ["free", "claude"]
    assert clock.sleeps == [2400, 1200]


def test_no_defer_ignores_sessions(repo: Path, source: Path) -> None:
    clock = FakeClock()
    rt = _runtime(clock, [[Process(1, "claude")]])
    cfg = _config(repo, DirSpec("claude", source, busy=("claude",)))
    assert _run(cfg, rt, defer=False).ok
    assert clock.sleeps == []


def test_failure_commits_log_and_completed_archives(
    repo: Path, remote: Path, source: Path, tmp_path: Path
) -> None:
    cfg = _config(repo, DirSpec("claude", source), DirSpec("gone", tmp_path / "missing"))
    report = _run(cfg, _runtime(FakeClock()))
    assert not report.ok
    files = git(remote, "ls-tree", "-r", "--name-only", "master").splitlines()
    assert "2026-09/work_claude_2026-09-26.tar.zst" in files
    assert "2026-09/work_backup_2026-09-26.log" in files
    assert "FAILED" in git(remote, "log", "-1", "--format=%s", "master")


def test_missing_repo_fails_without_writing(tmp_path: Path, source: Path) -> None:
    cfg = _config(tmp_path / "nope", DirSpec("claude", source))
    report = _run(cfg, _runtime(FakeClock()))
    assert "does not exist" in str(report.error)
    assert not (tmp_path / "nope").exists()


def test_dirty_repo_is_refused(repo: Path, source: Path) -> None:
    (repo / ".gitattributes").write_text("changed\n")
    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))
    assert "uncommitted" in str(report.error)


def test_archive_outside_lfs_is_refused(repo: Path, source: Path) -> None:
    (repo / ".gitattributes").unlink()
    git(repo, "commit", "-qam", "drop lfs")
    report = _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()))
    assert "not tracked by LFS" in str(report.error)
    assert not list((repo / "2026-09").glob("*.tar.zst"))


def test_push_race_is_rebased(repo: Path, remote: Path, source: Path, tmp_path: Path) -> None:
    # The other machine pushes after our pull but before our push.
    other = clone(remote, tmp_path / "other")
    cfg = _config(repo, DirSpec("claude", source))
    backup = Backup(
        cfg, RunOptions(profile="work"), GitRepo(repo, lfs=False), _runtime(FakeClock())
    )
    real_pull = backup.git.pull

    def pull_then_race() -> None:
        real_pull()
        (other / "personal.txt").write_text("p")
        git(other, "add", "personal.txt")
        git(other, "commit", "-qm", "personal")
        git(other, "push", "-q")

    backup.git.pull = pull_then_race
    assert backup.run(io.StringIO()).ok
    files = git(remote, "ls-tree", "-r", "--name-only", "master").splitlines()
    assert {"personal.txt", "2026-09/work_claude_2026-09-26.tar.zst"} <= set(files)


def test_no_push_commits_locally(repo: Path, remote: Path, source: Path) -> None:
    _run(_config(repo, DirSpec("claude", source)), _runtime(FakeClock()), push=False)
    assert git(repo, "log", "-1", "--format=%s").startswith("backup(work)")
    assert git(remote, "log", "-1", "--format=%s", "master") == "init"


def test_lock_is_exclusive(tmp_path: Path) -> None:
    lock = tmp_path / "state" / "run.lock"
    with run_lock(lock), pytest.raises(LockedError), run_lock(lock):
        pass
