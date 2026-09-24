from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

from .allowlist import Allowlist, AllowlistError, DeclaredHook, build_allowlist
from .appserver import (
    DEFAULT_TIMEOUT_SECONDS,
    AppServerError,
    AppServerPort,
    ClientFactoryPort,
    spawn_app_server,
)

# sysexits codes for the Ansible task that runs this
# (roles/devbox/tasks/install_codex_configs.yml): any non-zero fails the play, and
# the code says why — bad invocation, no reachable app-server, a protocol shape we
# do not recognise, or a trust state the repository refuses to accept.
EX_USAGE = 64
EX_UNAVAILABLE = 69
EX_PROTOCOL = 76
EX_CONFIG = 78

PROGRAM = "codex-hook-trust"
_PENDING_STATUSES = frozenset({"untrusted", "modified"})


class ProtocolError(ValueError):
    pass


class Ownership(StrEnum):
    CONFIG = "config"
    PLUGIN = "plugin"
    FOREIGN = "foreign"


@dataclass(frozen=True, slots=True)
class Hook:
    key: str
    event_name: str
    handler_type: str
    command: str | None
    source: str
    source_path: str
    plugin_id: str | None
    current_hash: str
    trust_status: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class HookInventory:
    hooks: tuple[Hook, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TrustPlan:
    owned: tuple[Hook, ...]
    pending: tuple[Hook, ...]
    refused: tuple[Hook, ...]
    disabled: tuple[Hook, ...]
    undiscovered: tuple[DeclaredHook, ...]

    def is_satisfied(self) -> bool:
        return not (self.pending or self.refused or self.undiscovered)


def list_hooks(client: AppServerPort, cwd: Path) -> HookInventory:
    response = client.request("hooks/list", {"cwds": [str(cwd)]})
    data = response.get("data")
    if not isinstance(data, list):
        message = "hooks/list did not answer with a `data` array"
        raise ProtocolError(message)
    hooks: list[Hook] = []
    warnings: list[str] = []
    errors: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            message = "hooks/list returned a `data` element that is not an object"
            raise ProtocolError(message)
        hooks.extend(_parse_hook(record) for record in _sequence(entry, "hooks"))
        warnings.extend(str(warning) for warning in _sequence(entry, "warnings"))
        errors.extend(_describe_error(error) for error in _sequence(entry, "errors"))
    return HookInventory(hooks=tuple(hooks), warnings=tuple(warnings), errors=tuple(errors))


def plan_trust(inventory: HookInventory, allowlist: Allowlist) -> TrustPlan:
    ownership = {hook.key: classify(hook, allowlist) for hook in inventory.hooks}
    owned = tuple(hook for hook in inventory.hooks if ownership[hook.key] is not Ownership.FOREIGN)
    foreign = tuple(hook for hook in inventory.hooks if ownership[hook.key] is Ownership.FOREIGN)
    discovered = {
        DeclaredHook(event_name=hook.event_name, command=hook.command)
        for hook in owned
        if hook.command is not None
    }
    return TrustPlan(
        owned=owned,
        pending=tuple(hook for hook in owned if hook.trust_status in _PENDING_STATUSES),
        refused=tuple(hook for hook in foreign if hook.trust_status in _PENDING_STATUSES),
        disabled=tuple(hook for hook in owned if not hook.enabled),
        undiscovered=tuple(sorted(allowlist.declared - discovered)),
    )


def classify(hook: Hook, allowlist: Allowlist) -> Ownership:
    if hook.plugin_id is not None and hook.plugin_id in allowlist.plugin_ids:
        return Ownership.PLUGIN
    declared_here = (
        hook.handler_type == "command"
        and hook.command is not None
        and Path(hook.source_path).resolve() == allowlist.config_path
        and DeclaredHook(event_name=hook.event_name, command=hook.command) in allowlist.declared
    )
    return Ownership.CONFIG if declared_here else Ownership.FOREIGN


def grant_trust(client: AppServerPort, pending: Sequence[Hook]) -> None:
    if not pending:
        return
    # `upsert` on the leaf keeps any sibling `enabled` flag the operator set in the
    # /hooks TUI; `replace` on the parent table would silently drop it. The key is
    # emitted as a quoted TOML segment because it embeds `.` (config.toml) and `:`.
    edits = [
        {
            "keyPath": f"hooks.state.{json.dumps(hook.key)}.trusted_hash",
            "mergeStrategy": "upsert",
            "value": hook.current_hash,
        }
        for hook in pending
    ]
    response = client.request("config/batchWrite", {"edits": edits})
    status = response.get("status")
    if status not in {"ok", "okOverridden"}:
        message = f"config/batchWrite reported status {status!r} instead of a successful write"
        raise ProtocolError(message)


def main(
    arguments: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    client_factory: ClientFactoryPort | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    env = dict(os.environ if environment is None else environment)
    try:
        options = _parse_arguments(arguments, env)
    except SystemExit as exit_request:
        return EX_USAGE if exit_request.code else 0
    try:
        allowlist = build_allowlist(
            repo_root=options.repo_root,
            codex_home=options.codex_home,
            plugin_ids=options.plugins,
        )
    except AllowlistError as error:
        print(f"{PROGRAM}: {error}", file=stderr)
        return EX_CONFIG

    factory = client_factory if client_factory is not None else spawn_app_server
    try:
        report = _reconcile(options, allowlist, factory, env)
    except AppServerError as error:
        print(f"{PROGRAM}: {error}", file=stderr)
        return EX_UNAVAILABLE
    except ProtocolError as error:
        print(f"{PROGRAM}: {error}", file=stderr)
        return EX_PROTOCOL

    _report(report, options=options, stdout=stdout, stderr=stderr)
    return _exit_code(report, options=options)


@dataclass(frozen=True, slots=True)
class _Options:
    repo_root: Path
    codex_home: Path
    cwd: Path
    plugins: tuple[str, ...]
    check: bool
    fail_on_drift: bool
    emit_json: bool
    timeout: float


@dataclass(frozen=True, slots=True)
class _Report:
    plan: TrustPlan
    inventory: HookInventory
    granted: tuple[Hook, ...]
    unverified: tuple[Hook, ...]


def _reconcile(
    options: _Options,
    allowlist: Allowlist,
    factory: ClientFactoryPort,
    env: Mapping[str, str],
) -> _Report:
    with factory(
        codex_home=options.codex_home,
        timeout=options.timeout,
        search_path=env.get("PATH"),
    ) as client:
        inventory = list_hooks(client, options.cwd)
        plan = plan_trust(inventory, allowlist)
        if options.check or not plan.pending:
            return _Report(plan=plan, inventory=inventory, granted=(), unverified=())
        grant_trust(client, plan.pending)
        verified = plan_trust(list_hooks(client, options.cwd), allowlist)
    return _Report(
        plan=plan,
        inventory=inventory,
        granted=plan.pending,
        unverified=verified.pending,
    )


def _exit_code(report: _Report, *, options: _Options) -> int:
    plan = report.plan
    if report.inventory.errors or plan.refused or plan.undiscovered or report.unverified:
        return EX_CONFIG
    if options.fail_on_drift and plan.pending:
        return EX_CONFIG
    return 0


def _report(report: _Report, *, options: _Options, stdout: TextIO, stderr: TextIO) -> None:
    plan = report.plan
    document: dict[str, object] = {
        "changed": bool(plan.pending) if options.check else bool(report.granted),
        "check": options.check,
        "codex_home": str(options.codex_home),
        "cwd": str(options.cwd),
        "granted": [_hook_document(hook) for hook in report.granted],
        "pending": [_hook_document(hook) for hook in plan.pending],
        "trusted": sorted(hook.key for hook in plan.owned if hook.trust_status == "trusted"),
        "managed": sorted(hook.key for hook in plan.owned if hook.trust_status == "managed"),
        "disabled": sorted(hook.key for hook in plan.disabled),
        "refused": [_hook_document(hook) for hook in plan.refused],
        "undiscovered": [
            {"event_name": declared.event_name, "command": declared.command}
            for declared in plan.undiscovered
        ],
        "unverified": [_hook_document(hook) for hook in report.unverified],
        "warnings": list(report.inventory.warnings),
        "errors": list(report.inventory.errors),
    }
    if options.emit_json:
        print(json.dumps(document, indent=2, sort_keys=True), file=stdout)
    else:
        print(_summary(report), file=stdout)
    for line in _failure_lines(report):
        print(f"{PROGRAM}: {line}", file=stderr)


def _summary(report: _Report) -> str:
    plan = report.plan
    counts = {
        "owned": len(plan.owned),
        "granted": len(report.granted),
        "pending": len(plan.pending),
        "disabled": len(plan.disabled),
        "refused": len(plan.refused),
        "undiscovered": len(plan.undiscovered),
    }
    return f"{PROGRAM}: " + " ".join(f"{name}={count}" for name, count in counts.items())


def _failure_lines(report: _Report) -> list[str]:
    lines = [f"hooks/list reported an error: {error}" for error in report.inventory.errors]
    lines += [
        f"refusing to trust {hook.key!r} ({hook.trust_status}) from {hook.source}: "
        "this repository does not declare it"
        for hook in report.plan.refused
    ]
    lines += [
        f"declared hook {declared.event_name} {declared.command!r} was not discovered by "
        "hooks/list; the configuration it should come from is not in effect"
        for declared in report.plan.undiscovered
    ]
    lines += [
        f"{hook.key!r} is still {hook.trust_status} after the trust write"
        for hook in report.unverified
    ]
    lines += [
        f"{hook.key!r} is trusted but disabled; it will not run until it is re-enabled"
        for hook in report.plan.disabled
    ]
    return lines


def _hook_document(hook: Hook) -> dict[str, object]:
    return {
        "key": hook.key,
        "event_name": hook.event_name,
        "source": hook.source,
        "plugin_id": hook.plugin_id,
        "trust_status": hook.trust_status,
        "enabled": hook.enabled,
    }


def _parse_arguments(arguments: Sequence[str] | None, env: Mapping[str, str]) -> _Options:
    default_repo_root = Path(__file__).resolve().parents[2]
    default_home = Path(env.get("CODEX_HOME") or Path(env.get("HOME", "~")) / ".codex")
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=(
            "Grant Codex hook trust for the hooks this repository declares. "
            "Hashes are read from the same binary that later verifies them."
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=default_repo_root)
    parser.add_argument("--codex-home", type=Path, default=default_home)
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="working directory hooks/list discovers against (default: CODEX_HOME)",
    )
    parser.add_argument(
        "--plugin",
        action="append",
        dest="plugins",
        default=[],
        metavar="PLUGIN@MARKETPLACE",
        help="repository-pinned plugin whose hooks may be trusted (repeatable)",
    )
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="exit non-zero when any declared hook is still untrusted",
    )
    parser.add_argument("--json", action="store_true", dest="emit_json")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parsed = parser.parse_args(list(arguments) if arguments is not None else None)
    codex_home = _anchor_at_home(parsed.codex_home, env)
    return _Options(
        repo_root=parsed.repo_root.expanduser().resolve(),
        codex_home=codex_home,
        cwd=(parsed.cwd.expanduser() if parsed.cwd is not None else codex_home),
        plugins=tuple(parsed.plugins),
        check=parsed.check,
        fail_on_drift=parsed.fail_on_drift,
        emit_json=parsed.emit_json,
        timeout=parsed.timeout,
    )


def _anchor_at_home(path: Path, env: Mapping[str, str]) -> Path:
    """dev_mode passes a home-relative CODEX_HOME (`.devbox/debug/dotfiles/.codex`).

    Ansible resolves those against the remote user's home, not the command's cwd.
    """
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded
    return Path(env.get("HOME", "~")).expanduser() / expanded


def _parse_hook(record: object) -> Hook:
    if not isinstance(record, dict):
        message = "hooks/list returned a hook entry that is not an object"
        raise ProtocolError(message)
    trust_status = _required_string(record, "trustStatus")
    if trust_status not in {"managed", "untrusted", "trusted", "modified"}:
        message = f"hooks/list reported an unrecognised trustStatus: {trust_status!r}"
        raise ProtocolError(message)
    enabled = record.get("enabled")
    if not isinstance(enabled, bool):
        message = "hooks/list returned a hook without a boolean `enabled`"
        raise ProtocolError(message)
    return Hook(
        key=_required_string(record, "key"),
        event_name=_required_string(record, "eventName"),
        handler_type=_required_string(record, "handlerType"),
        command=_optional_string(record, "command"),
        source=_required_string(record, "source"),
        source_path=_required_string(record, "sourcePath"),
        plugin_id=_optional_string(record, "pluginId"),
        current_hash=_required_string(record, "currentHash"),
        trust_status=trust_status,
        enabled=enabled,
    )


def _sequence(entry: Mapping[str, object], field: str) -> list[object]:
    value = entry.get(field)
    if not isinstance(value, list):
        message = f"hooks/list returned a `data` element without a `{field}` array"
        raise ProtocolError(message)
    return value


def _required_string(record: Mapping[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        message = f"hooks/list returned a hook without a non-empty `{field}`"
        raise ProtocolError(message)
    return value


def _optional_string(record: Mapping[str, object], field: str) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        message = f"hooks/list returned a hook whose `{field}` is neither a string nor null"
        raise ProtocolError(message)
    return value


def _describe_error(error: object) -> str:
    if isinstance(error, dict):
        return f"{error.get('path')}: {error.get('message')}"
    return str(error)
