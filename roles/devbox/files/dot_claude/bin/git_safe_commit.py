#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, proc

DEFAULT_INTEGRATION: Final[str] = "build/stable"

SECRET_PATTERNS: Final[tuple[str, ...]] = (
    ".env",
    ".env.*",
    "*/.env",
    "*/.env.*",
    "*.pem",
    "*.key",
    "*credentials*",
    "*.p12",
    "*.pfx",
    "*.jks",
)

SECRETS_DIR_PATTERNS: Final[tuple[str, ...]] = (
    "*/secrets/*",
    "secrets/*",
)


@dataclass(frozen=True)
class ParsedArgs:
    message: str
    files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParseFailure:
    reason: str


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(path, pat) for pat in patterns)


def is_secret_path(path: str) -> bool:
    if _matches_any(path, SECRETS_DIR_PATTERNS):
        return True
    return _matches_any(path, SECRET_PATTERNS)


def secret_category(path: str) -> str:
    if _matches_any(path, (".env", ".env.*", "*/.env", "*/.env.*")):
        return "environment file"
    if _matches_any(path, SECRETS_DIR_PATTERNS):
        return "secrets directory file"
    if _matches_any(path, SECRET_PATTERNS):
        return "sensitive file"
    return ""


def parse_args(argv: list[str]) -> ParsedArgs | ParseFailure:
    message: str | None = None
    files: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "-m":
            if i + 1 >= len(argv):
                return ParseFailure("-m requires a message argument.")
            message = argv[i + 1]
            i += 2
            continue
        if arg == "--":
            files.extend(argv[i + 1 :])
            break
        if arg.startswith("-"):
            return ParseFailure(f"Unknown flag '{arg}'. Only -m \"message\" is supported.")
        files.append(arg)
        i += 1
    if message is None:
        return ParseFailure(
            'Commit message required. Use: git_safe_commit.py -m "message" [files...]',
        )
    return ParsedArgs(message=message, files=files)


def current_branch() -> str:
    result = proc.run_cmd(["git", "branch", "--show-current"], timeout=5)
    if not result.success:
        return ""
    return result.stdout.strip()


def integration_branch() -> str:
    result = proc.run_cmd(
        ["git", "config", "--get", "claude.integrationBranch"],
        timeout=5,
    )
    if not result.success:
        return DEFAULT_INTEGRATION
    candidate = result.stdout.strip()
    return candidate or DEFAULT_INTEGRATION


def staged_files() -> list[str]:
    result = proc.run_cmd(["git", "diff", "--cached", "--name-only"], timeout=10)
    if not result.success:
        return []
    return [line for line in result.stdout.splitlines() if line]


def unstage(path: str) -> None:
    proc.run_cmd(["git", "reset", "HEAD", "--", path], timeout=10)


def add_files(files: list[str]) -> bool:
    cmd = ["git", "add", "-u"] if not files else ["git", "add", "--", *files]
    return proc.run_cmd(cmd, timeout=30).success


def nothing_staged() -> bool:
    return proc.run_cmd(["git", "diff", "--cached", "--quiet"], timeout=10).success


def commit(message: str) -> int:
    result = proc.run_cmd(["git", "commit", "-m", message], timeout=60)
    sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


def _check_branch(branch: str, integration: str) -> int | None:
    if branch == "":
        sys.stderr.write("BLOCKED: Not on any branch (detached HEAD).\n")
        return 1
    if branch in {"main", "master", integration}:
        sys.stderr.write(
            f"BLOCKED: Cannot commit on protected branch '{branch}'.\n"
            "Create a feature branch first:\n"
            f"  git checkout -b PROJ-123_feature {integration}\n",
        )
        return 1
    return None


def _check_secrets() -> int | None:
    for staged in staged_files():
        if is_secret_path(staged):
            category = secret_category(staged) or "sensitive file"
            sys.stderr.write(
                f"BLOCKED: Refusing to commit {category}: {staged}\n",
            )
            unstage(staged)
            return 1
    return None


def run(argv: list[str]) -> int:
    branch = current_branch()
    integration = integration_branch()
    branch_error = _check_branch(branch, integration)
    if branch_error is not None:
        return branch_error

    parsed = parse_args(argv)
    if isinstance(parsed, ParseFailure):
        sys.stderr.write(f"BLOCKED: {parsed.reason}\n")
        return 1

    if not add_files(parsed.files):
        sys.stderr.write("BLOCKED: git add failed.\n")
        return 1

    secret_error = _check_secrets()
    if secret_error is not None:
        return secret_error

    if nothing_staged():
        sys.stdout.write("Nothing to commit (no staged changes).\n")
        return 0

    return commit(parsed.message)


def main(argv: list[str] | None = None) -> int:
    env.setup()
    return run(argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
