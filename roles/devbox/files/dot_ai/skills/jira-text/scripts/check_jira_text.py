#!/usr/bin/env python3
"""Check text bound for Jira or Confluence for link and wording defects.

Prints one ``path:line: rule-id: message`` per finding. Exit status: 0 when
there are no findings, 1 when there are, 2 on a usage or read error.
Standard library only, so it runs on a bare interpreter.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DEFAULT_LABEL_PATTERNS: tuple[str, ...] = (
    r"\b[BDEIQR]\d{1,2}[a-z]?\b",
    r"\b[Dd]ecision \d+(?:\.\d+)+\b",
)

NOT_JIRA_PROJECTS = frozenset(
    {
        "AES",
        "CRC",
        "CVE",
        "ECMA",
        "GPT",
        "HTTP",
        "IEEE",
        "ISO",
        "PEP",
        "RFC",
        "RSA",
        "SHA",
        "TLS",
        "UTF",
    }
)

HTML_TAGS = frozenset(
    {
        "a",
        "b",
        "br",
        "code",
        "del",
        "details",
        "div",
        "em",
        "hr",
        "i",
        "img",
        "ins",
        "kbd",
        "li",
        "ol",
        "p",
        "pre",
        "s",
        "small",
        "span",
        "strong",
        "sub",
        "summary",
        "sup",
        "table",
        "td",
        "th",
        "tr",
        "u",
        "ul",
    }
)

SPEC_RULE_RE = re.compile(r"(?<![\w-])(?:[A-Z]+-)?BR-\d+\b")
JIRA_KEY_RE = re.compile(r"(?<![\w-])([A-Z][A-Z0-9]+)-\d+\b")
BARE_URL_RE = re.compile(r"<?https?://[^\s<>\])]+>?")
PLACEHOLDER_RE = re.compile(r"(?<![\w<])<([A-Za-z][\w-]*)>")
API_PATH_RE = re.compile(r"(?<![\w/.~-])/(?:v1|v2|v3|admin)(?![\w-])(?:/[^\s,;)\]]*)?")
LITERAL_RE = re.compile(r"\b(true|false|null)\b")
VALUE_BEFORE_RE = re.compile(
    r"(?:[:=]\s*"
    r"|\b(?:set|sets|setting|default|defaults|defaulted|change|changes|changed|reset|resets)"
    r"\s+(?:\w+\s+)?to\s+"
    r"|\b(?:returns?|sends?|equals?|becomes?)\s+)$",
    re.IGNORECASE,
)
ALONE_BEFORE_RE = re.compile(r"(?:^\s*(?:[-*+]|\d+\.)?\s*|\|\s*|\(\s*|[\"'])$")
ALONE_AFTER_RE = re.compile(r"^\s*(?:$|\||\)|[\"'])")
ENTITY_RE = re.compile(r"&(?:lt|gt);")
ANY_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[A-Za-z]+);")
QUARTER_RE = re.compile(r"Q[1-4]$")
YEAR_AFTER_RE = re.compile(r"^\s+(?:20)?\d{2}\b")
SECOND_PERSON_RE = re.compile(r"\b(?:you|your|yours)\b", re.IGNORECASE)

FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+\S")
MARKER_RE = re.compile(r"^\s*(?:<!--|%%)\s*jira-text:\s*(on|off)\s*(?:-->|%%)\s*$", re.IGNORECASE)
COMMENT_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(?:comment on|jira comment)\b", re.IGNORECASE)
DESCRIPTION_RE = re.compile(r"^\s*description:\s*$", re.IGNORECASE)
TRAILER_RE = re.compile(r"^\s*(?:open items|readiness)\s*:?\s*$", re.IGNORECASE)
VAULT_PARAGRAPH_RE = re.compile(r"^\s*(?:revised\b|parent:|before posting\b)", re.IGNORECASE)
H1_RE = re.compile(r"^\s{0,3}#\s")

PIN_LINE_RE = re.compile(r"\bpinned\b|^\s*pins?:", re.IGNORECASE)
SHA_TOKEN_RE = re.compile(r"`([0-9a-f]{7,40})`")
BLOB_RE = re.compile(r"^https?://[^/\s]+/(?:\S+?/-/blob|[^/\s]+/[^/\s]+/blob)/([^/\s#?]+)")
FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
SHORT_SHA_RE = re.compile(r"(?=[0-9a-f]*\d)[0-9a-f]{7,39}")
BROWSE_RE_TEMPLATE = r"/browse/{key}(?!\d)"
UNREADABLE_WORDS = frozenset({"here", "link", "this", "this link", "click here"})


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


@dataclass(frozen=True)
class Link:
    text_start: int
    text_end: int
    text: str
    url: str


@dataclass(frozen=True)
class LineView:
    """A line with code spans, URLs and wikilinks blanked, column positions kept."""

    text: str
    links: tuple[Link, ...]
    urls: tuple[str, ...]
    wikilinks: tuple[str, ...]

    def link_at(self, pos: int) -> Link | None:
        for link in self.links:
            if link.text_start <= pos < link.text_end:
                return link
        return None


def find_code_spans(line: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    i, n = 0, len(line)
    while i < n:
        if line[i] != "`":
            i += 1
            continue
        j = i
        while j < n and line[j] == "`":
            j += 1
        run = j - i
        k = j
        close = -1
        while k < n:
            k = line.find("`" * run, k)
            if k == -1:
                break
            end = k + run
            if end >= n or line[end] != "`":
                close = k
                break
            while k < n and line[k] == "`":
                k += 1
        if close == -1:
            i = j
            continue
        spans.append((i, close + run))
        i = close + run
    return spans


def _in_spans(pos: int, spans: Sequence[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in spans)


def _match_close(
    line: str, start: int, open_ch: str, close_ch: str, code: Sequence[tuple[int, int]]
) -> int:
    depth = 0
    for i in range(start, len(line)):
        if _in_spans(i, code):
            continue
        if line[i] == open_ch:
            depth += 1
        elif line[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i
    return -1


def build_view(line: str) -> LineView:
    code = find_code_spans(line)
    chars = list(line)
    for start, end in code:
        chars[start:end] = " " * (end - start)

    links: list[Link] = []
    urls: list[str] = []
    wikilinks: list[str] = []
    i = 0
    while i < len(line):
        if line[i] != "[" or _in_spans(i, code):
            i += 1
            continue
        if line.startswith("[[", i):
            end = line.find("]]", i + 2)
            if end != -1:
                wikilinks.append(line[i + 2 : end])
                chars[i : end + 2] = " " * (end + 2 - i)
                i = end + 2
                continue
        close = _match_close(line, i, "[", "]", code)
        if close == -1 or close + 1 >= len(line) or line[close + 1] != "(":
            i += 1
            continue
        paren_close = _match_close(line, close + 1, "(", ")", code)
        if paren_close == -1:
            i += 1
            continue
        target = line[close + 2 : paren_close].strip()
        url = target.split()[0].strip("<>") if target else ""
        links.append(Link(i + 1, close, line[i + 1 : close], url))
        urls.append(url)
        chars[close + 1 : paren_close + 1] = " " * (paren_close - close)
        i = paren_close + 1

    masked = "".join(chars)
    for match in BARE_URL_RE.finditer(masked):
        urls.append(match.group(0).strip("<>"))
        chars[match.start() : match.end()] = " " * (match.end() - match.start())
    return LineView("".join(chars), tuple(links), tuple(urls), tuple(wikilinks))


def fenced_lines(lines: Sequence[str], body_start: int) -> list[bool]:
    fenced = [False] * len(lines)
    fence: str | None = None
    for idx in range(body_start, len(lines)):
        match = FENCE_RE.match(lines[idx])
        if fence is None:
            if match:
                fence = match.group(1)
                fenced[idx] = True
            continue
        fenced[idx] = True
        if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
            fence = None
    return fenced


def frontmatter_end(lines: Sequence[str]) -> int:
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() in ("---", "..."):
                return idx + 1
    return 0


def _apply_markers(lines: Sequence[str], body_start: int, checked: list[bool]) -> bool:
    marker_at = {
        idx: m.group(1).lower()
        for idx in range(body_start, len(lines))
        if (m := MARKER_RE.match(lines[idx]))
    }
    if not marker_at:
        return False
    state = True
    for idx in range(body_start, len(lines)):
        if idx in marker_at:
            state = marker_at[idx] == "on"
        if idx in marker_at or not state:
            checked[idx] = False
    return True


def _comment_sections(
    lines: Sequence[str], body_start: int, fenced: Sequence[bool], checked: Sequence[bool]
) -> list[bool] | None:
    starts = [
        (idx, len(m.group(1)))
        for idx in range(body_start, len(lines))
        if not fenced[idx] and (m := COMMENT_HEADING_RE.match(lines[idx]))
    ]
    if not starts:
        return None
    keep = [False] * len(lines)
    for start, level in starts:
        for idx in range(start + 1, len(lines)):
            heading = HEADING_RE.match(lines[idx])
            if heading and not fenced[idx] and len(heading.group(1)) <= level:
                break
            keep[idx] = checked[idx]
    return keep


def _description_block(
    lines: Sequence[str], body_start: int, fenced: Sequence[bool], checked: Sequence[bool]
) -> list[bool] | None:
    start = next(
        (
            i
            for i in range(body_start, len(lines))
            if not fenced[i] and DESCRIPTION_RE.match(lines[i])
        ),
        None,
    )
    if start is None:
        return None
    keep = [False] * len(lines)
    for idx in range(start + 1, len(lines)):
        if not fenced[idx] and TRAILER_RE.match(lines[idx]):
            break
        keep[idx] = checked[idx]
    return keep


def _skip_vault_paragraphs(
    lines: Sequence[str], body_start: int, fenced: Sequence[bool], checked: list[bool]
) -> None:
    in_vault_paragraph = False
    for idx in range(body_start, len(lines)):
        line = lines[idx]
        if not line.strip():
            in_vault_paragraph = False
            continue
        if fenced[idx]:
            continue
        in_vault_paragraph = in_vault_paragraph or bool(VAULT_PARAGRAPH_RE.match(line))
        if in_vault_paragraph or H1_RE.match(line):
            checked[idx] = False


def jira_text_lines(
    lines: Sequence[str], body_start: int, fenced: Sequence[bool], *, whole: bool
) -> list[bool]:
    """Decide which lines are Jira-facing text; see SKILL.md, "Vault notes"."""
    checked = [idx >= body_start and not fenced[idx] for idx in range(len(lines))]
    if _apply_markers(lines, body_start, checked) or whole or body_start == 0:
        return checked
    for layout in (_comment_sections, _description_block):
        keep = layout(lines, body_start, fenced, checked)
        if keep is not None:
            return keep
    _skip_vault_paragraphs(lines, body_start, fenced, checked)
    return checked


def collect_pins(lines: Sequence[str], body_start: int, fenced: Sequence[bool]) -> list[str]:
    pins: list[str] = []
    for idx in range(body_start, len(lines)):
        if fenced[idx] or not PIN_LINE_RE.search(lines[idx]):
            continue
        pins.extend(
            sha for sha in SHA_TOKEN_RE.findall(lines[idx]) if any(c.isdigit() for c in sha)
        )
    return pins


def _mention_linked(kind: str, ident: str, link: Link | None) -> bool:
    if link is None:
        return False
    if kind == "spec":
        return "/wiki/" in link.url
    return re.search(BROWSE_RE_TEMPLATE.format(key=re.escape(ident)), link.url) is not None


def mentions(view: LineView) -> list[tuple[int, str, str]]:
    found: list[tuple[int, str, str]] = []
    text = view.text
    spec_spans: list[tuple[int, int]] = []
    for match in SPEC_RULE_RE.finditer(text):
        found.append((match.start(), "spec", match.group(0)))
        spec_spans.append((match.start(), match.end()))
    for match in JIRA_KEY_RE.finditer(text):
        if match.group(1) in NOT_JIRA_PROJECTS or _in_spans(match.start(), spec_spans):
            continue
        found.append((match.start(), "jira", match.group(0)))
    return sorted(found)


def quote_spans(text: str) -> list[tuple[int, int]]:
    """Spans of quoted words: someone else's text, which the author cannot reword."""
    spans: list[tuple[int, int]] = []
    straight = [i for i, ch in enumerate(text) if ch == '"']
    spans.extend((straight[i], straight[i + 1] + 1) for i in range(0, len(straight) - 1, 2))
    spans.extend((m.start(), m.end()) for m in re.finditer(r"“[^”]*”", text))
    return spans


def blank_spans(text: str, spans: Iterable[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        chars[start:end] = " " * (end - start)
    return "".join(chars)


def check_mentions(view: LineView, emit: _Emit) -> None:
    for pos, kind, ident in mentions(view):
        link = view.link_at(pos)
        if _mention_linked(kind, ident, link):
            continue
        rule = "unlinked-spec-rule" if kind == "spec" else "unlinked-jira-key"
        target = (
            "the spec page section that holds it" if kind == "spec" else f"its /browse/{ident} page"
        )
        where = "sits in a link to somewhere else" if link else "is not linked"
        emit(rule, f"{ident} {where}. Link every mention to {target}")


def check_link_texts(view: LineView, emit: _Emit, *, allow_code_links: bool) -> None:
    for link in view.links:
        if not allow_code_links and find_code_spans(link.text):
            emit(
                "code-in-link-text",
                f"link text [{link.text}] holds inline code, and Jira drops such a link and "
                "keeps only the code. Put the code outside the link or drop the backticks "
                "inside the link text",
            )
        text = link.text.replace("`", "").strip()
        if (
            text.startswith(":")
            or re.fullmatch(r"[\d\W_]*", text)
            or text.lower() in UNREADABLE_WORDS
        ):
            emit(
                "unreadable-link-text",
                f"link text [{link.text}] says nothing. "
                "Name the target (file:lines, ticket, whose comment)",
            )


def check_urls(view: LineView, pins: Sequence[str], emit: _Emit) -> None:
    for url in view.urls:
        match = BLOB_RE.match(url)
        if not match:
            continue
        ref = match.group(1)
        if FULL_SHA_RE.fullmatch(ref):
            if pins and not any(ref.startswith(pin) for pin in pins):
                emit("pin-mismatch", f"blob link at {ref[:12]} matches no commit in the pin header")
        elif SHORT_SHA_RE.fullmatch(ref):
            emit("unpinned-blob", f"blob link uses short SHA {ref}. Use the full 40-character SHA")
        else:
            emit(
                "unpinned-blob",
                f"blob link points at {ref!r}, which moves. Pin it to a 40-character commit SHA",
            )


def check_code_like(view: LineView, emit: _Emit) -> None:
    text = view.text
    for match in PLACEHOLDER_RE.finditer(text):
        if match.group(1).lower() not in HTML_TAGS:
            emit(
                "bare-placeholder",
                f"{match.group(0)} outside backticks. Write it as `{match.group(0)}`",
            )
    for match in API_PATH_RE.finditer(text):
        emit("bare-api-path", f"path {match.group(0)} outside backticks")
    for match in LITERAL_RE.finditer(text):
        before, after = text[: match.start()], text[match.end() :]
        if VALUE_BEFORE_RE.search(before) or (
            ALONE_BEFORE_RE.search(before) and ALONE_AFTER_RE.match(after)
        ):
            emit("bare-literal", f"value {match.group(0)} outside backticks")


def check_prose(
    view: LineView, raw: str, label_res: Sequence[re.Pattern[str]], emit: _Emit
) -> None:
    unquoted = blank_spans(view.text, quote_spans(view.text))
    if ";" in ANY_ENTITY_RE.sub(lambda m: " " * len(m.group(0)), unquoted):
        emit("semicolon", "semicolon joins clauses. Split into sentences or use a list")
    labels: list[str] = []
    for pattern in label_res:
        for match in pattern.finditer(unquoted):
            label = match.group(0)
            if QUARTER_RE.fullmatch(label) and YEAR_AFTER_RE.match(unquoted[match.end() :]):
                continue
            if label not in labels:
                labels.append(label)
    for label in labels:
        emit(
            "internal-label",
            f"internal label {label} means nothing outside the session. Name the thing instead",
        )
    url_free = raw
    for url in view.urls:
        url_free = url_free.replace(url, " ")
    for match in ENTITY_RE.finditer(url_free):
        emit(
            "html-entity",
            f"{match.group(0)} shows literally in Jira. Write the literal < or >",
        )
    for target in view.wikilinks:
        emit(
            "wikilink",
            f"[[{target}]] is a vault link and does not render in Jira. Use a URL link or drop it",
        )


def check_second_person(view: LineView, emit: _Emit) -> None:
    unquoted = blank_spans(view.text, quote_spans(view.text))
    for match in SECOND_PERSON_RE.finditer(unquoted):
        emit(
            "second-person",
            f'"{match.group(0)}" addresses one reader, but a document has many. '
            "Name the person or the group instead",
        )


class _Emit:
    def __init__(self, path: str, findings: list[Finding]) -> None:
        self.path = path
        self.findings = findings
        self.line = 0

    def __call__(self, rule: str, message: str) -> None:
        self.findings.append(Finding(self.path, self.line, rule, message))


def check_text(
    path: str,
    content: str,
    *,
    whole: bool = False,
    label_patterns: Iterable[str] = DEFAULT_LABEL_PATTERNS,
    allow_code_links: bool = False,
    document: bool = False,
) -> list[Finding]:
    lines = content.splitlines()
    body_start = frontmatter_end(lines)
    fenced = fenced_lines(lines, body_start)
    checked = jira_text_lines(lines, body_start, fenced, whole=whole)
    pins = collect_pins(lines, body_start, fenced)
    label_res = [re.compile(p) for p in label_patterns]

    findings: list[Finding] = []
    emit = _Emit(path, findings)
    for idx, line in enumerate(lines):
        if not checked[idx]:
            continue
        emit.line = idx + 1
        view = build_view(line)
        check_mentions(view, emit)
        check_link_texts(view, emit, allow_code_links=allow_code_links)
        check_urls(view, pins, emit)
        check_code_like(view, emit)
        check_prose(view, line, label_res, emit)
        if document:
            check_second_person(view, emit)
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("paths", nargs="+", type=Path, help="Markdown files to check")
    parser.add_argument(
        "--whole",
        action="store_true",
        help="check every line after the frontmatter, ignoring the vault-note layout "
        "(markers still apply)",
    )
    parser.add_argument(
        "--label-pattern",
        action="append",
        metavar="REGEX",
        help="internal-label regex; repeatable; replaces the defaults when given",
    )
    parser.add_argument(
        "--allow-code-links",
        action="store_true",
        help="allow inline code in link text (PR/MR descriptions not pasted into Jira)",
    )
    parser.add_argument(
        "--document",
        action="store_true",
        help="text published as a document: flag second-person words",
    )
    args = parser.parse_args(argv)

    patterns = args.label_pattern or list(DEFAULT_LABEL_PATTERNS)
    try:
        for pattern in patterns:
            re.compile(pattern)
    except re.error as err:
        print(f"invalid --label-pattern: {err}", file=sys.stderr)
        return 2

    total = 0
    for path in args.paths:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as err:
            print(f"{path}: cannot read: {err}", file=sys.stderr)
            return 2
        findings = check_text(
            str(path),
            content,
            whole=args.whole,
            label_patterns=patterns,
            allow_code_links=args.allow_code_links,
            document=args.document,
        )
        for finding in findings:
            print(finding.render())
            total += 1
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
