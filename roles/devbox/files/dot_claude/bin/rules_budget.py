#!/usr/bin/env python3
"""Rules-budget instrumentation for the Claude Code config tree (RI1).

Counts rule-like statements across ~/.claude source (skills, agents, commands,
UAP) so drift versus the ~150-200 concurrent-instruction budget reported for
frontier models is visible before every downstream tuning decision.

## What counts as a rule (heuristic, resolves Q-RI1-1 = D)

A rule is any line matching EITHER of the two branches below; matches are
deduplicated by (path, line-number):

  (A) Imperative match. A line whose first non-whitespace token (after an
      optional bullet marker or bold wrapper) is one of the imperative /
      modal keywords in KEYWORDS_HARD or KEYWORDS_SOFT. Also fires when
      such a keyword appears in **bold** at the start of the line (e.g.
      `- **NEVER** X`).

  (C) Section-header match. A markdown list item (bullet or numbered)
      nested under an H1-H6 heading whose title matches SECTION_HEADERS_RE
      (Rules / Instructions / Protocol / Policy / Convention / Anti-patterns
      / Do / Don't / Never / Always / Requirements / Discipline / Standards /
      Guidelines / Checklist).

## What is deliberately excluded

  - Fenced code blocks (```lang ... ```).
  - Frontmatter blocks (--- ... ---).
  - Blockquote text (> ...) — treated as citation, not authored rule.
  - Table rows (| ... |).
  - Prose paragraphs outside of bullets that do not open with a keyword.
    Modal-in-the-middle prose is intentionally under-counted rather than
    over-counted; the alternative (option B in the deep-dive) produces too
    many false positives on descriptive text.

## Weighting (resolves Q-RI1-2 = D)

Three numbers are reported per artefact and in aggregate:

  - flat        unweighted rule count (baseline).
  - strength    hard rules (MUST/NEVER/...) x2, soft rules (SHOULD/PREFER/...) x1.
  - scope_agg   at the report level: always-on artefacts contribute their flat
                count x3, trigger-loaded contribute x1.

## Classification (Q-RI1-3 = as listed)

  - Skills: SKILL.md files under skills/. always-on when frontmatter has
    `alwaysApply: true`; trigger-loaded otherwise.
  - Agents: agents/*.md. Trigger-loaded (spawned on demand).
  - Commands: commands/*.md. Trigger-loaded (invoked on demand).
  - UAP: USER_AUTHORITY_PROTOCOL.md at the config root. Always-on.

## Known blind spots

  - Rules embedded in prose paragraphs without a keyword-opening line are
    missed by design.
  - Bullets outside a rule-shaped section that lack a keyword prefix are
    missed by design.
  - Numbered list items nested inside other lists via indentation are
    counted normally; deeper structural nesting is not modelled.
  - Rule strength inference is lexical, not semantic: `SHOULD NEVER` is
    classified hard because NEVER is present.

## Non-goals (v1)

  - Adherence measurement — that belongs to `make eval-skills`.
  - Automatic trimming or removal suggestions.

## Invocation

  make rules-budget                         # markdown table to stdout
  make rules-budget ARGS='--json'           # JSON to stdout
  make rules-budget ARGS='--baseline PATH'  # write markdown to PATH

  # Direct, without make:
  uv run --project roles/devbox/files/dot_claude/bin \\
    python roles/devbox/files/dot_claude/bin/rules_budget.py [--json|--baseline PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Concurrent-instruction budget reported for frontier models
# (research_pattern_language.md [45]: Anthropic CLAUDE.md guidance).
BUDGET_LOW = 150
BUDGET_HIGH = 200

# Weights per Q-RI1-2 = D.
WEIGHT_HARD = 2
WEIGHT_SOFT = 1
WEIGHT_ALWAYS_ON = 3
WEIGHT_TRIGGER_LOADED = 1

# Artefact roots relative to the config root (Q-RI1-3).
SKILLS_GLOB = "skills/*/SKILL.md"
AGENTS_GLOB = "agents/*.md"
COMMANDS_GLOB = "commands/*.md"
UAP_REL = "USER_AUTHORITY_PROTOCOL.md"

# ---------------------------------------------------------------------------
# Heuristic vocabulary
# ---------------------------------------------------------------------------

# Hard = categorical / normative. Soft = advisory.
KEYWORDS_HARD = frozenset(
    {
        "MUST",
        "MUST NOT",
        "SHALL",
        "SHALL NOT",
        "NEVER",
        "ALWAYS",
        "DO NOT",
        "DON'T",
        "REQUIRED",
        "FORBIDDEN",
        "MANDATORY",
    }
)
KEYWORDS_SOFT = frozenset(
    {
        "SHOULD",
        "SHOULD NOT",
        "PREFER",
        "AVOID",
        "USE",
        "DO",
        "TRY",
        "CONSIDER",
        "RECOMMEND",
        "RECOMMENDED",
    }
)
_ALL_KEYWORDS = KEYWORDS_HARD | KEYWORDS_SOFT

# Longest first so multi-word phrases (e.g. `MUST NOT`) match before their prefix.
_KEYWORD_PATTERN = "|".join(
    re.escape(kw) for kw in sorted(_ALL_KEYWORDS, key=len, reverse=True)
)

# Opening tokens allowed before the keyword: whitespace, list bullets,
# numbered markers, and bold wrappers.
_LINE_PREFIX = r"^[\s]*(?:[-*+]\s+|\d+[.)]\s+)?(?:\*\*)?"
_IMPERATIVE_RE = re.compile(
    rf"{_LINE_PREFIX}(?P<kw>{_KEYWORD_PATTERN})\b",
    re.IGNORECASE,
)

# Section headers that mark rule-shaped content. Match is case-insensitive
# and applied to the trimmed heading text (with punctuation stripped).
SECTION_HEADERS_RE = re.compile(
    r"\b("
    r"rules?|instructions?|protocols?|policies|policy|conventions?|"
    r"anti[-\s]?patterns?|do|don'?ts?|never|always|requirements?|"
    r"discipline|standards?|guidelines?|checklists?|constraints?|"
    r"stop conditions|core rules?|approval|triggers?"
    r")\b",
    re.IGNORECASE,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s?")
_FRONTMATTER_DELIM = "---"
_CODE_FENCE_RE = re.compile(r"^\s*(```|~~~)")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleHit:
    line_no: int
    kind: str  # "imperative" | "section-bullet"
    strength: str  # "hard" | "soft"
    text: str


@dataclass
class Artefact:
    path: Path  # absolute
    rel_path: str  # relative to config root
    kind: str  # "skill" | "agent" | "command" | "uap"
    always_on: bool
    hits: list[RuleHit] = field(default_factory=list)

    @property
    def flat(self) -> int:
        return len(self.hits)

    @property
    def hard(self) -> int:
        return sum(1 for h in self.hits if h.strength == "hard")

    @property
    def soft(self) -> int:
        return sum(1 for h in self.hits if h.strength == "soft")

    @property
    def strength_weighted(self) -> int:
        return self.hard * WEIGHT_HARD + self.soft * WEIGHT_SOFT


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def _read_frontmatter_alwaysapply(lines: list[str]) -> bool:
    """Return True when frontmatter declares `alwaysApply: true`."""
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        return False
    for line in lines[1:]:
        if line.strip() == _FRONTMATTER_DELIM:
            return False
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        if key.strip() == "alwaysApply" and value.strip().lower() == "true":
            return True
    return False


def _frontmatter_end(lines: list[str]) -> int:
    """Return the 0-based index of the line after the closing --- (0 if none)."""
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        return 0
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _FRONTMATTER_DELIM:
            return i + 1
    return 0


# ---------------------------------------------------------------------------
# Rule detection
# ---------------------------------------------------------------------------


def _line_strength_from_content(line: str) -> str:
    """Infer strength from the whole line — any hard keyword wins."""
    upper = line.upper()
    for kw in KEYWORDS_HARD:
        if re.search(rf"\b{re.escape(kw)}\b", upper):
            return "hard"
    return "soft"


def _is_rule_section(title: str) -> bool:
    stripped = title.strip().strip("#").strip()
    stripped = re.sub(r"[^\w'\s-]", " ", stripped)
    return bool(SECTION_HEADERS_RE.search(stripped))


def scan_lines(lines: list[str]) -> list[RuleHit]:
    """Scan a markdown file (post-frontmatter) and return deduplicated hits."""
    hits: dict[int, RuleHit] = {}
    in_code_block = False
    section_stack: list[bool] = []  # per-heading: True if rule-shaped

    for idx, raw in enumerate(lines):
        line_no = idx + 1  # 1-based for reporting

        if _CODE_FENCE_RE.match(raw):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        heading = _HEADING_RE.match(raw)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2)
            while len(section_stack) >= level:
                section_stack.pop()
            while len(section_stack) < level - 1:
                # Fill missing ancestor levels as "not rule-shaped".
                section_stack.append(False)
            section_stack.append(_is_rule_section(title))
            continue

        if _BLOCKQUOTE_RE.match(raw) or _TABLE_ROW_RE.match(raw):
            continue
        if not raw.strip():
            continue

        # Branch A: imperative keyword at the start of the line.
        imperative = _IMPERATIVE_RE.match(raw)
        if imperative:
            hits[line_no] = RuleHit(
                line_no=line_no,
                kind="imperative",
                strength=_line_strength_from_content(raw),
                text=raw.strip(),
            )
            continue

        # Branch C: any bullet under a rule-shaped section.
        if _LIST_ITEM_RE.match(raw) and any(section_stack):
            hits[line_no] = RuleHit(
                line_no=line_no,
                kind="section-bullet",
                strength=_line_strength_from_content(raw),
                text=raw.strip(),
            )

    return sorted(hits.values(), key=lambda h: h.line_no)


# ---------------------------------------------------------------------------
# Artefact discovery
# ---------------------------------------------------------------------------


def _make_artefact(path: Path, kind: str, root: Path) -> Artefact:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    always_on = kind == "uap" or (
        kind == "skill" and _read_frontmatter_alwaysapply(lines)
    )
    body_start = _frontmatter_end(lines)
    body = lines[body_start:]
    hits = scan_lines(body)
    # Re-anchor line numbers to the original file.
    hits = [
        RuleHit(
            line_no=h.line_no + body_start,
            kind=h.kind,
            strength=h.strength,
            text=h.text,
        )
        for h in hits
    ]
    rel = path.relative_to(root).as_posix()
    return Artefact(path=path, rel_path=rel, kind=kind, always_on=always_on, hits=hits)


def discover(root: Path) -> list[Artefact]:
    artefacts: list[Artefact] = []

    uap = root / UAP_REL
    if uap.is_file():
        artefacts.append(_make_artefact(uap, "uap", root))

    for pattern, kind in (
        (SKILLS_GLOB, "skill"),
        (AGENTS_GLOB, "agent"),
        (COMMANDS_GLOB, "command"),
    ):
        for path in sorted(root.glob(pattern)):
            artefacts.append(_make_artefact(path, kind, root))

    return artefacts


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


@dataclass
class BudgetReport:
    root: Path
    artefacts: list[Artefact]

    def _by_scope(self, *, always_on: bool) -> list[Artefact]:
        return [a for a in self.artefacts if a.always_on is always_on]

    @property
    def always_on(self) -> list[Artefact]:
        return self._by_scope(always_on=True)

    @property
    def triggered(self) -> list[Artefact]:
        return self._by_scope(always_on=False)

    @property
    def always_on_flat(self) -> int:
        return sum(a.flat for a in self.always_on)

    @property
    def always_on_hard(self) -> int:
        return sum(a.hard for a in self.always_on)

    @property
    def always_on_soft(self) -> int:
        return sum(a.soft for a in self.always_on)

    @property
    def always_on_strength(self) -> int:
        return sum(a.strength_weighted for a in self.always_on)

    @property
    def scope_aggregate(self) -> int:
        return (
            self.always_on_flat * WEIGHT_ALWAYS_ON
            + sum(a.flat for a in self.triggered) * WEIGHT_TRIGGER_LOADED
        )

    def over_budget(self) -> str:
        """Return 'under' | 'in-range' | 'over' vs the [150, 200] budget."""
        count = self.always_on_flat
        if count < BUDGET_LOW:
            return "under"
        if count > BUDGET_HIGH:
            return "over"
        return "in-range"

    def top_offenders(self, n: int = 10) -> list[Artefact]:
        return sorted(self.artefacts, key=lambda a: a.flat, reverse=True)[:n]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_markdown(report: BudgetReport) -> str:
    lines: list[str] = []
    lines.append("# Rules-Budget Report")
    lines.append("")
    lines.append(f"**Root:** `{report.root}`")
    lines.append(
        f"**Budget reference:** {BUDGET_LOW}-{BUDGET_HIGH} concurrent instructions"
    )
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append("| Scope | Artefacts | Flat | Hard | Soft | Strength-weighted |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append(
        f"| Always-on | {len(report.always_on)} | {report.always_on_flat} | "
        f"{report.always_on_hard} | {report.always_on_soft} | "
        f"{report.always_on_strength} |"
    )
    lines.append(
        f"| Trigger-loaded | {len(report.triggered)} | "
        f"{sum(a.flat for a in report.triggered)} | "
        f"{sum(a.hard for a in report.triggered)} | "
        f"{sum(a.soft for a in report.triggered)} | "
        f"{sum(a.strength_weighted for a in report.triggered)} |"
    )
    lines.append("")
    lines.append(f"**Scope-weighted aggregate:** {report.scope_aggregate}")
    lines.append("")
    verdict = report.over_budget()
    lines.append(
        f"**Always-on flat count:** {report.always_on_flat} "
        f"({verdict} the {BUDGET_LOW}-{BUDGET_HIGH} budget)"
    )
    lines.append("")
    lines.append("## Always-on artefacts")
    lines.append("")
    lines.append(_table(report.always_on))
    lines.append("")
    lines.append(f"## Top {min(10, len(report.artefacts))} offenders (any scope)")
    lines.append("")
    lines.append(_table(report.top_offenders(10)))
    lines.append("")
    lines.append("## All artefacts")
    lines.append("")
    lines.append(_table(sorted(report.artefacts, key=lambda a: a.rel_path)))
    lines.append("")
    return "\n".join(lines)


def _table(artefacts: list[Artefact]) -> str:
    if not artefacts:
        return "_(none)_"
    header = "| Artefact | Kind | Scope | Flat | Hard | Soft | Strength |"
    sep = "|---|---|---|---:|---:|---:|---:|"
    rows = [header, sep]
    for a in artefacts:
        scope = "always-on" if a.always_on else "trigger"
        rows.append(
            f"| `{a.rel_path}` | {a.kind} | {scope} | {a.flat} | "
            f"{a.hard} | {a.soft} | {a.strength_weighted} |"
        )
    return "\n".join(rows)


def render_json(report: BudgetReport) -> str:
    payload = {
        "root": str(report.root),
        "budget": {"low": BUDGET_LOW, "high": BUDGET_HIGH},
        "weights": {
            "hard": WEIGHT_HARD,
            "soft": WEIGHT_SOFT,
            "always_on": WEIGHT_ALWAYS_ON,
            "trigger_loaded": WEIGHT_TRIGGER_LOADED,
        },
        "aggregate": {
            "always_on_flat": report.always_on_flat,
            "always_on_hard": report.always_on_hard,
            "always_on_soft": report.always_on_soft,
            "always_on_strength": report.always_on_strength,
            "triggered_flat": sum(a.flat for a in report.triggered),
            "scope_aggregate": report.scope_aggregate,
            "verdict": report.over_budget(),
        },
        "artefacts": [
            {
                "path": a.rel_path,
                "kind": a.kind,
                "always_on": a.always_on,
                "flat": a.flat,
                "hard": a.hard,
                "soft": a.soft,
                "strength_weighted": a.strength_weighted,
                "hits": [asdict(h) for h in a.hits],
            }
            for a in sorted(report.artefacts, key=lambda a: a.rel_path)
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_root() -> Path:
    """Locate the config root, walking upward from this script's directory."""
    here = Path(__file__).resolve().parent
    # bin/ sits inside dot_claude/ (repo) or ~/.claude/ (deployed).
    return here.parent


def build_report(root: Path) -> BudgetReport:
    artefacts = discover(root)
    return BudgetReport(root=root, artefacts=artefacts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count rule-like statements across ~/.claude config."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_default_root(),
        help="Config root (default: parent of this script's directory).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Write markdown to PATH (overwrites); also prints summary to stdout.",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        return 2

    report = build_report(root)

    if args.json:
        print(render_json(report))
        return 0

    markdown = render_markdown(report)
    if args.baseline is not None:
        args.baseline.write_text(markdown, encoding="utf-8")
        print(
            f"baseline written to {args.baseline} "
            f"({report.always_on_flat} always-on rules, verdict: {report.over_budget()})"
        )
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
