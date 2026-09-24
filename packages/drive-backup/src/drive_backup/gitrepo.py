"""The git side: preflight, pull, commit, push (LFS objects first).

Every git call runs with ``core.hooksPath=/dev/null``: a user-level hooks path
(commit-message rewriters, a global LFS purge) must not decide what a backup
commit looks like, and it would also shadow the repository's own LFS pre-push
hook. LFS objects are therefore uploaded explicitly with ``git lfs push`` before
the branch itself is pushed.

``GIT_LFS_SKIP_SMUDGE=1`` keeps ``pull`` from downloading every archive that other
machines pushed: the working tree only ever needs their pointers.
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


class GitError(Exception):
    """A git precondition failed or a git command exited non-zero."""


@dataclass
class GitRepo:
    path: Path
    lfs: bool = True
    push_attempts: int = 3

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ | {"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
        argv = ["git", "-c", "core.hooksPath=/dev/null", "-C", str(self.path), *args]
        proc = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        if check and proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            raise GitError(f"git {' '.join(args)} failed ({proc.returncode}): {detail}")
        return proc

    def _out(self, *args: str) -> str:
        return self._git(*args).stdout.strip()

    # -- preflight -----------------------------------------------------------------

    def preflight(self) -> None:
        if not self.path.is_dir():
            raise GitError(f"repository directory does not exist: {self.path}")
        top = self._git("rev-parse", "--show-toplevel", check=False)
        if top.returncode != 0:
            raise GitError(f"not a git repository: {self.path}")
        if Path(top.stdout.strip()).resolve() != self.path.resolve():
            raise GitError(f"{self.path} is inside {top.stdout.strip()}, not a repository root")
        self.branch()
        self.remote()
        dirty = self._out("status", "--porcelain", "--untracked-files=no")
        if dirty:
            raise GitError(f"working tree has uncommitted changes:\n{dirty}")
        if self.lfs:
            if self._git("lfs", "version", check=False).returncode != 0:
                raise GitError("git-lfs is not installed")
            if not self._git("config", "--get", "filter.lfs.clean", check=False).stdout.strip():
                raise GitError("git-lfs filters are not configured: run `git lfs install`")

    def branch(self) -> str:
        proc = self._git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
        if proc.returncode != 0:
            raise GitError("HEAD is detached; check out the branch backups go to")
        return proc.stdout.strip()

    def remote(self) -> str:
        branch = self.branch()
        proc = self._git("config", "--get", f"branch.{branch}.remote", check=False)
        if not proc.stdout.strip():
            raise GitError(f"branch {branch!r} has no upstream remote")
        return proc.stdout.strip()

    def require_lfs_tracked(self, rel: str) -> None:
        """Refuse to commit an archive that would bypass LFS."""
        attr = self._out("check-attr", "filter", "--", rel)
        if not attr.endswith(": lfs"):
            raise GitError(
                f"{rel} is not tracked by LFS ({attr!r}); add "
                "`*.tar.zst filter=lfs diff=lfs merge=lfs -text` to .gitattributes"
            )

    # -- sync ----------------------------------------------------------------------

    def pull(self) -> None:
        self._git("pull", "--ff-only", "--quiet")

    def commit(self, paths: Sequence[str], message: str) -> bool:
        """Commit exactly ``paths``; return False when there was nothing to commit."""
        if not paths:
            return False
        self._git("add", "--", *paths)
        staged = self._git("diff", "--cached", "--quiet", "--", *paths, check=False)
        if staged.returncode == 0:
            return False
        # A pathspec commit records only these paths, whatever else is staged.
        self._git("commit", "--quiet", "-m", message, "--", *paths)
        return True

    def push(self) -> None:
        branch, remote = self.branch(), self.remote()
        for attempt in range(1, self.push_attempts + 1):
            if self.lfs:
                self._git("lfs", "push", remote, branch)
            proc = self._git("push", "--quiet", remote, branch, check=False)
            if proc.returncode == 0:
                return
            log.warning("push attempt %d failed: %s", attempt, proc.stderr.strip())
            if attempt < self.push_attempts:
                # Another machine pushed first; our archives never collide with its.
                self._git("pull", "--rebase", "--quiet", remote, branch)
        raise GitError(f"push to {remote}/{branch} failed after {self.push_attempts} attempts")
