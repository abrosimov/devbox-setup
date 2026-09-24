"""Load and validate the TOML configuration.

Path rules, applied to ``repo_dir`` and every ``[[dir]].path``:

* ``$VAR`` / ``${VAR}`` are expanded from the environment; an unset variable is an
  error rather than a silently literal ``$VAR`` path.
* ``~`` expands to the home directory.
* A relative path is resolved against the workspace root (``$AION_AUTOPOIESEON``).
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import cast

WORKSPACE_ENV = "AION_AUTOPOIESEON"
PROFILE_ENV = "MNEMOSYNE_PERISTASEOS"
DEFAULT_REPO_DIR = "drive/base"

# `_` separates profile, name and date in archive file names, so it is not allowed
# inside either component.
_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_UNSET_VAR_RE = re.compile(r"\$(\w+|\{[^}]*\})")


class ConfigError(Exception):
    """The configuration file is missing, malformed or inconsistent."""


@dataclass(frozen=True)
class DirSpec:
    name: str
    path: Path
    exclude: tuple[str, ...] = ()
    busy: tuple[str, ...] = ()

    def is_excluded(self, rel: PurePosixPath) -> bool:
        return any(rel.full_match(pattern) for pattern in self.exclude)


@dataclass(frozen=True)
class DeferPolicy:
    interval_minutes: int = 15
    max_wait_minutes: int = 180


@dataclass(frozen=True)
class Config:
    repo_dir: Path
    dirs: tuple[DirSpec, ...]
    defer: DeferPolicy = field(default_factory=DeferPolicy)
    zstd_level: int = 9


def validate_token(kind: str, value: str) -> str:
    if not _TOKEN_RE.fullmatch(value):
        raise ConfigError(f"{kind} {value!r} must match {_TOKEN_RE.pattern}")
    return value


def resolve_path(raw: str, env: dict[str, str]) -> Path:
    def _sub(match: re.Match[str]) -> str:
        name = match.group(1).strip("{}")
        if name not in env:
            raise ConfigError(f"path {raw!r} references unset variable ${name}")
        return env[name]

    expanded = _UNSET_VAR_RE.sub(_sub, raw)
    if expanded == "~" or expanded.startswith("~/"):
        home = env.get("HOME")
        if not home:
            raise ConfigError(f"path {raw!r} uses ~ but HOME is unset")
        expanded = home + expanded[1:]
    path = Path(expanded)
    if not path.is_absolute():
        root = env.get(WORKSPACE_ENV)
        if not root:
            raise ConfigError(f"relative path {raw!r} needs ${WORKSPACE_ENV} to be set")
        path = Path(root) / path
    return Path(os.path.normpath(path))


type Table = dict[str, object]

_MISSING = object()


def _get[T](table: Table, key: str, kind: type[T], where: str, default: object = _MISSING) -> T:
    value = table.get(key, default)
    if value is _MISSING:
        raise ConfigError(f"{where}: missing required key {key!r}")
    # bool is an int subclass; a `true` level is a typo, not a number.
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ConfigError(f"{where}: {key!r} must be {kind.__name__}")
    return value


def _table(raw: object, where: str) -> Table:
    if not isinstance(raw, dict):
        raise ConfigError(f"{where} must be a table")
    return cast(Table, raw)


def _str_list(table: Table, key: str, where: str) -> tuple[str, ...]:
    values = cast(list[object], _get(table, key, list, where, []))
    strings = tuple(v for v in values if isinstance(v, str) and v)
    if len(strings) != len(values):
        raise ConfigError(f"{where}: {key!r} must be a list of non-empty strings")
    return strings


def _check_known(table: Table, known: set[str], where: str) -> None:
    unknown = sorted(set(table) - known)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {', '.join(unknown)}")


def _parse_dir(raw: object, index: int, env: dict[str, str]) -> DirSpec:
    where = f"[[dir]] #{index + 1}"
    table = _table(raw, where)
    _check_known(table, {"name", "path", "exclude", "busy"}, where)
    name = validate_token(f"{where} name", _get(table, "name", str, where))
    exclude = _str_list(table, "exclude", where)
    for pattern in exclude:
        if pattern.startswith("/") or ".." in PurePosixPath(pattern).parts:
            raise ConfigError(f"{where}: exclude {pattern!r} must be relative to the directory")
    return DirSpec(
        name=name,
        path=resolve_path(_get(table, "path", str, where), env),
        exclude=exclude,
        busy=_str_list(table, "busy", where),
    )


def _parse_defer(raw: object) -> DeferPolicy:
    table = _table(raw, "[defer]")
    _check_known(table, {"interval_minutes", "max_wait_minutes"}, "[defer]")
    policy = DeferPolicy(
        interval_minutes=_get(table, "interval_minutes", int, "[defer]", 15),
        max_wait_minutes=_get(table, "max_wait_minutes", int, "[defer]", 180),
    )
    if policy.interval_minutes < 1 or policy.max_wait_minutes < 0:
        raise ConfigError("[defer]: interval_minutes must be >= 1, max_wait_minutes >= 0")
    return policy


def _is_within(child: Path, parent: Path) -> bool:
    return child == parent or child.is_relative_to(parent)


def parse(data: Table, env: dict[str, str]) -> Config:
    _check_known(data, {"repo_dir", "zstd_level", "defer", "dir"}, "config")
    repo_dir = resolve_path(_get(data, "repo_dir", str, "config", DEFAULT_REPO_DIR), env)
    level = _get(data, "zstd_level", int, "config", 9)
    if not 1 <= level <= 22:
        raise ConfigError("config: zstd_level must be within 1..22")

    raw_dirs = cast(list[object], _get(data, "dir", list, "config", []))
    if not raw_dirs:
        raise ConfigError("config: at least one [[dir]] table is required")
    dirs = tuple(_parse_dir(raw, i, env) for i, raw in enumerate(raw_dirs))

    seen: set[str] = set()
    for spec in dirs:
        if spec.name in seen:
            raise ConfigError(f"duplicate [[dir]] name {spec.name!r}")
        seen.add(spec.name)
        # Either nesting makes a run archive its own output.
        if _is_within(repo_dir, spec.path) or _is_within(spec.path, repo_dir):
            raise ConfigError(f"[[dir]] {spec.name!r} ({spec.path}) overlaps repo_dir {repo_dir}")

    return Config(
        repo_dir=repo_dir,
        dirs=dirs,
        defer=_parse_defer(data.get("defer", {})),
        zstd_level=level,
    )


def load(path: Path, env: dict[str, str]) -> Config:
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    return parse(data, env)


def default_config_path(env: dict[str, str]) -> Path:
    base = env.get("XDG_CONFIG_HOME") or str(Path(env.get("HOME", "~")) / ".config")
    return Path(base) / "drive-backup" / "config.toml"
