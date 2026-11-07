"""One backup run: lock, archive, commit, push.

Everything is written into the private backup worktree (see ``gitrepo``), never
into the user's checkout. Output layout on the target branch::

    <YYYY-MM>/<profile>_<name>_<YYYY-MM-DD>.tar.zst            # fits in one part
    <YYYY-MM>/<profile>_<name>_<YYYY-MM-DD>.tar.zst.part-001   # otherwise, -002, …
    <YYYY-MM>/<profile>_backup_<YYYY-MM-DD>.log

The run log is committed together with the archives, and also when the run fails,
so a failure is visible from any clone of the repository. Only a failure that
leaves no worktree to commit into (repository missing or not a repository, remote
unreachable) stays local.
"""

from __future__ import annotations

import fcntl
import io
import logging
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .archive import ArchiveResult, write_archive
from .config import Config, DirSpec
from .gitrepo import GitError, GitRepo, Worktree

log = logging.getLogger("drive_backup")


class LockedError(Exception):
    """Another run holds the lock."""


@dataclass
class RunOptions:
    profile: str
    push: bool = True


@dataclass
class Runtime:
    """Side-effect seams; tests replace them."""

    now: Callable[[], datetime] = lambda: datetime.now().astimezone()
    monotonic: Callable[[], float] = time.monotonic


@dataclass
class RunReport:
    archives: list[ArchiveResult] = field(default_factory=list[ArchiveResult])
    error: BaseException | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@contextmanager
def run_lock(path: Path) -> Generator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LockedError(f"another drive-backup run holds {path}") from exc
        yield


def archive_name(profile: str, name: str, day: str, taken: Callable[[str], bool]) -> str:
    """``<profile>_<name>_<day>.tar.zst``, suffixed ``-2``, ``-3`` on same-day reruns."""
    base = f"{profile}_{name}_{day}"
    candidate, n = f"{base}.tar.zst", 1
    while taken(candidate):
        n += 1
        candidate = f"{base}-{n}.tar.zst"
    return candidate


def archive_taken(month_dir: Path, name: str) -> bool:
    return (month_dir / name).exists() or any(month_dir.glob(f"{name}.part-*"))


def _archive_label(result: ArchiveResult) -> str:
    first = result.parts[0].name
    return first if len(result.parts) == 1 else f"{first}..{len(result.parts):03d}"


class Backup:
    def __init__(
        self, config: Config, options: RunOptions, git: GitRepo, runtime: Runtime | None = None
    ) -> None:
        self.config = config
        self.options = options
        self.git = git
        self.rt = runtime or Runtime()
        self.started = self.rt.now()
        self.month = self.started.strftime("%Y-%m")
        self.day = self.started.strftime("%Y-%m-%d")

    def _archive(self, spec: DirSpec, tree: Worktree, report: RunReport) -> None:
        month_dir = tree.path / self.month
        name = archive_name(
            self.options.profile,
            spec.name,
            self.day,
            lambda n: archive_taken(month_dir, n),
        )
        # Fail fast, before compressing; every produced file is checked again below.
        tree.require_lfs_tracked(f"{self.month}/{name}")
        log.info("archiving %s (%s) -> %s/%s", spec.name, spec.path, self.month, name)
        t0 = self.rt.monotonic()
        result = write_archive(
            spec,
            month_dir / name,
            self.config.zstd_level,
            self.config.max_part_bytes,
            approve=lambda path: tree.require_lfs_tracked(str(path.relative_to(tree.path))),
        )
        for warning in result.warnings:
            log.warning("%s: %s", spec.name, warning)
        log.info(
            "archived %s: %d files, %.1f MiB -> %.1f MiB in %.0fs",
            spec.name,
            result.files,
            result.bytes_in / 2**20,
            result.bytes_out / 2**20,
            self.rt.monotonic() - t0,
        )
        if len(result.parts) > 1:
            log.info(
                "split %s into %d parts: %s",
                name,
                len(result.parts),
                ", ".join(f"{p.name} {p.stat().st_size / 2**20:.1f} MiB" for p in result.parts),
            )
        report.archives.append(result)

    def archive_all(self, tree: Worktree, report: RunReport) -> None:
        for spec in self.config.dirs:
            self._archive(spec, tree, report)

    def _log_path(self, tree: Worktree) -> Path:
        return tree.path / self.month / f"{self.options.profile}_backup_{self.day}.log"

    def _commit_message(self, report: RunReport) -> str:
        head = f"backup({self.options.profile}): {self.day}"
        if not report.ok:
            return f"{head} FAILED: {report.error}"
        names = ", ".join(_archive_label(r) for r in report.archives)
        return f"{head}: {names}"

    def run(self, log_buffer: io.StringIO) -> RunReport:
        report = RunReport()
        try:
            self.git.preflight()
            with self.git.worktree() as tree:
                self._backup(tree, report, log_buffer)
        except GitError as exc:
            # No worktree to commit into: the log stays local.
            report.error = exc
            log.error("backup not started: %s", exc)
        return report

    def _backup(self, tree: Worktree, report: RunReport, log_buffer: io.StringIO) -> None:
        log.info("backing up to %s/%s", tree.remote, tree.branch)
        try:
            self.archive_all(tree, report)
        except Exception as exc:
            report.error = exc
            log.exception("backup failed")

        log.info(
            "run %s: %d archive(s)", "succeeded" if report.ok else "FAILED", len(report.archives)
        )
        self._publish(tree, report, log_buffer)

    def _publish(self, tree: Worktree, report: RunReport, log_buffer: io.StringIO) -> None:
        log_path = self._log_path(tree)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(log_buffer.getvalue())
        paths = [str(p.relative_to(tree.path)) for r in report.archives for p in r.parts]
        paths.append(str(log_path.relative_to(tree.path)))
        try:
            tree.commit(paths, self._commit_message(report))
            if not tree.ahead():
                return
            if not self.options.push:
                log.info("not pushed; commit kept at %s", tree.keep_unpushed())
                return
            try:
                tree.push()
            except GitError:
                log.warning("commit kept at %s for the next run", tree.keep_unpushed())
                raise
            log.info("pushed to %s/%s", tree.remote, tree.branch)
        except GitError as exc:
            log.exception("publishing failed")
            if report.error is None:
                report.error = exc
