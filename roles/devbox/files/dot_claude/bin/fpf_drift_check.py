#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, paths, proc


@dataclass(frozen=True)
class DocSpec:
    name: str
    upstream_url: str
    relative_path: str
    state_filename: str


FPF_SPEC: Final[DocSpec] = DocSpec(
    name="FPF",
    upstream_url="https://raw.githubusercontent.com/ailev/FPF/main/FPF-Spec.md",
    relative_path="FPF-Spec.md",
    state_filename="fpf-drift",
)
NARRATIVE_SPEC: Final[DocSpec] = DocSpec(
    name="Narrative",
    upstream_url=(
        "https://raw.githubusercontent.com/ailev/FPF/main/DPFs/"
        "Narrativization-and-Narrative-Studies-Principles-Framework.md"
    ),
    relative_path="DPFs/Narrativization-and-Narrative-Studies-Principles-Framework.md",
    state_filename="narrative-drift",
)
SPECS: Final[tuple[DocSpec, ...]] = (FPF_SPEC, NARRATIVE_SPEC)

# The copy this engine actually loads, relative to $HOME — not a devbox-setup
# checkout, which may be ahead of or behind what was deployed.
REFERENCES_RELATIVE_PATH: Final[str] = ".claude/skills/fpf-thinking/references"
# Each engine deploys its own copy, so each keeps its own drift state.
ENGINE_STATE_SUBDIR: Final[str] = "claude"

DEFAULT_TTL_HOURS: Final[int] = 168

USAGE: Final[str] = (
    "Usage: fpf_drift_check.py [--force] [--references DIR]\n"
    "Refreshes drift state for the FPF spec and the companion Narrative doc,\n"
    "comparing upstream with the copy deployed for this engine\n"
    f"(default: ~/{REFERENCES_RELATIVE_PATH}) and writing each drifted line\n"
    "count (or '0') to its own state file. Each doc is refreshed when its TTL\n"
    "expires or its deployed copy changes; --force refreshes both.\n"
)


@dataclass(frozen=True)
class ParsedArgs:
    force: bool
    references: str | None
    show_usage: bool


@dataclass(frozen=True)
class ParseFailure:
    message: str


def parse_args(argv: list[str]) -> ParsedArgs | ParseFailure:
    force = False
    references: str | None = None
    show_usage = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--force":
            force = True
            i += 1
            continue
        if arg == "--references":
            if i + 1 >= len(argv):
                return ParseFailure("--references requires a directory argument.")
            references = argv[i + 1]
            i += 2
            continue
        if arg in ("-h", "--help"):
            show_usage = True
            i += 1
            continue
        return ParseFailure(f"Unknown argument '{arg}'.")
    return ParsedArgs(force=force, references=references, show_usage=show_usage)


def _home() -> Path:
    return Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or str(Path.home()))


def references_dir() -> Path:
    return _home() / REFERENCES_RELATIVE_PATH


def state_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME") or ""
    base = Path(xdg) if xdg else _home() / ".cache"
    return base / "devbox-setup" / ENGINE_STATE_SUBDIR


def state_file_for(spec: DocSpec) -> Path:
    return state_dir() / spec.state_filename


def source_file_for(spec: DocSpec) -> Path:
    return state_dir() / f"{spec.state_filename}.source"


def source_signature(local: Path) -> str:
    # A deploy rewrites the file, changing its size or mtime; hashing a
    # multi-megabyte spec on every statusline render is not worth it.
    stat = local.stat()
    return f"{stat.st_size} {stat.st_mtime_ns}"


def is_fresh(path: Path, ttl_hours: int) -> bool:
    if not path.is_file():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl_hours * 3600


def is_current(spec: DocSpec, local: Path, ttl_hours: int) -> bool:
    if not is_fresh(state_file_for(spec), ttl_hours):
        return False
    try:
        recorded = source_file_for(spec).read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return recorded == source_signature(local)


def download_upstream(target: Path, url: str, timeout: int = 10) -> bool:
    result = proc.run_cmd(
        [
            "curl",
            "-sfSL",
            "--max-time",
            str(timeout),
            url,
            "-o",
            str(target),
        ],
        timeout=timeout + 5,
    )
    return result.success


def count_drift(upstream: Path, local: Path) -> int:
    result = proc.run_cmd(
        ["diff", str(upstream), str(local)],
        timeout=15,
    )
    if result.returncode not in (0, 1):
        return 0
    if not result.stdout:
        return 0
    count = 0
    for line in result.stdout.splitlines():
        if line.startswith(("<", ">")):
            count += 1
    return count


def write_state(value: int, target: Path) -> None:
    paths.atomic_write(target, f"{value}\n")


def clear_state(spec: DocSpec) -> None:
    state_file_for(spec).unlink(missing_ok=True)
    source_file_for(spec).unlink(missing_ok=True)


def process_spec(spec: DocSpec, references: Path, *, force: bool) -> int:
    local = references / spec.relative_path
    if not local.is_file():
        # Nothing deployed means nothing to compare; a leftover number would lie.
        clear_state(spec)
        return 1

    if not force and is_current(spec, local, DEFAULT_TTL_HOURS):
        return 0

    state = state_file_for(spec)
    state.parent.mkdir(parents=True, exist_ok=True)
    signature = source_signature(local)

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{spec.state_filename}") as fh:
        tmp_path = Path(fh.name)
    try:
        if not download_upstream(tmp_path, spec.upstream_url):
            return 0
        drift = count_drift(tmp_path, local)
        write_state(drift, state)
        paths.atomic_write(source_file_for(spec), f"{signature}\n")
    finally:
        tmp_path.unlink(missing_ok=True)
    return 0


def run(argv: list[str]) -> int:
    parsed = parse_args(argv)
    if isinstance(parsed, ParseFailure):
        sys.stderr.write(f"{parsed.message}\n{USAGE}")
        return 2
    if parsed.show_usage:
        sys.stdout.write(USAGE)
        return 0

    references = Path(parsed.references) if parsed.references else references_dir()
    results = [process_spec(spec, references, force=parsed.force) for spec in SPECS]
    # Signal failure only when no deployed doc was found at all.
    if results and all(code == 1 for code in results):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    env.setup()
    return run(argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
