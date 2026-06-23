#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, io_json

WORK_TOOLS: Final[frozenset[str]] = frozenset({"Edit", "Write", "Bash", "Task", "NotebookEdit"})
FIRST_THRESHOLD: Final[int] = 40
REPEAT_INTERVAL: Final[int] = 25


@dataclass(frozen=True)
class CheckpointState:
    count: int
    last_suggestion: int


def state_path_for(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"claude-checkpoint-{session_id}"


def load_state(path: Path) -> CheckpointState:
    if not path.exists():
        return CheckpointState(count=0, last_suggestion=0)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return CheckpointState(count=0, last_suggestion=0)
    data = io_json.safe_load_json(raw)
    count_value = data.get("count", 0)
    last_value = data.get("lastSuggestion", 0)
    count = count_value if isinstance(count_value, int) else 0
    last = last_value if isinstance(last_value, int) else 0
    return CheckpointState(count=count, last_suggestion=last)


def save_state(path: Path, state: CheckpointState) -> None:
    payload: dict[str, object] = {"count": state.count, "lastSuggestion": state.last_suggestion}
    io_json.dump_json(path, payload)


def next_state(current: CheckpointState) -> tuple[CheckpointState, bool]:
    new_count = current.count + 1
    if current.last_suggestion == 0 and new_count >= FIRST_THRESHOLD:
        return CheckpointState(count=new_count, last_suggestion=new_count), True
    if current.last_suggestion > 0 and new_count - current.last_suggestion >= REPEAT_INTERVAL:
        return CheckpointState(count=new_count, last_suggestion=new_count), True
    return CheckpointState(count=new_count, last_suggestion=current.last_suggestion), False


def suggestion_message(count: int) -> str:
    return (
        f"[Context survival] You've made {count} tool calls this session. "
        "Consider summarising current progress and decisions into MEMORY.md "
        "before context compaction occurs. This preserves task state across "
        "compaction or session exit."
    )


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW

    session_value = data.get("session_id", "unknown")
    session_id = session_value if isinstance(session_value, str) else "unknown"
    tool_value = data.get("tool_name", "")
    tool_name = tool_value if isinstance(tool_value, str) else ""

    if tool_name not in WORK_TOOLS:
        return hooks.ALLOW

    path = state_path_for(session_id)
    state = load_state(path)
    updated, should_suggest = next_state(state)
    save_state(path, updated)

    if should_suggest:
        hooks.write_additional_context(suggestion_message(updated.count))

    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
