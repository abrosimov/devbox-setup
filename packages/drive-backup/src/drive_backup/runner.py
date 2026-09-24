"""One backup run: lock, defer while sessions are live, archive, commit, push.

Output layout inside the repository::

    <YYYY-MM>/<profile>_<name>_<YYYY-MM-DD>.tar.zst
    <YYYY-MM>/<profile>_backup_<YYYY-MM-DD>.log

The run log is committed together with the archives, and also when the run fails,
so a failure is visible from any clone of the repository. Only a failure that
leaves no usable repository (missing, not a repo, detached HEAD) stays local.
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
from .gitrepo import GitError, GitRepo
from .processes import ProcessLister, find_busy, list_processes

log = logging.getLogger("drive_backup")


class LockedError(Exception):
    """Another run holds the lock."""


@dataclass
class RunOptions:
    profile: str
    defer: bool = True
    push: bool = True


@dataclass
class Runtime:
    """Side-effect seams; tests replace them."""

    now: Callable[[], datetime] = lambda: datetime.now().astimezone()
    sleep: Callable[[float], None] = time.sleep
    monotonic: Callable[[], float] = time.monotonic
    processes: ProcessLister = list_processes


@dataclass
class RunReport:
    archives: list[ArchiveResult] = field(default_factory=list[ArchiveResult])
    forced: list[str] = field(default_factory=list[str])
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


class Backup:
    def __init__(
        self, config: Config, options: RunOptions, git: GitRepo, runtime: Runtime | None = None
    ) -> None:
        self.config = config
        self.options = options
        self.git = git
        self.rt = runtime or Runtime()
        self.started = self.rt.now()
        self.month_dir = config.repo_dir / self.started.strftime("%Y-%m")
        self.day = self.started.strftime("%Y-%m-%d")

    # -- archiving -----------------------------------------------------------------

    def _archive(self, spec: DirSpec, report: RunReport) -> None:
        rel_month = self.month_dir.relative_to(self.config.repo_dir)
        name = archive_name(
            self.options.profile, spec.name, self.day, lambda n: (self.month_dir / n).exists()
        )
        self.git.require_lfs_tracked(f"{rel_month}/{name}")
        log.info("archiving %s (%s) -> %s/%s", spec.name, spec.path, rel_month, name)
        t0 = self.rt.monotonic()
        result = write_archive(spec, self.month_dir / name, self.config.zstd_level)
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
        report.archives.append(result)

    def _busy(self, spec: DirSpec) -> list[str]:
        procs = find_busy(spec.busy, self.rt.processes)
        return [f"{p.pid} {p.args[:80]}" for p in procs]

    def archive_all(self, report: RunReport) -> None:
        pending = list(self.config.dirs)
        policy = self.config.defer
        deadline = self.rt.monotonic() + policy.max_wait_minutes * 60
        while pending:
            waiting: list[DirSpec] = []
            for spec in pending:
                busy: list[str] = self._busy(spec) if self.options.defer else []
                if busy:
                    log.info("%s is in use, deferring: %s", spec.name, "; ".join(busy))
                    waiting.append(spec)
                else:
                    self._archive(spec, report)
            pending = waiting
            if not pending:
                return
            remaining = deadline - self.rt.monotonic()
            if remaining <= 0:
                for spec in pending:
                    log.warning(
                        "%s still in use after deferral window; archiving anyway", spec.name
                    )
                    report.forced.append(spec.name)
                    self._archive(spec, report)
                return
            self.rt.sleep(min(policy.interval_minutes * 60, remaining))

    # -- run -----------------------------------------------------------------------

    def _log_path(self) -> Path:
        return self.month_dir / f"{self.options.profile}_backup_{self.day}.log"

    def _commit_message(self, report: RunReport) -> str:
        head = f"backup({self.options.profile}): {self.day}"
        if not report.ok:
            return f"{head} FAILED: {report.error}"
        names = ", ".join(r.path.name for r in report.archives)
        return f"{head}: {names}"

    def run(self, log_buffer: io.StringIO) -> RunReport:
        report = RunReport()
        try:
            self.git.preflight()
        except GitError as exc:
            # No usable repository: there is nowhere to commit the log to.
            report.error = exc
            log.error("repository unusable: %s", exc)
            return report

        try:
            self.git.pull()
            self.archive_all(report)
        except Exception as exc:
            report.error = exc
            log.exception("backup failed")

        log.info(
            "run %s: %d archive(s)", "succeeded" if report.ok else "FAILED", len(report.archives)
        )
        self._publish(report, log_buffer)
        return report

    def _publish(self, report: RunReport, log_buffer: io.StringIO) -> None:
        log_path = self._log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(log_buffer.getvalue())
        repo = self.config.repo_dir
        paths = [str(r.path.relative_to(repo)) for r in report.archives]
        paths.append(str(log_path.relative_to(repo)))
        try:
            committed = self.git.commit(paths, self._commit_message(report))
            if committed and self.options.push:
                self.git.push()
                log.info("pushed")
        except GitError as exc:
            log.exception("publishing failed")
            if report.error is None:
                report.error = exc
