#!/usr/bin/env python3
# Denies shell commands that create or name a Git branch containing "/" (feat/x, fix/y).
# Branch names are flat: `PROJ-123_short_description` or `short_description`.
# Imported as a rule by bash_decision_gate.py (Claude, Antigravity) and registered as a
# PreToolUse hook on its own for Codex. Shipped byte-identical to ~/.codex/bin and the
# Antigravity bin (Codex hooks must be self-contained): stdlib only.
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

BLOCK_EXIT: Final[int] = 2
SEPARATORS: Final[frozenset[str]] = frozenset({"&&", "||", "|", ";", "&", "(", ")", "\n"})
SHELLS: Final[frozenset[str]] = frozenset({"bash", "sh", "zsh", "fish", "dash", "ksh"})
GIT_GLOBAL_VALUE_OPTS: Final[frozenset[str]] = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"},
)
CHECKOUT_NEW_OPTS: Final[frozenset[str]] = frozenset({"-b", "-B", "--orphan"})
SWITCH_NEW_OPTS: Final[frozenset[str]] = frozenset(
    {"-c", "-C", "--create", "--force-create", "--orphan"},
)
WORKTREE_NEW_OPTS: Final[frozenset[str]] = frozenset({"-b", "-B"})
BRANCH_RENAME_OPTS: Final[frozenset[str]] = frozenset({"-m", "-M", "--move", "-c", "-C", "--copy"})
# Any of these makes `git branch` list, delete or edit rather than create.
BRANCH_NON_CREATE_OPTS: Final[frozenset[str]] = frozenset(
    {
        "-d", "-D", "--delete", "-l", "--list", "-a", "--all", "-r", "--remotes",
        "-v", "-vv", "--verbose", "--show-current", "--contains", "--no-contains",
        "--merged", "--no-merged", "--points-at", "-u", "--set-upstream-to",
        "--unset-upstream", "--edit-description",
    },
)  # fmt: skip
BRANCH_VALUE_OPTS: Final[frozenset[str]] = frozenset({"--sort", "--format", "--column"})


def _git_subcommand(argv: list[str]) -> tuple[str, list[str]] | None:
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in GIT_GLOBAL_VALUE_OPTS:
            i += 2
            continue
        if arg.startswith("-"):
            i += 1
            continue
        return arg, argv[i + 1 :]
    return None


def _option_value(args: list[str], names: frozenset[str]) -> Iterator[str]:
    for i, arg in enumerate(args):
        if arg in names and i + 1 < len(args):
            yield args[i + 1]
            continue
        name, sep, value = arg.partition("=")
        if sep and name in names and name.startswith("--"):
            yield value


def _branch_create_names(args: list[str]) -> Iterator[str]:
    if any(
        a in BRANCH_NON_CREATE_OPTS or a.split("=", 1)[0] in BRANCH_NON_CREATE_OPTS for a in args
    ):
        return
    positionals: list[str] = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in BRANCH_VALUE_OPTS:
            skip = True
            continue
        if not arg.startswith("-"):
            positionals.append(arg)
    if any(a in BRANCH_RENAME_OPTS for a in args):
        if positionals:
            yield positionals[-1]
        return
    if positionals:
        yield positionals[0]


def _push_destinations(args: list[str]) -> Iterator[str]:
    positionals = [a for a in args if not a.startswith("-")]
    for refspec in positionals[1:]:
        if ":" not in refspec:
            continue
        dst = refspec.split(":", 1)[1]
        if dst.startswith("refs/"):
            if not dst.startswith("refs/heads/"):
                continue
            dst = dst.removeprefix("refs/heads/")
        if dst:
            yield dst


def _git_branch_names(argv: list[str]) -> Iterator[str]:
    parsed = _git_subcommand(argv)
    if parsed is None:
        return
    sub, args = parsed
    if sub == "checkout":
        yield from _option_value(args, CHECKOUT_NEW_OPTS)
    elif sub == "switch":
        yield from _option_value(args, SWITCH_NEW_OPTS)
    elif sub == "branch":
        yield from _branch_create_names(args)
    elif sub == "worktree" and args[:1] == ["add"]:
        yield from _option_value(args[1:], WORKTREE_NEW_OPTS)
    elif sub == "push":
        yield from _push_destinations(args)


def _proj_branch_names(argv: list[str]) -> Iterator[str]:
    if len(argv) >= 4 and argv[1] == "wt" and argv[2] in {"add", "fork"}:
        yield argv[3]


def _segments(tokens: list[str]) -> Iterator[list[str]]:
    current: list[str] = []
    for token in tokens:
        if token in SEPARATORS or (token and set(token) <= set(";&|()\n")):
            if current:
                yield current
            current = []
            continue
        current.append(token)
    if current:
        yield current


def _strip_leaders(argv: list[str]) -> list[str]:
    i = 0
    while i < len(argv) and ("=" in argv[i] and not argv[i].startswith("-")):
        i += 1
    while i < len(argv) and argv[i] in {"env", "command", "exec", "nohup", "time", "sudo"}:
        i += 1
    return argv[i:]


def _shell_payload(argv: list[str]) -> str | None:
    for i, arg in enumerate(argv[1:], start=1):
        if arg.startswith("-") and not arg.startswith("--") and "c" in arg:
            return argv[i + 1] if i + 1 < len(argv) else None
    return None


def _segment_branch(argv: list[str], depth: int) -> str | None:
    tool = Path(argv[0]).name
    if tool in SHELLS:
        payload = _shell_payload(argv)
        return slashed_branch(payload, depth + 1) if payload and depth < 3 else None
    if tool == "git":
        names = _git_branch_names(argv)
    elif tool == "proj":
        names = _proj_branch_names(argv)
    else:
        return None
    return next((name for name in names if "/" in name), None)


def slashed_branch(cmd: str, depth: int = 0) -> str | None:
    """Return the first branch name with a "/" that ``cmd`` would create, else None."""
    lexer = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    for segment in _segments(tokens):
        argv = _strip_leaders(segment)
        found = _segment_branch(argv, depth) if argv else None
        if found:
            return found
    return None


def reason(name: str) -> str:
    flat = name.rsplit("/", 1)[-1]
    return (
        f"Branch name '{name}' contains '/'. Branch names must be flat: use "
        f"'{flat}' or 'PROJ-123_{flat}' (Jira key, underscore, snake_case description), "
        "never a 'feat/', 'fix/' or other slash prefix."
    )


def _command_from(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    cmd = tool_input.get("command") or tool_input.get("cmd") or ""
    if isinstance(cmd, list) and all(isinstance(part, str) for part in cmd):
        return shlex.join(cmd)
    return cmd if isinstance(cmd, str) else ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    found = slashed_branch(_command_from(payload))
    if found is None:
        return 0
    sys.stderr.write(f"BLOCKED [branch-name-slash]: {reason(found)}\n")
    return BLOCK_EXIT


if __name__ == "__main__":
    sys.exit(main())
