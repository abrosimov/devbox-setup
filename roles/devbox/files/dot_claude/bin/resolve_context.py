#!/usr/bin/env python3
"""Resolve the task context every command and agent starts from.

The profile (MNEMOSYNE_PERISTASEOS) is read first and always: it decides where
the repository's vault may live. The repository then declares the vault in
`.vault-root` at its top level: the name of one immediate child on a personal
machine, an absolute path outside the repository on a work machine. A Jira
issue in the branch name is a convenience, never a requirement.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, proc

PROFILE_VAR: Final[str] = "MNEMOSYNE_PERISTASEOS"
PROFILES: Final[frozenset[str]] = frozenset({"personal", "work"})
VAULT_ROOT_FILE: Final[str] = ".vault-root"
JIRA_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z]+-[0-9]+$")

USAGE: Final[str] = (
    "Usage: resolve_context.py\n"
    "\n"
    "Prints one JSON object: PROFILE, VAULT, BRANCH, JIRA_ISSUE (null when the\n"
    "branch carries none), BRANCH_NAME.\n"
    "\n"
    "Exit codes:\n"
    "  0  Context resolved\n"
    "  1  Not a git repository, profile unset, or no usable .vault-root (stderr says which)\n"
)


class ContextError(Exception):
    """A condition the caller must fix; the message is the whole explanation."""


@dataclass(frozen=True)
class Context:
    profile: str
    vault: str
    branch: str
    jira_issue: str | None
    branch_name: str

    def to_json(self) -> str:
        payload = {
            "PROFILE": self.profile,
            "VAULT": self.vault,
            "BRANCH": self.branch,
            "JIRA_ISSUE": self.jira_issue,
            "BRANCH_NAME": self.branch_name,
        }
        return json.dumps(payload, ensure_ascii=False)


def read_profile(environ: dict[str, str]) -> str:
    profile = environ.get(PROFILE_VAR, "").strip()
    if not profile:
        message = (
            f"{PROFILE_VAR} is not set. `make personal` / `make work` render it into the shell rc;"
            " start a new shell, or run the provisioning once on this machine."
        )
        raise ContextError(message)
    if profile not in PROFILES:
        message = f"{PROFILE_VAR}={profile!r} is not one of {sorted(PROFILES)}."
        raise ContextError(message)
    return profile


def resolve_vault(profile: str, toplevel: Path, declared: str | None) -> Path:
    """Apply the profile's rule to the content of .vault-root."""
    if declared is None:
        where = (
            "the name of a child directory such as `docs`"
            if profile == "personal"
            else "an absolute path outside the repository"
        )
        message = (
            f"{toplevel / VAULT_ROOT_FILE} is missing; on a {profile} machine it must hold {where}."
        )
        raise ContextError(message)
    value = declared.strip()
    external = value.startswith(("/", "~"))
    if profile == "personal":
        if external or not value:
            message = (
                f"{VAULT_ROOT_FILE} holds {value!r}; on a personal machine the vault lives inside"
                " the repository, so it must name one immediate child directory."
            )
            raise ContextError(message)
        if "/" in value or value.startswith("."):
            message = (
                f"{VAULT_ROOT_FILE} holds {value!r}; it must name one immediate, non-dot child."
            )
            raise ContextError(message)
        vault = toplevel / value
        if vault.is_symlink() or not vault.is_dir():
            message = f"{vault} is not a directory (symlinks are not admitted)."
            raise ContextError(message)
        return vault
    if not external:
        message = (
            f"{VAULT_ROOT_FILE} holds {value!r}; on a work machine the vault lives outside the"
            " repository, so it must be an absolute path (or start with `~`)."
        )
        raise ContextError(message)
    vault = Path(value).expanduser()
    if not vault.is_dir():
        message = f"{vault} is not a directory."
        raise ContextError(message)
    resolved_vault = vault.resolve()
    resolved_top = toplevel.resolve()
    if resolved_vault == resolved_top or resolved_top in resolved_vault.parents:
        message = (
            f"{vault} lies inside the repository; on a work machine the vault must be outside it."
        )
        raise ContextError(message)
    return resolved_vault


def split_branch(branch: str) -> tuple[str | None, str]:
    """`PROJ-123_name` -> ("PROJ-123", "name"); anything else -> (None, branch)."""
    head, sep, tail = branch.partition("_")
    if sep and tail and JIRA_RE.match(head):
        return head, tail
    return None, branch


def git_toplevel() -> Path:
    """The repository root; raises when the cwd is not inside a git work tree."""
    inside = proc.run_cmd(["git", "rev-parse", "--is-inside-work-tree"], timeout=5)
    if not inside.success or inside.stdout.strip() != "true":
        message = "not inside a git repository."
        raise ContextError(message)
    result = proc.run_cmd(["git", "rev-parse", "--show-toplevel"], timeout=5)
    if not result.success or not result.stdout.strip():
        message = "git rev-parse --show-toplevel failed."
        raise ContextError(message)
    return Path(result.stdout.strip())


def current_branch() -> str:
    result = proc.run_cmd(["git", "branch", "--show-current"], timeout=5)
    return result.stdout.strip() if result.success else ""


def read_vault_root(toplevel: Path) -> str | None:
    marker = toplevel / VAULT_ROOT_FILE
    if not marker.is_file():
        return None
    return marker.read_text(encoding="utf-8")


def resolve(profile: str, toplevel: Path, declared: str | None, branch: str) -> Context:
    vault = resolve_vault(profile, toplevel, declared)
    jira_issue, branch_name = split_branch(branch)
    return Context(
        profile=profile,
        vault=str(vault),
        branch=branch,
        jira_issue=jira_issue,
        branch_name=branch_name,
    )


def main(argv: list[str] | None = None) -> int:
    env.setup()
    args = argv if argv is not None else sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        sys.stdout.write(USAGE)
        return 0
    if args:
        sys.stderr.write(f"Unknown option: {args[0]}\n")
        return 1

    try:
        profile = read_profile(dict(os.environ))
        toplevel = git_toplevel()
        context = resolve(profile, toplevel, read_vault_root(toplevel), current_branch())
    except ContextError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1

    sys.stdout.write(context.to_json() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
