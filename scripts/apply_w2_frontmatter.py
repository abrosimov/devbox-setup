#!/usr/bin/env python3
"""Apply W2 frontmatter fields (``problem:`` + ``related:``) in bulk.

Reads the data table at
``roles/devbox/files/dot_claude/future_projects/claude_tuning/w2_frontmatter_data.yaml``
and patches skill/agent frontmatter in place.

Idempotent: running twice on the same tree emits no changes on the second run.
Safe by default: refuses to overwrite existing ``problem:`` or ``related:``
values. Use ``--force`` to replace them.

Usage:
  scripts/apply_w2_frontmatter.py --dry-run     # show unified diff, no writes
  scripts/apply_w2_frontmatter.py               # apply changes
  scripts/apply_w2_frontmatter.py --skills      # skills only
  scripts/apply_w2_frontmatter.py --agents      # agents only
  scripts/apply_w2_frontmatter.py --force       # overwrite existing values
"""

from __future__ import annotations

import argparse
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_ROOT = REPO_ROOT / "roles" / "devbox" / "files" / "dot_claude"
DATA_TABLE = (
    CLAUDE_ROOT / "future_projects" / "claude_tuning" / "w2_frontmatter_data.yaml"
)


# ---------------------------------------------------------------------------
# Frontmatter patching
# ---------------------------------------------------------------------------


@dataclass
class Patch:
    kind: str  # "skill" or "agent"
    name: str
    file: Path
    problem: str
    related: list[str]


def _find_frontmatter_bounds(lines: list[str]) -> tuple[int, int] | None:
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return 0, i
    return None


def _has_key(fm_lines: list[str], key: str) -> bool:
    prefix = f"{key}:"
    return any(line.strip().startswith(prefix) for line in fm_lines)


def _remove_key(fm_lines: list[str], key: str) -> list[str]:
    """Remove ``key:`` and its continuation lines (block-style YAML aware)."""
    prefix = f"{key}:"
    out: list[str] = []
    skipping = False
    for line in fm_lines:
        stripped = line.lstrip()
        if stripped.startswith(prefix):
            skipping = True
            continue
        if skipping:
            if line.startswith((" ", "\t")) or stripped.startswith("-"):
                continue
            skipping = False
        out.append(line)
    return out


def _quote_yaml_string(value: str) -> str:
    """Quote a string safely for YAML (double-quote with escaping)."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_related(names: list[str]) -> str:
    if not names:
        return "[]"
    return "[" + ", ".join(names) + "]"


def apply_patch(content: str, patch: Patch, *, force: bool) -> tuple[str, bool, list[str]]:
    """Return (new_content, changed, notes).

    Adds ``problem:`` and ``related:`` before the closing frontmatter divider.
    Refuses to overwrite existing values unless ``force=True``.
    """
    lines = content.split("\n")
    bounds = _find_frontmatter_bounds(lines)
    if bounds is None:
        return content, False, [f"no frontmatter in {patch.file}"]
    start, end = bounds
    fm_lines = lines[start + 1 : end]
    body = lines[end:]
    notes: list[str] = []

    has_problem = _has_key(fm_lines, "problem")
    has_related = _has_key(fm_lines, "related")

    if has_problem and not force:
        notes.append("problem: already set (use --force to overwrite)")
    else:
        fm_lines = _remove_key(fm_lines, "problem")

    if has_related and not force:
        notes.append("related: already set (use --force to overwrite)")
    else:
        fm_lines = _remove_key(fm_lines, "related")

    add_problem = patch.problem and (not has_problem or force)
    add_related = (not has_related) or force

    if add_problem:
        fm_lines.append(f"problem: {_quote_yaml_string(patch.problem)}")
    if add_related:
        fm_lines.append(f"related: {_format_related(patch.related)}")

    new_lines = ["---", *fm_lines, *body]
    new_content = "\n".join(new_lines)
    changed = new_content != content
    return new_content, changed, notes


# ---------------------------------------------------------------------------
# Data-table loading and patch resolution
# ---------------------------------------------------------------------------


def load_data(path: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    with path.open() as f:
        data = yaml.safe_load(f)
    return data.get("skills", {}) or {}, data.get("agents", {}) or {}


def resolve_patches(
    skills: dict[str, dict],
    agents: dict[str, dict],
    *,
    include_skills: bool,
    include_agents: bool,
) -> list[Patch]:
    out: list[Patch] = []
    if include_skills:
        for name, entry in sorted(skills.items()):
            skill_file = CLAUDE_ROOT / "skills" / name / "SKILL.md"
            if not skill_file.exists():
                print(f"WARN: skill {name} not found at {skill_file}", file=sys.stderr)
                continue
            out.append(
                Patch(
                    kind="skill",
                    name=name,
                    file=skill_file,
                    problem=entry.get("problem", "") or "",
                    related=list(entry.get("related", []) or []),
                )
            )
    if include_agents:
        for name, entry in sorted(agents.items()):
            agent_file = CLAUDE_ROOT / "agents" / f"{name}.md"
            if not agent_file.exists():
                print(f"WARN: agent {name} not found at {agent_file}", file=sys.stderr)
                continue
            out.append(
                Patch(
                    kind="agent",
                    name=name,
                    file=agent_file,
                    problem=entry.get("problem", "") or "",
                    related=list(entry.get("related", []) or []),
                )
            )
    return out


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------


def _unified_diff(before: str, after: str, path: Path) -> str:
    rel = path.relative_to(REPO_ROOT)
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            n=3,
        )
    )


def run(patches: Iterable[Patch], *, dry_run: bool, force: bool) -> tuple[int, int, int]:
    """Return (changed, skipped, errors)."""
    changed = skipped = errors = 0
    for patch in patches:
        try:
            before = patch.file.read_text()
        except OSError as e:
            print(f"ERROR: {patch.file}: {e}", file=sys.stderr)
            errors += 1
            continue

        after, did_change, notes = apply_patch(before, patch, force=force)

        if not did_change:
            skipped += 1
            if notes:
                for note in notes:
                    print(f"  skip {patch.kind}/{patch.name}: {note}")
            continue

        if dry_run:
            diff = _unified_diff(before, after, patch.file)
            sys.stdout.write(diff)
        else:
            patch.file.write_text(after)
        changed += 1

    return changed, skipped, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply problem: + related: frontmatter fields from "
            "future_projects/claude_tuning/w2_frontmatter_data.yaml."
        ),
    )
    parser.add_argument("--data", type=Path, default=DATA_TABLE, help="YAML data table")
    parser.add_argument("--dry-run", action="store_true", help="Print unified diff, do not write")
    parser.add_argument("--force", action="store_true", help="Overwrite existing values")
    parser.add_argument("--skills", action="store_true", help="Skills only (default: both)")
    parser.add_argument("--agents", action="store_true", help="Agents only (default: both)")
    args = parser.parse_args()

    if not args.data.exists():
        print(f"ERROR: data table not found: {args.data}", file=sys.stderr)
        sys.exit(2)

    include_skills = args.skills or not args.agents
    include_agents = args.agents or not args.skills

    skills, agents = load_data(args.data)
    patches = resolve_patches(
        skills, agents, include_skills=include_skills, include_agents=include_agents
    )
    changed, skipped, errors = run(patches, dry_run=args.dry_run, force=args.force)

    action = "would change" if args.dry_run else "changed"
    print(
        f"\n{action}: {changed}, skipped: {skipped}, errors: {errors} "
        f"({len(patches)} total)",
        file=sys.stderr,
    )
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
