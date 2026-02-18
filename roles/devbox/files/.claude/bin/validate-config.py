#!/usr/bin/env python3
"""Validate Claude Code agent/skill/command configuration integrity.

Checks:
  agents         Agent frontmatter fields, model values, skill cross-references
  skills         Skill frontmatter fields, name/directory match
  commands       Command frontmatter fields
  json           JSON validity for schemas/, hooks.json, settings.json
  references     Broken markdown links in agent files
  stale          Old-style doc references, formatting issues
  grounding      Builder skill grounding reference files
  meta-pipeline  Meta-reviewer existence, builder skill wiring

Usage:
  validate-config.py                           # all checks, ~/.claude root
  validate-config.py --root .                  # all checks, current directory
  validate-config.py --check agents,skills     # subset of checks
  validate-config.py --json                    # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> dict[str, str] | None:
    """Extract YAML frontmatter from markdown content.

    Handles:
      - Simple  key: value  (split on first colon)
      - Quoted values  key: "value with: colons"
      - Multiline >  continuation blocks
      - List field  skills: a, b, c  (kept as raw string)

    Returns None when no valid ``---`` delimited block is found.
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None

    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return None

    result: dict[str, str] = {}
    current_key: str | None = None
    current_value = ""
    multiline = False

    for line in lines[1:end]:
        # Inside a multiline > block — accumulate until next key or blank
        if multiline:
            stripped = line.strip()
            if stripped and not re.match(r"^[a-zA-Z][-\w]*:", line):
                current_value += " " + stripped
                continue
            # Flush multiline value
            if current_key:
                result[current_key] = current_value.strip()
            multiline = False
            current_key = None
            current_value = ""
            # Fall through to process current line as potential new key

        if ":" not in line:
            continue
        # Skip YAML list items (- foo: bar)
        if line.lstrip().startswith("-"):
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value == ">":
            current_key = key
            current_value = ""
            multiline = True
            continue

        # Strip surrounding quotes
        if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]

        result[key] = value

    # Flush trailing multiline
    if multiline and current_key:
        result[current_key] = current_value.strip()

    return result


def parse_skills_list(content: str) -> list[str]:
    """Return skill names from the ``skills:`` frontmatter field."""
    fm = parse_frontmatter(content)
    if not fm or "skills" not in fm:
        return []
    raw = fm["skills"]
    # Strip optional surrounding brackets  skills: [a, b, c]
    raw = raw.strip("[] ")
    return [s.strip() for s in raw.split(",") if s.strip()]


# ---------------------------------------------------------------------------
# Individual checks — each returns (errors, warnings)
# ---------------------------------------------------------------------------

def check_agents(root: Path) -> tuple[list[str], list[str]]:
    agents_dir = root / "agents"
    errors: list[str] = []
    warnings: list[str] = []

    if not agents_dir.is_dir():
        errors.append("[AGENT_DIR] agents/ directory not found")
        return errors, warnings

    available_skills: set[str] = set()
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        available_skills = {
            d.name
            for d in skills_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        }

    for agent_file in sorted(agents_dir.glob("*.md")):
        name = agent_file.name
        content = agent_file.read_text()
        fm = parse_frontmatter(content)

        if fm is None:
            errors.append(f"[AGENT_FRONTMATTER] {name}: Missing or invalid frontmatter")
            continue

        for field in ("name", "description", "tools", "model", "skills"):
            if field not in fm:
                errors.append(f'[AGENT_FIELD] {name}: Missing required field "{field}"')

        if "model" in fm and fm["model"] not in ("sonnet", "opus", "haiku"):
            errors.append(
                f'[AGENT_MODEL] {name}: Invalid model "{fm["model"]}" '
                "(expected sonnet/opus/haiku)"
            )

        for skill in parse_skills_list(content):
            if skill not in available_skills:
                errors.append(f'[SKILL_REF] {name}: References non-existent skill "{skill}"')

    return errors, warnings


def check_skills(root: Path) -> tuple[list[str], list[str]]:
    skills_dir = root / "skills"
    errors: list[str] = []
    warnings: list[str] = []

    if not skills_dir.is_dir():
        errors.append("[SKILL_DIR] skills/ directory not found")
        return errors, warnings

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"[SKILL_FILE] {skill_dir.name}: Missing SKILL.md")
            continue

        content = skill_file.read_text()
        fm = parse_frontmatter(content)

        if fm is None:
            errors.append(
                f"[SKILL_FRONTMATTER] {skill_dir.name}/SKILL.md: "
                "Missing or invalid frontmatter"
            )
            continue

        if "name" not in fm:
            errors.append(
                f'[SKILL_FIELD] {skill_dir.name}/SKILL.md: Missing "name" field'
            )
        elif fm["name"] != skill_dir.name:
            warnings.append(
                f"[SKILL_NAME_MISMATCH] {skill_dir.name}/SKILL.md: "
                f'name="{fm["name"]}" != directory "{skill_dir.name}"'
            )

        if "description" not in fm:
            errors.append(
                f'[SKILL_FIELD] {skill_dir.name}/SKILL.md: Missing "description" field'
            )

    return errors, warnings


def check_commands(root: Path) -> tuple[list[str], list[str]]:
    commands_dir = root / "commands"
    errors: list[str] = []
    warnings: list[str] = []

    if not commands_dir.is_dir():
        errors.append("[CMD_DIR] commands/ directory not found")
        return errors, warnings

    for cmd_file in sorted(commands_dir.glob("*.md")):
        content = cmd_file.read_text()
        fm = parse_frontmatter(content)

        if fm is None:
            errors.append(f"[CMD_FRONTMATTER] {cmd_file.name}: Missing or invalid frontmatter")
            continue

        if "description" not in fm:
            errors.append(f'[CMD_FIELD] {cmd_file.name}: Missing "description" field')

    return errors, warnings


def check_json_files(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for name in ("settings.json", "hooks.json"):
        path = root / name
        if path.exists():
            try:
                json.loads(path.read_text())
            except json.JSONDecodeError as e:
                errors.append(f"[JSON_INVALID] {name}: {e}")

    schemas_dir = root / "schemas"
    if schemas_dir.is_dir():
        for schema_file in sorted(schemas_dir.glob("*.json")):
            try:
                json.loads(schema_file.read_text())
            except json.JSONDecodeError as e:
                errors.append(f"[JSON_INVALID] schemas/{schema_file.name}: {e}")

    return errors, warnings


_LINK_RE = re.compile(r"\]\((?!https?://|#|mailto:)([^)]+)\)")


def check_references(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return errors, warnings

    for md_file in sorted(agents_dir.glob("*.md")):
        content = md_file.read_text()
        for match in _LINK_RE.finditer(content):
            target = match.group(1)
            if target.startswith("../") or "://" in target:
                continue
            candidates = [root / target, root / "docs" / target]
            if not any(c.exists() for c in candidates):
                errors.append(f'[DOC_REF] {md_file.name}: Broken link to "{target}"')

    return errors, warnings


_STALE_PATTERNS = [
    (re.compile(r"go/go_"), "old-style Go doc reference"),
    (re.compile(r"python/python_"), "old-style Python doc reference"),
]


def check_stale_patterns(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return errors, warnings

    for agent_file in sorted(agents_dir.glob("*.md")):
        lines = agent_file.read_text().split("\n")
        in_code_block = False

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            for pattern, desc in _STALE_PATTERNS:
                if pattern.search(line):
                    warnings.append(f"[STALE] {agent_file.name}:{i}: {desc}")

    return errors, warnings


_GROUNDING_REFS: dict[str, list[str]] = {
    "agent-builder": [
        "references/anthropic-agent-authoring.md",
        "references/anthropic-prompt-engineering.md",
    ],
    "skill-builder": [
        "references/anthropic-skill-authoring.md",
    ],
}


def check_grounding(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for skill_name, refs in _GROUNDING_REFS.items():
        skill_dir = root / "skills" / skill_name
        if not skill_dir.is_dir():
            errors.append(f"[GROUNDING] skills/{skill_name}: Directory not found")
            continue
        for ref in refs:
            if not (skill_dir / ref).exists():
                errors.append(f"[GROUNDING] {skill_name}/{ref}: File not found")

    return errors, warnings


def check_meta_pipeline(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    meta_file = root / "agents" / "meta_reviewer.md"
    if not meta_file.exists():
        errors.append("[META_PIPELINE] agents/meta_reviewer.md not found")
        return errors, warnings

    skills = parse_skills_list(meta_file.read_text())

    if "agent-builder" not in skills:
        errors.append('[META_PIPELINE] meta_reviewer.md: "agent-builder" missing from skills')
    if "skill-builder" not in skills:
        errors.append('[META_PIPELINE] meta_reviewer.md: "skill-builder" missing from skills')

    for skill in ("agent-builder", "skill-builder"):
        if not (root / "skills" / skill / "SKILL.md").exists():
            errors.append(f"[META_PIPELINE] skills/{skill}/SKILL.md not found")

    return errors, warnings


# ---------------------------------------------------------------------------
# Registry & runner
# ---------------------------------------------------------------------------

ALL_CHECKS: dict[str, callable] = {
    "agents": check_agents,
    "skills": check_skills,
    "commands": check_commands,
    "json": check_json_files,
    "references": check_references,
    "stale": check_stale_patterns,
    "grounding": check_grounding,
    "meta-pipeline": check_meta_pipeline,
}


def run_checks(root: Path, checks: list[str] | None = None) -> dict:
    selected = checks or list(ALL_CHECKS.keys())
    all_errors: list[str] = []
    all_warnings: list[str] = []

    for name in selected:
        fn = ALL_CHECKS.get(name)
        if fn is None:
            all_errors.append(f"[CONFIG] Unknown check: {name}")
            continue
        errs, warns = fn(root)
        all_errors.extend(errs)
        all_warnings.extend(warns)

    agents_dir = root / "agents"
    skills_dir = root / "skills"
    commands_dir = root / "commands"

    counts = {
        "agents": len(list(agents_dir.glob("*.md"))) if agents_dir.is_dir() else 0,
        "skills": (
            len([
                d for d in skills_dir.iterdir()
                if d.is_dir() and (d / "SKILL.md").exists()
            ])
            if skills_dir.is_dir()
            else 0
        ),
        "commands": len(list(commands_dir.glob("*.md"))) if commands_dir.is_dir() else 0,
        "errors": len(all_errors),
        "warnings": len(all_warnings),
    }

    return {"errors": all_errors, "warnings": all_warnings, "counts": counts}


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_text(results: dict) -> str:
    counts = results["counts"]
    lines: list[str] = []

    lines.append("Configuration Validation Report")
    lines.append("=" * 40)
    lines.append("")

    if results["errors"]:
        lines.append("Errors (must fix)")
        lines.append("-" * 20)
        for e in results["errors"]:
            lines.append(f"  {e}")
        lines.append("")

    if results["warnings"]:
        lines.append("Warnings (should fix)")
        lines.append("-" * 20)
        for w in results["warnings"]:
            lines.append(f"  {w}")
        lines.append("")

    lines.append("Summary")
    lines.append("-" * 20)
    lines.append(f"  Agents:   {counts['agents']}")
    lines.append(f"  Skills:   {counts['skills']}")
    lines.append(f"  Commands: {counts['commands']}")
    lines.append(f"  Errors:   {counts['errors']}")
    lines.append(f"  Warnings: {counts['warnings']}")
    lines.append("")

    if counts["errors"] == 0 and counts["warnings"] == 0:
        lines.append("PASS")
    elif counts["errors"] > 0:
        lines.append(f"FAIL — {counts['errors']} error(s)")
    else:
        lines.append(f"WARN — {counts['warnings']} warning(s)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Claude Code agent/skill/command configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Available checks: " + ", ".join(ALL_CHECKS),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.home() / ".claude",
        help="Root directory of Claude Code config (default: ~/.claude)",
    )
    parser.add_argument(
        "--check",
        type=str,
        default=None,
        help="Comma-separated list of checks to run (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    checks = [c.strip() for c in args.check.split(",")] if args.check else None
    results = run_checks(args.root, checks)

    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        print(format_text(results))

    sys.exit(1 if results["counts"]["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
