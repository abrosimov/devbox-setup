#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, proc

DEFAULT_PLANS_DIR: Final[str] = "docs/implementation_plans"
JIRA_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z]+-[0-9]+$")

USAGE: Final[str] = (
    "Usage: resolve_context.py [--plans-dir <path>]\n"
    "\n"
    "Options:\n"
    "  --plans-dir <path>  Override plans directory (default: docs/implementation_plans)\n"
    "  -h, --help          Show this help\n"
    "\n"
    "Exit codes:\n"
    "  0  Valid context resolved (JSON on stdout)\n"
    "  1  Not a git repository\n"
    "  2  Branch does not match PROJ-123_description convention\n"
)


@dataclass(frozen=True)
class Context:
    jira_issue: str
    branch_name: str
    branch: str
    project_dir: str

    def to_json(self) -> str:
        payload = {
            "JIRA_ISSUE": self.jira_issue,
            "BRANCH_NAME": self.branch_name,
            "BRANCH": self.branch,
            "PROJECT_DIR": self.project_dir,
        }
        return json.dumps(payload, ensure_ascii=False)


@dataclass(frozen=True)
class ParsedArgs:
    plans_dir: str
    show_help: bool


def parse_args(argv: list[str]) -> ParsedArgs | None:
    plans_dir = DEFAULT_PLANS_DIR
    show_help = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            show_help = True
            i += 1
            continue
        if arg == "--plans-dir":
            if i + 1 >= len(argv):
                sys.stderr.write("ERROR: --plans-dir requires a value\n")
                return None
            plans_dir = argv[i + 1]
            i += 2
            continue
        sys.stderr.write(f"Unknown option: {arg}\n")
        return None
    return ParsedArgs(plans_dir=plans_dir, show_help=show_help)


def inside_git_repo() -> bool:
    result = proc.run_cmd(
        ["git", "rev-parse", "--is-inside-work-tree"],
        timeout=5,
    )
    return result.success and result.stdout.strip() == "true"


def current_branch() -> str:
    result = proc.run_cmd(["git", "branch", "--show-current"], timeout=5)
    if not result.success:
        return ""
    return result.stdout.strip()


def resolve(branch: str, plans_dir: str) -> Context | None:
    if not branch:
        return None
    jira_issue, _, branch_name = branch.partition("_")
    if not JIRA_RE.match(jira_issue):
        return None
    if not branch_name:
        return None
    project_dir = f"{plans_dir}/{jira_issue}/{branch_name}"
    return Context(
        jira_issue=jira_issue,
        branch_name=branch_name,
        branch=branch,
        project_dir=project_dir,
    )


def main(argv: list[str] | None = None) -> int:
    env.setup()
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args is None:
        return 1
    if args.show_help:
        sys.stdout.write(USAGE)
        return 0

    if not inside_git_repo():
        sys.stderr.write("ERROR: not inside a git repository\n")
        return 1

    branch = current_branch()
    if not branch:
        sys.stderr.write("ERROR: detached HEAD — no branch name available\n")
        return 2

    context = resolve(branch, args.plans_dir)
    if context is None:
        sys.stderr.write(
            f"Branch '{branch}' does not match PROJ-123_description convention.\n",
        )
        return 2

    sys.stdout.write(context.to_json() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
