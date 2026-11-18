#!/usr/bin/env python3
"""Convert the Markdown subset of Jira and Confluence drafts to Confluence HTML.

Supports ``##`` and ``###`` headings, paragraphs, flat ``- `` and ``1. `` lists, pipe
tables (first row is the header), inline code and ``[text](https://...)`` links. Any
other block syntax stops the conversion with ``path:line: message``, so nothing is
dropped silently. Prints the link counts in and out. Exit status: 0 on success, 2 on
a usage, read, write or conversion error. Standard library only.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

Kind = Literal["blank", "heading", "bullet", "numbered", "table", "paragraph"]

TOC_MACRO = (
    '<div data-type="extension" data-extension-key="toc" '
    'data-extension-type="com.atlassian.confluence.macro.core" '
    'data-parameters=\'{"macroParams":{"minLevel":{"value":"2"},'
    '"maxLevel":{"value":"3"}},"macroMetadata":{"schemaVersion":{"value":"1"},'
    '"title":"Table of Contents"}}\'></div>'
)

HEADING_RE = re.compile(r"^(#{2,3}) +(\S.*)$")
BULLET_RE = re.compile(r"^- +(\S.*)$")
NUMBERED_RE = re.compile(r"^(\d+)\. +(\S.*)$")
TABLE_SEPARATOR_RE = re.compile(r"^\|?(?:\s*:?-+:?\s*\|)*\s*:?-+:?\s*\|?\s*$")
LINK_RE = re.compile(r"\[((?:`[^`]*`|[^\]`])+)\]\((https?://[^)\s]+)\)")
UNSUPPORTED: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\s"), "indented line (nested list, continuation or code block)"),
    (re.compile(r"^(?:`{3,}|~{3,})"), "fenced code block"),
    (re.compile(r"^#"), "heading other than ## or ###"),
    (re.compile(r"^>"), "block quote"),
    (re.compile(r"^[*+](?:\s|$)"), "bullet other than '- '"),
    (re.compile(r"^\d+[.)](?:\s|$)"), "numbered item other than '1. text'"),
    (re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$"), "horizontal rule or frontmatter"),
)


class ConversionError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.line = line


def _classify(line: str, number: int) -> Kind:
    if not line.strip():
        return "blank"
    if HEADING_RE.match(line):
        return "heading"
    if BULLET_RE.match(line):
        return "bullet"
    if NUMBERED_RE.match(line):
        return "numbered"
    if line.startswith("|"):
        return "table"
    for pattern, what in UNSUPPORTED:
        if pattern.match(line):
            msg = f"unsupported {what}: {line.strip()[:60]}"
            raise ConversionError(msg, number)
    return "paragraph"


def _tick_run(text: str, start: int) -> int:
    return len(text[start:]) - len(text[start:].lstrip("`"))


def _code_span_end(text: str, start: int) -> int:
    run = _tick_run(text, start)
    pos = start + run
    while (close := text.find("`" * run, pos)) != -1:
        if _tick_run(text, close) == run:
            return close + run
        pos = close + _tick_run(text, close)
    return -1


def _code(span: str) -> str:
    ticks = _tick_run(span, 0)
    content = span[ticks:-ticks]
    if len(content) > 1 and content[0] == content[-1] == " " and content.strip():
        content = content[1:-1]
    return f"<code>{html.escape(content, quote=False)}</code>"


def inline(text: str, number: int) -> str:
    out: list[str] = []
    plain = 0
    i = 0
    while i < len(text):
        rendered: str | None = None
        if text[i] == "`":
            end = _code_span_end(text, i)
            if end == -1:
                msg = f"unbalanced backticks: {text[i : i + 60]}"
                raise ConversionError(msg, number)
            rendered = _code(text[i:end])
        elif text[i] == "[" and (match := LINK_RE.match(text, i)):
            end = match.end()
            href = html.escape(match.group(2), quote=True)
            rendered = f'<a href="{href}">{inline(match.group(1), number)}</a>'
        if rendered is None:
            i += 1
            continue
        out.append(html.escape(text[plain:i], quote=False))
        out.append(rendered)
        i = plain = end
    out.append(html.escape(text[plain:], quote=False))
    return "".join(out)


def _heading(lines: Sequence[str], first: int) -> str:
    match = HEADING_RE.match(lines[0])
    if match is None:
        msg = "not a heading"
        raise ConversionError(msg, first)
    level = len(match.group(1))
    return f"<h{level}>{inline(match.group(2).strip(), first)}</h{level}>"


def _paragraph(lines: Sequence[str], first: int) -> str:
    body = " ".join(inline(line.strip(), first + k) for k, line in enumerate(lines))
    return f"<p>{body}</p>"


def _items(lines: Sequence[str], first: int, pattern: re.Pattern[str]) -> str:
    items: list[str] = []
    for k, line in enumerate(lines):
        match = pattern.match(line)
        if match is None:
            msg = "not a list item"
            raise ConversionError(msg, first + k)
        items.append(f"<li><p>{inline(match.groups()[-1].strip(), first + k)}</p></li>")
    return "".join(items)


def _bullets(lines: Sequence[str], first: int) -> str:
    return f"<ul>{_items(lines, first, BULLET_RE)}</ul>"


def _numbered(lines: Sequence[str], first: int) -> str:
    match = NUMBERED_RE.match(lines[0])
    start = int(match.group(1)) if match else 1
    attribute = f' start="{start}"' if start != 1 else ""
    return f"<ol{attribute}>{_items(lines, first, NUMBERED_RE)}</ol>"


def _cells(row: str, number: int, tag: str) -> str:
    cells = row.strip().removeprefix("|").removesuffix("|").split("|")
    return "".join(f"<{tag}><p>{inline(cell.strip(), number)}</p></{tag}>" for cell in cells)


def _table(lines: Sequence[str], first: int) -> str:
    if len(lines) < 2 or not TABLE_SEPARATOR_RE.match(lines[1]):
        msg = "table without a |---| separator after the header row"
        raise ConversionError(msg, first)
    head = f"<tr>{_cells(lines[0], first, 'th')}</tr>"
    body = "".join(
        f"<tr>{_cells(row, first + 2 + k, 'td')}</tr>" for k, row in enumerate(lines[2:])
    )
    return f"<table><thead>{head}</thead><tbody>{body}</tbody></table>"


RENDERERS: dict[Kind, Callable[[Sequence[str], int], str]] = {
    "heading": _heading,
    "paragraph": _paragraph,
    "bullet": _bullets,
    "numbered": _numbered,
    "table": _table,
}


def convert(markdown: str, *, toc: bool = False) -> str:
    lines = markdown.splitlines()
    kinds = [_classify(line, number) for number, line in enumerate(lines, 1)]
    blocks: list[str] = []
    toc_pending = toc
    i = 0
    while i < len(lines):
        kind = kinds[i]
        end = i + 1
        if kind not in ("blank", "heading"):
            while end < len(lines) and kinds[end] == kind:
                end += 1
        if kind == "heading" and toc_pending and lines[i].startswith("## "):
            blocks.append(TOC_MACRO)
            toc_pending = False
        if kind != "blank":
            blocks.append(RENDERERS[kind](lines[i:end], i + 1))
        i = end
    if toc_pending:
        msg = "--toc needs a ## heading to place the table of contents before"
        raise ConversionError(msg)
    return "\n".join(blocks) + "\n"


def count_source_links(markdown: str) -> int:
    return len(LINK_RE.findall(markdown))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("source", type=Path, metavar="IN_MD", help="Markdown file to convert")
    parser.add_argument("target", type=Path, metavar="OUT_HTML", help="HTML file to write")
    parser.add_argument(
        "--toc",
        action="store_true",
        help="insert a Table of Contents macro (levels 2-3) before the first ## heading",
    )
    args = parser.parse_args(argv)

    try:
        markdown = args.source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"{args.source}: cannot read: {err}", file=sys.stderr)
        return 2
    try:
        result = convert(markdown, toc=args.toc)
    except ConversionError as err:
        where = f"{args.source}:{err.line}" if err.line else str(args.source)
        print(f"{where}: {err.message}", file=sys.stderr)
        return 2
    try:
        args.target.write_text(result, encoding="utf-8")
    except OSError as err:
        print(f"{args.target}: cannot write: {err}", file=sys.stderr)
        return 2
    toc_note = ", toc: inserted" if args.toc else ""
    print(
        f"links in: {count_source_links(markdown)}, links out: {result.count('<a href=')}{toc_note}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
