#!/usr/bin/env python3
"""SessionStart hook: prepare or audit a Python project's uv venv.

Two modes, decided by whether ``$CLAUDE_PROJECT_DIR/.claude/sync.toml`` exists:

* **Sync mode** (file present): run ``uv sync --frozen`` with the declared
  groups/extras. Emit an ``additionalContext`` line reporting what was synced,
  so Claude does not need to guess whether pytest/ruff/etc. are available.
* **Detect-only mode** (file absent): parse ``pyproject.toml``; if it declares
  optional groups or extras, emit an ``additionalContext`` line naming them
  so Claude does not silently assume they are installed in ``.venv/``.

Rules of engagement:

* Exits 0 silently for non-Python projects (no ``pyproject.toml``).
* Never fails the session — all errors degrade to an advisory message.
* Uses ``--frozen`` in sync mode so the lockfile is never mutated by a hook.

Wired to ``SessionStart`` (matchers ``startup|resume``) in hooks.json; the
outer timeout there is 15s, which bounds ``UV_TIMEOUT_SEC`` below.
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, proc

if TYPE_CHECKING:
    from collections.abc import Mapping

# Leave a few seconds of headroom under the 15s hook timeout so that if
# ``uv sync`` blocks on network the hook can return a graceful message rather
# than being SIGKILLed by Claude Code with no output.
UV_TIMEOUT_SEC: Final[int] = 10


def _project_dir(data: Mapping[str, object]) -> Path | None:
    root = os.environ.get("CLAUDE_PROJECT_DIR")
    if root:
        return Path(root)
    cwd_value = data.get("cwd")
    if isinstance(cwd_value, str) and cwd_value:
        return Path(cwd_value)
    return None


def _load_pyproject(project: Path) -> dict[str, object] | None:
    pyproject = project / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        return tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _declared_groups(pyproject: Mapping[str, object]) -> list[str]:
    groups = pyproject.get("dependency-groups")
    if not isinstance(groups, dict):
        return []
    return sorted(groups.keys())


def _declared_extras(pyproject: Mapping[str, object]) -> list[str]:
    project = pyproject.get("project")
    if not isinstance(project, dict):
        return []
    extras = project.get("optional-dependencies")
    if not isinstance(extras, dict):
        return []
    return sorted(extras.keys())


def _load_sync_config(project: Path) -> dict[str, object] | None:
    sync_toml = project / ".claude" / "sync.toml"
    if not sync_toml.is_file():
        return None
    try:
        return tomllib.loads(sync_toml.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _build_sync_args(config: Mapping[str, object]) -> list[str]:
    # Empty file → opt-in for "everything" (user placed the marker but did
    # not specify which groups; safest interpretation is that they want a
    # full sync). Any explicit key disables this fallback.
    if not config:
        return ["uv", "sync", "--frozen", "--all-groups", "--all-extras"]

    args = ["uv", "sync", "--frozen"]

    if bool(config.get("all_groups")):
        args.append("--all-groups")
    else:
        groups = config.get("groups")
        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, str) and group:
                    args.extend(["--group", group])

    if bool(config.get("all_extras")):
        args.append("--all-extras")
    else:
        extras = config.get("extras")
        if isinstance(extras, list):
            for extra in extras:
                if isinstance(extra, str) and extra:
                    args.extend(["--extra", extra])

    return args


def _sync_mode(project: Path, config: Mapping[str, object]) -> str:
    args = _build_sync_args(config)
    result = proc.run_cmd(args, cwd=project, timeout=UV_TIMEOUT_SEC)
    if result.timed_out:
        return (
            f"[SessionStart] `uv sync` timed out after {UV_TIMEOUT_SEC}s in "
            f"{project}. Session continues; run `uv sync` manually to prepare "
            "the venv."
        )
    if not result.success:
        last_line = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ""
        return (
            f"[SessionStart] `{' '.join(args)}` failed "
            f"(exit {result.returncode}): {last_line}. "
            "Session continues; venv may be incomplete."
        )
    flags = " ".join(args[2:])
    return (
        f"[SessionStart] Ran `uv sync {flags}` in {project}. "
        "Venv is in sync with .claude/sync.toml — `uv run <cmd>` will resolve "
        "declared tools."
    )


def _detect_mode(project: Path, pyproject: Mapping[str, object]) -> str | None:
    groups = _declared_groups(pyproject)
    extras = _declared_extras(pyproject)
    if not groups and not extras:
        return None
    lines = [f"[SessionStart] Python project at {project} declares optional dependencies:"]
    if groups:
        lines.append(f"- dependency-groups: {', '.join(groups)}")
    if extras:
        lines.append(f"- extras: {', '.join(extras)}")
    lines.append(
        "By default `uv sync` installs only the `dev` group. Do NOT assume "
        "other groups/extras are present in `.venv/`. If a tool (pytest, "
        "ruff, mypy, etc.) appears missing, either ask the user to "
        "`uv sync --group <name>` or invoke with `uv run --group <name> <cmd>` "
        "— do not invent flags silently. To auto-sync on every SessionStart, "
        "create `.claude/sync.toml` in the project root."
    )
    return "\n".join(lines)


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    project = _project_dir(data)
    if project is None:
        return 0

    pyproject = _load_pyproject(project)
    if pyproject is None:
        return 0

    sync_config = _load_sync_config(project)
    message = (
        _sync_mode(project, sync_config)
        if sync_config is not None
        else _detect_mode(project, pyproject)
    )

    if message:
        hooks.write_additional_context(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
