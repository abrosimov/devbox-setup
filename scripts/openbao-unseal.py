#!/usr/bin/python3
"""Unseal the remote OpenBao server with the Shamir key kept in this Mac's Keychain.

Run by the `local.openbao-unseal` LaunchAgent. The server's forced command for the
dedicated SSH account reads one line (the key) from stdin, submits it only while
OpenBao is sealed, and answers with one JSON line. The destination (host, user, port)
comes only from the local config file, never from this repository. Every run appends
one line to the log; a Mac without the config or the Keychain item does nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TextIO

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

SECURITY = "/usr/bin/security"
SSH = "/usr/bin/ssh"
KEYCHAIN_ACCOUNT = "openbao"
KEYCHAIN_SERVICE_PREFIX = "openbao-unseal-"
# errSecItemNotFound, as `security` reports it in its exit status.
KEYCHAIN_ITEM_NOT_FOUND = 44
CONNECT_TIMEOUT_SECONDS = 10
RUN_TIMEOUT_SECONDS = 60
SSH_CONNECTION_FAILED = 255
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG = 2
LOG_MAX_BYTES = 1_048_576
DETAIL_MAX_CHARS = 300
ACTIONS = frozenset({"none", "unsealed", "failed"})
CONFIG_KEYS = frozenset({"ssh_host", "ssh_user", "ssh_port", "inventory_host"})
INVENTORY_HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
SSH_HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
SSH_USER = re.compile(r"[a-z_][a-z0-9_-]*")
MAX_PORT = 65_535

DEFAULT_CONFIG = "~/.config/openbao-unseal/config.json"
DEFAULT_LOG = "~/Library/Logs/openbao-unseal.log"
DEFAULT_IDENTITY = "~/.ssh/openbao_unseal_ed25519"


class ConfigError(Exception):
    pass


class ConfigMissingError(ConfigError):
    pass


class KeychainError(Exception):
    pass


class ProtocolError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    ssh_host: str
    ssh_user: str
    ssh_port: int | None
    inventory_host: str

    @property
    def destination(self) -> str:
        return f"{self.ssh_user}@{self.ssh_host}"

    @property
    def keychain_service(self) -> str:
        return KEYCHAIN_SERVICE_PREFIX + self.inventory_host


@dataclass(frozen=True)
class Response:
    sealed_before: bool
    sealed_after: bool
    action: str
    error: str | None


@dataclass(frozen=True)
class Outcome:
    code: int
    message: str


class Runner(Protocol):
    def run(
        self, argv: Sequence[str], *, stdin: str | None, timeout: float
    ) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(
        self, argv: Sequence[str], *, stdin: str | None, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        if stdin is None:
            return subprocess.run(
                list(argv),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        return subprocess.run(
            list(argv),
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )


def load_config(path: Path) -> Config:
    try:
        document: object = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        message = f"not configured: no {path}"
        raise ConfigMissingError(message) from error
    except OSError as error:
        message = f"cannot read {path}: {error.strerror or error}"
        raise ConfigError(message) from error
    except ValueError as error:
        message = f"{path} is not valid JSON: {error}"
        raise ConfigError(message) from error
    message = ""
    if not isinstance(document, dict):
        message = f"{path} must hold a JSON object"
        raise ConfigError(message)
    unknown = sorted(str(key) for key in document if key not in CONFIG_KEYS)
    ssh_host = document.get("ssh_host")
    ssh_user = document.get("ssh_user")
    ssh_port = document.get("ssh_port")
    inventory_host = document.get("inventory_host")
    # Every value reaches argv or a Keychain lookup; a leading '-' would turn a
    # host or user into an ssh option.
    if unknown:
        message = f"{path}: unknown keys {', '.join(unknown)}"
    elif not isinstance(ssh_host, str) or not SSH_HOST.fullmatch(ssh_host):
        message = f"{path}: ssh_host must be a host name, address or ssh alias"
    elif not isinstance(ssh_user, str) or not SSH_USER.fullmatch(ssh_user):
        message = f"{path}: ssh_user must be the server's unseal account name"
    elif not _valid_port(ssh_port):
        message = f"{path}: ssh_port must be an integer between 1 and {MAX_PORT}"
    elif not isinstance(inventory_host, str) or not INVENTORY_HOST.fullmatch(inventory_host):
        message = f"{path}: inventory_host must be the server's inventory host name"
    else:
        return Config(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_port=ssh_port if isinstance(ssh_port, int) else None,
            inventory_host=inventory_host,
        )
    raise ConfigError(message)


def _valid_port(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_PORT


def read_unseal_key(runner: Runner, service: str) -> str | None:
    completed = runner.run(
        [SECURITY, "find-generic-password", "-s", service, "-a", KEYCHAIN_ACCOUNT, "-w"],
        stdin=None,
        timeout=RUN_TIMEOUT_SECONDS,
    )
    if completed.returncode == KEYCHAIN_ITEM_NOT_FOUND:
        return None
    if completed.returncode != 0:
        message = f"security exited {completed.returncode}: {_last_line(completed.stderr)}"
        raise KeychainError(message)
    key = completed.stdout.strip()
    if not key:
        message = f"Keychain item {service} is empty"
        raise KeychainError(message)
    return key


def ssh_command(config: Config, identity: Path) -> list[str]:
    port = [] if config.ssh_port is None else ["-p", str(config.ssh_port)]
    return [
        SSH,
        *port,
        "-i",
        str(identity),
        "-T",
        "-o",
        "BatchMode=yes",
        # Offer only the unseal key: agent keys are not authorised for this
        # account and would use up the server's authentication attempts.
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"ConnectTimeout={CONNECT_TIMEOUT_SECONDS}",
        "-o",
        "ClearAllForwardings=yes",
        config.destination,
    ]


def parse_response(stdout: str) -> Response:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        message = "empty response"
        raise ProtocolError(message)
    last = lines[-1]
    try:
        document: object = json.loads(last)
    except ValueError as error:
        message = f"response is not JSON: {_clip(last)}"
        raise ProtocolError(message) from error
    if not isinstance(document, dict):
        message = f"response is not a JSON object: {_clip(last)}"
        raise ProtocolError(message)
    sealed_before = document.get("sealed_before")
    sealed_after = document.get("sealed_after")
    action = document.get("action")
    error = document.get("error")
    if not isinstance(sealed_before, bool) or not isinstance(sealed_after, bool):
        message = f"sealed_before/sealed_after missing: {_clip(last)}"
    elif not isinstance(action, str) or action not in ACTIONS:
        message = f"unknown action: {_clip(last)}"
    elif error is not None and not isinstance(error, str):
        message = f"error is not a string: {_clip(last)}"
    else:
        return Response(
            sealed_before=sealed_before, sealed_after=sealed_after, action=action, error=error
        )
    raise ProtocolError(message)


def unseal(config: Config, identity: Path, runner: Runner) -> Outcome:
    service = config.keychain_service
    try:
        key = read_unseal_key(runner, service)
    except KeychainError as error:
        return Outcome(EXIT_FAILED, f"cannot read Keychain item {service}: {error}")
    except subprocess.TimeoutExpired:
        return Outcome(EXIT_FAILED, f"security timed out after {RUN_TIMEOUT_SECONDS} s")
    if key is None:
        return Outcome(EXIT_OK, f"no Keychain item {service}; nothing to do")
    if not identity.is_file():
        return Outcome(EXIT_FAILED, f"no SSH key at {identity}")
    return submit(config, identity, key, runner)


def submit(config: Config, identity: Path, key: str, runner: Runner) -> Outcome:
    try:
        completed = runner.run(
            ssh_command(config, identity), stdin=key + "\n", timeout=RUN_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        return Outcome(EXIT_FAILED, f"ssh timed out after {RUN_TIMEOUT_SECONDS} s")
    if completed.returncode == SSH_CONNECTION_FAILED:
        return Outcome(EXIT_FAILED, f"ssh failed: {_last_line(completed.stderr)}")
    try:
        response = parse_response(completed.stdout)
    except ProtocolError as error:
        return Outcome(
            EXIT_FAILED,
            f"server exited {completed.returncode} with a bad response: {error}",
        )
    state = (
        f"sealed_before={str(response.sealed_before).lower()} "
        f"sealed_after={str(response.sealed_after).lower()}"
    )
    if completed.returncode == 0 and not response.sealed_after:
        verb = "unsealed" if response.action == "unsealed" else "already unsealed"
        return Outcome(EXIT_OK, f"{verb} ({state})")
    detail = f": {_clip(response.error)}" if response.error else ""
    return Outcome(
        EXIT_FAILED,
        f"server exited {completed.returncode}, action={response.action} ({state}){detail}",
    )


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.stat().st_size > LOG_MAX_BYTES:
            path.replace(path.with_name(path.name + ".1"))
    except FileNotFoundError:
        pass
    with path.open("a", encoding="utf-8") as log:
        log.write(line + "\n")


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return _clip(lines[-1]) if lines else "no output"


def _clip(text: str) -> str:
    return text if len(text) <= DETAIL_MAX_CHARS else text[:DETAIL_MAX_CHARS] + "..."


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unseal the remote OpenBao server from this Mac's Keychain."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--identity", default=DEFAULT_IDENTITY)
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="validate the config and exit without reading the Keychain or connecting",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    clock: Callable[[], str] = _timestamp,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    arguments = _parse_arguments(argv)
    config_path = Path(arguments.config).expanduser()
    log_path = Path(arguments.log).expanduser()
    try:
        config = load_config(config_path)
    except ConfigError as error:
        if arguments.check_config:
            print(f"openbao-unseal: {error}", file=stderr)
            return EXIT_CONFIG
        append_log(log_path, f"{clock()} openbao-unseal: {error}")
        return EXIT_OK if isinstance(error, ConfigMissingError) else EXIT_CONFIG
    if arguments.check_config:
        print(
            f"openbao-unseal: config ok ({config.destination}, "
            f"Keychain item {config.keychain_service})",
            file=stdout,
        )
        return EXIT_OK
    outcome = unseal(
        config,
        Path(arguments.identity).expanduser(),
        SubprocessRunner() if runner is None else runner,
    )
    append_log(log_path, f"{clock()} openbao-unseal {config.inventory_host}: {outcome.message}")
    return outcome.code


if __name__ == "__main__":
    raise SystemExit(main())
