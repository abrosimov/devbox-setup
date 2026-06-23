#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, paths, proc

GITIGNORE_ENTRY = "tmp/"


def is_blocked_path(value: str) -> bool:
    if not value:
        return False
    # The literal "/tmp/" here is the POSIX path being matched against user-supplied
    # commands, not a tempfile we create — S108 does not apply.
    return "/tmp/" in value or "/var/tmp/" in value  # noqa: S108


def is_blocked_file_target(value: str) -> bool:
    if not value:
        return False
    return value.startswith(("/tmp/", "/var/tmp/"))  # noqa: S108


def find_project_root(cwd: Path) -> Path:
    git_root = paths.find_git_root(cwd)
    if git_root is not None:
        return git_root
    result = proc.run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=cwd, timeout=5)
    if result.success:
        candidate = result.stdout.strip()
        if candidate:
            return Path(candidate)
    return cwd


def ensure_tmp_dir(root: Path) -> Path:
    tmp_dir = root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


def ensure_gitignore(root: Path) -> None:
    gitignore = root / ".gitignore"
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8").splitlines()
        for line in existing:
            if line.strip() == GITIGNORE_ENTRY:
                return
        suffix = "" if gitignore.read_text(encoding="utf-8").endswith("\n") else "\n"
        with gitignore.open("a", encoding="utf-8") as fh:
            fh.write(suffix + GITIGNORE_ENTRY + "\n")
        return
    paths.atomic_write(gitignore, GITIGNORE_ENTRY + "\n")


def _extract_command_and_path(data: dict[str, object]) -> tuple[str, str]:
    # Env vars take priority for full parity with the original bash script —
    # Claude Code's hook wrapper sets ``$CC_BASH_COMMAND`` / ``$CC_TOOL_INPUT_FILE_PATH``.
    # Stdin JSON is the fallback for direct invocation without the wrapper.
    env_command = os.environ.get("CC_BASH_COMMAND", "")
    env_file_path = os.environ.get("CC_TOOL_INPUT_FILE_PATH", "")
    if env_command or env_file_path:
        return env_command, env_file_path

    tool_input_value = data.get("tool_input", {})
    tool_input = tool_input_value if isinstance(tool_input_value, dict) else {}

    command_value = tool_input.get("command", "")
    command = command_value if isinstance(command_value, str) else ""

    file_path_value = tool_input.get("file_path", "")
    file_path = file_path_value if isinstance(file_path_value, str) else ""

    return command, file_path


def evaluate(data: dict[str, object]) -> tuple[bool, str | None]:
    command, file_path = _extract_command_and_path(data)

    if is_blocked_path(command):
        return True, command
    if is_blocked_file_target(file_path):
        return True, file_path
    return False, None


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    # Empty stdin is fine: env-var protocol may still supply command/path.
    # If both stdin and env are empty, ``evaluate`` returns ``(False, None)``.

    blocked, _target = evaluate(data)
    if not blocked:
        return hooks.ALLOW

    cwd = Path(os.environ.get("PWD") or Path.cwd())
    root = find_project_root(cwd)
    ensure_tmp_dir(root)
    ensure_gitignore(root)

    sys.stderr.write(
        # User-facing message mentions the blocked POSIX path — not a tempfile we create.
        f"BLOCKED: Do not use /tmp/ or /var/tmp/. Use {root}/tmp/ instead "  # noqa: S108
        "(project-local). The directory has been auto-created and added to "
        ".gitignore.\n",
    )
    return hooks.BLOCK


if __name__ == "__main__":
    sys.exit(main())
