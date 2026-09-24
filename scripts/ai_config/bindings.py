from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .core import BindingProvider, FieldBinding, FieldManifest, home_binding_suffix
from .document import assign_value, snapshot_mapping
from .model import SemanticSnapshot

if TYPE_CHECKING:
    from pathlib import Path


class BindingResolutionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str


class CommandRunner(Protocol):
    def __call__(self, arguments: tuple[str, ...], /) -> CommandResult: ...


def run_command(arguments: tuple[str, ...]) -> CommandResult:
    try:
        completed = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        message = "binding provider command could not be executed"
        raise BindingResolutionError(message) from error
    return CommandResult(returncode=completed.returncode, stdout=completed.stdout)


# Bindings exist only for values a rendered artefact must never contain: a
# secret, or a path that is specific to one machine. Everything a profile decides
# is Jinja in the repository source, resolved from repository data, so that
# reconciliation never depends on the ambient shell it was invoked from.
@dataclass(frozen=True, slots=True)
class BindingProviders:
    home: Path
    command_runner: CommandRunner = run_command

    def resolve(self, binding: FieldBinding) -> str:
        match binding.provider:
            case BindingProvider.KEYCHAIN:
                return self._resolve_keychain(binding)
            case BindingProvider.HOME:
                return self._resolve_home(binding)

    def _resolve_home(self, binding: FieldBinding) -> str:
        return str(self.home / home_binding_suffix(binding.key))

    def _resolve_keychain(self, binding: FieldBinding) -> str:
        service, separator, account = binding.key.partition("/")
        if not separator or not service or not account:
            message = "keychain bindings must use service/account"
            raise BindingResolutionError(message)
        result = self.command_runner(
            (
                "security",
                "find-generic-password",
                "-s",
                service,
                "-a",
                account,
                "-w",
            )
        )
        if result.returncode != 0:
            message = "keychain binding is unavailable"
            raise BindingResolutionError(message)
        return result.stdout.rstrip("\r\n")


def resolve_snapshot_bindings(
    snapshot: SemanticSnapshot,
    manifest: FieldManifest,
    providers: BindingProviders,
) -> SemanticSnapshot:
    configuration = snapshot_mapping(snapshot)
    for rule in manifest.rules:
        if rule.binding is not None:
            assign_value(configuration, rule.path, providers.resolve(rule.binding))
    return SemanticSnapshot.from_value(configuration)
