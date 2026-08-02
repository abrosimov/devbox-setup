#!/usr/bin/env python3
import sys
import re
from pathlib import Path

def translate_file(path: Path):
    content = path.read_text()
    if not content.startswith("---\n"):
        return

    # Extract frontmatter
    end_idx = content.find("\n---\n", 4)
    if end_idx == -1:
        return
    
    frontmatter = content[4:end_idx]
    body = content[end_idx:]

    lines = frontmatter.split("\n")
    new_lines = []
    
    for line in lines:
        if line.startswith("model:"):
            # opus -> pro, sonnet -> flash
            val = line.split(":", 1)[1].strip()
            if val == "opus":
                new_lines.append("model: pro")
            elif val == "sonnet":
                new_lines.append("model: flash")
            else:
                new_lines.append(line)
        elif line.startswith("tools:"):
            # tools: Read, Edit, Bash -> tools: [read_file, write_to_file, run_command]
            val = line.split(":", 1)[1].strip()
            tools = [t.strip() for t in val.split(",") if t.strip()]
            translated_tools = []
            for t in tools:
                tl = t.lower()
                if tl == "read":
                    translated_tools.append("view_file")
                    translated_tools.append("grep_search")
                elif tl == "edit" or tl == "write":
                    translated_tools.extend(["write_to_file", "replace_file_content", "multi_replace_file_content"])
                elif tl == "bash":
                    translated_tools.append("run_command")
                elif tl == "ls":
                    translated_tools.append("list_dir")
                else:
                    translated_tools.append(tl) # fallback
            new_lines.append("tools:")
            for tt in translated_tools:
                new_lines.append(f"  - {tt}")
        else:
            new_lines.append(line)

    new_content = "---\n" + "\n".join(new_lines) + body
    if new_content != content:
        path.write_text(new_content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    agents_dir = Path(sys.argv[1])
    for md_file in agents_dir.glob("*.md"):
        translate_file(md_file)
