#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks, paths

UV_LOCK: Final[str] = "uv.lock"
POETRY_LOCK: Final[str] = "poetry.lock"
PNPM_LOCK: Final[str] = "pnpm-lock.yaml"
YARN_LOCK: Final[str] = "yarn.lock"
NPM_LOCK: Final[str] = "package-lock.json"

PYTHON_SCRIPT_RE: Final[re.Pattern[str]] = re.compile(r"^python3?\s+(?!-)")

CACHE_WORKAROUND_VARS: Final[tuple[str, ...]] = (
    "UV_CACHE_DIR",
    "UV_TOOL_DIR",
    "RUFF_CACHE_DIR",
    "MYPY_CACHE_DIR",
    "PYTEST_CACHE_DIR",
    "PIP_CACHE_DIR",
    "POETRY_CACHE_DIR",
    "GOCACHE",
    "GOMODCACHE",
    "GOTMPDIR",
    "GOPATH",
    "NPM_CONFIG_CACHE",
    "YARN_CACHE_FOLDER",
    "PNPM_STORE_PATH",
    "CARGO_HOME",
    "CARGO_TARGET_DIR",
)

# Go toolchain/module-resolution overrides. GOTOOLCHAIN is pinned to `local`
# in settings.json — overriding forces a toolchain download that will fail in
# sandbox. GOSUMDB/GOINSECURE bypass checksum verification. The remaining vars
# override module resolution or build behaviour — almost always a workaround.
# Cross-compilation (GOOS/GOARCH) and CGO_ENABLED are legitimate tuners and
# stay out of this list.
GO_TOOLCHAIN_OVERRIDE_VARS: Final[tuple[str, ...]] = (
    "GOTOOLCHAIN",
    "GOFLAGS",
    "GOPROXY",
    "GOSUMDB",
    "GOPRIVATE",
    "GOINSECURE",
    "GO111MODULE",
    "GOWORK",
    "GOVCS",
    "GOEXPERIMENT",
)

_ALL_WATCHED_VARS: Final[frozenset[str]] = frozenset(
    CACHE_WORKAROUND_VARS + GO_TOOLCHAIN_OVERRIDE_VARS + ("PYTHONPATH",),
)

# `export VAR=…` anywhere in the command (mid-line, after `;`, etc.).
EXPORT_ASSIGN_RE: Final[re.Pattern[str]] = re.compile(
    r"\bexport\s+([A-Za-z_][A-Za-z0-9_]*)=",
)

# Standalone `VAR=…` followed by a command separator (`;`, `&&`, `||`, newline).
# Distinguishes from leading `VAR=… <cmd>` (handled by LEADING_ENV_ASSIGNS_RE)
# and from `docker run -e VAR=… image cmd` (no separator after value).
STANDALONE_ASSIGN_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[\s;&|(])([A-Za-z_][A-Za-z0-9_]*)=\S+\s*(?:;|&&|\|\||\n)",
)

LEADING_ENV_ASSIGNS_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:env\s+)?((?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)+)",
)

VENV_DIRECT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[\s;&|(=])(?:\S*/)?\.venv/bin/[A-Za-z0-9_.-]+",
)

PYTHON_C_IMPORT_RE: Final[re.Pattern[str]] = re.compile(
    r"\bpython3?\s+-c\s+[\"']?\s*import\s",
)

UV_RUN_PY_C_IMPORT_RE: Final[re.Pattern[str]] = re.compile(
    r"\buv\s+run\b[^;|&]*\bpython3?\s+-c\s+[\"']?\s*import\s",
)

PYTEST_COLLECT_ONLY_RE: Final[re.Pattern[str]] = re.compile(
    r"\bpytest\b[^;|&]*\s(?:--collect-only|--co)(?:\s|$)",
)

NO_SYNC_RE: Final[re.Pattern[str]] = re.compile(
    r"\buv\s+run\b[^;|&]*\s--no-sync\b",
)

SKIP_CACHE_FLAGS_RE: Final[re.Pattern[str]] = re.compile(
    r"("
    r"\bpytest\b[^;|&]*\s-p\s+no:cacheprovider\b"
    r"|\bpytest\b[^;|&]*\s--no-cacheprovider\b"
    r"|\bmypy\b[^;|&]*\s--no-incremental\b"
    r"|\bruff\b[^;|&]*\s--no-cache\b"
    r"|\bpip\s+install\b[^;|&]*\s--force-reinstall\b"
    r"|\bpip\s+install\b[^;|&]*\s--ignore-installed\b"
    r")",
)

ALLOW_EMPTY_COMMIT_RE: Final[re.Pattern[str]] = re.compile(
    r"\bgit\s+commit\b[^;|&]*\s--allow-empty\b",
)

FORCE_FLAGS_RE: Final[re.Pattern[str]] = re.compile(
    r"("
    r"\bkill\s+-9\b"
    r"|\bkill\s+-KILL\b"
    r"|\bchmod\s+(?:-R\s+)?777\b"
    r")",
)


@dataclass(frozen=True)
class Block:
    message: str


def _starts_with(cmd: str, prefix: str) -> bool:
    return cmd == prefix or cmd.startswith((prefix + " ", prefix + "\t"))


def _strip_leading_env_assigns(cmd: str) -> str:
    """Return ``cmd`` with any leading ``[env] VAR=value …`` prefix removed.

    Downstream toolchain checks (``_check_pytest``, ``_check_venv_direct``,
    ``_check_bare_python_script``, …) key off the head of the command. A
    project-specific inline env-prefix like ``ENV_NAME=local pytest tests/``
    otherwise hides ``pytest`` behind the assignment and slips past them.

    ``_check_env_var_workaround`` and ``_check_export_cache_workaround``
    still run against the original ``cmd`` — they need to see the assigns.
    """
    match = LEADING_ENV_ASSIGNS_RE.match(cmd)
    if match is None:
        return cmd
    return cmd[match.end() :]


def _has_marker(start: Path, marker: str) -> bool:
    root = paths.find_project_root(start, (marker,))
    return root is not None


def _has_python_project(start: Path) -> bool:
    return _has_marker(start, UV_LOCK) or _has_marker(start, POETRY_LOCK)


def _check_go_fmt(cmd: str) -> Block | None:
    if "go fmt" in cmd or "gofmt" in cmd:
        return Block(
            "Use `goimports -local <module-name>`, not go fmt/gofmt. "
            "Extract module name from go.mod.",
        )
    return None


def _check_pip(cmd: str) -> Block | None:
    pip_prefixes = (
        "pip install",
        "pip3 install",
        "python -m pip",
        "python3 -m pip",
    )
    for prefix in pip_prefixes:
        if cmd.startswith(prefix):
            return Block(
                "Use `uv add <package>` (or `poetry add` in poetry projects). "
                "Never use pip install directly.",
            )
    return None


def _check_venv(cmd: str) -> Block | None:
    venv_prefixes = ("python -m venv", "python3 -m venv")
    for prefix in venv_prefixes:
        if cmd.startswith(prefix):
            return Block(
                "Do not create venvs manually. Use `uv sync` — uv creates "
                "and manages .venv automatically.",
            )
    return None


def _workaround_block(var: str, form: str) -> Block:
    """Build a Block message for a watched env var in one of three forms.

    form: ``inline`` (leading `VAR=… <cmd>`), ``export`` (`export VAR=…`),
    ``standalone`` (`VAR=…;` mid-command). Message wording is tailored per
    var class: caches, PYTHONPATH, Go toolchain overrides.
    """
    prefix = {
        "inline": f"Inline `{var}=…` at command start",
        "export": f"`export {var}=…`",
        "standalone": f"Standalone `{var}=…;` assignment",
    }[form]
    if var in CACHE_WORKAROUND_VARS:
        return Block(
            f"{prefix} overrides tool cache/tool-dir paths set at session start "
            "via settings.json env — never override manually. If the cache is "
            "corrupt, run `uv cache clean` (or the tool's own clean subcommand) "
            "and retry.",
        )
    if var == "PYTHONPATH":
        return Block(
            f"{prefix} is a workaround. Configure imports in pyproject.toml "
            "(src-layout, packages) or use `uv run` — do not patch sys.path at "
            "invocation time.",
        )
    # Go toolchain / module-resolution override
    return Block(
        f"{prefix} overrides Go toolchain or module behaviour. GOTOOLCHAIN is "
        "pinned to `local` in settings.json (override forces a toolchain "
        "download that fails in sandbox); GOSUMDB/GOINSECURE bypass checksum "
        "verification; GOPROXY/GOPRIVATE/GO111MODULE/GOWORK/GOVCS/GOFLAGS/"
        "GOEXPERIMENT override module resolution or build behaviour and are "
        "almost always a workaround. If the Go build fails, escalate to the "
        "user — do not reroute via env vars.",
    )


def _check_env_var_workaround(cmd: str) -> Block | None:
    match = LEADING_ENV_ASSIGNS_RE.match(cmd)
    if not match:
        return None
    leading = match.group(1)
    for var in CACHE_WORKAROUND_VARS:
        if re.search(rf"\b{re.escape(var)}=", leading):
            return _workaround_block(var, "inline")
    if re.search(r"\bPYTHONPATH=", leading):
        return _workaround_block("PYTHONPATH", "inline")
    for var in GO_TOOLCHAIN_OVERRIDE_VARS:
        if re.search(rf"\b{re.escape(var)}=", leading):
            return _workaround_block(var, "inline")
    return None


def _check_export_cache_workaround(cmd: str) -> Block | None:
    """Catch `export VAR=…` and standalone `VAR=…;` mid-command.

    Leading `VAR=… <cmd>` inline env-prefix is handled by
    ``_check_env_var_workaround``; this check covers the two remaining forms
    that reach the same effect through the current shell environment.
    """
    for match in EXPORT_ASSIGN_RE.finditer(cmd):
        var = match.group(1)
        if var in _ALL_WATCHED_VARS:
            return _workaround_block(var, "export")
    for match in STANDALONE_ASSIGN_RE.finditer(cmd):
        var = match.group(1)
        if var in _ALL_WATCHED_VARS:
            return _workaround_block(var, "standalone")
    return None


def _check_uvx(cmd: str, start: Path) -> Block | None:
    if not _starts_with(cmd, "uvx"):
        return None
    if _has_marker(start, UV_LOCK):
        return Block(
            "`uvx <tool>` runs an isolated one-shot install and bypasses the "
            "project's uv environment and lockfile. In a uv project, use "
            "`uv add <tool>` (or `uv add --dev`) and then `uv run <tool>`. "
            "If `uv run <tool>` fails, escalate to the user — do not bypass "
            "with uvx.",
        )
    return None


def _check_no_sync(cmd: str) -> Block | None:
    if NO_SYNC_RE.search(cmd):
        return Block(
            "`uv run --no-sync` bypasses environment management. If sync is "
            "slow or broken, fix pyproject.toml — do not skip it.",
        )
    return None


def _check_skip_cache_flags(cmd: str) -> Block | None:
    if SKIP_CACHE_FLAGS_RE.search(cmd):
        return Block(
            "Skip-cache/skip-reinstall flags (`--no-cache`, `--no-incremental`, "
            "`--no-cacheprovider`, `--force-reinstall`, `--ignore-installed`) "
            "are workarounds. If cache is corrupt, run the tool's `cache clean`. "
            "If reinstall is needed, update the lockfile.",
        )
    return None


def _check_allow_empty_commit(cmd: str) -> Block | None:
    if ALLOW_EMPTY_COMMIT_RE.search(cmd):
        return Block(
            "`git commit --allow-empty` is ad-hoc CI-trigger validation. "
            "Do not create empty commits — push a real change or re-run CI "
            "explicitly.",
        )
    return None


def _check_force_flags(cmd: str) -> Block | None:
    if FORCE_FLAGS_RE.search(cmd):
        return Block(
            "Force flags (`kill -9`, `chmod 777`) are escalation shortcuts. "
            "Use `kill -TERM` first, chmod the minimum required mode, or fix "
            "the underlying config/permissions.",
        )
    return None


def _check_pytest_collect_only(cmd: str) -> Block | None:
    if PYTEST_COLLECT_ONLY_RE.search(cmd):
        return Block(
            "`pytest --collect-only`/`--co` is ad-hoc wiring validation. "
            "Trust the framework or add a real test. See `code-writing-"
            "protocols` → No ad-hoc validation.",
        )
    return None


def _check_python_tool(cmd: str, tool: str, start: Path) -> Block | None:
    if not (_starts_with(cmd, tool) or _starts_with(cmd, f"python -m {tool}")):
        return None
    if _has_marker(start, UV_LOCK):
        return Block(
            f"This is a uv project. Use `uv run {tool}` instead of bare `{tool}`.",
        )
    if _has_marker(start, POETRY_LOCK):
        return Block(
            f"This is a poetry project. Use `poetry run {tool}` instead of bare `{tool}`.",
        )
    return None


def _check_pytest(cmd: str, start: Path) -> Block | None:
    if _starts_with(cmd, "pytest") or _starts_with(cmd, "python -m pytest"):
        return _check_python_tool(cmd, "pytest", start)
    return None


def _check_mypy(cmd: str, start: Path) -> Block | None:
    if not _starts_with(cmd, "mypy"):
        return None
    return _check_python_tool(cmd, "mypy", start)


def _check_pylint(cmd: str, start: Path) -> Block | None:
    if not _starts_with(cmd, "pylint"):
        return None
    if _has_marker(start, UV_LOCK):
        return Block("This is a uv project. Use `uv run pylint` instead of bare `pylint`.")
    return None


def _check_bare_python_script(cmd: str, start: Path) -> Block | None:
    if not PYTHON_SCRIPT_RE.match(cmd):
        return None
    if _has_marker(start, UV_LOCK):
        return Block(
            "This is a uv project. Use `uv run python ...` instead of bare `python`.",
        )
    if _has_marker(start, POETRY_LOCK):
        return Block(
            "This is a poetry project. Use `poetry run python ...` instead of bare `python`.",
        )
    return None


def _check_venv_direct(cmd: str, start: Path) -> Block | None:
    if not VENV_DIRECT_RE.search(cmd):
        return None
    if _has_marker(start, UV_LOCK):
        return Block(
            "Direct `.venv/bin/…` calls bypass uv. Use `uv run <tool>` instead — "
            "it resolves the correct interpreter and env.",
        )
    if _has_marker(start, POETRY_LOCK):
        return Block(
            "Direct `.venv/bin/…` calls bypass poetry. Use `poetry run <tool>`.",
        )
    return None


def _check_python_c_import(cmd: str, start: Path) -> Block | None:
    if not (PYTHON_C_IMPORT_RE.search(cmd) or UV_RUN_PY_C_IMPORT_RE.search(cmd)):
        return None
    if not _has_python_project(start):
        return None
    return Block(
        'Ad-hoc import check (`python -c "import X"`) is forbidden. If the '
        "import matters, add a smoke test to the suite. See `code-writing-"
        "protocols` → No ad-hoc validation.",
    )


def _npm_block_for_pnpm(start: Path) -> Block | None:
    if _has_marker(start, PNPM_LOCK):
        return Block(
            "This is a pnpm project (pnpm-lock.yaml exists). Use `pnpm install` / `pnpm add`.",
        )
    return None


def _npm_block_for_yarn(start: Path) -> Block | None:
    if _has_marker(start, YARN_LOCK):
        return Block(
            "This is a yarn project (yarn.lock exists). Use `yarn install` / `yarn add`.",
        )
    return None


def _check_npm(cmd: str, start: Path) -> Block | None:
    triggers = ("npm install", "npm i ", "npm i", "npm add", "npm ci")
    if not any(cmd.startswith(t) for t in triggers):
        return None
    block = _npm_block_for_pnpm(start)
    if block is not None:
        return block
    return _npm_block_for_yarn(start)


def _check_yarn(cmd: str, start: Path) -> Block | None:
    if not cmd.startswith(("yarn install", "yarn add")):
        return None
    block = _npm_block_for_pnpm(start)
    if block is not None:
        return block
    if _has_marker(start, NPM_LOCK):
        return Block(
            "This is an npm project (package-lock.json exists). Use `npm install`.",
        )
    return None


def _check_pnpm(cmd: str, start: Path) -> Block | None:
    if not cmd.startswith(("pnpm install", "pnpm add")):
        return None
    if _has_marker(start, NPM_LOCK):
        return Block(
            "This is an npm project (package-lock.json exists). Use `npm install`.",
        )
    return _npm_block_for_yarn(start)


def evaluate(cmd: str, start: Path) -> Block | None:
    for env_check in (_check_env_var_workaround, _check_export_cache_workaround):
        result = env_check(cmd)
        if result is not None:
            return result

    stripped = _strip_leading_env_assigns(cmd)

    for check in (
        _check_go_fmt,
        _check_pip,
        _check_venv,
        _check_no_sync,
        _check_skip_cache_flags,
        _check_allow_empty_commit,
        _check_force_flags,
        _check_pytest_collect_only,
    ):
        result = check(stripped)
        if result is not None:
            return result
    for context_check in (
        _check_uvx,
        _check_pytest,
        _check_mypy,
        _check_pylint,
        _check_bare_python_script,
        _check_venv_direct,
        _check_python_c_import,
        _check_npm,
        _check_yarn,
        _check_pnpm,
    ):
        result = context_check(stripped, start)
        if result is not None:
            return result
    return None


def main() -> int:
    env.setup()
    cmd = os.environ.get("CC_BASH_COMMAND", "")
    if not cmd:
        return hooks.ALLOW
    cwd_value = os.environ.get("PWD") or str(Path.cwd())
    start = Path(cwd_value)
    block = evaluate(cmd, start)
    if block is not None:
        sys.stderr.write(f"BLOCKED: {block.message}\n")
        return hooks.BLOCK
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
