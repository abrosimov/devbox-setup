# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Ensure every line in TARGET_LINES is present in a text file.

Template for ai_written_scripts/<slug>/main.py. Replace the planning,
execution and verification bodies with the real task, keeping the shape:
plan (pure, tested) -> print plan -> execute unless --dry-run -> verify.

Run:   uv run ai_written_scripts/<slug>/main.py [--dry-run] --file PATH
Test:  uv run --with pytest pytest ai_written_scripts/<slug>
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

TARGET_LINES: tuple[str, ...] = ("example.setting = true",)


@dataclass(frozen=True)
class Step:
    description: str
    line: str


def plan(current: str, wanted: tuple[str, ...]) -> list[Step]:
    """Return only the steps still needed, so a second run plans nothing."""
    present = set(current.splitlines())
    return [Step(f"append {line!r}", line) for line in wanted if line not in present]


def execute(path: Path, steps: list[Step]) -> None:
    if not steps:
        return
    existing = path.read_text() if path.exists() else ""
    prefix = "" if existing == "" or existing.endswith("\n") else "\n"
    addition = "".join(f"{step.line}\n" for step in steps)
    path.write_text(existing + prefix + addition)


def verify(current: str, wanted: tuple[str, ...]) -> list[str]:
    """Return the wanted lines that are still missing; empty means success."""
    present = set(current.splitlines())
    return [line for line in wanted if line not in present]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", type=Path, required=True, help="file to update")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and change nothing")
    args = parser.parse_args(argv)

    path: Path = args.file
    current = path.read_text() if path.exists() else ""
    steps = plan(current, TARGET_LINES)

    if not steps:
        print(f"nothing to do: {path} is already up to date")
    for step in steps:
        print(f"{'would ' if args.dry_run else ''}{step.description} to {path}")

    if args.dry_run:
        return 0

    execute(path, steps)

    missing = verify(path.read_text() if path.exists() else "", TARGET_LINES)
    if missing:
        print(f"VERIFY FAILED: still missing {missing} in {path}", file=sys.stderr)
        return 1
    print(f"VERIFY OK: {path} contains all {len(TARGET_LINES)} expected line(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
