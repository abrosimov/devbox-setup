#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, paths, proc

SE_ARTIFACT_RE: Final[re.Pattern[str]] = re.compile(r"^se_([a-z]+)_output\.json$")
SUFFIX_TO_LANG: Final[dict[str, str]] = {"go": "go", "python": "python", "frontend": "node"}
ROOT_MARKERS: Final[tuple[str, ...]] = (
    "go.mod",
    "pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "package.json",
    "Cargo.toml",
)
VERIFY_TIMEOUT: Final[int] = 120


def lang_from_filename(file_name: str) -> str | None:
    match = SE_ARTIFACT_RE.match(file_name)
    if match is None:
        return None
    return SUFFIX_TO_LANG.get(match.group(1))


def verify_script_path() -> Path:
    home = Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp")  # noqa: S108
    return home / ".claude" / "bin" / "verify-se-completion"


def format_failures(parsed: dict[str, object]) -> str:
    checks = parsed.get("checks")
    if not isinstance(checks, dict):
        return ""
    failures: list[str] = []
    for check_name, info in checks.items():
        if not isinstance(info, dict):
            continue
        if info.get("status") != "FAIL":
            continue
        detail = info.get("detail", "")
        error = info.get("error", "")
        suffix = ""
        if isinstance(error, str) and error:
            suffix = " — " + error[:200]
        failures.append(f"  {check_name}: {detail}{suffix}")
    return "\n".join(failures)


def block(message: str) -> int:
    sys.stderr.write(message)
    if not message.endswith("\n"):
        sys.stderr.write("\n")
    return hooks.BLOCK


def artifact_file_path(data: dict[str, object]) -> str | None:
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_path_value = tool_input.get("file_path")
    if not isinstance(file_path_value, str) or not file_path_value:
        return None
    if not SE_ARTIFACT_RE.match(Path(file_path_value).name):
        return None
    return file_path_value


def parse_verification_result(result: proc.CmdResult) -> dict[str, object] | str:
    if result.timed_out:
        return (
            "BLOCKED: Verification timed out. Fix the verification infrastructure "
            "before writing completion artifacts."
        )
    output = result.stdout.strip()
    if not output:
        return "BLOCKED: Could not parse verification output. Cannot confirm build/lint status."
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        snippet = (result.stderr or output)[:500]
        return f"BLOCKED: Build/lint verification failed.\n{snippet}"
    if not isinstance(parsed, dict):
        return "BLOCKED: Could not parse verification output. Cannot confirm build/lint status."
    return parsed


def run_verification(lang: str, project_root: Path) -> int:
    verify_path = verify_script_path()
    if not verify_path.exists():
        return block(
            f"BLOCKED: verify-se-completion script not found at {verify_path}. "
            "Cannot write completion artifacts without verification infrastructure.",
        )

    result = proc.run_cmd(
        [str(verify_path), "--lang", lang, "--work-dir", str(project_root), "--json"],
        timeout=VERIFY_TIMEOUT,
    )

    outcome = parse_verification_result(result)
    if isinstance(outcome, str):
        return block(outcome)

    if outcome.get("result") == "PASS":
        return hooks.ALLOW

    failures = format_failures(outcome)
    body = "\n" + failures if failures else ""
    return block(
        "BLOCKED: Build/lint verification failed. Fix these before writing completion artifacts."
        + body,
    )


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW

    file_path_value = artifact_file_path(data)
    if file_path_value is None:
        return hooks.ALLOW

    file_name = Path(file_path_value).name
    lang = lang_from_filename(file_name)
    if lang is None:
        known = ", ".join(SUFFIX_TO_LANG)
        return block(
            f'BLOCKED: Unknown language suffix in artifact "{file_name}". Known suffixes: {known}.',
        )

    project_root = paths.find_project_root(Path(file_path_value).parent, ROOT_MARKERS)
    if project_root is None:
        return block(
            "BLOCKED: Could not detect project root for SE artifact verification. "
            "Cannot write completion artifacts without a verifiable project.",
        )

    return run_verification(lang, project_root)


if __name__ == "__main__":
    sys.exit(main())
