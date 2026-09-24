from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

REPO_CONFIG_RELATIVE_PATH = Path("roles/devbox/files/dot_codex/config.toml.j2")

# `hooks.state` is Codex's own trust/enablement bookkeeping, not a hook declaration.
_STATE_KEY = "state"
_COMMAND_HANDLER = "command"


class AllowlistError(ValueError):
    pass


@dataclass(frozen=True, slots=True, order=True)
class DeclaredHook:
    event_name: str
    command: str


@dataclass(frozen=True, slots=True)
class Allowlist:
    config_path: Path
    declared: frozenset[DeclaredHook]
    plugin_ids: frozenset[str]

    def __post_init__(self) -> None:
        if not self.declared and not self.plugin_ids:
            message = (
                "the hook trust allowlist is empty; refusing to run rather than "
                "leaving every hook untrusted or trusting hooks nobody declared"
            )
            raise AllowlistError(message)


def build_allowlist(
    *,
    repo_root: Path,
    codex_home: Path,
    plugin_ids: Sequence[str],
) -> Allowlist:
    source = repo_root / REPO_CONFIG_RELATIVE_PATH
    try:
        document = tomllib.loads(source.read_text(encoding="utf-8"))
    except OSError as error:
        message = f"cannot read the repository Codex configuration: {source}"
        raise AllowlistError(message) from error
    except tomllib.TOMLDecodeError as error:
        message = f"the repository Codex configuration is not valid TOML: {source}"
        raise AllowlistError(message) from error
    for plugin_id in plugin_ids:
        if not plugin_id.strip():
            message = "plugin identifiers in the allowlist must be non-empty"
            raise AllowlistError(message)
    return Allowlist(
        config_path=(codex_home / "config.toml").resolve(),
        declared=frozenset(_declared_hooks(document.get("hooks"), source)),
        plugin_ids=frozenset(plugin_ids),
    )


def _declared_hooks(block: object, source: Path) -> Iterator[DeclaredHook]:
    if block is None:
        return
    if not isinstance(block, dict):
        message = f"[hooks] in {source} must be a table"
        raise AllowlistError(message)
    for event_name, groups in block.items():
        if event_name == _STATE_KEY:
            continue
        for command in _commands(str(event_name), groups, source):
            yield DeclaredHook(event_name=camel_case(str(event_name)), command=command)


def _commands(event_name: str, groups: object, source: Path) -> Iterator[str]:
    if not isinstance(groups, list):
        message = f"hooks.{event_name} in {source} must be an array of hook groups"
        raise AllowlistError(message)
    for group in groups:
        entries = group.get("hooks") if isinstance(group, dict) else None
        if not isinstance(entries, list):
            message = f"hooks.{event_name} in {source} must declare a `hooks` array per group"
            raise AllowlistError(message)
        for entry in entries:
            yield _command(event_name, entry, source)


def _command(event_name: str, entry: object, source: Path) -> str:
    if not isinstance(entry, dict):
        message = f"hooks.{event_name} in {source} declares a handler that is not a table"
        raise AllowlistError(message)
    if entry.get("type") != _COMMAND_HANDLER:
        message = (
            f"hooks.{event_name} in {source} declares a "
            f"{entry.get('type')!r} handler; only command hooks can be trusted here"
        )
        raise AllowlistError(message)
    command = entry.get("command")
    if not isinstance(command, str) or not command.strip():
        message = f"hooks.{event_name} in {source} declares a handler without a command"
        raise AllowlistError(message)
    return command


def camel_case(event_name: str) -> str:
    """config.toml spells events `PreToolUse`; `hooks/list` answers `preToolUse`."""
    return event_name[:1].lower() + event_name[1:]
