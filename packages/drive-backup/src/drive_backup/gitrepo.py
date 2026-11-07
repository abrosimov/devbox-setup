"""The git side: a private worktree on the target branch, commit, push (LFS objects first).

A run never reads or modifies the user's checkout of ``repo_dir``: whatever branch,
upstream, HEAD or working-tree state it has, the run fetches the target branch (the
remote's default branch unless configured), checks it out detached into a private
worktree inside the git directory, writes and commits there, and pushes ``HEAD`` to
that branch. The worktree is removed afterwards; one left by a crashed run is removed
at the start of the next.

Every git call runs with ``core.hooksPath=/dev/null``: a user-level hooks path
(commit-message rewriters, a global LFS purge) must not decide what a backup
commit looks like, and it would also shadow the repository's own LFS pre-push
hook. LFS objects are therefore uploaded explicitly with ``git lfs push`` before
the branch itself is pushed.

``GIT_LFS_SKIP_SMUDGE=1`` keeps the worktree checkout from downloading every archive
that other machines pushed: it only ever needs their pointers.

A commit that is not pushed (``--no-push``, or every push attempt failed) is kept at
``refs/drive-backup/unpushed/<sha>``. The next run replays it onto the remote tip
and pushes it together with its own commit. A rebase that stops half-way is
aborted, so it never wedges the following runs.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

WORKTREE_DIR: Final = "drive-backup-worktree"
UNPUSHED_PREFIX: Final = "refs/drive-backup/unpushed/"


class GitError(Exception):
    """A git precondition failed or a git command exited non-zero."""


@dataclass(frozen=True)
class _Git:
    cwd: Path

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ | {"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
        argv = ["git", "-c", "core.hooksPath=/dev/null", "-C", str(self.cwd), *args]
        proc = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        if check and proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            raise GitError(f"git {' '.join(args)} failed ({proc.returncode}): {detail}")
        return proc

    def out(self, *args: str) -> str:
        return self.run(*args).stdout.strip()

    def fetch(self, remote: str, branch: str) -> str:
        tracking = f"refs/remotes/{remote}/{branch}"
        self.run("fetch", "--quiet", "--no-tags", remote, f"+refs/heads/{branch}:{tracking}")
        return tracking


@dataclass
class GitRepo:
    path: Path
    lfs: bool = True
    push_attempts: int = 3
    remote: str = "origin"
    branch: str | None = None

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return _Git(self.path).run(*args, check=check)

    def _out(self, *args: str) -> str:
        return self._git(*args).stdout.strip()

    def preflight(self) -> None:
        if not self.path.is_dir():
            raise GitError(f"repository directory does not exist: {self.path}")
        top = self._git("rev-parse", "--show-toplevel", check=False)
        if top.returncode != 0:
            raise GitError(f"not a git repository: {self.path}")
        if Path(top.stdout.strip()).resolve() != self.path.resolve():
            raise GitError(f"{self.path} is inside {top.stdout.strip()}, not a repository root")
        if self.lfs:
            if self._git("lfs", "version", check=False).returncode != 0:
                raise GitError("git-lfs is not installed")
            if not self._git("config", "--get", "filter.lfs.clean", check=False).stdout.strip():
                raise GitError("git-lfs filters are not configured: run `git lfs install`")

    def target_branch(self) -> str:
        if self.branch:
            return self.branch
        prefix = f"{self.remote}/"
        head = self._git(
            "symbolic-ref", "--quiet", "--short", f"refs/remotes/{self.remote}/HEAD", check=False
        ).stdout.strip()
        if head.startswith(prefix):
            return head.removeprefix(prefix)
        for line in self._out("ls-remote", "--symref", self.remote, "HEAD").splitlines():
            ref, _, name = line.partition("\t")
            if name == "HEAD" and ref.startswith("ref: refs/heads/"):
                return ref.removeprefix("ref: refs/heads/")
        raise GitError(
            f"cannot resolve the default branch of remote {self.remote!r}; "
            "set `branch` in the config"
        )

    def worktree_path(self) -> Path:
        common = self._out("rev-parse", "--path-format=absolute", "--git-common-dir")
        return Path(common) / WORKTREE_DIR

    @contextmanager
    def worktree(self) -> Generator[Worktree]:
        path = self.worktree_path()
        self._discard_worktree(path)
        try:
            branch = self.target_branch()
            tracking = _Git(self.path).fetch(self.remote, branch)
            # --force: a crashed run may have left the path registered but missing.
            self._git("worktree", "add", "--quiet", "--force", "--detach", str(path), tracking)
            tree = Worktree(
                path, self.remote, branch, lfs=self.lfs, push_attempts=self.push_attempts
            )
            tree.replay_unpushed()
            yield tree
        finally:
            self._discard_worktree(path)

    def _discard_worktree(self, path: Path) -> None:
        # Not `git worktree prune`: it would also drop the user's worktrees on unmounted disks.
        self._git("worktree", "remove", "--force", "--force", str(path), check=False)
        shutil.rmtree(path, ignore_errors=True)
        if path.exists():
            log.warning("could not remove the backup worktree %s", path)


class Worktree:
    def __init__(
        self, path: Path, remote: str, branch: str, *, lfs: bool, push_attempts: int
    ) -> None:
        self.path = path
        self.remote = remote
        self.branch = branch
        self._lfs = lfs
        self._push_attempts = push_attempts
        self._git = _Git(path)
        self._replayed: list[str] = []

    @property
    def tracking(self) -> str:
        return f"refs/remotes/{self.remote}/{self.branch}"

    def require_lfs_tracked(self, rel: str) -> None:
        """Refuse to commit an archive that would bypass LFS."""
        attr = self._git.out("check-attr", "filter", "--", rel)
        if not attr.endswith(": lfs"):
            raise GitError(
                f"{rel} is not tracked by LFS ({attr!r}); add "
                "`*.tar.zst filter=lfs diff=lfs merge=lfs -text` and "
                "`*.tar.zst.part-* filter=lfs diff=lfs merge=lfs -text` to .gitattributes"
            )

    def _rebase(self, onto: str) -> None:
        try:
            self._git.run("rebase", "--quiet", onto)
        except GitError:
            self._git.run("rebase", "--abort", check=False)
            raise

    def replay_unpushed(self) -> None:
        refs = self._git.out(
            "for-each-ref", "--sort=committerdate", "--format=%(refname)", UNPUSHED_PREFIX
        ).splitlines()
        for ref in refs:
            base = self._git.out("rev-parse", "HEAD")
            try:
                self._git.run("checkout", "--quiet", "--detach", ref)
                self._rebase(base)
            except GitError as exc:
                self._git.run("checkout", "--quiet", "--force", "--detach", base, check=False)
                log.warning("cannot replay %s, left in place: %s", ref, exc)
                continue
            self._replayed.append(ref)
            log.info("replayed unpushed backup commit(s) from %s", ref)

    def commit(self, paths: Sequence[str], message: str) -> bool:
        """Commit exactly ``paths``; return False when there was nothing to commit."""
        if not paths:
            return False
        self._git.run("add", "--", *paths)
        staged = self._git.run("diff", "--cached", "--quiet", "--", *paths, check=False)
        if staged.returncode == 0:
            return False
        # A pathspec commit records only these paths, whatever else is staged.
        self._git.run("commit", "--quiet", "-m", message, "--", *paths)
        return True

    def ahead(self) -> bool:
        return self._git.out("rev-list", "--count", f"{self.tracking}..HEAD") != "0"

    def push(self) -> None:
        target = f"HEAD:refs/heads/{self.branch}"
        for attempt in range(1, self._push_attempts + 1):
            if self._lfs:
                self._git.run("lfs", "push", self.remote, "HEAD")
            proc = self._git.run("push", "--quiet", self.remote, target, check=False)
            if proc.returncode == 0:
                self._drop_replayed(keep=None)
                return
            log.warning("push attempt %d failed: %s", attempt, proc.stderr.strip())
            if attempt < self._push_attempts:
                # Another machine pushed first; our archives never collide with its.
                self._git.fetch(self.remote, self.branch)
                self._rebase(self.tracking)
        raise GitError(
            f"push to {self.remote}/{self.branch} failed after {self._push_attempts} attempts"
        )

    def keep_unpushed(self) -> str:
        head = self._git.out("rev-parse", "HEAD")
        ref = f"{UNPUSHED_PREFIX}{head}"
        self._git.run("update-ref", ref, head)
        self._drop_replayed(keep=ref)
        return ref

    def _drop_replayed(self, keep: str | None) -> None:
        for ref in self._replayed:
            if ref != keep:
                self._git.run("update-ref", "-d", ref, check=False)
        self._replayed.clear()
