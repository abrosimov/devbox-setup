#!/usr/bin/env python3
"""pre_bash_safety_gate — PreToolUse hook that blocks dangerous Bash commands.

Reads the literal command from $CC_BASH_COMMAND. Exits 2 with a
``BLOCKED [rule-name]: <reason>`` message on stderr when a rule matches,
0 otherwise. Replaces the inline ``case`` blockers previously inlined in
hooks.json with a single rule table.

Stdlib only — no external dependencies.
"""

from __future__ import annotations

import fnmatch
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# --- allow-lists and recognised tokens --------------------------------------

# Path basename components that mark an ``rm -rf`` target as safe.
SAFE_RM_BASENAMES: frozenset = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        ".next",
        ".cache",
        ".pytest_cache",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".parcel-cache",
        "coverage",
        "htmlcov",
        ".turbo",
        ".vite",
    }
)

# Lint/type suppression directives that should never be written via Bash.
LINT_SUPPRESSION_TOKENS: tuple[str, ...] = (
    "noqa",
    "nolint",
    "ts-ignore",
    "ts-expect-error",
    "eslint-disable",
    "type: ignore",
    "type:ignore",
    "SuppressWarnings",
)

# Bash builtins/commands that write to files (substring-matched against the
# raw command, preserving the legacy hook's behaviour).
FILE_WRITER_TOKENS: tuple[str, ...] = (
    "sed",
    "echo",
    "printf",
    "cat",
    "tee",
    "perl",
    "python",
    "ruby",
    "awk",
)

# SQL CLI tools whose ``-c`` / ``-e`` flags execute literal SQL.
SQL_TOOL_NAMES: frozenset = frozenset(
    {
        "psql",
        "mysql",
        "mariadb",
        "sqlite3",
        "cockroach",
    }
)
SQL_EXEC_FLAGS: frozenset = frozenset(
    {
        "-c",
        "-e",
        "--command",
        "--execute",
    }
)
SQL_DESTRUCTIVE_RE = re.compile(
    r"\b(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE(\s+TABLE)?)\b",
    re.IGNORECASE,
)


# --- types ------------------------------------------------------------------


@dataclass(frozen=True)
class Ctx:
    """Per-invocation context passed to every rule."""

    cmd: str  # raw command as received from $CC_BASH_COMMAND
    argv: list[str]  # shlex-tokenised argv (empty if cmd is unparseable)


@dataclass(frozen=True)
class Decision:
    blocked: bool
    rule_name: str | None = None
    message: str | None = None


ALLOW = Decision(blocked=False)
RuleFn = Callable[[Ctx], str | None]


# --- helpers ----------------------------------------------------------------


def _tool(argv: list[str]) -> str:
    return os.path.basename(argv[0]) if argv else ""


def _current_branch() -> str:
    try:
        out = subprocess.check_output(
            ["git", "branch", "--show-current"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def _project_root_from_cwd() -> Path | None:
    """Walk up from cwd looking for a .git directory; return the project root.

    Returns None if cwd is outside any git checkout.
    """
    try:
        cwd = Path.cwd().resolve()
    except (OSError, RuntimeError):
        return None
    for ancestor in (cwd, *cwd.parents):
        if (ancestor / ".git").is_dir():
            return ancestor
    return None


def _is_within_project_tmp(path: str) -> bool:
    """True if path resolves under <project-root>/tmp/.

    Uses realpath() to resolve symlinks — prevents escape via a tmp/foo symlink
    that points outside the project. Returns False if cwd is not in a git checkout.

    Relative paths are anchored to <project-root>, not the current working
    directory. At runtime the two coincide (Claude Code launches commands from
    the project root); anchoring to project_root makes the logic robust under
    tests where cwd is patched at the Path.cwd() level only.
    """
    project_root = _project_root_from_cwd()
    if project_root is None:
        return False
    try:
        p = Path(path)
        if not p.is_absolute():
            p = project_root / p
        abs_path = p.resolve(strict=False)
        safe_root = (project_root / "tmp").resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    if abs_path == safe_root:
        # rm -rf tmp itself is not intended — only contents.
        return False
    try:
        abs_path.relative_to(safe_root)
        return True
    except ValueError:
        return False


def _is_safe_rm_path(path: str) -> bool:
    # Literal env-var references — agents often emit these unexpanded.
    if path.startswith(("$TMPDIR", "${TMPDIR}", "$TMP", "${TMP}")):
        return True
    # /tmp prefix.
    if path.startswith("/tmp/") or path.rstrip("/") == "/tmp":
        return True
    # Resolved $TMPDIR (macOS sets this to /var/folders/...).
    tmpdir = os.environ.get("TMPDIR", "")
    if tmpdir:
        try:
            abs_path = os.path.abspath(path)
            abs_tmp = os.path.abspath(tmpdir).rstrip("/")
            if abs_path == abs_tmp or abs_path.startswith(abs_tmp + "/"):
                return True
        except (ValueError, OSError):
            pass
    # Project-local tmp/ — realpath-validated, symlink-safe.
    if _is_within_project_tmp(path):
        return True
    # Any directory component matches a known safe basename.
    parts = path.replace("\\", "/").strip("/").split("/")
    return any(p in SAFE_RM_BASENAMES for p in parts)


def _protected_branches() -> frozenset[str]:
    """Set of protected branch patterns (supports fnmatch wildcards).

    Reads CC_PROTECTED_BRANCHES (comma-separated). Defaults to {"main", "master"}.
    Empty / whitespace-only entries are ignored. Parsed on every call — cheap, and
    avoids a mutable module-level cache.
    """
    raw = os.environ.get("CC_PROTECTED_BRANCHES", "main,master")
    return frozenset(b.strip() for b in raw.split(",") if b.strip())


def _refspec_target(refspec: str) -> str:
    """Normalised remote-side of a git refspec.

    Returns the right-hand side after ":" (or the whole refspec if no ":"),
    with a leading "+" (force marker) and any "refs/heads/" or
    "refs/remotes/<remote>/" prefix stripped. Used to compare push targets
    against a protected-branch list.
    """
    target = refspec.split(":", 1)[1] if ":" in refspec else refspec
    target = target.removeprefix("+")
    if target.startswith("refs/heads/"):
        return target[len("refs/heads/") :]
    if target.startswith("refs/remotes/"):
        parts = target.split("/", 3)
        if len(parts) == 4:
            return parts[3]
    return target


def _matches_protected(branch: str, patterns: frozenset[str]) -> bool:
    if not branch:
        return False
    return any(fnmatch.fnmatchcase(branch, p) for p in patterns)


def _push_positionals(argv: list[str]) -> list[str]:
    """Positional arguments to ``git push`` (all argv entries past ``push`` that
    do not start with ``-``). Used to extract remote + refspec(s)."""
    return [a for a in argv[2:] if not a.startswith("-")]


# --- rule implementations ---------------------------------------------------


def rule_heredoc(ctx: Ctx) -> str | None:
    if "<<" in ctx.cmd:
        return (
            "Use the Write tool to create files or Edit to modify them. "
            "Do not use Bash heredocs (<<). Write/Edit are auto-approved in "
            "acceptEdits mode and produce cleaner diffs."
        )
    return None


def rule_commit_on_main(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) == "git" and len(ctx.argv) >= 2 and ctx.argv[1] == "commit":
        if _current_branch() in {"main", "master"}:
            return "Cannot commit on the main/master branch. Create a feature branch first."
    return None


def rule_merge_on_main(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) == "git" and len(ctx.argv) >= 2 and ctx.argv[1] == "merge":
        if _current_branch() in {"main", "master"}:
            return "Cannot merge into the main/master branch. Use a feature branch instead."
    return None


def rule_force_push(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "git" or len(ctx.argv) < 2 or ctx.argv[1] != "push":
        return None
    msg = "Force push is not allowed. Push normally or ask the user."
    for arg in ctx.argv[2:]:
        if arg == "-f":
            return msg
        if arg == "--force" or arg.startswith("--force="):
            return msg
        # --force-with-lease is the safer variant and is intentionally allowed.
        if arg.startswith("--"):
            continue
        # Refspec with '+' prefix (e.g. "+feature", "+local:main") or with
        # ":+" (e.g. "local:+main") is force-semantic at the git layer.
        if arg.startswith("+") or ":+" in arg:
            return msg
    return None


def rule_push_mirror_all(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "git" or len(ctx.argv) < 2 or ctx.argv[1] != "push":
        return None
    for arg in ctx.argv[2:]:
        if arg in {"--mirror", "--all"}:
            return (
                "git push --mirror/--all is not allowed (pushes all refs). "
                "Push specific branches instead."
            )
    return None


def rule_push_delete_branch(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "git" or len(ctx.argv) < 2 or ctx.argv[1] != "push":
        return None
    msg = (
        "Branch deletion via git push is not allowed. Ask the user before deleting remote branches."
    )
    for arg in ctx.argv[2:]:
        if arg == "--delete":
            return msg
        # Refspec ":<branch>" with empty source side = delete remote ref.
        if arg.startswith(":") and len(arg) > 1:
            return msg
    return None


def rule_push_to_protected(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "git" or len(ctx.argv) < 2 or ctx.argv[1] != "push":
        return None
    positionals = _push_positionals(ctx.argv)
    # Bare `git push` or `git push <remote>` (no refspec) — current branch is
    # the implicit target. rule_commit_on_main already prevents new commits on
    # main/master, so an upstream push from those branches is a no-op.
    if len(positionals) < 2:
        return None
    refspecs = positionals[1:]
    protected = _protected_branches()
    for refspec in refspecs:
        target = _refspec_target(refspec)
        if _matches_protected(target, protected):
            return (
                f"Cannot push to protected branch '{target}'. "
                "Use a feature branch and open a PR/MR."
            )
    return None


def rule_amend(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) == "git" and len(ctx.argv) >= 2 and ctx.argv[1] == "commit":
        if "--amend" in ctx.argv:
            return "Amending commits is not allowed. Create a new commit instead."
    return None


def rule_no_verify(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) == "git" and len(ctx.argv) >= 2 and ctx.argv[1] == "commit":
        if "--no-verify" in ctx.argv:
            return (
                "--no-verify is not allowed. Fix the pre-commit hook issues "
                "instead of bypassing them."
            )
    return None


def rule_lint_suppression_via_bash(ctx: Ctx) -> str | None:
    if not any(t in ctx.cmd for t in LINT_SUPPRESSION_TOKENS):
        return None
    if any(t in ctx.cmd for t in FILE_WRITER_TOKENS):
        return (
            "Detected Bash command that writes lint suppression directives "
            "to files. Use the Edit tool instead, and fix the underlying "
            "issue rather than suppressing it."
        )
    return None


def rule_rm_rf(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "rm":
        return None
    has_recursive = False
    has_force = False
    paths: list[str] = []
    for arg in ctx.argv[1:]:
        if arg == "--":
            continue
        if arg == "--recursive":
            has_recursive = True
        elif arg == "--force":
            has_force = True
        elif arg.startswith("-") and not arg.startswith("--"):
            if "r" in arg or "R" in arg:
                has_recursive = True
            if "f" in arg:
                has_force = True
        else:
            paths.append(arg)
    if not (has_recursive and has_force) or not paths:
        return None
    unsafe = [p for p in paths if not _is_safe_rm_path(p)]
    if unsafe:
        return (
            f"rm -rf outside known-safe paths is not allowed. "
            f"Unsafe targets: {' '.join(unsafe)}. "
            "State the path and ask the user before proceeding."
        )
    return None


def rule_git_reset_hard(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) == "git" and len(ctx.argv) >= 2 and ctx.argv[1] == "reset":
        if "--hard" in ctx.argv:
            return "git reset --hard destroys uncommitted work. Ask the user before running."
    return None


def rule_git_clean(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "git" or len(ctx.argv) < 2 or ctx.argv[1] != "clean":
        return None
    for arg in ctx.argv[2:]:
        if arg == "--force":
            return "git clean --force destroys untracked work. Ask the user before running."
        if arg.startswith("-") and not arg.startswith("--") and "f" in arg:
            return "git clean -f destroys untracked work. Ask the user before running."
    return None


def rule_wholesale_checkout_restore(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "git" or len(ctx.argv) < 2:
        return None
    if ctx.argv[1] == "checkout" and len(ctx.argv) >= 3 and ctx.argv[-1] == ".":
        return (
            "Wholesale `git checkout .` discards local edits. Restore named files or ask the user."
        )
    if ctx.argv[1] == "restore" and len(ctx.argv) >= 3 and ctx.argv[-1] == ".":
        return "Wholesale `git restore` discards local edits. Restore named files or ask the user."
    return None


def rule_branch_force_delete(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) == "git" and len(ctx.argv) >= 3 and ctx.argv[1] == "branch":
        if "-D" in ctx.argv:
            return "git branch -D force-deletes unmerged branches. Use -d, or ask the user."
    return None


def rule_destructive_sql(ctx: Ctx) -> str | None:
    tool = _tool(ctx.argv)
    if tool not in SQL_TOOL_NAMES:
        return None
    for i, arg in enumerate(ctx.argv[1:], start=1):
        sql_payload: str | None = None
        if arg in SQL_EXEC_FLAGS and i + 1 < len(ctx.argv):
            sql_payload = ctx.argv[i + 1]
        elif arg.startswith("--command=") or arg.startswith("--execute="):
            sql_payload = arg.split("=", 1)[1]
        if sql_payload and SQL_DESTRUCTIVE_RE.search(sql_payload):
            return f"Destructive SQL detected in {tool}. Confirm with the user before running."
    return None


# --- rule table -------------------------------------------------------------

RULES: list[tuple[str, RuleFn]] = [
    ("heredoc", rule_heredoc),
    ("commit-on-main", rule_commit_on_main),
    ("merge-on-main", rule_merge_on_main),
    ("force-push", rule_force_push),
    ("push-mirror-all", rule_push_mirror_all),
    ("push-delete-branch", rule_push_delete_branch),
    ("push-to-protected", rule_push_to_protected),
    ("amend", rule_amend),
    ("no-verify", rule_no_verify),
    ("lint-suppression-via-bash", rule_lint_suppression_via_bash),
    ("rm-rf", rule_rm_rf),
    ("git-reset-hard", rule_git_reset_hard),
    ("git-clean", rule_git_clean),
    ("wholesale-checkout-restore", rule_wholesale_checkout_restore),
    ("branch-force-delete", rule_branch_force_delete),
    ("destructive-sql", rule_destructive_sql),
]


# --- entry points -----------------------------------------------------------


def evaluate(cmd: str) -> Decision:
    """Evaluate ``cmd`` against the rule table. First match wins."""
    try:
        argv = shlex.split(cmd, comments=False, posix=True)
    except ValueError:
        argv = []  # unparseable — only raw-string rules can still fire
    ctx = Ctx(cmd=cmd, argv=argv)
    for name, rule in RULES:
        msg = rule(ctx)
        if msg:
            return Decision(blocked=True, rule_name=name, message=msg)
    return ALLOW


def main() -> int:
    cmd = os.environ.get("CC_BASH_COMMAND", "")
    if not cmd:
        return 0
    decision = evaluate(cmd)
    if decision.blocked:
        sys.stderr.write(f"BLOCKED [{decision.rule_name}]: {decision.message}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
