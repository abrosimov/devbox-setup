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
    local_relative_path: str
    state_filename: str


FPF_SPEC: Final[DocSpec] = DocSpec(
    name="FPF",
    upstream_url="https://raw.githubusercontent.com/ailev/FPF/main/FPF-Spec.md",
    local_relative_path="roles/devbox/files/dot_claude/docs/FPF-Spec.md",
    state_filename="fpf-drift",
)
NARRATIVE_SPEC: Final[DocSpec] = DocSpec(
    name="Narrative",
    upstream_url=(
        "https://raw.githubusercontent.com/ailev/FPF/main/"
        "Narrativization-and-Narrative-Studies-Principles-Framework.md"
    ),
    local_relative_path=(
        "roles/devbox/files/dot_claude/docs/"
        "Narrativization-and-Narrative-Studies-Principles-Framework.md"
    ),
    state_filename="narrative-drift",
)
SPECS: Final[tuple[DocSpec, ...]] = (FPF_SPEC, NARRATIVE_SPEC)

DEFAULT_TTL_HOURS: Final[int] = 168

# Retained so the FPF-only entrypoint and callers (statusline, tide) that key off
# the FPF spec keep resolving without a spec object.
UPSTREAM_URL: Final[str] = FPF_SPEC.upstream_url
LOCAL_RELATIVE_PATH: Final[str] = FPF_SPEC.local_relative_path

USAGE: Final[str] = (
    "Usage: fpf_drift_check.py [--force] [--local PATH]\n"
    "Refreshes drift state for the FPF spec and the companion Narrative doc,\n"
    "writing each drifted line count (or '0') to its own state file.\n"
    "Each doc is TTL-gated on its own state file; --force refreshes both.\n"
    "--local PATH overrides the FPF spec location only; the Narrative doc is\n"
    "always located by walking up from the current directory.\n"
)


@dataclass(frozen=True)
class ParsedArgs:
    force: bool
    local: str | None
    show_usage: bool


@dataclass(frozen=True)
class ParseFailure:
    message: str


def parse_args(argv: list[str]) -> ParsedArgs | ParseFailure:
    force = False
    local: str | None = None
    show_usage = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--force":
            force = True
            i += 1
            continue
        if arg == "--local":
            if i + 1 >= len(argv):
                return ParseFailure("--local requires a path argument.")
            local = argv[i + 1]
            i += 2
            continue
        if arg in ("-h", "--help"):
            show_usage = True
            i += 1
            continue
        return ParseFailure(f"Unknown argument '{arg}'.")
    return ParsedArgs(force=force, local=local, show_usage=show_usage)


def state_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME") or ""
    if xdg:
        base = Path(xdg)
    else:
        home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or str(Path.home())
        base = Path(home) / ".cache"
    return base / "devbox-setup"


def state_file_for(spec: DocSpec) -> Path:
    return state_dir() / spec.state_filename


def state_file() -> Path:
    return state_file_for(FPF_SPEC)


def is_fresh(path: Path, ttl_hours: int) -> bool:
    if not path.is_file():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl_hours * 3600


def find_local_spec(start: Path, relative_path: str = LOCAL_RELATIVE_PATH) -> Path | None:
    current = start.resolve() if start.exists() else start
    if current.is_file():
        current = current.parent
    depth = 0
    while depth <= 20:
        candidate = current / relative_path
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent
        depth += 1
    return None


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


def process_spec(spec: DocSpec, *, force: bool, local_override: str | None) -> int:
    state = state_file_for(spec)
    state.parent.mkdir(parents=True, exist_ok=True)

    if not force and is_fresh(state, DEFAULT_TTL_HOURS):
        return 0

    if local_override is not None:
        local_spec: Path | None = Path(local_override)
    else:
        cwd = Path(os.environ.get("PWD") or Path.cwd())
        local_spec = find_local_spec(cwd, spec.local_relative_path)

    if local_spec is None or not local_spec.is_file():
        return 1

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{spec.state_filename}") as fh:
        tmp_path = Path(fh.name)
    try:
        if not download_upstream(tmp_path, spec.upstream_url):
            return 0
        drift = count_drift(tmp_path, local_spec)
        write_state(drift, state)
    finally:
        if tmp_path.exists():
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

    results = [
        process_spec(
            spec,
            force=parsed.force,
            local_override=parsed.local if spec is FPF_SPEC else None,
        )
        for spec in SPECS
    ]
    # Signal failure only when no vendored doc was found at all (mirrors the
    # former FPF-only "not in repo" exit code).
    if results and all(code == 1 for code in results):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    env.setup()
    return run(argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
