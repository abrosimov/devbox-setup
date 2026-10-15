# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Split the staged changes into topic commits on master and push them.

Run:   uv run ai_written_scripts/commit-staged-topics/commit_topics.py [--dry-run] [--no-push]
Test:  uv run pytest ai_written_scripts/commit-staged-topics
"""

import argparse
import shlex
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

BRANCH: Final = "master"
REMOTE: Final = "origin"
EXCLUDE_STRAY_LOG: Final = ":(exclude)roles/devbox/files/.config/nvim/nvim.log"


@dataclass(frozen=True)
class Topic:
    message: str
    pathspecs: tuple[str, ...]


TOPICS: Final[tuple[Topic, ...]] = (
    Topic(
        "Add the TLA+ toolchain with Neovim support",
        (
            "CLAUDE.md",
            "roles/devbox/tasks/darwin/install_tlaplus.yml",
            "roles/devbox/tasks/darwin/install_tlaplus_tool.yml",
            "roles/devbox/tasks/main_darwin.yml",
            "roles/devbox/defaults/main/packages.yml",
            "roles/devbox/defaults/main/shell.yml",
            "roles/devbox/files/.config/nvim",
            EXCLUDE_STRAY_LOG,
        ),
    ),
    Topic(
        "Calibrate when agents and engine adapters ask the user questions",
        (
            "docs/design/ai-config-question-calibration.md",
            "roles/devbox/files/dot_ai/USER_AUTHORITY_PROTOCOL.md",
            "roles/devbox/files/dot_claude/CLAUDE_ADAPTER.md",
            "roles/devbox/files/dot_agy/GEMINI_ADAPTER.md",
            "roles/devbox/files/dot_codex/AGENTS.md",
            "roles/devbox/files/dot_ai/agents",
            "roles/devbox/files/dot_codex/agents",
            "roles/devbox/files/dot_ai/commands/techne-plan.md",
            "roles/devbox/files/dot_ai/skills/agent-base-protocol",
            "roles/devbox/files/dot_ai/skills/agent-communication",
            "roles/devbox/files/dot_ai/skills/code-writing-protocols",
            "roles/devbox/files/dot_ai/skills/go-review-checklist",
            "roles/devbox/files/dot_ai/skills/response-templates",
            "roles/devbox/files/dot_ai/skills/workflow",
        ),
    ),
    Topic(
        "Refresh the FPF Library bundle into the DPFs layout and route fpf-thinking"
        " through Core entries and domain frameworks",
        (".", EXCLUDE_STRAY_LOG),
    ),
)


class GitError(Exception):
    def __init__(self, args: Sequence[str], stderr: str) -> None:
        self.command = shlex.join(["git", *args])
        self.stderr = stderr.strip()
        super().__init__(self.command)


@dataclass(frozen=True)
class Git:
    root: Path

    @classmethod
    def discover(cls, cwd: Path) -> "Git":
        return cls(Path(Git(cwd).run("rev-parse", "--show-toplevel").strip()))

    def run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise GitError(args, result.stderr or result.stdout)
        return result.stdout

    def paths(self, subcommand: str, *args: str) -> list[str]:
        return [path for path in self.run(subcommand, "-z", *args).split("\0") if path]

    def has_diff(self, *args: str) -> bool:
        result = subprocess.run(
            ["git", "diff", "--quiet", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode not in {0, 1}:
            raise GitError(["diff", "--quiet", *args], result.stderr)
        return result.returncode == 1


@dataclass(frozen=True)
class PlannedCommit:
    topic: Topic
    files: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    commits: tuple[PlannedCommit, ...]
    staged: frozenset[str]
    left_out: tuple[str, ...]


@dataclass
class Progress:
    reset_done: bool = False
    pushed: bool = False
    created: list[str] = field(default_factory=list)


def assign_files(matches_per_topic: Sequence[Sequence[str]]) -> list[tuple[str, ...]]:
    """Give each path to the first topic that matches it, as sequential `git add` runs do."""
    claimed: set[str] = set()
    assigned: list[tuple[str, ...]] = []
    for matches in matches_per_topic:
        own = tuple(sorted(set(matches) - claimed))
        claimed.update(own)
        assigned.append(own)
    return assigned


def matching_changes(git: Git, pathspecs: Sequence[str]) -> list[str]:
    tracked = git.paths("diff", "HEAD", "--name-only", "--no-renames", "--", *pathspecs)
    untracked = git.paths("ls-files", "--others", "--exclude-standard", "--", *pathspecs)
    return [*tracked, *untracked]


def build_plan(git: Git, topics: Sequence[Topic]) -> Plan:
    staged = frozenset(git.paths("diff", "--cached", "--name-only", "--no-renames"))
    assigned = assign_files([matching_changes(git, topic.pathspecs) for topic in topics])
    commits = tuple(
        PlannedCommit(topic, files) for topic, files in zip(topics, assigned, strict=True)
    )
    covered = {path for commit in commits for path in commit.files}
    return Plan(commits, staged, tuple(sorted(staged - covered)))


def preconditions(git: Git) -> list[str]:
    problems: list[str] = []
    branch = git.run("rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch != BRANCH:
        problems.append(f"current branch is {branch!r}, expected {BRANCH!r}")
    if not git.has_diff("--cached"):
        problems.append("nothing is staged")
    unstaged = git.paths("diff", "--name-only")
    if unstaged:
        problems.append(
            "tracked files have unstaged changes, which this script would commit "
            "unreviewed: " + ", ".join(unstaged)
        )
    return problems


def print_plan(plan: Plan) -> None:
    total = len(plan.commits)
    for index, commit in enumerate(plan.commits, start=1):
        print(f"[{index}/{total}] {commit.topic.message!r}: {len(commit.files)} path(s)")
        for path in commit.files:
            marker = "" if path in plan.staged else "  (not staged now; included by git add -A)"
            print(f"    {path}{marker}")
    if plan.left_out:
        print(f"left out of every commit (stays uncommitted): {', '.join(plan.left_out)}")


def execute(git: Git, topics: Sequence[Topic], *, push: bool, progress: Progress) -> None:
    print("unstaging everything: git reset -q")
    git.run("reset", "-q")
    progress.reset_done = True

    total = len(topics)
    for index, topic in enumerate(topics, start=1):
        # git add fails outright on a pathspec that matches no file at all.
        if matching_changes(git, topic.pathspecs):
            git.run("add", "-A", "--", *topic.pathspecs)
        if not git.has_diff("--cached"):
            print(f"[{index}/{total}] skipped {topic.message!r}: nothing to commit")
            continue
        print(f"[{index}/{total}] committing {topic.message!r}")
        git.run("commit", "-m", topic.message)
        sha = git.run("rev-parse", "--short", "HEAD").strip()
        progress.created.append(f"{sha} {topic.message}")

    if push:
        print(f"pushing {BRANCH} to {REMOTE}")
        git.run("push", REMOTE, BRANCH)
        progress.pushed = True


def verify(git: Git, topics: Sequence[Topic], *, pushed: bool) -> list[str]:
    failures: list[str] = []
    for topic in topics:
        remaining = matching_changes(git, topic.pathspecs)
        if remaining:
            failures.append(f"{topic.message!r} still has uncommitted paths: {remaining}")
    if pushed:
        local = git.run("rev-parse", BRANCH).strip()
        remote = git.run("rev-parse", f"{REMOTE}/{BRANCH}").strip()
        if local != remote:
            failures.append(f"{REMOTE}/{BRANCH} is at {remote}, local {BRANCH} at {local}")
    return failures


def report_failure(git: Git, error: GitError, progress: Progress) -> None:
    print(f"FAILED: {error.command}", file=sys.stderr)
    if error.stderr:
        print(error.stderr, file=sys.stderr)
    if not progress.reset_done:
        print("Nothing was changed.", file=sys.stderr)
        return
    try:
        git.run("reset", "-q")
    except GitError as reset_error:
        print(f"could not unstage afterwards: {reset_error.stderr}", file=sys.stderr)
    for line in progress.created:
        print(f"committed before the failure: {line}", file=sys.stderr)
    if not progress.pushed:
        print("Nothing was pushed.", file=sys.stderr)
    print(
        "Nothing is lost: every change not yet committed is left unstaged in the working tree;"
        " inspect it with `git status`.",
        file=sys.stderr,
    )


def main(argv: Sequence[str] | None = None, topics: Sequence[Topic] = TOPICS) -> int:
    parser = argparse.ArgumentParser(description="Split staged changes into topic commits.")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    parser.add_argument("--no-push", action="store_true", help="commit but do not push")
    args = parser.parse_args(argv)

    progress = Progress()
    git = Git(Path.cwd())
    try:
        git = Git.discover(Path.cwd())
        problems = preconditions(git)
        if problems:
            for problem in problems:
                print(f"refusing: {problem}", file=sys.stderr)
            return 1

        plan = build_plan(git, topics)
        print_plan(plan)
        if args.dry_run:
            print("dry run: nothing changed")
            return 0

        execute(git, topics, push=not args.no_push, progress=progress)
        failures = verify(git, topics, pushed=progress.pushed)
    except GitError as error:
        report_failure(git, error, progress)
        return 1

    if failures:
        for failure in failures:
            print(f"VERIFY FAILED: {failure}", file=sys.stderr)
        return 1
    pushed_note = f", pushed to {REMOTE}/{BRANCH}" if progress.pushed else ", not pushed"
    print(f"VERIFY OK: {len(progress.created)} commit(s) created{pushed_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
