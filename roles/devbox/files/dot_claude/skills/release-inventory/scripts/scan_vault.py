#!/usr/bin/env python3
"""Index Jira-keyed notes in an Obsidian vault so a release sync can diff against Jira.

Emits JSON on stdout. Never writes to the vault.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

KEY_RE = re.compile(r"^(?P<key>[A-Z][A-Z0-9]+-\d+)(?P<suffix>$|[^0-9].*)")
RELEASE_DIR_RE = re.compile(r"^Release-(?P<version>\d+\.\d+)$")

META_PATTERNS: dict[str, re.Pattern[str]] = {
    "type": re.compile(r"Type:\s*\*{0,2}([^.*\n]+?)\*{0,2}\s*\."),
    "jira_status": re.compile(r"Jira status:\s*\*{0,2}([^.*\n]+?)\*{0,2}\s*\."),
    "priority": re.compile(r"Priority:\s*\*{0,2}([^.*\n]+?)\*{0,2}\s*\."),
    "sprint": re.compile(r"Sprint:\s*\*{0,2}(v\d+\.\d+\.\d+)\*{0,2}"),
    "fix_version": re.compile(r"fixVersion:\s*\*{0,2}(Version \d+\.\d+\.\d+)\*{0,2}"),
}

FRONTMATTER_LIST_ITEM = re.compile(r"^\s*-\s+(.*)$")
FRONTMATTER_PAIR = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*):\s*(?P<value>.*)$")


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the small subset of YAML actually used in these notes.

    Avoids a PyYAML dependency: the skill must run on a bare interpreter.
    """
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}

    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw in lines[1:end]:
        item = FRONTMATTER_LIST_ITEM.match(raw)
        if item and current_key is not None:
            value = item.group(1).strip().strip('"').strip("'")
            existing = data.get(current_key)
            if isinstance(existing, list):
                existing.append(value)
            else:
                data[current_key] = [value]
            continue
        pair = FRONTMATTER_PAIR.match(raw)
        if pair:
            key: str = pair.group("key")
            current_key = key
            value = pair.group("value").strip().strip('"').strip("'")
            data[key] = value or []
    return data


def parse_meta_block(text: str) -> dict[str, str]:
    """Extract the ticket fields the notes record in prose, as *hints* only.

    Jira is authoritative; these values exist so the caller can diff cheaply
    without reading every note into context.
    """
    found: dict[str, str] = {}
    head = text[:4000]
    for field, pattern in META_PATTERNS.items():
        match = pattern.search(head)
        if match:
            found[field] = match.group(1).strip()
    return found


def iter_markdown(vault: Path) -> Iterator[Path]:
    for path in vault.rglob("*.md"):
        if any(part.startswith(".") for part in path.relative_to(vault).parts):
            continue
        yield path


def classify(path: Path) -> tuple[str, bool] | None:
    """Return (jira key, is_canonical) — canonical means the stem is exactly the key."""
    match = KEY_RE.match(path.stem)
    if not match:
        return None
    return match.group("key"), match.group("suffix") == ""


def scan_releases(vault: Path) -> dict[str, Any]:
    releases: dict[str, Any] = {}
    root = vault / "Projects" / "Releases"
    if not root.is_dir():
        return releases
    for entry in sorted(root.iterdir()):
        match = RELEASE_DIR_RE.match(entry.name)
        if not entry.is_dir() or not match:
            continue
        version = match.group("version")
        note = entry / f"Release {version}.md"
        buckets = {
            bucket: sorted(str(p.relative_to(vault)) for p in (entry / bucket).glob("*.md"))
            for bucket in ("Epics", "Tasks", "Bugs")
            if (entry / bucket).is_dir()
        }
        releases[version] = {
            "dir": str(entry.relative_to(vault)),
            "note": str(note.relative_to(vault)) if note.is_file() else None,
            "buckets": buckets,
            "missing_buckets": [
                bucket for bucket in ("Epics", "Tasks", "Bugs") if not (entry / bucket).is_dir()
            ],
        }
    return releases


def build_index(vault: Path, projects: frozenset[str]) -> dict[str, Any]:
    notes: dict[str, dict[str, Any]] = {}
    problems: list[dict[str, str]] = []

    for path in iter_markdown(vault):
        classified = classify(path)
        if classified is None:
            continue
        key, is_canonical = classified
        if projects and key.split("-", 1)[0] not in projects:
            continue
        rel = str(path.relative_to(vault))
        entry = notes.setdefault(key, {"canonical": None, "duplicates": [], "companions": []})
        if not is_canonical:
            entry["companions"].append(rel)
            continue
        if entry["canonical"] is None:
            entry["canonical"] = rel
        else:
            entry["duplicates"].append(rel)
            problems.append(
                {
                    "kind": "duplicate-key",
                    "key": key,
                    "detail": f"{entry['canonical']} and {rel} both claim {key}; "
                    "Obsidian [[wikilinks]] to this key are ambiguous",
                }
            )

    for key, entry in notes.items():
        canonical = entry["canonical"]
        if canonical is None:
            entry["frontmatter"] = {}
            entry["meta"] = {}
            problems.append(
                {
                    "kind": "companion-without-canonical",
                    "key": key,
                    "detail": f"companions exist ({', '.join(entry['companions'])}) "
                    f"but no note named exactly {key}.md",
                }
            )
            continue
        text = (vault / canonical).read_text(encoding="utf-8", errors="replace")
        entry["frontmatter"] = parse_frontmatter(text)
        entry["meta"] = parse_meta_block(text)
        entry["companions"].sort()
        entry["duplicates"].sort()

    return {
        "vault": str(vault),
        "notes": dict(sorted(notes.items())),
        "releases": scan_releases(vault),
        "problems": problems,
    }


def default_vault() -> Path:
    """Locate the vault under the active profile's workspace root.

    The vault itself is a work-profile artefact; this only resolves where the
    workspace root lives, since that differs per profile (`~/Work` on work,
    `~/Projects` on personal). Off the work profile the resolved path will not
    exist and `main` reports it — that is the intended outcome, not a fallback to
    somebody else's workspace. PROJECTS_DIR is the transitional alias of
    AION_AUTOPOIESEON.
    """
    workspace = os.environ.get("AION_AUTOPOIESEON") or os.environ.get("PROJECTS_DIR")
    if workspace:
        return Path(workspace).expanduser() / "oiai-work-notes"
    return Path.home() / "Work" / "oiai-work-notes"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vault",
        type=Path,
        default=default_vault(),
        help=(
            "Vault root (default: $AION_AUTOPOIESEON/oiai-work-notes, "
            "which exists on the work profile only)"
        ),
    )
    parser.add_argument(
        "--keys",
        nargs="*",
        default=None,
        help="Restrict the notes map to these Jira keys",
    )
    parser.add_argument(
        "--projects",
        default="OICM,MLOPS,OISP,INFRA",
        help="Comma-separated Jira project keys to index; empty string disables the "
        "filter (default: OICM,MLOPS,OISP,INFRA)",
    )
    args = parser.parse_args(argv)

    vault: Path = args.vault.expanduser().resolve()
    if not vault.is_dir():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 2

    projects = frozenset(p.strip() for p in args.projects.split(",") if p.strip())
    index = build_index(vault, projects)
    if args.keys:
        wanted = set(args.keys)
        index["notes"] = {k: v for k, v in index["notes"].items() if k in wanted}
        index["missing"] = sorted(wanted - set(index["notes"]))

    json.dump(index, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
