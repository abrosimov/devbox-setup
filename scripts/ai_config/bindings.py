from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .core import BindingProvider, FieldBinding, FieldManifest
from .document import assign_value, snapshot_mapping
from .model import SemanticSnapshot

if TYPE_CHECKING:
    from collections.abc import Mapping


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


@dataclass(frozen=True, slots=True)
class BindingProviders:
    profile: str
    environment: Mapping[str, str]
    command_runner: CommandRunner = run_command

    @classmethod
    def system(cls, profile: str) -> BindingProviders:
        return cls(profile=profile, environment=os.environ)

    def resolve(self, binding: FieldBinding) -> str:
        match binding.provider:
            case BindingProvider.PROFILE:
                return self._resolve_profile(binding)
            case BindingProvider.ENVIRONMENT:
                return self._resolve_environment(binding)
            case BindingProvider.KEYCHAIN:
                return self._resolve_keychain(binding)

    def _resolve_profile(self, binding: FieldBinding) -> str:
        if binding.key != "devbox_active_profile":
            message = "unknown profile binding"
            raise BindingResolutionError(message)
        if not self.profile:
            message = "profile binding requires --profile"
            raise BindingResolutionError(message)
        return self.profile

    def _resolve_environment(self, binding: FieldBinding) -> str:
        value = self.environment.get(binding.key)
        if value is None:
            message = f"environment binding is unavailable: {binding.key}"
            raise BindingResolutionError(message)
        return value

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
