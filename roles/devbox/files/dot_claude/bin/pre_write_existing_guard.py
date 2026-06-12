#!/usr/bin/env python3
"""pre-write-existing-guard — PreToolUse hook that blocks Write on existing non-empty files.

Forces the agent to use Edit/MultiEdit (string-replace) instead of Write
(whole-file overwrite) when the target file already exists with content.
Whole-file overwrites cause silent content loss, whitespace and quote
normalisation, and import reordering — all of which evade diff review.

Empty files (size 0) are exempt: the touch-then-write workflow is common
and benign.

Reads the Claude Code PreToolUse event JSON from stdin and inspects
``tool_input.file_path``. Writes a ``BLOCKED [pre-write-existing-guard]: ...``
message to stderr and exits 2 only when the target exists and has size > 0.

Stdlib only — no external dependencies.

Event: PreToolUse (matcher: Write)
Exit codes:
    0  — allow (no file_path, file missing, file empty, or any error path)
    2  — block (file exists with size > 0)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RULE_NAME: str = "pre-write-existing-guard"


def _extract_file_path(raw: str) -> str | None:
    if not raw.strip():
        return None
    try:
        event = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(event, dict):
        return None
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path")
    return file_path if isinstance(file_path, str) and file_path else None


def _is_blocking(file_path: str) -> bool:
    try:
        size = Path(file_path).stat().st_size
    except OSError:
        return False
    return size > 0


def main() -> int:
    file_path = _extract_file_path(sys.stdin.read())
    if file_path is None:
        return 0
    if not _is_blocking(file_path):
        return 0
    sys.stderr.write(
        f'BLOCKED [{RULE_NAME}]: Write on existing non-empty file "{file_path}" '
        "is not allowed. Use Edit or MultiEdit instead — they string-replace "
        "specific spans and avoid whole-file drift (silent content loss, "
        "whitespace/quote normalisation, import reordering). If you genuinely "
        "need to fully rewrite the file, delete it first or ask the user.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
