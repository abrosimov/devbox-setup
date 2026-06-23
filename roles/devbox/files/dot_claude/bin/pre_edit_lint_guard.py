#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import hooks


@dataclass(frozen=True)
class SuppressionPattern:
    regex: re.Pattern[str]
    lang: str
    directive: str


@dataclass(frozen=True)
class LazyTypePattern:
    regex: re.Pattern[str]
    directive: str
    fix: str


def _sup(pattern: str, lang: str, directive: str) -> SuppressionPattern:
    return SuppressionPattern(re.compile(pattern, re.IGNORECASE), lang, directive)


SUPPRESSION_PATTERNS: Final[tuple[SuppressionPattern, ...]] = (
    _sup(r"//\s*nolint", "Go", "//nolint"),
    _sup(r"# noqa", "Python", "# noqa"),
    _sup(r"# type:\s*ignore", "Python", "# type: ignore"),
    _sup(r"@ts-ignore", "TypeScript", "@ts-ignore"),
    _sup(r"@ts-expect-error", "TypeScript", "@ts-expect-error"),
    _sup(r"eslint-disable", "TypeScript", "eslint-disable"),
    _sup(r"@SuppressWarnings", "Java", "@SuppressWarnings"),
)

_PY_ANY_IMPORT_RE: Final[re.Pattern[str]] = re.compile(
    r"from\s+typing\s+import\s+(?:[^#\n]*,\s*)?Any(?:\s*,|\s*$|\s*\))",
    re.MULTILINE,
)

LAZY_TYPE_PATTERNS_BY_EXT: Final[dict[str, tuple[LazyTypePattern, ...]]] = {
    "py": (
        LazyTypePattern(
            _PY_ANY_IMPORT_RE,
            "from typing import Any",
            "Import and use specific types (str, int, dict[str, X], Protocol, etc.)",
        ),
        LazyTypePattern(
            re.compile(r":\s*Any\b"),
            ": Any",
            "Use a specific type annotation. If truly dynamic, use object or a Protocol.",
        ),
        LazyTypePattern(
            re.compile(r"->\s*Any\b"),
            "-> Any",
            "Specify the actual return type. Use overloads for multiple return types.",
        ),
    ),
    "ts": (
        LazyTypePattern(
            re.compile(r":\s*any\b(?!\s*\[)"),
            ": any",
            "Use unknown + type guard, or a specific type/interface.",
        ),
        LazyTypePattern(
            re.compile(r"\bas\s+any\b"),
            "as any",
            "Use a proper type assertion (as SpecificType) or fix the type mismatch.",
        ),
        LazyTypePattern(
            re.compile(r"<any\s*>"),
            "<any>",
            "Use a specific generic type parameter.",
        ),
    ),
    "go": (
        LazyTypePattern(
            re.compile(r"interface\s*\{\s*\}"),
            "interface{}",
            "Use the 'any' builtin (Go 1.18+) or preferably a concrete type/interface.",
        ),
    ),
}
LAZY_TYPE_ALIASES: Final[dict[str, str]] = {"tsx": "ts"}


def collect_texts(tool_name: str, tool_input: dict[str, object]) -> tuple[str, str]:
    if tool_name == "Edit":
        new_value = tool_input.get("new_string", "")
        old_value = tool_input.get("old_string", "")
        new_text = new_value if isinstance(new_value, str) else ""
        old_text = old_value if isinstance(old_value, str) else ""
        return new_text, old_text
    if tool_name == "Write":
        content_value = tool_input.get("content", "")
        content = content_value if isinstance(content_value, str) else ""
        return content, ""
    return "", ""


def detect_suppression(
    new_text: str,
    old_text: str,
    *,
    is_edit: bool,
) -> list[SuppressionPattern]:
    findings: list[SuppressionPattern] = []
    for pattern in SUPPRESSION_PATTERNS:
        if not pattern.regex.search(new_text):
            continue
        if is_edit and pattern.regex.search(old_text):
            continue
        findings.append(pattern)
    return findings


def file_extension(file_path: str) -> str:
    if not file_path:
        return ""
    return file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""


def patterns_for_ext(ext: str) -> tuple[LazyTypePattern, ...]:
    resolved = LAZY_TYPE_ALIASES.get(ext, ext)
    return LAZY_TYPE_PATTERNS_BY_EXT.get(resolved, ())


def detect_lazy_types(
    new_text: str,
    old_text: str,
    ext: str,
    *,
    is_edit: bool,
) -> list[LazyTypePattern]:
    patterns = patterns_for_ext(ext)
    findings: list[LazyTypePattern] = []
    for pattern in patterns:
        if not pattern.regex.search(new_text):
            continue
        if is_edit and pattern.regex.search(old_text):
            continue
        findings.append(pattern)
    return findings


def format_suppression_message(findings: list[SuppressionPattern]) -> str:
    directives = ", ".join(f"{f.directive} ({f.lang})" for f in findings)
    return (
        f"BLOCKED: Lint suppression directive detected: {directives}. "
        "Fix the underlying lint issue instead of suppressing it. "
        "If suppression is truly necessary, ask the user for explicit approval first. "
        "Fix hierarchy: fix code → refactor → ask user → suppress (with approval only).\n"
    )


def format_lazy_message(findings: list[LazyTypePattern]) -> str:
    details = "\n".join(f"  • {f.directive} → {f.fix}" for f in findings)
    return (
        f"BLOCKED: Lazy typing pattern detected:\n{details}\n"
        "Use proper types instead of Any/any. "
        "If this is genuinely needed for interop or dynamic data, ask the user for approval.\n"
    )


def parse_hook_data(
    data: dict[str, object],
) -> tuple[str, dict[str, object]] | None:
    tool_value = data.get("tool_name", "")
    tool_name = tool_value if isinstance(tool_value, str) else ""
    if tool_name not in {"Edit", "Write"}:
        return None
    tool_input_value = data.get("tool_input", {})
    if not isinstance(tool_input_value, dict):
        return None
    return tool_name, tool_input_value


def check_suppression(new_text: str, old_text: str, *, is_edit: bool) -> int:
    findings = detect_suppression(new_text, old_text, is_edit=is_edit)
    if not findings:
        return hooks.ALLOW
    sys.stderr.write(format_suppression_message(findings))
    return hooks.BLOCK


def check_lazy_types(
    new_text: str,
    old_text: str,
    ext: str,
    *,
    is_edit: bool,
) -> int:
    findings = detect_lazy_types(new_text, old_text, ext, is_edit=is_edit)
    if not findings:
        return hooks.ALLOW
    sys.stderr.write(format_lazy_message(findings))
    return hooks.BLOCK


def main() -> int:
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW

    parsed = parse_hook_data(data)
    if parsed is None:
        return hooks.ALLOW
    tool_name, tool_input_value = parsed

    new_text, old_text = collect_texts(tool_name, tool_input_value)
    if not new_text:
        return hooks.ALLOW

    is_edit = tool_name == "Edit"
    suppression_status = check_suppression(new_text, old_text, is_edit=is_edit)
    if suppression_status != hooks.ALLOW:
        return suppression_status

    file_path_value = tool_input_value.get("file_path", "")
    file_path = file_path_value if isinstance(file_path_value, str) else ""
    ext = file_extension(file_path)
    return check_lazy_types(new_text, old_text, ext, is_edit=is_edit)


if __name__ == "__main__":
    sys.exit(main())
