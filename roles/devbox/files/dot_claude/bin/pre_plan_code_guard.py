#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import hooks

CODE_LANGS: Final[frozenset[str]] = frozenset(
    {
        "go",
        "golang",
        "python",
        "py",
        "python3",
        "ts",
        "typescript",
        "tsx",
        "js",
        "javascript",
        "jsx",
        "mjs",
        "cjs",
        "java",
        "kotlin",
        "kt",
        "scala",
        "groovy",
        "rust",
        "rs",
        "c",
        "cpp",
        "c++",
        "cc",
        "cxx",
        "h",
        "hpp",
        "hh",
        "objc",
        "cs",
        "csharp",
        "ruby",
        "rb",
        "php",
        "swift",
        "sql",
        "proto",
        "protobuf",
        "graphql",
        "gql",
    }
)

SAFE_LANGS: Final[frozenset[str]] = frozenset(
    {
        "json",
        "json5",
        "jsonc",
        "yaml",
        "yml",
        "toml",
        "ini",
        "cfg",
        "conf",
        "properties",
        "csv",
        "tsv",
        "markdown",
        "md",
        "mermaid",
        "diff",
        "patch",
        "http",
        "dotenv",
        "env",
    }
)

ALWAYS_LANGS: Final[frozenset[str]] = frozenset({"bash", "sh", "shell", "zsh", "console"})

CODE_SIGNATURES: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^\s*func\s+[A-Za-z_(]"),
    re.compile(r"^\s*def\s+\w+\s*\("),
    re.compile(r"^\s*async\s+def\s+\w+\s*\("),
    re.compile(r"^\s*class\s+\w+"),
    re.compile(r"^\s*(public|private|protected)\s+(static\s+)?[\w<>\[\]]+\s+\w+"),
    re.compile(r"^\s*package\s+[\w./]+"),
    re.compile(r"^\s*import\s+[\w.{*]"),
    re.compile(r"^\s*from\s+[\w.]+\s+import\s+"),
    re.compile(r"^\s*type\s+\w+\s+(struct|interface)\b"),
    re.compile(r"^\s*(export\s+)?(default\s+)?(function|interface|enum)\s+\w"),
    re.compile(r"^\s*(const|let|var)\s+\w+\s*[:=]"),
    re.compile(r"^\s*@[\w.]+(\(|\s*$)"),
    re.compile(r"^\s*(if|for|while|switch)\s*\(.*\)\s*\{\s*$"),
    re.compile(r"=>\s*\{?\s*$"),
)

FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^|\n)[ \t]*(`{3,}|~{3,})[ \t]*([A-Za-z0-9_+#-]*)[ \t]*\n(.*?)(?:\n[ \t]*\1[ \t]*(?=\n|$))",
    re.DOTALL,
)

REMEDIATION: Final[str] = (
    "\nThe implementation planner describes WHAT, not HOW. Remove the code and\n"
    "describe the behaviour (inputs, outputs, rules) instead. The machine-readable\n"
    "execution DAG belongs in plan_output.json, not as a code block in plan.md.\n"
)
USAGE_EXIT: Final[int] = 10


def is_plan_file(file_path: str) -> bool:
    return Path(file_path).name == "plan.md"


def count_signatures(body: str) -> int:
    hits = 0
    for line in body.split("\n"):
        if any(pattern.search(line) for pattern in CODE_SIGNATURES):
            hits += 1
    return hits


def find_code(content: str) -> list[str]:
    violations: list[str] = []
    for match in FENCE_RE.finditer(content):
        tag = (match.group(2) or "").lower()
        body = match.group(3) or ""

        if tag in CODE_LANGS:
            violations.append(
                f"fenced ```{tag} block — source code is not allowed in plan.md",
            )
            continue
        if tag in SAFE_LANGS:
            continue

        hits = count_signatures(body)
        threshold = 1 if tag in ALWAYS_LANGS else 2
        if hits >= threshold:
            label = f"```{tag}" if tag else "untagged"
            violations.append(
                f"{label} fenced block with {hits} code signature(s) "
                "— describe behaviour instead of code",
            )
    return violations


def collect_write_content(tool_name: str, tool_input: dict[str, object]) -> str:
    if tool_name == "Write":
        content = tool_input.get("content", "")
        return content if isinstance(content, str) else ""
    if tool_name == "Edit":
        new = tool_input.get("new_string", "")
        return new if isinstance(new, str) else ""
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits", [])
        if not isinstance(edits, list):
            return ""
        parts: list[str] = []
        for edit in edits:
            if not isinstance(edit, dict):
                continue
            new_string = edit.get("new_string", "")
            if isinstance(new_string, str) and new_string:
                parts.append(new_string)
        return "\n".join(parts)
    fallback = tool_input.get("content") or tool_input.get("new_string", "")
    return fallback if isinstance(fallback, str) else ""


def run_cli(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if "--file" not in argv:
        sys.stderr.write("usage: pre_plan_code_guard.py --file <path> | --self-test\n")
        return USAGE_EXIT
    idx = argv.index("--file")
    if idx + 1 >= len(argv):
        sys.stderr.write("usage: pre_plan_code_guard.py --file <path> | --self-test\n")
        return USAGE_EXIT
    file_path = argv[idx + 1]
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"ERROR: cannot read {file_path}: {exc}\n")
        return USAGE_EXIT
    violations = find_code(content)
    if violations:
        joined = "\n  - ".join(violations)
        sys.stderr.write(f"FAIL: {file_path} contains code:\n  - {joined}\n{REMEDIATION}")
        return hooks.BLOCK
    sys.stdout.write(f"PASS: {file_path} contains no code blocks\n")
    return hooks.ALLOW


def self_test() -> int:
    cases: list[tuple[str, str, int]] = [
        ("clean prose", "# Plan\n\n| FR | AC |\n|----|----|\n| 1 | x |\n", 0),
        ("go fence", "## X\n\n```go\nfunc Foo() {}\n```\n", 2),
        ("python fence", "```python\ndef foo():\n    pass\n```\n", 2),
        ("json allowed", '```json\n{"a": 1}\n```\n', 0),
        ("mermaid allowed", "```mermaid\ngraph TD; A-->B\n```\n", 0),
        ("untagged code", "```\nclass Foo:\n    def bar(self):\n        return 1\n```\n", 2),
        (
            "untagged prose",
            "```\nThis is just an example sentence.\nAnother sentence here.\n```\n",
            0,
        ),
        ("bash leak", "```bash\ngo build ./...\n```\n", 0),
        ("bash code leak", "```bash\nfunc main() {}\n```\n", 2),
    ]
    failed = 0
    for name, content, want in cases:
        got = hooks.BLOCK if find_code(content) else hooks.ALLOW
        status = "ok  " if got == want else "FAIL"
        if got != want:
            failed += 1
        sys.stdout.write(f"  [{status}] {name} (want {want}, got {got})\n")
    sys.stdout.write("self-test: PASS\n" if failed == 0 else f"self-test: {failed} FAILED\n")
    return 0 if failed == 0 else 1


def run_hook() -> int:
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW

    tool_value = data.get("tool_name", "")
    tool_name = tool_value if isinstance(tool_value, str) else ""
    tool_input_value = data.get("tool_input", {})
    if not isinstance(tool_input_value, dict):
        return hooks.ALLOW

    file_path_value = tool_input_value.get("file_path", "")
    file_path = file_path_value if isinstance(file_path_value, str) else ""
    if not is_plan_file(file_path):
        return hooks.ALLOW

    content = collect_write_content(tool_name, tool_input_value)
    if not content:
        return hooks.ALLOW

    violations = find_code(content)
    if not violations:
        return hooks.ALLOW

    joined = "\n  - ".join(violations)
    sys.stderr.write(
        f"BLOCKED: plan.md may not contain source code.\n  - {joined}\n{REMEDIATION}",
    )
    return hooks.BLOCK


def main() -> int:
    argv = sys.argv[1:]
    if "--file" in argv or "--self-test" in argv:
        return run_cli(argv)
    return run_hook()


if __name__ == "__main__":
    sys.exit(main())
