#!/usr/bin/env python3
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, proc

DEFAULT_INTEGRATION: Final[str] = "build/stable"


@dataclass(frozen=True)
class ParsedArgs:
    source: str
    target_override: str | None


@dataclass(frozen=True)
class ParseFailure:
    reason: str
    show_usage: bool = False


def usage(integration: str) -> str:
    return (
        "Usage: git_safe_merge.py <source-branch> [--into <target>]\n"
        f"  Default target: {integration}\n"
    )


def parse_args(argv: list[str]) -> ParsedArgs | ParseFailure:
    target: str | None = None
    source: str | None = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--into":
            if i + 1 >= len(argv):
                return ParseFailure("--into requires a branch name.")
            target = argv[i + 1]
            i += 2
            continue
        if arg.startswith("-"):
            return ParseFailure(
                f"Unknown flag '{arg}'. Usage: git_safe_merge.py <source> [--into <target>]",
            )
        if source is not None:
            return ParseFailure(
                f"Unexpected positional argument '{arg}'.",
            )
        source = arg
        i += 1
    if source is None:
        return ParseFailure("", show_usage=True)
    return ParsedArgs(source=source, target_override=target)


def integration_branch() -> str:
    result = proc.run_cmd(
        ["git", "config", "--get", "claude.integrationBranch"],
        timeout=5,
    )
    if not result.success:
        return DEFAULT_INTEGRATION
    candidate = result.stdout.strip()
    return candidate or DEFAULT_INTEGRATION


def branch_exists(name: str) -> bool:
    return proc.run_cmd(["git", "rev-parse", "--verify", name], timeout=5).success


def merge_base(source: str, target: str) -> str:
    result = proc.run_cmd(["git", "merge-base", source, target], timeout=10)
    if not result.success:
        return ""
    return result.stdout.strip()


def commits_ahead(target: str, source: str) -> int:
    result = proc.run_cmd(
        ["git", "rev-list", "--count", f"{target}..{source}"],
        timeout=10,
    )
    if not result.success:
        return 0
    try:
        return int(result.stdout.strip() or "0")
    except ValueError:
        return 0


def current_branch() -> str:
    result = proc.run_cmd(["git", "branch", "--show-current"], timeout=5)
    if not result.success:
        return ""
    return result.stdout.strip()


def has_uncommitted_changes() -> bool:
    if not proc.run_cmd(["git", "diff", "--quiet"], timeout=10).success:
        return True
    return not proc.run_cmd(["git", "diff", "--cached", "--quiet"], timeout=10).success


def stash_changes(label: str) -> bool:
    result = proc.run_cmd(["git", "stash", "push", "-m", label], timeout=15)
    return result.success


def stash_pop() -> None:
    proc.run_cmd(["git", "stash", "pop"], timeout=15)


def switch_branch(name: str) -> bool:
    return proc.run_cmd(["git", "switch", name], timeout=15).success


def merge_ff(source: str) -> proc.CmdResult:
    return proc.run_cmd(["git", "merge", "--ff-only", source], timeout=60)


def restore(original: str, *, stashed: bool) -> None:
    if original:
        proc.run_cmd(["git", "switch", original], timeout=15)
    if stashed:
        stash_pop()


def _validate_args(parsed: ParsedArgs | ParseFailure, integration: str) -> int | tuple[str, str]:
    if isinstance(parsed, ParseFailure):
        if parsed.show_usage:
            sys.stderr.write(usage(integration))
            return 1
        sys.stderr.write(f"BLOCKED: {parsed.reason}\n")
        return 1
    target = parsed.target_override or integration
    source = parsed.source
    if target in {"main", "master"}:
        sys.stderr.write(
            f"BLOCKED: Cannot merge into '{target}'.\n"
            f"Use the integration branch instead: "
            f"git_safe_merge.py {source} --into {integration}\n",
        )
        return 1
    return source, target


def _check_branches(source: str, target: str) -> int | None:
    if not branch_exists(source):
        sys.stderr.write(f"BLOCKED: Source branch '{source}' does not exist.\n")
        return 1
    if not branch_exists(target):
        sys.stderr.write(
            f"BLOCKED: Target branch '{target}' does not exist.\n"
            f"Create it first: git branch {target} main\n",
        )
        return 1
    return None


def _perform_merge(source: str, target: str) -> int:
    if not switch_branch(target):
        sys.stderr.write(f"BLOCKED: Could not switch to '{target}'.\n")
        return 1
    result = merge_ff(source)
    if not result.success:
        sys.stderr.write(
            f"FAILED: Fast-forward merge not possible. '{target}' has diverged from "
            f"'{source}'.\n\nOptions:\n"
            f"  1. Rebase source onto target:  git rebase {target} {source}\n"
            f"  2. Manual merge (creates merge commit):  git switch {target} && "
            f"git merge {source}\n",
        )
        return 1
    sys.stdout.write(f"Merged '{source}' into '{target}' (fast-forward).\n")
    return 0


def run(argv: list[str]) -> int:
    integration = integration_branch()
    validated = _validate_args(parse_args(argv), integration)
    if isinstance(validated, int):
        return validated
    source, target = validated

    branch_error = _check_branches(source, target)
    if branch_error is not None:
        return branch_error

    if merge_base(source, target) and commits_ahead(target, source) == 0:
        sys.stdout.write(f"Nothing to merge: '{source}' is already in '{target}'.\n")
        return 0

    original = current_branch()
    stashed = False
    if has_uncommitted_changes():
        sys.stdout.write("Stashing uncommitted changes...\n")
        if stash_changes(f"git-safe-merge: auto-stash before merging {source} into {target}"):
            stashed = True

    try:
        return _perform_merge(source, target)
    finally:
        restore(original, stashed=stashed)


def main(argv: list[str] | None = None) -> int:
    env.setup()
    return run(argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
