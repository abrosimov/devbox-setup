#!/usr/bin/env python3
"""bash_decision_gate — unified PreToolUse hook for Bash tool calls.

Replaces ``pre_bash_safety_gate.py`` (deny rules) and
``permission_auto_approve.py`` (allow signal) with a single hook driven
by bashlex AST analysis.

Three phases:

  Phase 1 — DENY rules (ported from safety_gate)
      First-match-wins table of categorical denials: rm-rf outside safe
      paths, force-push, push to protected branches, amend, --no-verify,
      reset --hard, clean -f, wholesale checkout/restore, destructive
      SQL, lint-suppression via bash writers, heredocs.

  Phase 2 — Structural ALLOW analysis (bashlex AST)
      For every CommandNode reachable in the tree (including those
      nested in command substitutions, process substitutions, and the
      argument of ``bash -c`` recursively parsed), five checks:
        (a) interpreter inline-exec (python -c, eval, ...) → deny
            with hint pointing at .claude/claude_written_scripts/
        (b) shell inline-exec (bash -c) → recursive bashlex.parse on
            the inner script; inner failures propagate
        (c) system-protected path (~/.ssh, /etc/shadow, *.pem) → deny
        (d) audit-dir protection — deleting/overwriting
            ./.claude/claude_written_scripts/** → deny
        (e) write-escape — known write commands targeting paths outside
            (effective_cwd, allowed_dirs, /tmp, $TMPDIR) → deny
        (f) redundant-cd — leading ``cd <path>`` whose resolved target is
            already effective_cwd → deny (Shell discipline)
      effective_cwd tracks ``cd <path> &&`` and ``git -C <path>`` shifts.

  Phase 3 — Positive allow signal
      Every command segment must match a Bash(…) pattern from
      ~/.claude/settings.json ``permissions.allow``. Built-ins (cd, true,
      test, ...) skip this check. If all segments match → allow; else
      → defer (Claude Code's matcher handles).

Telemetry: every non-allow outcome (deny / defer / parse failure) appends
a JSONL record to ~/.claude/state/missed_approvals/YYYY/MM/DD/HH.jsonl
(UTC sharded). Consumed by the techne-fewer-permission-prompts skill.
"""

from __future__ import annotations

import contextlib
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bashlex
import bashlex.errors
from _claude_lib import env, hooks

# ============================================================
# CONSTANTS — Phase 1 (ported from safety_gate)
# ============================================================

SAFE_RM_BASENAMES: Final[frozenset[str]] = frozenset(
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
    },
)

LINT_SUPPRESSION_TOKENS: Final[tuple[str, ...]] = (
    "noqa",
    "nolint",
    "ts-ignore",
    "ts-expect-error",
    "eslint-disable",
    "type: ignore",
    "type:ignore",
    "SuppressWarnings",
)

FILE_WRITER_TOKENS: Final[tuple[str, ...]] = (
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

SQL_TOOL_NAMES: Final[frozenset[str]] = frozenset(
    {"psql", "mysql", "mariadb", "sqlite3", "cockroach"},
)
SQL_EXEC_FLAGS: Final[frozenset[str]] = frozenset({"-c", "-e", "--command", "--execute"})
SQL_DESTRUCTIVE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE(\s+TABLE)?)\b",
    re.IGNORECASE,
)


# ============================================================
# CONSTANTS — Phase 2 (AST analysis)
# ============================================================

INTERP_INLINE_BIN: Final[frozenset[str]] = frozenset(
    {"python", "python3", "node", "ruby", "perl"},
)
INTERP_INLINE_FLAGS: Final[frozenset[str]] = frozenset({"-c", "-e", "-m"})
SHELL_INLINE_BIN: Final[frozenset[str]] = frozenset({"bash", "sh", "zsh", "fish"})
DOT_SOURCE: Final[frozenset[str]] = frozenset({"eval", "exec", "source", "."})

# Glob patterns matched against any positional argument literal.
# fnmatch — case-sensitive; sufficient for the conventional secret locations.
SECRET_GLOBS: Final[tuple[str, ...]] = (
    "~/.ssh",
    "~/.ssh/*",
    "~/.ssh/**",
    "~/.aws",
    "~/.aws/*",
    "~/.aws/**",
    "~/.gnupg",
    "~/.gnupg/*",
    "~/.gnupg/**",
    "~/.password-store",
    "~/.password-store/*",
    "~/.password-store/**",
    "~/.config/op",
    "~/.config/op/*",
    "~/.config/op/**",
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/sudoers.d/*",
    "/etc/master.passwd",
    "*.pem",
    "*.key",
    "**/*.pem",
    "**/*.key",
)

AUDIT_DIR_REL: Final[str] = ".claude/claude_written_scripts"

# Commands whose argv targets are paths and which mutate the filesystem.
# Conservative: known writes only; unknown commands skip (e) and fall through
# to the positive-allow phase.
WRITE_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "rm",
        "rmdir",
        "unlink",
        "shred",
        "mv",
        "cp",
        "install",
        "mkdir",
        "touch",
        "chmod",
        "chown",
        "chgrp",
        "chflags",
        "ln",
        "link",
        "tee",
        "patch",
        "dd",
        "rsync",
    },
)

# Commands whose write behaviour depends on flags — special-cased.
AMBIGUOUS_COMMANDS: Final[frozenset[str]] = frozenset(
    {"sed", "awk", "find", "tar", "unzip", "gzip", "git"},
)

GIT_WRITE_SUBCMDS: Final[frozenset[str]] = frozenset(
    {
        "add",
        "commit",
        "rm",
        "mv",
        "checkout",
        "switch",
        "restore",
        "stash",
        "push",
        "pull",
        "fetch",
        "merge",
        "rebase",
        "reset",
        "revert",
        "cherry-pick",
        "apply",
        "am",
        "clean",
        "gc",
        "prune",
        "init",
        "clone",
        "tag",
    },
)

# Shell built-ins / pure-syntactic / always-safe — skip positive-allow check.
BUILTIN_SAFE: Final[frozenset[str]] = frozenset(
    {"cd", "true", "false", "test", "[", ":", "pwd", "echo", "printf"},
)

# Redirect target whitelist — always-writable destinations.
ALWAYS_WRITABLE_PREFIXES: Final[tuple[str, ...]] = (
    "/dev/null",
    "/dev/stderr",
    "/dev/stdout",
)


# ============================================================
# TYPES
# ============================================================


@dataclass(frozen=True)
class Decision:
    behavior: Literal["allow", "deny", "ask", "defer"]
    reason: str | None = None
    rule: str | None = None


ALLOW_DECISION: Final[Decision] = Decision("allow")
DEFER_DECISION: Final[Decision] = Decision("defer")


@dataclass(frozen=True)
class _Phase1LegacyDecision:
    """Legacy Decision shape (pre-unification) — kept so the ported
    ``test_pre_bash_safety_gate.py`` suite continues to compile against the
    same helpers. Production code uses :class:`Decision` instead.
    """

    blocked: bool
    rule_name: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class Ctx:
    cmd: str
    argv: list[str]


# ============================================================
# Phase 1 helpers (ported verbatim from safety_gate)
# ============================================================


def _tool(argv: list[str]) -> str:
    return Path(argv[0]).name if argv else ""


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
    try:
        cwd = Path.cwd().resolve()
    except (OSError, RuntimeError):
        return None
    for ancestor in (cwd, *cwd.parents):
        if (ancestor / ".git").is_dir():
            return ancestor
    return None


def _is_within_project_tmp(path: str) -> bool:
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
        return False
    try:
        abs_path.relative_to(safe_root)
    except ValueError:
        return False
    return True


def _is_safe_rm_path(path: str) -> bool:
    if path.startswith(("$TMPDIR", "${TMPDIR}", "$TMP", "${TMP}")):
        return True
    if path.startswith("/tmp/") or path.rstrip("/") == "/tmp":  # noqa: S108
        return True
    tmpdir = os.environ.get("TMPDIR", "")
    if tmpdir:
        try:
            abs_path = str(Path(path).absolute())
            abs_tmp = str(Path(tmpdir).absolute()).rstrip("/")
            if abs_path == abs_tmp or abs_path.startswith(abs_tmp + "/"):
                return True
        except (ValueError, OSError):
            pass
    if _is_within_project_tmp(path):
        return True
    parts = path.replace("\\", "/").strip("/").split("/")
    return any(p in SAFE_RM_BASENAMES for p in parts)


def _protected_branches() -> frozenset[str]:
    raw = os.environ.get("CC_PROTECTED_BRANCHES", "main,master")
    return frozenset(b.strip() for b in raw.split(",") if b.strip())


def _refspec_target(refspec: str) -> str:
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
    return [a for a in argv[2:] if not a.startswith("-")]


def _parse_rm_args(argv: list[str]) -> tuple[bool, bool, list[str]]:
    has_recursive = False
    has_force = False
    paths: list[str] = []
    for arg in argv:
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
    return has_recursive, has_force, paths


# ============================================================
# Phase 1 rules
# ============================================================


def rule_heredoc(ctx: Ctx) -> str | None:
    if "<<" in ctx.cmd:
        return (
            "Use the Write tool to create files or Edit to modify them. "
            "Do not use Bash heredocs (<<). Write/Edit are auto-approved in "
            "acceptEdits mode and produce cleaner diffs."
        )
    return None


def rule_commit_on_main(ctx: Ctx) -> str | None:
    if (
        _tool(ctx.argv) == "git"
        and len(ctx.argv) >= 2
        and ctx.argv[1] == "commit"
        and _current_branch() in {"main", "master"}
    ):
        return "Cannot commit on the main/master branch. Create a feature branch first."
    return None


def rule_merge_on_main(ctx: Ctx) -> str | None:
    if (
        _tool(ctx.argv) == "git"
        and len(ctx.argv) >= 2
        and ctx.argv[1] == "merge"
        and _current_branch() in {"main", "master"}
    ):
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
        if arg.startswith("--"):
            continue
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
        if arg.startswith(":") and len(arg) > 1:
            return msg
    return None


def rule_push_to_protected(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "git" or len(ctx.argv) < 2 or ctx.argv[1] != "push":
        return None
    positionals = _push_positionals(ctx.argv)
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
    if (
        _tool(ctx.argv) == "git"
        and len(ctx.argv) >= 2
        and ctx.argv[1] == "commit"
        and "--amend" in ctx.argv
    ):
        return "Amending commits is not allowed. Create a new commit instead."
    return None


def rule_no_verify(ctx: Ctx) -> str | None:
    if (
        _tool(ctx.argv) == "git"
        and len(ctx.argv) >= 2
        and ctx.argv[1] == "commit"
        and "--no-verify" in ctx.argv
    ):
        return "--no-verify is not allowed. Fix pre-commit hook issues instead of bypassing."
    return None


def rule_lint_suppression_via_bash(ctx: Ctx) -> str | None:
    if not any(t in ctx.cmd for t in LINT_SUPPRESSION_TOKENS):
        return None
    if any(t in ctx.cmd for t in FILE_WRITER_TOKENS):
        return (
            "Detected Bash command that writes lint suppression directives to files. "
            "Use the Edit tool instead, and fix the underlying issue rather than suppressing it."
        )
    return None


def rule_rm_rf(ctx: Ctx) -> str | None:
    if _tool(ctx.argv) != "rm":
        return None
    has_recursive, has_force, paths = _parse_rm_args(ctx.argv[1:])
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
    if (
        _tool(ctx.argv) == "git"
        and len(ctx.argv) >= 2
        and ctx.argv[1] == "reset"
        and "--hard" in ctx.argv
    ):
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
        return (
            "Wholesale `git restore .` discards local edits. Restore named files or ask the user."
        )
    return None


def rule_branch_force_delete(ctx: Ctx) -> str | None:
    if (
        _tool(ctx.argv) == "git"
        and len(ctx.argv) >= 3
        and ctx.argv[1] == "branch"
        and "-D" in ctx.argv
    ):
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
        elif arg.startswith(("--command=", "--execute=")):
            sql_payload = arg.split("=", 1)[1]
        if sql_payload and SQL_DESTRUCTIVE_RE.search(sql_payload):
            return f"Destructive SQL detected in {tool}. Confirm with the user before running."
    return None


RuleFn = Callable[[Ctx], str | None]

PHASE1_RULES: Final[list[tuple[str, RuleFn]]] = [
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


def phase1_check(cmd: str) -> Decision:
    try:
        argv = shlex.split(cmd, comments=False, posix=True)
    except ValueError:
        argv = []
    ctx = Ctx(cmd=cmd, argv=argv)
    for name, rule in PHASE1_RULES:
        msg = rule(ctx)
        if msg:
            return Decision(
                behavior="deny",
                reason=f"BLOCKED [{name}]: {msg}",
                rule=name,
            )
    return DEFER_DECISION


def evaluate_phase1_legacy(cmd: str) -> _Phase1LegacyDecision:
    """Phase-1-only evaluation in the pre-unification Decision shape.

    Exists so the ~110 existing safety_gate rule tests still run unchanged
    against the new module — they only need an import-site swap. New code
    should call :func:`phase1_check` or the top-level :func:`evaluate`.
    """
    d = phase1_check(cmd)
    if d.behavior == "deny":
        msg = d.reason or ""
        prefix = f"BLOCKED [{d.rule}]: "
        msg = msg.removeprefix(prefix)
        return _Phase1LegacyDecision(blocked=True, rule_name=d.rule, message=msg)
    return _Phase1LegacyDecision(blocked=False)


# ============================================================
# Phase 2 — AST analysis
# ============================================================


_INTERP_DENY_REASON: Final[str] = (
    "Inline-exec via interpreter (-c/-e/-m) или eval/exec/source запрещён. "
    "Сохрани скрипт в ./.claude/claude_written_scripts/<name>.<ext> "
    "(директория является audit trail — удаление и перезапись запрещены) "
    "и запусти его по пути. Если скрипт нужен повторно, переиспользуй файл; "
    "иначе создай новый с уникальным именем."
)

_SECRET_DENY_REASON: Final[str] = (
    "Path '{path}' содержит секреты (~/.ssh, ~/.aws, ~/.gnupg, *.pem, *.key, "  # noqa: S105 -- deny-reason message template, not a credential
    "/etc/shadow, /etc/sudoers). Чтение и запись запрещены."
)

_AUDIT_DENY_REASON: Final[str] = (
    "Path '{path}' внутри ./.claude/claude_written_scripts/ — это audit trail "
    "запущенных скриптов. Удаление и перезапись запрещены."
)

_WRITE_ESCAPE_REASON: Final[str] = (
    "Write/delete target '{path}' за пределами workspace (effective_cwd={cwd}). "
    "Используй Edit-tool для файлов в workspace, добавь каталог через /add-dir, "
    "или cd в нужный каталог перед операцией."
)

_REDUNDANT_CD_REASON: Final[str] = (
    "Redundant `cd {path}` — the shell is already in that directory "
    "(effective_cwd={cwd}). Drop the `cd` prefix and run the command directly. "
    "To operate elsewhere use a path flag (`git -C <path>`, `make -C <path>`, "
    "`pytest --rootdir <path>`) or an absolute path; for sustained work in "
    "another directory add it to the session with `/add-dir <path>`."
)


def parse_safely(cmd: str) -> tuple[list[object] | None, str | None]:
    """Parse cmd with bashlex; return (trees, error_reason).

    On any parse failure (empty, comment, ParsingError, NotImplementedError,
    or unexpected None/str results from bashlex internals), returns
    (None, reason_str). Never raises.
    """
    try:
        trees = bashlex.parse(cmd)
    except bashlex.errors.ParsingError as e:
        return None, f"parse_error:{e}"
    except NotImplementedError as e:
        return None, f"not_implemented:{e}"
    except Exception as e:  # noqa: BLE001  # bashlex throws bare exceptions
        return None, f"unknown_error:{type(e).__name__}:{e}"
    if not trees:
        return None, "empty_parse"
    for t in trees:
        if not hasattr(t, "kind") or getattr(t, "kind", None) is None:
            return None, "invalid_parse_result"
    return trees, None


def _node_kind(node: object) -> str:
    return getattr(node, "kind", "") or ""


def _extract_argv(cmd_node: object) -> list[str]:
    """Words only — drop assignments and redirects."""
    return [
        p.word
        for p in getattr(cmd_node, "parts", [])
        if _node_kind(p) == "word" and hasattr(p, "word")
    ]


def _extract_redirects(cmd_node: object) -> list[object]:
    return [p for p in getattr(cmd_node, "parts", []) if _node_kind(p) == "redirect"]


def _nested_substitutions(word_node: object) -> Iterator[object]:
    """Yield commandsubstitution / processsubstitution nodes within a word."""
    for p in getattr(word_node, "parts", []) or []:
        if _node_kind(p) in {"commandsubstitution", "processsubstitution"}:
            yield p


def _resolve_cwd_shift(current: Path, target_str: str) -> Path:
    """Compute new effective_cwd after `cd <target_str>`."""
    if target_str.startswith("~"):
        target_str = str(Path(target_str).expanduser())
    p = Path(target_str)
    if p.is_absolute():
        return p
    return (current / p).resolve()


def walk_commands(
    node: object,
    eff_cwd: Path,
    depth: int = 0,
) -> Iterator[tuple[object, Path]]:
    """Yield every reachable CommandNode with its effective_cwd.

    Tracks:
    - leading ``cd <path> &&`` in a list — subsequent commands shift cwd
    - nested substitutions inside word parts — recurse via .command
    - subshells and brace groups (compound) — descend with current cwd
    - bashlex returns a forest; each tree handled independently

    Note: ``git -C <path>`` is not handled here — it's per-command and
    applied at use site (see _effective_cwd_for).
    """
    if depth > 8:
        return
    kind = _node_kind(node)

    if kind == "command":
        yield node, eff_cwd
        for part in getattr(node, "parts", []):
            for sub in _nested_substitutions(part):
                inner = getattr(sub, "command", None)
                if inner is not None:
                    yield from walk_commands(inner, eff_cwd, depth + 1)
        for r in _extract_redirects(node):
            output = getattr(r, "output", None)
            if output is not None and not isinstance(output, int):
                for sub in _nested_substitutions(output):
                    inner = getattr(sub, "command", None)
                    if inner is not None:
                        yield from walk_commands(inner, eff_cwd, depth + 1)
        return

    if kind == "pipeline":
        for p in getattr(node, "parts", []):
            if _node_kind(p) == "command":
                yield from walk_commands(p, eff_cwd, depth + 1)
        return

    if kind in {"list", "compound"}:
        current = eff_cwd
        cd_pending: str | None = None
        for p in getattr(node, "parts", []):
            pkind = _node_kind(p)
            if pkind == "command":
                argv = _extract_argv(p)
                if argv and argv[0] == "cd" and len(argv) >= 2:
                    cd_pending = argv[1]
                    yield p, current
                else:
                    yield p, current
                    for part in getattr(p, "parts", []):
                        for sub in _nested_substitutions(part):
                            inner = getattr(sub, "command", None)
                            if inner is not None:
                                yield from walk_commands(inner, current, depth + 1)
            elif pkind == "operator":
                op = getattr(p, "op", "")
                if op in {"&&", ";"} and cd_pending is not None:
                    current = _resolve_cwd_shift(current, cd_pending)
                cd_pending = None
            elif pkind in {"compound", "list"}:
                yield from walk_commands(p, current, depth + 1)


def _effective_cwd_for(argv: list[str], base: Path) -> Path:
    """Apply per-command cwd shifts: ``git -C <path>``."""
    if not argv or argv[0] != "git":
        return base
    for i, a in enumerate(argv[1:], start=1):
        if a == "-C" and i + 1 < len(argv):
            return _resolve_cwd_shift(base, argv[i + 1])
    return base


# ----- (a) interpreter inline-exec -----


def check_interp_inline_exec(argv: list[str]) -> Decision | None:
    if not argv:
        return None
    head = argv[0]
    if head in DOT_SOURCE:
        return Decision(behavior="deny", reason=_INTERP_DENY_REASON, rule="interp-dot-source")
    if head in INTERP_INLINE_BIN:
        for a in argv[1:]:
            if a in INTERP_INLINE_FLAGS:
                return Decision(
                    behavior="deny",
                    reason=_INTERP_DENY_REASON,
                    rule="interp-inline-exec",
                )
            if a.startswith(("--command", "--exec")):
                return Decision(
                    behavior="deny",
                    reason=_INTERP_DENY_REASON,
                    rule="interp-inline-exec",
                )
    return None


# ----- (b) shell inline-exec — recursive -----


def _shell_c_payload(argv: list[str]) -> str | None:
    """Return the argument to ``-c`` for bash/sh/zsh/fish, or None."""
    for i, a in enumerate(argv[1:], start=1):
        if a == "-c" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("-") and not a.startswith("--") and a.endswith("c") and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _xargs_inner_argv(argv: list[str]) -> list[str] | None:
    """For ``xargs <cmd> [args...]`` return [<cmd>, *args] for analysis."""
    if not argv or argv[0] != "xargs":
        return None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in {"-I", "-J", "-L", "-n", "-P", "-e", "-E", "-d", "-s"} and i + 1 < len(argv):
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return argv[i:]
    return None


def check_shell_inline_exec(
    argv: list[str],
    eff_cwd: Path,
    settings_allow: list[str],
    audit_root: Path,
    extra_writable: tuple[Path, ...],
    depth: int = 0,
) -> Decision | None:
    """Recurse into the script body of ``bash -c '...'`` (and equivalent).

    Returns deny propagated from inner; None to let outer continue.
    """
    if depth > 4:
        return Decision(
            behavior="deny",
            reason="Inline-exec nesting too deep.",
            rule="recursion-limit",
        )
    head = argv[0] if argv else ""
    inner_script: str | None = None
    if head in SHELL_INLINE_BIN:
        inner_script = _shell_c_payload(argv)
    elif head == "xargs":
        inner = _xargs_inner_argv(argv)
        if inner and inner[0] in SHELL_INLINE_BIN:
            inner_script = _shell_c_payload(inner)
        elif inner and inner[0] in INTERP_INLINE_BIN:
            # xargs into python/node/ruby with -c/-e/-m → deny
            d = check_interp_inline_exec(inner)
            if d:
                return d
    if inner_script is None:
        return None

    trees, err = parse_safely(inner_script)
    if trees is None:
        return Decision(
            behavior="deny",
            reason=(
                f"Inner shell script для `{head} -c` не парсится ({err}). "
                "Запиши скрипт в файл и запусти по пути."
            ),
            rule="shell-inline-unparseable",
        )
    for tree in trees:
        for cmd_node, cwd in walk_commands(tree, eff_cwd):
            inner_argv = _extract_argv(cmd_node)
            if not inner_argv:
                continue
            d = _analyze_segment(
                cmd_node,
                inner_argv,
                cwd,
                settings_allow,
                audit_root,
                extra_writable,
                depth + 1,
            )
            if d is not None and d.behavior == "deny":
                return d
    return None


# ----- (c) secret-path check -----


def _expand_user_arg(arg: str) -> str:
    if arg.startswith("~"):
        return str(Path(arg).expanduser())
    return arg


def check_secret_path(argv: list[str]) -> Decision | None:
    for arg in argv[1:]:
        if not arg or arg.startswith("-"):
            continue
        candidates = {arg, _expand_user_arg(arg)}
        for cand in candidates:
            for pattern in SECRET_GLOBS:
                expanded = str(Path(pattern).expanduser())
                if fnmatch.fnmatchcase(cand, pattern) or fnmatch.fnmatchcase(cand, expanded):
                    return Decision(
                        behavior="deny",
                        reason=_SECRET_DENY_REASON.format(path=arg),
                        rule="secret-path",
                    )
    return None


# ----- (d) audit-dir protection -----


def _resolve_arg_path(arg: str, eff_cwd: Path) -> Path:
    raw = _expand_user_arg(arg)
    p = Path(raw)
    if not p.is_absolute():
        p = eff_cwd / p
    try:
        return p.resolve(strict=False)
    except (OSError, RuntimeError):
        return p


def _within(path: Path, ancestor: Path) -> bool:
    try:
        path.relative_to(ancestor)
    except ValueError:
        return False
    else:
        return True


def check_audit_dir(
    cmd_node: object,
    argv: list[str],
    eff_cwd: Path,
    audit_root: Path,
) -> Decision | None:
    if not argv:
        return None
    head = argv[0]
    targets: list[str] = []

    if head in {"rm", "rmdir", "unlink", "shred", "mv"}:
        targets = [a for a in argv[1:] if not a.startswith("-")]
    elif head == "cp":
        positionals = [a for a in argv[1:] if not a.startswith("-")]
        targets = positionals
    elif head == "find":
        if any(f in argv[1:] for f in ("-delete", "-exec", "-execdir", "-ok")):
            i = 1
            while i < len(argv) and not argv[i].startswith("-"):
                targets.append(argv[i])
                i += 1
    elif head == "sed":
        if any(a in {"-i", "--in-place"} or a.startswith("-i") for a in argv[1:]):
            targets = [a for a in argv[1:] if not a.startswith("-")][1:]
    elif head == "git" and len(argv) >= 2 and argv[1] in {"rm", "mv"}:
        targets = [a for a in argv[2:] if not a.startswith("-")]
    elif head == "tee":
        targets = [a for a in argv[1:] if not a.startswith("-")]

    for r in _extract_redirects(cmd_node):
        rtype = getattr(r, "type", "")
        if rtype not in {">", ">>", "&>", ">|"}:
            continue
        output = getattr(r, "output", None)
        if output is None or isinstance(output, int):
            continue
        target_word = getattr(output, "word", None)
        if isinstance(target_word, str):
            targets.append(target_word)

    for t in targets:
        if not t or t.startswith("-"):
            continue
        resolved = _resolve_arg_path(t, eff_cwd)
        if _within(resolved, audit_root) or resolved == audit_root:
            return Decision(
                behavior="deny",
                reason=_AUDIT_DENY_REASON.format(path=t),
                rule="audit-dir",
            )
    return None


# ----- (e) write-escape check -----


def _is_write_command(argv: list[str]) -> bool:
    if not argv:
        return False
    head = argv[0]
    if head in WRITE_COMMANDS:
        return True
    if head in AMBIGUOUS_COMMANDS:
        if head == "sed":
            return any(a in {"-i", "--in-place"} or a.startswith("-i") for a in argv[1:])
        if head == "awk":
            return any(a in {"-i", "--in-place"} or "system(" in a for a in argv[1:])
        if head == "find":
            return any(f in argv[1:] for f in ("-delete", "-exec", "-execdir", "-ok"))
        if head == "tar":
            return any(
                ("c" in a or "x" in a) and a.startswith("-") and not a.startswith("--")
                for a in argv[1:]
            ) or any(
                a in {"--create", "--extract", "--append", "--update", "--delete"} for a in argv[1:]
            )
        if head == "unzip":
            return not any(a in {"-l", "-v", "-t"} for a in argv[1:])
        if head == "gzip":
            return not any(a in {"-l", "--list", "-t", "--test"} for a in argv[1:])
        if head == "git":
            if len(argv) < 2:
                return False
            return argv[1] in GIT_WRITE_SUBCMDS
    return False


def _is_writable_target(target: str, eff_cwd: Path, extra: tuple[Path, ...]) -> bool:
    if not target:
        return True
    for prefix in ALWAYS_WRITABLE_PREFIXES:
        if target == prefix or target.startswith(prefix + "/"):
            return True
    resolved = _resolve_arg_path(target, eff_cwd)
    if _within(resolved, eff_cwd) or resolved == eff_cwd:
        return True
    return any(_within(resolved, w) or resolved == w for w in extra)


def _write_path_args(argv: list[str]) -> list[str]:
    """Positional args that are paths for the write classification of this cmd."""
    if not argv:
        return []
    head = argv[0]
    positionals = [a for a in argv[1:] if not a.startswith("-") and a != "--"]

    if head in {"rm", "rmdir", "unlink", "shred", "mv", "cp", "tee", "install", "rsync"}:
        return positionals
    if head in {"mkdir", "touch", "ln", "link"}:
        return positionals
    if head in {"chmod", "chown", "chgrp", "chflags"}:
        return positionals[1:]
    if head == "find":
        starts: list[str] = []
        for a in argv[1:]:
            if a.startswith("-"):
                break
            starts.append(a)
        return starts
    if head == "sed":
        return positionals[1:]
    if head == "awk":
        return positionals[1:]
    if head == "tar":
        for i, a in enumerate(argv[1:], start=1):
            if a in {"-f", "--file"} and i + 1 < len(argv):
                return [argv[i + 1]]
            if a.startswith("--file="):
                return [a.split("=", 1)[1]]
        return []
    if head == "patch":
        return positionals
    if head == "git" and len(argv) >= 2:
        sub = argv[1]
        if sub in {"add", "rm", "mv", "checkout", "restore", "switch"}:
            return [a for a in argv[2:] if not a.startswith("-") and a != "--"]
        return []
    return []


def check_write_escape(
    cmd_node: object,
    argv: list[str],
    eff_cwd: Path,
    extra_writable: tuple[Path, ...],
) -> Decision | None:
    seg_cwd = _effective_cwd_for(argv, eff_cwd)

    # Redirect targets are checked unconditionally — `echo hi > /etc/foo`
    # is a write even though echo itself is not in WRITE_COMMANDS.
    for r in _extract_redirects(cmd_node):
        rtype = getattr(r, "type", "")
        if rtype not in {">", ">>", "&>", ">|"}:
            continue
        output = getattr(r, "output", None)
        if output is None or isinstance(output, int):
            continue
        target_word = getattr(output, "word", "")
        if isinstance(target_word, str) and not _is_writable_target(
            target_word,
            seg_cwd,
            extra_writable,
        ):
            return Decision(
                behavior="deny",
                reason=_WRITE_ESCAPE_REASON.format(path=target_word, cwd=str(seg_cwd)),
                rule="write-escape",
            )

    # argv positional targets — only meaningful for known write commands.
    if not _is_write_command(argv):
        return None
    for arg in _write_path_args(argv):
        if not _is_writable_target(arg, seg_cwd, extra_writable):
            return Decision(
                behavior="deny",
                reason=_WRITE_ESCAPE_REASON.format(path=arg, cwd=str(seg_cwd)),
                rule="write-escape",
            )
    return None


# ----- (f) redundant-cd check -----

# Chars that mean the target is expanded by the shell at runtime — we cannot
# resolve it statically, so we never flag it (avoids false positives on
# `cd "$PWD"`, `cd $(git rev-parse --show-toplevel)`, globbed targets).
_CD_DYNAMIC_CHARS: Final[str] = "$*?`"


def check_redundant_cd(argv: list[str], eff_cwd: Path) -> Decision | None:
    """Deny a leading ``cd <path>`` whose target is the current directory.

    A ``cd`` into the directory the shell is already in adds nothing and
    obscures intent (User Authority Protocol — Shell discipline: applies even
    when ``<path>`` equals the current directory). Blocking forces the model to
    reissue without the noise. Genuine directory changes (resolved target !=
    eff_cwd) and runtime-expanded targets pass untouched.
    """
    if len(argv) < 2 or argv[0] != "cd":
        return None
    target = argv[1]
    if target.startswith("-"):  # `cd -`, option flags — not a literal path
        return None
    if any(c in target for c in _CD_DYNAMIC_CHARS):
        return None
    if _resolve_arg_path(target, eff_cwd) != eff_cwd:
        return None
    return Decision(
        behavior="deny",
        reason=_REDUNDANT_CD_REASON.format(path=target, cwd=str(eff_cwd)),
        rule="redundant-cd",
    )


# ----- Phase 2 driver -----


def _analyze_segment(
    cmd_node: object,
    argv: list[str],
    eff_cwd: Path,
    settings_allow: list[str],
    audit_root: Path,
    extra_writable: tuple[Path, ...],
    depth: int = 0,
) -> Decision | None:
    """Apply structural checks to a single CommandNode segment."""
    d = check_redundant_cd(argv, eff_cwd)
    if d is not None:
        return d
    d = check_interp_inline_exec(argv)
    if d is not None:
        return d
    d = check_shell_inline_exec(
        argv,
        eff_cwd,
        settings_allow,
        audit_root,
        extra_writable,
        depth,
    )
    if d is not None:
        return d
    d = check_secret_path(argv)
    if d is not None:
        return d
    d = check_audit_dir(cmd_node, argv, eff_cwd, audit_root)
    if d is not None:
        return d
    d = check_write_escape(cmd_node, argv, eff_cwd, extra_writable)
    if d is not None:
        return d
    return None


# ============================================================
# Phase 3 — positive allow match against settings.json
# ============================================================


def _quote_arg(a: str) -> str:
    """Re-emit an argv token so it matches settings.json Bash() patterns."""
    if not a:
        return "''"
    if all(c.isalnum() or c in "@%+=:,./-_" for c in a):
        return a
    return shlex.quote(a)


def _segment_strings(argv: list[str]) -> list[str]:
    """Render argv into candidate strings for fnmatch against allow patterns.

    Produces both raw-joined and shlex-quoted variants because settings.json
    patterns are written for the raw form.
    """
    if not argv:
        return []
    raw = " ".join(argv)
    quoted = " ".join(_quote_arg(a) for a in argv)
    return [raw, quoted] if raw != quoted else [raw]


def _matches_any_allow(argv: list[str], patterns: list[str]) -> bool:
    if not argv:
        return True
    if argv[0] in BUILTIN_SAFE:
        return True
    # Shell wrappers `bash -c '...'` (and equivalents) — Phase 2 has already
    # recursively verified the inner script via check_shell_inline_exec.
    # If Phase 2 didn't deny, treat the wrapper as approved.
    if argv[0] in SHELL_INLINE_BIN and "-c" in argv[1:]:
        return True
    for seg_str in _segment_strings(argv):
        for pat in patterns:
            if fnmatch.fnmatchcase(seg_str, pat):
                return True
    return False


def _load_bash_allow_patterns() -> list[str]:
    """Read ~/.claude/settings.json permissions.allow, extract Bash(...) bodies."""
    home = Path(os.environ.get("HOME") or "/tmp")  # noqa: S108
    settings_path = home / ".claude" / "settings.json"
    try:
        text = settings_path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    allow = data.get("permissions", {}).get("allow", [])
    return [
        entry[5:-1]
        for entry in allow
        if isinstance(entry, str) and entry.startswith("Bash(") and entry.endswith(")")
    ]


def _load_allowed_dirs() -> list[str]:
    home = Path(os.environ.get("HOME") or "/tmp")  # noqa: S108
    settings_path = home / ".claude" / "settings.json"
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    val = data.get("permissions", {}).get("allowedDirectories", [])
    if isinstance(val, list):
        return [str(v) for v in val if isinstance(v, str)]
    return []


def _writable_paths(allowed_dirs: list[str]) -> tuple[Path, ...]:
    out: list[Path] = []
    for d in allowed_dirs:
        try:
            out.append(Path(d).expanduser().resolve())
        except (OSError, RuntimeError):
            continue
    tmp_env = os.environ.get("TMPDIR")
    if tmp_env:
        with contextlib.suppress(OSError, RuntimeError):
            out.append(Path(tmp_env).resolve())
    # /tmp on macOS is a symlink to /private/tmp. Resolve so that
    # _within() comparisons against resolved target paths match.
    try:
        out.append(Path("/tmp").resolve())  # noqa: S108
    except (OSError, RuntimeError):
        out.append(Path("/tmp"))  # noqa: S108
    return tuple(out)


# ============================================================
# Telemetry
# ============================================================


def _telemetry_path() -> Path:
    home = Path(os.environ.get("HOME") or "/tmp")  # noqa: S108
    now = datetime.now(UTC)
    return (
        home
        / ".claude"
        / "state"
        / "missed_approvals"
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{now.day:02d}"
        / f"{now.hour:02d}.jsonl"
    )


# Size threshold above which the current shard is rotated aside. Per-hour
# partitioning already caps most growth; this is a safety net for pathological
# hours (e.g. a runaway agent) that would otherwise let a single file grow
# without bound.
TELEMETRY_MAX_BYTES: Final[int] = 1 * 1024 * 1024  # 1 MiB
TELEMETRY_MAX_ROTATED: Final[int] = 5


def _rotate_telemetry(path: Path) -> None:
    """Rename the shard aside and prune old rotations. Best-effort."""
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size < TELEMETRY_MAX_BYTES:
        return
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    rotated = path.with_name(f"{path.name}.{stamp}.old")
    try:
        path.replace(rotated)
    except OSError:
        return
    # Prune older rotations, keeping the most recent TELEMETRY_MAX_ROTATED.
    try:
        siblings = sorted(
            path.parent.glob(f"{path.name}.*.old"),
            key=lambda p: p.name,
            reverse=True,
        )
    except OSError:
        return
    for old in siblings[TELEMETRY_MAX_ROTATED:]:
        try:
            old.unlink()
        except OSError:
            continue


def log_miss(
    cmd: str,
    cwd: str,
    reason: str,
    details: str | None = None,
) -> None:
    """Best-effort append to hourly telemetry shard. Never raises."""
    try:
        path = _telemetry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            _rotate_telemetry(path)
        record: dict[str, str] = {
            "ts": datetime.now(UTC).isoformat(),
            "cwd": cwd,
            "cmd": cmd,
            "reason": reason,
        }
        if details:
            record["details"] = details
        line = json.dumps(record, ensure_ascii=False)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001, S110  # telemetry MUST NOT break the hook
        pass


# ============================================================
# Top-level evaluation
# ============================================================


def evaluate(
    cmd: str,
    cwd: str,
    allowed_dirs: list[str],
    settings_allow: list[str],
) -> Decision:
    # Phase 1 — deny rules
    p1 = phase1_check(cmd)
    if p1.behavior == "deny":
        return p1

    # Phase 2 — AST analysis
    trees, err = parse_safely(cmd)
    if trees is None:
        log_miss(cmd, cwd, "parse_failure", err)
        return DEFER_DECISION

    eff_cwd = Path(cwd).resolve()
    audit_root = (eff_cwd / AUDIT_DIR_REL).resolve(strict=False)
    extra_writable = _writable_paths(allowed_dirs)

    segments: list[tuple[object, Path]] = []
    for tree in trees:
        for node, scwd in walk_commands(tree, eff_cwd):
            argv = _extract_argv(node)
            if not argv:
                continue
            segments.append((node, scwd))
            d = _analyze_segment(
                node,
                argv,
                scwd,
                settings_allow,
                audit_root,
                extra_writable,
            )
            if d is not None:
                return d

    # Phase 3 — positive allow against settings.json
    for node, _ in segments:
        argv = _extract_argv(node)
        if not _matches_any_allow(argv, settings_allow):
            return DEFER_DECISION
    return ALLOW_DECISION


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW
    if data.get("tool_name") != "Bash":
        return hooks.ALLOW
    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return hooks.ALLOW
    cmd = tool_input.get("command", "")
    if not isinstance(cmd, str) or not cmd.strip():
        return hooks.ALLOW
    cwd_value = data.get("cwd", str(Path.cwd()))
    cwd = cwd_value if isinstance(cwd_value, str) else str(Path.cwd())

    allowed_dirs = _load_allowed_dirs()
    settings_allow = _load_bash_allow_patterns()

    decision = evaluate(cmd, cwd, allowed_dirs, settings_allow)

    if decision.behavior == "deny":
        log_miss(cmd, cwd, "deny", decision.rule)
        sys.stderr.write(f"BLOCKED [{decision.rule}]: {decision.reason}\n")
        hooks.write_decision("deny", reason=decision.reason)
        return hooks.BLOCK
    if decision.behavior == "allow":
        hooks.write_decision("allow")
        return hooks.ALLOW

    # defer — silent fall-through; log for telemetry
    log_miss(cmd, cwd, "defer", "no_allow_match_or_unknown")
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
