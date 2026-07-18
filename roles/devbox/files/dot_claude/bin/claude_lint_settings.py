#!/usr/bin/env python3
"""Diagnose mutually-exclusive rules in Claude Code settings files.

Claude Code merges permissions across three layers, low -> high precedence:

    ~/.claude/settings.json            (user)
      -> <project>/.claude/settings.json        (project)
        -> <project>/.claude/settings.local.json  (local)

Across those layers `deny` always beats `allow`. That makes it easy to add an
`allow` rule that silently never takes effect because a broader `deny` -- often
in the user layer -- covers it. This linter loads all three layers, computes the
effective ruleset, and reports the self-cancelling cases. It never writes: which
rule is "right" is a human decision.

Checks (report-only):
  * dead-allow          allow rule covered by a broader deny (deny wins)
  * allow-deny-conflict identical rule present in both allow and deny
  * syntax-variant      same base in both `X:*` and `X *` forms (matches differ)
  * duplicate           identical rule listed twice in one file's allow/deny
  * unparseable         settings file is not valid JSON
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env

SETTINGS_FILES: Final[tuple[str, ...]] = ("settings.json", "settings.local.json")
CLAUDE_DIR: Final[str] = ".claude"
RULE_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$")

USAGE: Final[str] = (
    "Usage: claude_lint_settings.py [--all] [--json] [--quiet]\n"
    "  Report mutually-exclusive rules in Claude Code settings files.\n"
    "\n"
    "Options:\n"
    "  --all    Scan every project under $AION_AUTOPOIESEON (default: current project)\n"
    "  --json   Emit findings as JSON instead of a human report\n"
    "  --quiet  Print nothing; communicate only via exit code\n"
    "\n"
    "Exit code: 0 when clean, 1 when any finding is reported, 2 on usage error.\n"
)


@dataclass
class ParsedArgs:
    scan_all: bool = False
    as_json: bool = False
    quiet: bool = False
    show_usage: bool = False


@dataclass(frozen=True)
class ParseFailure:
    message: str


def parse_args(argv: list[str]) -> ParsedArgs | ParseFailure:
    args = ParsedArgs()
    for arg in argv:
        if arg == "--all":
            args.scan_all = True
        elif arg == "--json":
            args.as_json = True
        elif arg == "--quiet":
            args.quiet = True
        elif arg in ("-h", "--help"):
            args.show_usage = True
        else:
            return ParseFailure(f"Unknown option: {arg}")
    return args


@dataclass(frozen=True)
class Rule:
    """A single permission entry, tagged with where it came from."""

    tool: str
    inner: str | None  # None => bare tool (e.g. "Read"), matches everything
    raw: str
    layer: str  # user | project | local
    verb: str  # allow | deny


@dataclass(frozen=True)
class Finding:
    kind: str
    detail: str

    def to_json(self) -> dict[str, str]:
        return {"kind": self.kind, "detail": self.detail}


@dataclass
class ProjectReport:
    label: str
    findings: list[Finding] = field(default_factory=list)


# --- parsing -----------------------------------------------------------------


def split_rule(raw: str) -> tuple[str, str | None]:
    """Split "Tool(inner)" into (tool, inner); bare "Tool" -> (tool, None)."""
    match = RULE_RE.match(raw.strip())
    if match:
        return match.group(1), match.group(2)
    return raw.strip(), None


def deny_prefix(inner: str | None) -> str | None:
    """Literal command prefix a trailing-wildcard deny rule matches, else None.

    Claude Code only treats `:*` / ` *` as a wildcard at the *end* of a pattern;
    an interior `*` or `:` is literal. To avoid false "dead-allow" claims this
    linter reasons about coverage only for clean trailing-wildcard prefixes:

      * ``Bash(git push *)`` / ``Bash(git reset:*)`` -> prefix "git push" / "git reset"
      * ``Bash(git push * :*)`` -> None (interior ``*`` -- unsafe to reason about)
      * ``Bash(git status)``    -> None (exact rule -- handled as a conflict)
      * bare tool ``Bash``      -> "" (matches every command for that tool)
    """
    if inner is None:
        return ""
    if inner.endswith(":*"):
        prefix = inner[:-2]
    elif inner.endswith("*"):
        prefix = inner[:-1].rstrip(" ")
    else:
        return None
    return None if "*" in prefix else prefix


def allow_stem(inner: str | None) -> str:
    """Literal leading portion of an allow rule, up to its first wildcard."""
    if inner is None:
        return ""
    return inner.split("*", 1)[0]


def wildcard_base(inner: str | None) -> str | None:
    """Return the command stem of a wildcard rule, or None if not wildcarded."""
    if inner is None:
        return None
    if inner.endswith(":*"):
        return inner[:-2].rstrip()
    if inner.endswith(" *"):
        return inner[:-2].rstrip()
    return None


def deny_covers_allow(deny: Rule, allow: Rule) -> bool:
    """True when the deny rule provably subsumes the allow rule (same tool).

    Conservative by design: only a clean trailing-wildcard deny prefix that ends
    at a word boundary inside the allow rule counts, so a broad allow that a deny
    only partially restricts is *not* reported as dead.
    """
    if deny.tool != allow.tool:
        return False
    prefix = deny_prefix(deny.inner)
    if prefix is None:
        return False
    if prefix == "":
        return True
    stem = allow_stem(allow.inner)
    if not stem.startswith(prefix):
        return False
    rest = stem[len(prefix) :]
    return rest == "" or rest[0] in (" ", ":")


# --- layer loading -----------------------------------------------------------


@dataclass(frozen=True)
class LoadedLayer:
    layer: str
    path: Path
    rules: list[Rule]
    parse_error: str | None
    dup_findings: list[Finding]


def _extract_rules(data: dict[str, object], layer: str) -> tuple[list[Rule], list[Finding]]:
    perms = data.get("permissions")
    if not isinstance(perms, dict):
        return [], []
    rules: list[Rule] = []
    dups: list[Finding] = []
    for verb in ("allow", "deny"):
        raw_list = perms.get(verb)
        if not isinstance(raw_list, list):
            continue
        seen: set[str] = set()
        for item in raw_list:
            if not isinstance(item, str):
                continue
            if item in seen:
                dups.append(
                    Finding(
                        "duplicate",
                        f"{layer}/{verb}: {item!r} listed more than once",
                    )
                )
                continue
            seen.add(item)
            tool, inner = split_rule(item)
            rules.append(Rule(tool=tool, inner=inner, raw=item, layer=layer, verb=verb))
    return rules, dups


def load_layer(path: Path, layer: str) -> LoadedLayer:
    if not path.is_file():
        return LoadedLayer(layer, path, [], None, [])
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except (ValueError, OSError) as exc:
        return LoadedLayer(layer, path, [], str(exc), [])
    if not isinstance(data, dict):
        return LoadedLayer(layer, path, [], "top-level JSON is not an object", [])
    rules, dups = _extract_rules(data, layer)
    return LoadedLayer(layer, path, rules, None, dups)


# --- analysis ----------------------------------------------------------------


def analyse(layers: list[LoadedLayer]) -> list[Finding]:
    findings: list[Finding] = []

    for layer in layers:
        if layer.parse_error is not None:
            findings.append(
                Finding("unparseable", f"{layer.layer}: {layer.path} -- {layer.parse_error}")
            )
        findings.extend(layer.dup_findings)

    rules = [r for layer in layers for r in layer.rules]
    allows = [r for r in rules if r.verb == "allow"]
    denies = [r for r in rules if r.verb == "deny"]

    findings.extend(_conflict_findings(allows, denies))
    findings.extend(_syntax_findings(rules))
    return findings


def _conflict_findings(allows: list[Rule], denies: list[Rule]) -> list[Finding]:
    findings: list[Finding] = []
    deny_index: dict[tuple[str, str | None], Rule] = {(d.tool, d.inner): d for d in denies}
    for allow in allows:
        exact = deny_index.get((allow.tool, allow.inner))
        if exact is not None:
            findings.append(
                Finding(
                    "allow-deny-conflict",
                    f"{allow.raw} allowed in {allow.layer} but denied in {exact.layer} "
                    f"(deny wins -- allow is dead)",
                )
            )
            continue
        for deny in denies:
            if deny.raw == allow.raw:
                continue
            if deny_covers_allow(deny, allow):
                findings.append(
                    Finding(
                        "dead-allow",
                        f"{allow.raw} ({allow.layer}) never takes effect -- covered by "
                        f"deny {deny.raw} ({deny.layer})",
                    )
                )
                break
    return findings


def _syntax_findings(rules: list[Rule]) -> list[Finding]:
    forms: dict[tuple[str, str], set[str]] = {}
    raws: dict[tuple[str, str], set[str]] = {}
    for rule in rules:
        base = wildcard_base(rule.inner)
        if base is None or rule.inner is None:
            continue
        form = ":*" if rule.inner.endswith(":*") else " *"
        key = (rule.tool, base)
        forms.setdefault(key, set()).add(form)
        raws.setdefault(key, set()).add(rule.raw)
    findings: list[Finding] = []
    for key, seen_forms in sorted(forms.items()):
        if len(seen_forms) > 1:
            variants = ", ".join(sorted(raws[key]))
            findings.append(
                Finding(
                    "syntax-variant",
                    f"{key[0]}({key[1]} ...) mixes ':*' and ' *' forms: {variants} "
                    "-- they match differently",
                )
            )
    return findings


# --- scope resolution --------------------------------------------------------


def user_layer_path() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or str(Path.home())
    return Path(home) / CLAUDE_DIR / "settings.json"


def find_project_claude_dir(start: Path) -> Path | None:
    current = start.resolve() if start.exists() else start
    if current.is_file():
        current = current.parent
    while True:
        candidate = current / CLAUDE_DIR
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def _project_layers(claude_dir: Path, *, include_user: bool) -> list[LoadedLayer]:
    layers: list[LoadedLayer] = []
    if include_user:
        user_path = user_layer_path()
        # Skip the user layer when the project *is* ~/.claude to avoid double load.
        if user_path.parent.resolve() != claude_dir.resolve():
            layers.append(load_layer(user_path, "user"))
    layers.append(load_layer(claude_dir / "settings.json", "project"))
    layers.append(load_layer(claude_dir / "settings.local.json", "local"))
    return layers


def _workspace_root() -> Path:
    root = os.environ.get("AION_AUTOPOIESEON") or os.environ.get("PROJECTS_DIR")
    if root:
        return Path(root)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / "Projects"


def discover_claude_dirs(workspace: Path) -> list[Path]:
    return [
        candidate
        for entry in sorted(workspace.glob("*/"))
        for candidate in (entry / CLAUDE_DIR, entry / "base" / CLAUDE_DIR)
        if candidate.is_dir()
    ]


def _project_label(claude_dir: Path, workspace: Path) -> str:
    try:
        rel = claude_dir.relative_to(workspace)
        return str(rel.parent) if rel.parent != Path() else str(rel)
    except ValueError:
        return str(claude_dir.parent)


# --- orchestration -----------------------------------------------------------


def run(argv: list[str], cwd: Path) -> tuple[int, list[ProjectReport] | str]:
    parsed = parse_args(argv)
    if isinstance(parsed, ParseFailure):
        return 2, parsed.message
    if parsed.show_usage:
        return 0, USAGE

    reports: list[ProjectReport] = []
    if parsed.scan_all:
        workspace = _workspace_root()
        claude_dirs = discover_claude_dirs(workspace)
        if not claude_dirs:
            return 2, f"No projects with .claude/ found under {workspace}"
        for claude_dir in claude_dirs:
            layers = _project_layers(claude_dir, include_user=True)
            reports.append(ProjectReport(_project_label(claude_dir, workspace), analyse(layers)))
    else:
        claude_dir = find_project_claude_dir(cwd)
        if claude_dir is None:
            return 2, "No .claude/ directory found from the current path"
        layers = _project_layers(claude_dir, include_user=True)
        reports.append(ProjectReport(str(claude_dir.parent), analyse(layers)))

    has_findings = any(r.findings for r in reports)
    return (1 if has_findings else 0), reports


def format_report(reports: list[ProjectReport]) -> str:
    dirty = [r for r in reports if r.findings]
    if not dirty:
        scanned = len(reports)
        suffix = "project" if scanned == 1 else "projects"
        return f"No conflicting settings rules found ({scanned} {suffix} scanned).\n"
    lines: list[str] = []
    total = 0
    for report in dirty:
        lines.append(f"### {report.label}")
        for finding in report.findings:
            total += 1
            lines.append(f"    [{finding.kind}] {finding.detail}")
        lines.append("")
    plural = "finding" if total == 1 else "findings"
    lines.append(f"{total} {plural} across {len(dirty)} project(s).")
    return "\n".join(lines) + "\n"


def format_json(reports: list[ProjectReport]) -> str:
    payload = [{"project": r.label, "findings": [f.to_json() for f in r.findings]} for r in reports]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    env.setup()
    args = argv if argv is not None else sys.argv[1:]
    parsed = parse_args(args)
    exit_code, payload = run(args, Path.cwd())

    if isinstance(payload, str):
        stream = sys.stdout if exit_code == 0 else sys.stderr
        stream.write(payload if payload.endswith("\n") else payload + "\n")
        if exit_code == 2 and not (isinstance(parsed, ParsedArgs) and parsed.show_usage):
            sys.stderr.write(USAGE)
        return exit_code

    if isinstance(parsed, ParsedArgs) and parsed.quiet:
        return exit_code
    rendered = (
        format_json(payload)
        if isinstance(parsed, ParsedArgs) and parsed.as_json
        else format_report(payload)
    )
    sys.stdout.write(rendered)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
