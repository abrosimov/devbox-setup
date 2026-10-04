#!/usr/bin/env python3
"""Rewrite deployed Claude agent frontmatter into Antigravity's model and tool names."""

import sys
from pathlib import Path

# Antigravity selects a capability tier rather than a named model.
MODEL_MAP = {"opus": "pro", "sonnet": "flash"}

# A single Claude tool often needs several Antigravity tools to cover the same ground:
# Antigravity has no combined reader, and splits editing across three distinct tools.
# Expressing the vocabulary as a table keeps the mapping reviewable as data; a name with
# no entry is passed through lower-cased, so a hand-written Antigravity tool still works.
TOOL_MAP = {
    "read": ["view_file", "grep_search"],
    "edit": ["write_to_file", "replace_file_content", "multi_replace_file_content"],
    "write": ["write_to_file", "replace_file_content", "multi_replace_file_content"],
    "bash": ["run_command"],
    "ls": ["list_dir"],
}


def translate_model_line(line: str) -> str:
    value = line.split(":", 1)[1].strip()
    tier = MODEL_MAP.get(value)
    return f"model: {tier}" if tier is not None else line


def translate_tools_line(line: str) -> list[str]:
    value = line.split(":", 1)[1].strip()
    names = [name.strip().lower() for name in value.split(",") if name.strip()]
    translated: list[str] = []
    for name in names:
        translated.extend(TOOL_MAP.get(name, [name]))
    return ["tools:", *(f"  - {tool}" for tool in translated)]


def translate_frontmatter(frontmatter: str) -> list[str]:
    new_lines: list[str] = []
    for line in frontmatter.split("\n"):
        if line.startswith("model:"):
            new_lines.append(translate_model_line(line))
        elif line.startswith("tools:"):
            new_lines.extend(translate_tools_line(line))
        else:
            new_lines.append(line)
    return new_lines


def translate_file(path: Path) -> None:
    content = path.read_text()
    if not content.startswith("---\n"):
        return

    # Search from index 4 so the opening delimiter cannot be mistaken for the closing one.
    end_idx = content.find("\n---\n", 4)
    if end_idx == -1:
        return

    frontmatter = content[4:end_idx]
    body = content[end_idx:]

    new_content = "---\n" + "\n".join(translate_frontmatter(frontmatter)) + body
    if new_content != content:
        path.write_text(new_content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    agents_dir = Path(sys.argv[1])
    for md_file in agents_dir.glob("*.md"):
        translate_file(md_file)
