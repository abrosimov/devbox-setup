from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from drive_backup.config import Config, DirSpec, parse
from drive_backup.gitrepo import GitError, GitRepo
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


def _run(cfg: Config, rt: Runtime, *, push: bool = True) -> RunReport:
    options = RunOptions(profile="work", push=push)
    backup = Backup(cfg, options, GitRepo(cfg.repo_dir, lfs=False), rt)
    return backup.run(io.StringIO("log line\n"))


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


def test_parts_outside_lfs_are_refused_and_removed(repo: Path, source: Path) -> None:
    (repo / ".gitattributes").write_text("*.tar.zst filter=lfs diff=lfs merge=lfs -text\n")
    git(repo, "commit", "-qam", "no part pattern")
    cfg = _config(repo, DirSpec("claude", source), max_part_bytes=64)
    report = _run(cfg, _runtime(FakeClock()), push=False)

    assert "part-001 is not tracked by LFS" in str(report.error)
    assert sorted(p.name for p in (repo / "2026-09").iterdir()) == ["work_backup_2026-09-26.log"]


def test_unpushed_commit_from_failed_run_is_rebased_and_pushed(
    repo: Path, remote: Path, source: Path, tmp_path: Path
) -> None:
    cfg = _config(repo, DirSpec("claude", source))
    _run(cfg, _runtime(FakeClock()), push=False)
    other = clone(remote, tmp_path / "other")
    (other / "personal.txt").write_text("p")
    git(other, "add", "personal.txt")
    git(other, "commit", "-qm", "personal")
    git(other, "push", "-q")

    report = _run(cfg, _runtime(FakeClock()))

    assert report.ok, report.error
    files = git(remote, "ls-tree", "-r", "--name-only", "master").splitlines()
    assert {
        "personal.txt",
        "2026-09/work_claude_2026-09-26.tar.zst",
        "2026-09/work_claude_2026-09-26-2.tar.zst",
    } <= set(files)
    assert git(repo, "status", "--porcelain") == ""


def test_conflicting_pull_is_aborted_and_leaves_the_branch_usable(
    repo: Path, remote: Path, tmp_path: Path
) -> None:
    (repo / "notes.txt").write_text("local\n")
    git(repo, "add", "notes.txt")
    git(repo, "commit", "-qm", "local")
    local_head = git(repo, "rev-parse", "HEAD")
    other = clone(remote, tmp_path / "other")
    (other / "notes.txt").write_text("remote\n")
    git(other, "add", "notes.txt")
    git(other, "commit", "-qm", "remote")
    git(other, "push", "-q")

    gitrepo = GitRepo(repo, lfs=False)
    with pytest.raises(GitError, match="pull --rebase"):
        gitrepo.pull()

    git_dir = repo / ".git"
    assert not (git_dir / "rebase-merge").exists()
    assert not (git_dir / "rebase-apply").exists()
    assert git(repo, "rev-parse", "HEAD") == local_head
    assert gitrepo.branch() == "master"
    assert git(repo, "status", "--porcelain") == ""


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
