#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, proc

WORKING_STATE_RE: Final[re.Pattern[str]] = re.compile(
    r"## Working State\n[\s\S]*?(?=\n## |\n$|$)",
)


def home_dir() -> Path:
    return Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp")  # noqa: S108


def find_memory_dir(cwd: Path) -> Path | None:
    claude_dir = home_dir() / ".claude" / "projects"
    if not claude_dir.exists():
        return None

    entries = sorted(p for p in claude_dir.iterdir() if p.is_dir())
    normalised = str(cwd).replace("/", "-")
    if normalised.startswith("--"):
        normalised = normalised[1:]

    for entry in entries:
        memory_file = entry / "memory" / "MEMORY.md"
        if memory_file.exists() and (normalised in entry.name or entry.name == normalised):
            return entry / "memory"

    latest: Path | None = None
    latest_time = 0.0
    for entry in entries:
        memory_file = entry / "memory" / "MEMORY.md"
        if memory_file.exists():
            mtime = memory_file.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
                latest = entry / "memory"
    return latest


def git(cmd: list[str], cwd: Path) -> str:
    result = proc.run_cmd(cmd, cwd=cwd, timeout=5)
    if not result.success:
        return ""
    return result.stdout.strip()


def collect_git_state(cwd: Path) -> dict[str, str | list[str]]:
    branch = git(["git", "branch", "--show-current"], cwd)
    if not branch:
        return {"branch": ""}
    sha = git(["git", "rev-parse", "--short", "HEAD"], cwd)
    modified = [
        line for line in git(["git", "diff", "--name-only", "HEAD"], cwd).splitlines() if line
    ][:5]
    staged = [
        line for line in git(["git", "diff", "--cached", "--name-only"], cwd).splitlines() if line
    ][:5]
    seen: set[str] = set()
    all_files: list[str] = []
    for f in [*modified, *staged]:
        if f not in seen:
            seen.add(f)
            all_files.append(f)
    return {
        "branch": branch,
        "sha": sha,
        "files": all_files,
    }


def render_working_state(state: dict[str, str | list[str]], event: str, now: str) -> str:
    files = state.get("files", [])
    files_line = ", ".join(files) if isinstance(files, list) and files else "no uncommitted changes"
    event_label = "context compacted" if event == "PreCompact" else "session ended"
    branch = state.get("branch", "")
    sha = state.get("sha", "")
    return "\n".join(
        [
            "## Working State",
            f"- **Branch**: {branch}",
            f"- **SHA**: {sha}",
            f"- **Modified**: {files_line}",
            f"- **Last event**: {event_label} at {now}",
            "- **Note**: Read MEMORY.md Working State to reconstruct context",
        ]
    )


def update_memory(memory_dir: Path, event: str, cwd: Path, now: str) -> None:
    memory_file = memory_dir / "MEMORY.md"
    if not memory_file.exists():
        return
    state = collect_git_state(cwd)
    if not state.get("branch"):
        return

    working_state = render_working_state(state, event, now)
    content = memory_file.read_text(encoding="utf-8")
    if WORKING_STATE_RE.search(content):
        new_content = WORKING_STATE_RE.sub(working_state, content, count=1)
    else:
        new_content = working_state + "\n\n" + content
    memory_file.write_text(new_content, encoding="utf-8")


def current_timestamp() -> str:
    now = datetime.now(UTC).replace(microsecond=0)
    return now.strftime("%Y-%m-%d %H:%M")


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return 1

    cwd_value = data.get("cwd", "")
    cwd = Path(cwd_value) if isinstance(cwd_value, str) and cwd_value else Path.cwd()
    event_value = data.get("hook_event_name", "SessionEnd")
    event = event_value if isinstance(event_value, str) else "SessionEnd"

    memory_dir = find_memory_dir(cwd)
    if memory_dir is not None:
        update_memory(memory_dir, event, cwd, current_timestamp())

    if event == "PreCompact":
        hooks.write_additional_context(
            "Working state saved to MEMORY.md. After compaction, check "
            "MEMORY.md Working State section for context.",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
