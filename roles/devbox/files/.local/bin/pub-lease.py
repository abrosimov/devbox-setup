#!/usr/bin/python3

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import ipaddress
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TextIO, cast

if TYPE_CHECKING:
    from collections.abc import Callable

LEASE_SECONDS = 1_800
MAX_LEASE_SECONDS = 43_200
NETWORK_MISS_LIMIT = 2
EXPECTED_MODE = "warp+doh"
EXPECTED_PROTOCOL = "wireguard"
EXPECTED_PROTOCOL_SOURCE = "consumer_overrides"
LEGACY_STATE_VERSION = 1
CURRENT_STATE_VERSION = 2
LEASE_MODES = frozenset({"tunnel_only", EXPECTED_MODE})
INTERACTIVE_LOCK_TIMEOUT = 10.0
WARP_COMMAND_TIMEOUT = 5.0
LOG_MAX_BYTES = 1_048_576
INVALID_RETENTION_SECONDS = 7 * 24 * 60 * 60
SUPPORTED_MODES = frozenset({"warp", "doh", "dot", "warp+dot", "proxy"}) | LEASE_MODES
SUPPORTED_PROTOCOLS = frozenset({"masque", "wireguard"})
SUPPORTED_PROTOCOL_SOURCES = frozenset({EXPECTED_PROTOCOL_SOURCE, "network_policy"})

STATUS_CONNECTED = "Connected"
STATUS_DISCONNECTED = "Disconnected"
STATUS_CONNECTING = "Connecting"
STATUS_UNABLE_TO_CONNECT = "Unable to connect"
STATUS_REGISTRATION_MISSING = "Registration Missing"
KNOWN_STATUSES = frozenset(
    {
        STATUS_CONNECTED,
        STATUS_DISCONNECTED,
        STATUS_CONNECTING,
        STATUS_UNABLE_TO_CONNECT,
        STATUS_REGISTRATION_MISSING,
    }
)
# Statuses a lease may start from but restoration cannot be held to.
DEGRADED_STATUSES = frozenset({STATUS_CONNECTING, STATUS_UNABLE_TO_CONNECT})
CAPTURABLE_STATUSES = frozenset({STATUS_CONNECTED, STATUS_DISCONNECTED}) | DEGRADED_STATUSES

NOTIFY_TITLE = "pub mode"
NOTIFY_TIMEOUT_SECONDS = 5.0
# Title and body travel as argv, never interpolated into AppleScript source, so warp-cli output
# reaching a message cannot alter the script that displays it.
OSASCRIPT_NOTIFY = (
    "/usr/bin/osascript",
    "-e",
    "on run argv",
    "-e",
    "display notification (item 2 of argv) with title (item 1 of argv)",
    "-e",
    "end run",
    "--",
)


class WarpError(RuntimeError):
    pass


class StateError(RuntimeError):
    pass


@dataclass(frozen=True)
class WaitBudget:
    attempts: int
    progress: bool


ACTIVATION_WAIT = WaitBudget(attempts=120, progress=True)
INTERACTIVE_RESTORE_WAIT = WaitBudget(attempts=60, progress=True)
# The reconciler retries every 60s, so it can afford to block; an interactive caller cannot.
RECONCILER_RESTORE_WAIT = WaitBudget(attempts=60, progress=False)
SETTINGS_APPLY_WAIT = WaitBudget(attempts=30, progress=True)
SETTLE_WAIT = WaitBudget(attempts=10, progress=True)


class WarpPort(Protocol):
    def tunnel_settings(self) -> tuple[str, str, str]: ...

    def mode(self) -> str: ...

    def status(self) -> str: ...

    def policy_lock(self) -> str: ...

    def protocol(self) -> tuple[str, str]: ...

    def set_mode(self, mode: str) -> None: ...

    def set_protocol(self, protocol: str) -> None: ...

    def reset_protocol(self) -> None: ...

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def wait_for_status(
        self, expected: str, *, attempts: int, tick: Callable[[], None]
    ) -> bool: ...

    def wait_for_settings(
        self,
        expected: tuple[str, str, str],
        *,
        attempts: int,
        tick: Callable[[], None],
    ) -> bool: ...

    def settle_status(self, *, attempts: int, tick: Callable[[], None]) -> str: ...


class NetworkPort(Protocol):
    def signature(self) -> str | None: ...


class ReadinessPort(Protocol):
    def failure(self) -> str | None: ...


@dataclass(frozen=True)
class HTTPSReadiness:
    executable: str = "/usr/bin/curl"
    strong: bool = True

    def failure(self) -> str | None:
        return self._post_failure() if self.strong else self._head_failure()

    def _head_failure(self) -> str | None:
        try:
            result = subprocess.run(
                [
                    self.executable,
                    "-q",
                    "--noproxy",
                    "*",
                    "--head",
                    "--silent",
                    "--show-error",
                    "--output",
                    os.devnull,
                    "--connect-timeout",
                    "5",
                    "--max-time",
                    "10",
                    "https://api.anthropic.com/",
                ],
                capture_output=True,
                check=False,
                timeout=12,
            )
        except subprocess.TimeoutExpired:
            return "DNS/HTTPS readiness check timed out"
        except OSError:
            return "could not run DNS/HTTPS readiness check"
        if result.returncode == 6:
            return "system DNS could not resolve api.anthropic.com"
        if result.returncode != 0:
            return f"HTTPS readiness check failed (curl exit {result.returncode})"
        return None

    def _post_failure(self) -> str | None:
        payload_size = 16_384
        try:
            result = subprocess.run(
                [
                    self.executable,
                    "-q",
                    "--noproxy",
                    "*",
                    "--http1.1",
                    "--silent",
                    "--show-error",
                    "--output",
                    os.devnull,
                    "--connect-timeout",
                    "10",
                    "--max-time",
                    "30",
                    "--request",
                    "POST",
                    "--header",
                    "content-type: application/json",
                    "--header",
                    "anthropic-version: 2023-06-01",
                    "--data-binary",
                    "@-",
                    "--write-out",
                    "%{http_code} %{size_upload}",
                    "https://api.anthropic.com/v1/messages",
                ],
                input=b"\0" * payload_size,
                capture_output=True,
                check=False,
                timeout=35,
            )
        except subprocess.TimeoutExpired:
            return "Anthropic upload readiness check timed out"
        except OSError:
            return "could not run Anthropic upload readiness check"
        return _upload_result_failure(result, payload_size)


def _upload_result_failure(
    result: subprocess.CompletedProcess[bytes], payload_size: int
) -> str | None:
    if result.returncode == 6:
        return "system DNS could not resolve api.anthropic.com"
    if result.returncode != 0:
        return f"Anthropic upload readiness check failed (curl exit {result.returncode})"
    try:
        status_text, uploaded_text = result.stdout.decode("ascii").strip().split()
        status = int(status_text)
        uploaded = int(float(uploaded_text))
    except (UnicodeError, ValueError):
        return "Anthropic upload readiness check returned unreadable metrics"
    if status != 401:
        return f"Anthropic upload readiness check returned HTTP {status}, expected 401"
    if uploaded != payload_size:
        return f"Anthropic upload readiness check was incomplete ({uploaded}/{payload_size} bytes)"
    return None


class NotifierPort(Protocol):
    def notify(self, message: str) -> None: ...


@dataclass(frozen=True)
class LeaseState:
    version: int
    phase: str
    lease_id: str
    started_at: float
    expires_at: float
    boot_session: str
    previous_mode: str
    previous_status: str
    expected_mode: str
    previous_protocol: str | None = None
    previous_protocol_source: str | None = None
    expected_protocol: str | None = None
    expected_protocol_source: str | None = None
    network_signature: str | None = None
    network_misses: int = 0
    hard_expires_at: float | None = None
    extras: dict[str, object] = field(default_factory=dict)

    @property
    def previous_connected(self) -> bool:
        return self.previous_status == STATUS_CONNECTED

    @classmethod
    def from_object(cls, value: object) -> LeaseState:
        if not isinstance(value, dict):
            raise StateError
        fields = cast("dict[str, object]", value)
        version = _state_version(fields.get("version"))
        phase = fields.get("phase")
        lease_id = fields.get("lease_id")
        started_at = fields.get("started_at")
        expires_at = fields.get("expires_at")
        boot_session = fields.get("boot_session")
        previous_mode = fields.get("previous_mode")
        previous_connected = fields.get("previous_connected")
        expected_mode = fields.get("expected_mode")

        if not isinstance(phase, str) or phase not in {"activating", "active", "restoring"}:
            raise StateError
        if not isinstance(lease_id, str) or not lease_id:
            raise StateError
        if not _is_number(started_at) or not _is_number(expires_at):
            raise StateError
        validated_started_at = cast("int | float", started_at)
        validated_expires_at = cast("int | float", expires_at)
        if validated_expires_at < validated_started_at:
            raise StateError
        if not isinstance(boot_session, str) or not isinstance(previous_mode, str):
            raise StateError
        if type(previous_connected) is not bool:
            raise StateError
        if not isinstance(expected_mode, str) or expected_mode not in LEASE_MODES:
            raise StateError
        protocol_state = _protocol_state(fields)
        _validate_protocol_schema(version, protocol_state)
        return cls(
            version=version,
            phase=phase,
            lease_id=lease_id,
            started_at=validated_started_at,
            expires_at=validated_expires_at,
            boot_session=boot_session,
            previous_mode=previous_mode,
            previous_status=_restore_status(fields, previous_connected=previous_connected),
            expected_mode=expected_mode,
            previous_protocol=protocol_state[0],
            previous_protocol_source=protocol_state[1],
            expected_protocol=protocol_state[2],
            expected_protocol_source=protocol_state[3],
            network_signature=_network_signature(fields),
            network_misses=_network_misses(fields),
            hard_expires_at=_hard_expiry(fields, started_at=validated_started_at),
            extras={key: item for key, item in fields.items() if key not in _STATE_FIELDS},
        )

    def to_object(self) -> dict[str, object]:
        value = dict(self.extras)
        value.update(
            {
                "version": self.version,
                "phase": self.phase,
                "lease_id": self.lease_id,
                "started_at": self.started_at,
                "expires_at": self.expires_at,
                "boot_session": self.boot_session,
                "previous_mode": self.previous_mode,
                "previous_status": self.previous_status,
                "previous_connected": self.previous_connected,
                "expected_mode": self.expected_mode,
                "previous_protocol": self.previous_protocol,
                "previous_protocol_source": self.previous_protocol_source,
                "expected_protocol": self.expected_protocol,
                "expected_protocol_source": self.expected_protocol_source,
                "network_signature": self.network_signature,
                "network_misses": self.network_misses,
                "hard_expires_at": self.hard_expires_at,
            }
        )
        return value


def _restore_status(fields: dict[str, object], *, previous_connected: bool) -> str:
    # v1 leases predating restore intent carry only the boolean, so a missing previous_status
    # falls back to it and disagreement on Connected is fatal. A degraded intent has no boolean
    # encoding: a downgraded reader restores it as Disconnected, not best-effort.
    if "previous_status" not in fields:
        return STATUS_CONNECTED if previous_connected else STATUS_DISCONNECTED
    status = fields["previous_status"]
    if not isinstance(status, str) or status not in CAPTURABLE_STATUSES:
        raise StateError
    if (status == STATUS_CONNECTED) != previous_connected:
        raise StateError
    return status


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


# These three drive the reconciler, so they are validated here rather than surviving as unchecked
# extras: a "1" reaching the miss counter would raise TypeError where nothing catches it.
def _network_signature(fields: dict[str, object]) -> str | None:
    value = fields.get("network_signature")
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != _DIGEST_LENGTH:
        raise StateError
    if not set(value) <= _HEX_DIGITS:
        raise StateError
    return value


def _network_misses(fields: dict[str, object]) -> int:
    value = fields.get("network_misses", 0)
    if type(value) is not int or not 0 <= value <= NETWORK_MISS_LIMIT:
        raise StateError
    return value


def _hard_expiry(fields: dict[str, object], *, started_at: float) -> float | None:
    value = fields.get("hard_expires_at")
    if value is None:
        return None
    if not _is_number(value):
        raise StateError
    expiry = cast("int | float", value)
    if expiry < started_at:
        raise StateError
    return expiry


def _protocol_state(
    fields: dict[str, object],
) -> tuple[str | None, str | None, str | None, str | None]:
    names = (
        "previous_protocol",
        "previous_protocol_source",
        "expected_protocol",
        "expected_protocol_source",
    )
    values = tuple(fields.get(name) for name in names)
    if all(value is None for value in values):
        return None, None, None, None
    if not all(isinstance(value, str) for value in values):
        raise StateError
    previous, previous_source, expected, expected_source = cast("tuple[str, str, str, str]", values)
    if previous not in SUPPORTED_PROTOCOLS or expected not in SUPPORTED_PROTOCOLS:
        raise StateError
    if (
        previous_source not in SUPPORTED_PROTOCOL_SOURCES
        or expected_source != EXPECTED_PROTOCOL_SOURCE
        or expected != EXPECTED_PROTOCOL
    ):
        raise StateError
    return previous, previous_source, expected, expected_source


def _state_version(value: object) -> int:
    if type(value) is not int or value not in {LEGACY_STATE_VERSION, CURRENT_STATE_VERSION}:
        raise StateError
    return value


def _validate_protocol_schema(
    version: int,
    protocol_state: tuple[str | None, str | None, str | None, str | None],
) -> None:
    has_protocol_state = protocol_state[0] is not None
    if (version == LEGACY_STATE_VERSION and has_protocol_state) or (
        version == CURRENT_STATE_VERSION and not has_protocol_state
    ):
        raise StateError


_DIGEST_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")

_STATE_FIELDS = frozenset(
    {
        "version",
        "phase",
        "lease_id",
        "started_at",
        "expires_at",
        "boot_session",
        "previous_mode",
        "previous_status",
        "previous_connected",
        "expected_mode",
        "previous_protocol",
        "previous_protocol_source",
        "expected_protocol",
        "expected_protocol_source",
        "network_signature",
        "network_misses",
        "hard_expires_at",
    }
)


@dataclass(frozen=True)
class StatePaths:
    directory: Path
    log: Path

    @property
    def lease(self) -> Path:
        return self.directory / "lease.json"

    @property
    def recovery(self) -> Path:
        return self.directory / "recovery.json"

    @property
    def lock(self) -> Path:
        return self.directory / "lease.lock"

    @property
    def disabled(self) -> Path:
        return self.directory / "disabled"

    @property
    def policy_notice(self) -> Path:
        return self.directory / "policy-notice.txt"


class StateStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths

    def metadata_exists(self) -> bool:
        return self.paths.lease.exists() or self.paths.recovery.exists()

    def lease_exists(self) -> bool:
        return self.paths.lease.exists()

    def load_lease(self) -> LeaseState | None:
        return self._load(self.paths.lease)

    def load_recovery(self) -> LeaseState | None:
        return self._load(self.paths.recovery)

    def write_lease(self, state: LeaseState) -> None:
        self._atomic_write(self.paths.lease, state)

    def write_recovery(self, state: LeaseState) -> None:
        self._atomic_write(self.paths.recovery, state)

    def delete_metadata(self) -> None:
        self.paths.lease.unlink(missing_ok=True)
        self.paths.recovery.unlink(missing_ok=True)

    def write_policy_notice(self, text: str) -> None:
        # Prose, not state: nothing may restore from a breadcrumb.
        self.paths.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.paths.policy_notice.write_text(f"{text}\n", encoding="utf-8")
        self.paths.policy_notice.chmod(0o600)

    def read_policy_notice(self) -> str | None:
        try:
            text = self.paths.policy_notice.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return None
        return text or None

    def clear_policy_notice(self) -> None:
        with contextlib.suppress(OSError):
            self.paths.policy_notice.unlink(missing_ok=True)

    def quarantine(self, now: int) -> None:
        suffix = f"invalid.{now}.{os.getpid()}"
        for path in (self.paths.lease, self.paths.recovery):
            if path.exists():
                path.replace(path.with_name(f"{path.name}.{suffix}"))
        self.cleanup_invalid_state()

    def prepare_locked_operation(self) -> None:
        self.paths.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.paths.directory.chmod(0o700)
        self.cleanup_invalid_state()
        self.rotate_log_if_needed()

    def cleanup_invalid_state(self) -> None:
        if not self.paths.directory.exists():
            return
        cutoff = time.time() - INVALID_RETENTION_SECONDS
        for pattern in ("lease.json.invalid.*", "recovery.json.invalid.*"):
            for path in self.paths.directory.glob(pattern):
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()

    def rotate_log_if_needed(self) -> None:
        if not self.paths.log.is_file() or self.paths.log.stat().st_size <= LOG_MAX_BYTES:
            return
        shutil.copyfile(self.paths.log, self.paths.log.with_name(f"{self.paths.log.name}.1"))
        self.paths.log.write_bytes(b"")

    def _load(self, path: Path) -> LeaseState | None:
        if not path.is_file():
            return None
        try:
            with path.open(encoding="utf-8") as stream:
                value: object = json.load(stream)
            return LeaseState.from_object(value)
        except (OSError, UnicodeError, json.JSONDecodeError, StateError):
            return None

    def _atomic_write(self, target: Path, state: LeaseState) -> None:
        # A lease that cannot be parsed back is unrecoverable, so nothing unparseable may reach the
        # target path — neither the encoded form nor what actually landed on disk.
        LeaseState.from_object(state.to_object())
        self.paths.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix="state.", dir=self.paths.directory)
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = -1
                json.dump(state.to_object(), stream, indent=2, allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            with temporary.open(encoding="utf-8") as stream:
                written: object = json.load(stream)
            LeaseState.from_object(written)
            temporary.replace(target)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)


def _sanitised_output(text: str) -> str:
    # warp-cli output is untrusted and ends up on the terminal and in the log file.
    printable = "".join(character if character.isprintable() else " " for character in text)
    detail = " ".join(printable.split())
    return f"{detail[:497]}..." if len(detail) > 500 else detail


class WarpClient:
    def __init__(
        self,
        executable: Path,
        *,
        sleeper: Callable[[float], None] = time.sleep,
        poll_interval: float = 1.0,
        timeout: float = WARP_COMMAND_TIMEOUT,
    ) -> None:
        self.executable = executable
        self.sleeper = sleeper
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.connection_failure: str | None = None
        self.last_status = "unknown"
        self.last_reason = "unavailable"

    def tunnel_settings(self) -> tuple[str, str, str]:
        payload = self._json_command("settings")
        settings = payload.get("settings")
        sources = payload.get("sources")
        if not isinstance(settings, dict) or not isinstance(sources, dict):
            detail = "WARP tunnel settings are unavailable"
            raise WarpError(detail)
        mode = settings.get("operation_mode")
        protocol = settings.get("warp_tunnel_protocol")
        source = sources.get("warp_tunnel_protocol")
        if (
            not isinstance(mode, str)
            or not mode
            or not isinstance(protocol, str)
            or not protocol
            or not isinstance(source, str)
            or not source
        ):
            detail = "WARP tunnel settings are unavailable"
            raise WarpError(detail)
        return mode, protocol.lower(), source

    def mode(self) -> str:
        return self.tunnel_settings()[0]

    def status(self) -> str:
        self.connection_failure = None
        payload = self._json_command("status")
        status = payload.get("status")
        if not isinstance(status, str) or not status:
            raise WarpError
        self.last_status = status if status in KNOWN_STATUSES else "unknown"
        reason = payload.get("reason")
        reason_name = _safe_warp_reason(reason)
        self.last_reason = reason_name
        if status == STATUS_UNABLE_TO_CONNECT and reason_name == "Port53Bound":
            self.connection_failure = (
                "WARP DNS could not start: local port 53 is already in use (Port53Bound)"
            )
        return status

    def policy_lock(self) -> str:
        answer = self._run("settings", "mode-switch-allowed").stdout.strip()
        if answer == "true":
            return "unlocked"
        if answer == "false":
            return "switch_locked"
        # An unreadable probe is a broken probe, not proof that an administrator owns the mode.
        # Calling it locked would delete the only record of the mode to restore.
        detail = f"unreadable mode-switch policy: {_sanitised_output(answer)}"
        raise WarpError(detail)

    def protocol(self) -> tuple[str, str]:
        _, protocol, source = self.tunnel_settings()
        return protocol, source

    def set_mode(self, mode: str) -> None:
        self._command("mode", mode)

    def set_protocol(self, protocol: str) -> None:
        names = {"masque": "MASQUE", "wireguard": "WireGuard"}
        try:
            name = names[protocol]
        except KeyError as error:
            detail = "unsupported WARP tunnel protocol"
            raise WarpError(detail) from error
        self._command("tunnel", "protocol", "set", name)

    def reset_protocol(self) -> None:
        self._command("tunnel", "protocol", "reset")

    def connect(self) -> None:
        self._command("connect")

    def disconnect(self) -> None:
        self._command("disconnect")

    def wait_for_status(self, expected: str, *, attempts: int, tick: Callable[[], None]) -> bool:
        status = self._poll(lambda status: status == expected, attempts=attempts, tick=tick)
        if status is None and expected == STATUS_CONNECTED and self.connection_failure is not None:
            raise WarpError(self.connection_failure)
        return status is not None

    def wait_for_settings(
        self,
        expected: tuple[str, str, str],
        *,
        attempts: int,
        tick: Callable[[], None],
    ) -> bool:
        last_error: WarpError | None = None
        for attempt in range(attempts):
            try:
                last_error = None
                if self.tunnel_settings() == expected:
                    return True
            except WarpError as error:
                last_error = error
            if attempt + 1 < attempts:
                tick()
                self.sleeper(self.poll_interval)
        if last_error is not None:
            raise last_error
        return False

    def settle_status(self, *, attempts: int, tick: Callable[[], None]) -> str:
        settled = self._poll(
            lambda status: status != STATUS_CONNECTING,
            attempts=attempts,
            tick=tick,
        )
        return STATUS_CONNECTING if settled is None else settled

    def _poll(
        self,
        accepts: Callable[[str], bool],
        *,
        attempts: int,
        tick: Callable[[], None],
    ) -> str | None:
        last_error: WarpError | None = None
        for attempt in range(attempts):
            try:
                status = self.status()
                last_error = None
                if accepts(status):
                    return status
            except WarpError as error:
                last_error = error
            if attempt + 1 < attempts:
                tick()
                self.sleeper(self.poll_interval)
        if last_error is not None:
            raise last_error
        if self.last_status != "unknown" and self.connection_failure is None:
            self.connection_failure = (
                f"last WARP status={self.last_status}, reason={self.last_reason}"
            )
        return None

    def _json_command(self, command: str) -> dict[str, object]:
        result = self._run("-j", command)
        try:
            value: object = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise WarpError from error
        if not isinstance(value, dict):
            raise WarpError
        return cast("dict[str, object]", value)

    def _command(self, *arguments: str) -> None:
        self._run(*arguments)

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                [str(self.executable), *arguments],
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as error:
            detail = "warp-cli command timed out"
            raise WarpError(detail) from error
        except OSError as error:
            detail = "warp-cli command could not be started"
            raise WarpError(detail) from error
        if result.returncode != 0:
            raise WarpError(_sanitised_output(result.stderr))
        return result


_SAFE_WARP_REASONS = frozenset(
    {
        "CheckingNetwork",
        "ConnectivityCheckFailed",
        "NetworkHealthy",
        "PerformingConnectivityChecks",
        "PerformingHappyEyeballs",
        "Port53Bound",
    }
)


def _safe_warp_reason(value: object) -> str:
    if isinstance(value, str) and value in _SAFE_WARP_REASONS:
        return value
    if isinstance(value, dict):
        matches = sorted(str(key) for key in value if key in _SAFE_WARP_REASONS)
        if matches:
            return ",".join(matches)
    return "unavailable"


class SystemNetwork:
    # Absolute paths: the LaunchDaemon supplies no login shell and its PATH is not this program's
    # to trust. Every input is read locally — no root, no Location Services, no network request.
    def __init__(
        self,
        *,
        scutil: Path = Path("/usr/sbin/scutil"),
        arp: Path = Path("/usr/sbin/arp"),
        timeout: float = 5.0,
    ) -> None:
        self.scutil = scutil
        self.arp = arp
        self.timeout = timeout

    def signature(self) -> str | None:
        route = self._primary_route()
        if route is None:
            return None
        router, interface = route
        gateway_mac = self._gateway_mac(router, interface)
        if gateway_mac is None:
            return None
        # The interface locates the route and the ARP entry but is deliberately left out of the
        # digest: the same gateway reached over en0 or a dock's en16 is the same network.
        return hashlib.sha256(f"{router}\n{gateway_mac}".encode()).hexdigest()

    def _primary_route(self) -> tuple[str, str] | None:
        # scutil prints "Permission denied" and still exits 0, so the parse decides, not the status.
        output = self._read([str(self.scutil)], stdin="show State:/Network/Global/IPv4\n")
        if output is None:
            return None
        values = _scutil_values(output)
        router = values.get("Router", "")
        interface = values.get("PrimaryInterface", "")
        if not _is_ipv4(router) or not interface.isalnum():
            return None
        return router, interface

    def _gateway_mac(self, router: str, interface: str) -> str | None:
        output = self._read([str(self.arp), "-n", "-i", interface, router])
        return None if output is None else _normalised_mac(output)

    def _read(self, command: list[str], *, stdin: str = "") -> str | None:
        try:
            result = subprocess.run(
                command,
                input=stdin,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return None if result.returncode != 0 else result.stdout


def _scutil_values(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    return values


def _is_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        return False
    return True


def _normalised_mac(arp_output: str) -> str | None:
    # arp renders the gateway as c4:f:a6:64:be:10 while other macOS sources render the same address
    # as c4:0f:a6:64:be:10, so octets are zero-padded before they can reach the digest.
    tokens = arp_output.split()
    if "at" not in tokens:
        return None
    address = tokens.index("at") + 1
    if address >= len(tokens):
        return None
    octets = tokens[address].split(":")
    if len(octets) != 6:
        return None
    normalised: list[str] = []
    for octet in octets:
        if len(octet) not in {1, 2} or not set(octet.lower()) <= _HEX_DIGITS:
            return None
        normalised.append(f"{int(octet, 16):02x}")
    return ":".join(normalised)


@dataclass(frozen=True)
class FixedNetwork:
    value: str | None

    def signature(self) -> str | None:
        return self.value


@dataclass(frozen=True)
class CommandNotifier:
    command: tuple[str, ...]
    timeout: float = NOTIFY_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls, environment: dict[str, str]) -> CommandNotifier:
        override = environment.get("PUB_NOTIFY_COMMAND")
        if override is not None:
            return cls((override,) if override else ())
        # launchctl asuser adopts the target user's Mach bootstrap namespace (man launchctl) — the
        # only documented route from a system-domain job into the GUI session that renders these.
        return cls(("/bin/launchctl", "asuser", str(os.getuid()), *OSASCRIPT_NOTIFY))

    def notify(self, message: str) -> None:
        if not self.command:
            return
        # Best effort by contract: no delivery failure may change the outcome of a lease operation.
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(
                [*self.command, NOTIFY_TITLE, message],
                capture_output=True,
                check=False,
                timeout=self.timeout,
            )


class Progress:
    # Ticks fire only after a poll has missed, so an instant operation stays silent.
    def __init__(self, stream: TextIO, activity: str, *, enabled: bool) -> None:
        self.stream = stream
        self.activity = activity
        self.enabled = enabled
        self.started = False

    def tick(self) -> None:
        if not self.enabled:
            return
        if not self.started:
            self.stream.write(f"pub: {self.activity}")
            self.started = True
        self.stream.write(".")
        self.stream.flush()

    def finish(self) -> None:
        if self.started:
            self.stream.write("\n")
            self.stream.flush()


class ReconcileOutcome(Enum):
    UNCHANGED = "unchanged"
    RESTORED = "restored"
    OWNERSHIP_LOST = "ownership_lost"
    FAILED = "failed"


class Controller:
    def __init__(
        self,
        store: StateStore,
        warp: WarpPort,
        network: NetworkPort,
        notifier: NotifierPort,
        *,
        readiness: ReadinessPort,
        clock: Callable[[], int],
        boot_session: Callable[[], str],
        stdout: TextIO = sys.stdout,
        stderr: TextIO = sys.stderr,
        interactive: bool,
    ) -> None:
        self.store = store
        self.warp = warp
        self.network = network
        self.notifier = notifier
        self.readiness = readiness
        self.clock = clock
        self.boot_session = boot_session
        self.stdout = stdout
        self.stderr = stderr
        self.interactive = interactive
        self._warp_failure: WarpError | None = None

    def on(self) -> int:
        if self.store.paths.disabled.is_file():
            return self._fail("pub mode is disabled by the current configuration")
        context = self._time_context()
        if context is None:
            return self._fail("could not identify the current boot session")

        outcome = self._reconcile_locked(INTERACTIVE_RESTORE_WAIT)
        if outcome is ReconcileOutcome.FAILED:
            return 1
        if not self._policy_allows_activation():
            return 1
        if self.store.lease_exists():
            return self._renew(*context)
        return self._activate(*context)

    def _renew(self, now: int, boot_id: str) -> int:
        state = self.store.load_lease()
        if state is None:
            return self._fail("invalid lease state and recovery snapshot")
        if state.expected_mode != EXPECTED_MODE or state.expected_protocol is None:
            if not self._restore_previous_state(INTERACTIVE_RESTORE_WAIT):
                return self._fail("legacy lease restoration failed; migration will retry")
            return self._activate(now, boot_id, prior=state)
        if not self._ensure_tunnel_ready():
            return self._readiness_failed()
        # Re-homing is deliberate: pub on at a different pub adopts that network rather than
        # failing its own signature check on the next reconcile. An existing ceiling does not move.
        renewed = replace(
            state,
            phase="active",
            started_at=now,
            expires_at=_renewed_expiry(state, now),
            boot_session=boot_id,
            network_signature=self.network.signature(),
            network_misses=0,
            hard_expires_at=(
                state.hard_expires_at
                if state.hard_expires_at is not None
                else now + MAX_LEASE_SECONDS
            ),
        )
        try:
            self.store.write_lease(renewed)
        except (OSError, StateError, TypeError, ValueError):
            return self._fail(
                "WARP tunnel is ready, but renewed lease metadata could not be saved; "
                "previous expiry remains unchanged"
            )
        print(f"pub mode renewed until {_format_epoch(renewed.expires_at)}", file=self.stdout)
        return 0

    def _activate(self, now: int, boot_id: str, *, prior: LeaseState | None = None) -> int:
        previous = self._previous_warp_state()
        if previous is None:
            return 1
        previous_mode, previous_status, previous_protocol, previous_protocol_source = previous
        self.store.clear_policy_notice()

        state = LeaseState(
            version=CURRENT_STATE_VERSION,
            phase="activating",
            lease_id=str(uuid.uuid4()),
            started_at=now,
            expires_at=now + LEASE_SECONDS,
            boot_session=boot_id,
            previous_mode=previous_mode,
            previous_status=previous_status,
            expected_mode=EXPECTED_MODE,
            previous_protocol=previous_protocol,
            previous_protocol_source=previous_protocol_source,
            expected_protocol=EXPECTED_PROTOCOL,
            expected_protocol_source=EXPECTED_PROTOCOL_SOURCE,
            hard_expires_at=now + MAX_LEASE_SECONDS,
        )
        if prior is not None:
            state = replace(
                state,
                lease_id=prior.lease_id,
                previous_mode=prior.previous_mode,
                previous_status=prior.previous_status,
                previous_protocol=previous_protocol,
                previous_protocol_source=previous_protocol_source,
                expires_at=_renewed_expiry(prior, now),
                hard_expires_at=prior.hard_expires_at or now + MAX_LEASE_SECONDS,
                extras=prior.extras,
            )
        # The recovery snapshot must exist on disk before any WARP mutation; a crash mid-transition
        # would otherwise lose the previous mode forever.
        try:
            self.store.write_recovery(state)
            self.store.write_lease(state)
        except (OSError, StateError, TypeError, ValueError):
            return self._fail("could not save activation metadata; WARP left unchanged")
        if not self._ensure_tunnel_ready():
            return self._readiness_failed()
        try:
            # Captured with the tunnel already up, so it is comparable with what every later
            # reconcile reads; a signature taken before the mode change would not be.
            self.store.write_lease(
                replace(state, phase="active", network_signature=self.network.signature())
            )
        except (OSError, StateError, TypeError, ValueError):
            return self._fail(
                "WARP tunnel is ready, but activation metadata could not be finalised; "
                "recovery retained"
            )
        print(f"pub mode ON until {_format_epoch(state.expires_at)}", file=self.stdout)
        return 0

    def off(self, *, force: bool = False) -> int:
        if not self.store.metadata_exists():
            return self._report_already_off()
        outcome = self._reconcile_locked(INTERACTIVE_RESTORE_WAIT)
        if outcome is ReconcileOutcome.FAILED:
            return self._handle_failed_reconcile(force=force)
        if not self.store.lease_exists():
            if outcome in {ReconcileOutcome.RESTORED, ReconcileOutcome.OWNERSHIP_LOST}:
                return 0
            return self._report_already_off()
        if not self._restore_previous_state(INTERACTIVE_RESTORE_WAIT):
            return self._fail("WARP restoration failed; will retry automatically")
        print("pub mode OFF; previous WARP state restored", file=self.stdout)
        return 0

    def _report_already_off(self) -> int:
        return _report_already_off(self.store, self.stdout)

    def status(self) -> int:
        print(
            f"WARP: mode={self._mode_or_unknown()}, status={self._status_or_unknown()}",
            file=self.stdout,
        )
        notice = self.store.read_policy_notice()
        if notice is not None:
            print(f"pub: {notice}", file=self.stdout)
        if not self.store.metadata_exists():
            print("pub lease: inactive", file=self.stdout)
            return 0
        state = self.store.load_lease()
        if state is None:
            if self.store.load_recovery() is not None:
                return self._fail(
                    "corrupt lease state; recovery snapshot is available to pub off/reconcile"
                )
            return self._fail("corrupt lease state and recovery snapshot")
        remaining = max(0, int(state.expires_at - self.clock()))
        hours, remainder = divmod(remaining, 3600)
        minutes = remainder // 60
        print(
            f"pub lease: phase={state.phase}, expires={_format_epoch(state.expires_at)}, "
            f"remaining={hours}h{minutes:02d}m",
            file=self.stdout,
        )
        return 0

    def reconcile(self) -> int:
        return (
            1 if self._reconcile_locked(RECONCILER_RESTORE_WAIT) is ReconcileOutcome.FAILED else 0
        )

    def _reconcile_locked(self, restore: WaitBudget) -> ReconcileOutcome:
        if not self.store.metadata_exists():
            return ReconcileOutcome.UNCHANGED
        state = self._recover_state()
        if state is None:
            return ReconcileOutcome.FAILED
        policy = self._inspect_policy_ownership(state)
        if policy is not ReconcileOutcome.UNCHANGED:
            return policy
        ownership = self._inspect_mode_ownership(state)
        if ownership is not ReconcileOutcome.UNCHANGED:
            return ownership
        state, renewal = self._renew_against_network(state, restore)
        if renewal is not None:
            return renewal
        return self._close_if_needed(state, restore)

    def _recover_state(self) -> LeaseState | None:
        state = self.store.load_lease()
        recovery = self.store.load_recovery()
        try:
            if state is not None and recovery is None:
                self.store.write_recovery(state)
            elif state is None and recovery is not None:
                state = replace(recovery, phase="restoring")
                self.store.write_lease(state)
                print(
                    "pub: corrupt lease metadata recovered from immutable snapshot",
                    file=self.stderr,
                )
        except (OSError, StateError, TypeError, ValueError):
            state = None
        if state is None:
            self._fail("invalid lease state and recovery snapshot")
        return state

    def _inspect_policy_ownership(self, state: LeaseState) -> ReconcileOutcome:
        policy_lock = self._policy_lock()
        if policy_lock is None:
            self._fail("could not inspect WARP policy; lease retained")
            return ReconcileOutcome.FAILED
        if policy_lock != "unlocked":
            return self._drop_policy_controlled_lease(state, policy_lock)
        return ReconcileOutcome.UNCHANGED

    def _inspect_mode_ownership(self, state: LeaseState) -> ReconcileOutcome:
        try:
            current_mode = self.warp.mode()
            current_protocol = self.warp.protocol() if state.expected_protocol is not None else None
        except WarpError as error:
            self._remember_warp_failure(error)
            self._fail("could not inspect WARP state; lease retained")
            return ReconcileOutcome.FAILED
        # A manual mode change ends ownership; a manual disconnect only pauses the tunnel, so the
        # expected mode still counts as owned and the restoration snapshot is kept.
        transitional = state.phase in {"activating", "restoring"}
        owns_mode = current_mode == state.expected_mode or (
            transitional and current_mode == state.previous_mode
        )
        expected_protocol = (state.expected_protocol, state.expected_protocol_source)
        previous_protocol = (state.previous_protocol, state.previous_protocol_source)
        owns_protocol = (
            current_protocol is None
            or current_protocol == expected_protocol
            or (transitional and current_protocol == previous_protocol)
        )
        if owns_mode and owns_protocol:
            return ReconcileOutcome.UNCHANGED
        self.store.delete_metadata()
        protocol_detail = ""
        if current_protocol is not None:
            protocol_detail = f", protocol={current_protocol[0]}, source={current_protocol[1]}"
        self._announce(
            "lease ownership lost; WARP left unchanged "
            f"(mode={current_mode}{protocol_detail}, status={self._status_or_unknown()})",
            self.stderr,
        )
        return ReconcileOutcome.OWNERSHIP_LOST

    def _close_if_needed(self, state: LeaseState, restore: WaitBudget) -> ReconcileOutcome:
        if state.phase in {"activating", "restoring"}:
            if not self._restore_previous_state(restore):
                self._fail("WARP restoration pending; will retry")
                return ReconcileOutcome.FAILED
            self._announce(
                "interrupted WARP transition completed; previous WARP state restored",
                self.stdout,
            )
            return ReconcileOutcome.RESTORED

        context = self._time_context()
        if context is None:
            self._fail("could not identify the current boot session")
            return ReconcileOutcome.FAILED
        now, boot_id = context
        boot_changed = boot_id != state.boot_session
        if now < state.expires_at and not boot_changed:
            return ReconcileOutcome.UNCHANGED
        if boot_changed:
            closure_reason = "boot session changed"
        elif state.hard_expires_at is not None and now >= state.hard_expires_at:
            closure_reason = "maximum lease duration reached"
        else:
            closure_reason = "lease expired"
        return self._close_lease(closure_reason, restore)

    def _close_lease(self, closure_reason: str, restore: WaitBudget) -> ReconcileOutcome:
        if not self._restore_previous_state(restore):
            self._fail(f"{closure_reason}, but WARP restoration failed; will retry")
            return ReconcileOutcome.FAILED
        self._announce(f"{closure_reason}; previous WARP state restored", self.stdout)
        return ReconcileOutcome.RESTORED

    def _renew_against_network(
        self, state: LeaseState, restore: WaitBudget
    ) -> tuple[LeaseState, ReconcileOutcome | None]:
        # Guarded so renewal never revives a lease another rule is about to close: transitional
        # phases belong to _close_if_needed, and an elapsed expiry is dead rather than renewable.
        # A boot-session change needs no guard — _close_if_needed closes on it whatever the expiry.
        if state.network_signature is None or state.phase != "active":
            return state, None
        now = self.clock()
        if now >= state.expires_at:
            return state, None
        observed = self.network.signature()
        if observed is None:
            # Asleep, link-down and mid-DHCP are indistinguishable here and all three are
            # transient, so the lease is neither renewed nor penalised: it ages out on expiry.
            return state, None
        if observed != state.network_signature:
            return self._count_network_miss(state, restore)
        if state.hard_expires_at is not None and now >= state.hard_expires_at:
            return state, self._close_lease("maximum lease duration reached", restore)
        return self._store_renewal(
            replace(state, expires_at=_renewed_expiry(state, now), network_misses=0)
        )

    def _count_network_miss(
        self, state: LeaseState, restore: WaitBudget
    ) -> tuple[LeaseState, ReconcileOutcome | None]:
        misses = state.network_misses + 1
        if misses >= NETWORK_MISS_LIMIT:
            return state, self._close_lease("network changed", restore)
        return self._store_renewal(replace(state, network_misses=misses))

    def _store_renewal(self, state: LeaseState) -> tuple[LeaseState, ReconcileOutcome | None]:
        try:
            self.store.write_lease(state)
        except (OSError, StateError, TypeError, ValueError):
            self._fail("lease renewal could not be saved; the lease keeps its current expiry")
            return state, ReconcileOutcome.FAILED
        return state, None

    def _ensure_tunnel_ready(self) -> bool:
        try:
            if not self._prepare_tunnel():
                return False
            self.warp.connect()
            if not self._wait_for_status(
                STATUS_CONNECTED, ACTIVATION_WAIT, "waiting for the WARP tunnel"
            ):
                return False
            if not self._tunnel_matches_expected():
                return False
        except WarpError as error:
            self._remember_warp_failure(error)
            return False
        failure = self.readiness.failure()
        if failure is not None:
            self._fail(failure)
            return False
        return True

    def _prepare_tunnel(self) -> bool:
        if self._tunnel_matches_expected():
            return True
        self.warp.disconnect()
        if not self._wait_for_status(
            STATUS_DISCONNECTED,
            INTERACTIVE_RESTORE_WAIT,
            "leaving the previous WARP mode",
        ):
            return False
        self.warp.set_mode(EXPECTED_MODE)
        self.warp.set_protocol(EXPECTED_PROTOCOL)
        progress = self._progress("waiting for WARP settings to apply", SETTINGS_APPLY_WAIT)
        try:
            return self.warp.wait_for_settings(
                (EXPECTED_MODE, EXPECTED_PROTOCOL, EXPECTED_PROTOCOL_SOURCE),
                attempts=SETTINGS_APPLY_WAIT.attempts,
                tick=progress.tick,
            )
        finally:
            progress.finish()

    def _tunnel_matches_expected(self) -> bool:
        return self.warp.tunnel_settings() == (
            EXPECTED_MODE,
            EXPECTED_PROTOCOL,
            EXPECTED_PROTOCOL_SOURCE,
        )

    def _readiness_failed(self) -> int:
        restored = self._restore_previous_state(INTERACTIVE_RESTORE_WAIT)
        outcome = (
            "previous state restored" if restored else "restoration pending; recovery retained"
        )
        return self._fail(f"WARP tunnel did not become ready; {outcome}")

    def _restore_previous_state(self, budget: WaitBudget) -> bool:
        state = self.store.load_lease()
        if state is None:
            return False
        if state.previous_mode not in SUPPORTED_MODES:
            self._fail(f"saved WARP mode is unsupported: {state.previous_mode}")
            return False
        try:
            restored = self._perform_restore(state, budget)
        except (OSError, StateError, TypeError, ValueError, WarpError) as error:
            if isinstance(error, WarpError):
                self._remember_warp_failure(error)
            return False
        return restored

    def _perform_restore(self, state: LeaseState, budget: WaitBudget) -> bool:
        self.store.write_lease(replace(state, phase="restoring"))
        if state.previous_protocol is not None:
            self.warp.disconnect()
            if not self._wait_for_status(
                STATUS_DISCONNECTED, budget, "disconnecting for WARP restoration"
            ):
                return False
            self._restore_protocol(state)
        self.warp.set_mode(state.previous_mode)
        if state.previous_protocol is not None and not self._wait_for_settings(
            (
                state.previous_mode,
                state.previous_protocol,
                cast("str", state.previous_protocol_source),
            ),
            SETTINGS_APPLY_WAIT,
            "waiting for previous WARP settings to apply",
        ):
            return False
        if not self._restore_connection(state.previous_status, budget):
            return False
        if not self._restored_state_matches(state):
            return False
        self.store.delete_metadata()
        return True

    def _restored_state_matches(self, state: LeaseState) -> bool:
        if self.warp.mode() != state.previous_mode:
            return False
        return state.previous_protocol is None or self.warp.protocol() == (
            state.previous_protocol,
            state.previous_protocol_source,
        )

    def _restore_protocol(self, state: LeaseState) -> None:
        if state.previous_protocol_source == "network_policy":
            self.warp.reset_protocol()
            return
        if (
            state.previous_protocol_source == EXPECTED_PROTOCOL_SOURCE
            and state.previous_protocol is not None
        ):
            self.warp.set_protocol(state.previous_protocol)
            return
        raise StateError

    def _restore_connection(self, previous_status: str, budget: WaitBudget) -> bool:
        activity = "restoring the previous WARP state"
        if previous_status == STATUS_DISCONNECTED:
            self.warp.disconnect()
            return self._wait_for_status(STATUS_DISCONNECTED, budget, activity)
        if previous_status == STATUS_CONNECTED:
            self.warp.connect()
            return self._wait_for_status(STATUS_CONNECTED, budget, activity)
        # Only a pre-lease state that really was connected may hold the lease open until it
        # reconnects. A degraded one aims to reconnect, but neither a refused connection nor an
        # unreadable status may strand the lease on the network that degraded it.
        with contextlib.suppress(WarpError):
            self.warp.connect()
            self._wait_for_status(STATUS_CONNECTED, budget, activity)
        return True

    def _wait_for_status(self, expected: str, budget: WaitBudget, activity: str) -> bool:
        progress = self._progress(activity, budget)
        try:
            return self.warp.wait_for_status(expected, attempts=budget.attempts, tick=progress.tick)
        finally:
            progress.finish()

    def _wait_for_settings(
        self,
        expected: tuple[str, str, str],
        budget: WaitBudget,
        activity: str,
    ) -> bool:
        progress = self._progress(activity, budget)
        try:
            return self.warp.wait_for_settings(
                expected,
                attempts=budget.attempts,
                tick=progress.tick,
            )
        finally:
            progress.finish()

    def _progress(self, activity: str, budget: WaitBudget) -> Progress:
        # Progress is chatter, not result: stdout carries only what a scripted caller may match.
        return Progress(self.stderr, activity, enabled=budget.progress and self.interactive)

    def _force_off_without_snapshot(self) -> int:
        # With both metadata files unreadable the previous mode is unknown, so stop the tunnel but
        # restore nothing — guessing a mode is worse than leaving the user to set one.
        try:
            if self.warp.mode() in LEASE_MODES:
                self.warp.disconnect()
                if not self._wait_for_status(
                    STATUS_DISCONNECTED,
                    INTERACTIVE_RESTORE_WAIT,
                    "stopping the WARP tunnel",
                ):
                    return 1
            self.store.quarantine(self.clock())
        except WarpError as error:
            self._remember_warp_failure(error)
            return self._fail("could not inspect or update WARP state")
        except (OSError, StateError):
            return 1
        print(
            "pub: WARNING: recovery snapshot unavailable; metadata quarantined and prior WARP "
            "mode was not guessed",
            file=self.stderr,
        )
        return 0

    def _mode_or_unknown(self) -> str:
        try:
            return self.warp.mode()
        except WarpError:
            return "unknown"

    def _status_or_unknown(self) -> str:
        try:
            return self.warp.status()
        except WarpError:
            return "unknown"

    def _policy_lock(self) -> str | None:
        try:
            return self.warp.policy_lock()
        except WarpError as error:
            self._remember_warp_failure(error)
            return None

    def _time_context(self) -> tuple[int, str] | None:
        try:
            return self.clock(), self.boot_session()
        except (OSError, ValueError):
            return None

    def _drop_policy_controlled_lease(
        self, state: LeaseState, policy_lock: str
    ) -> ReconcileOutcome:
        # Policy is inspected before ownership, so the mode may already have moved — mid-restoration
        # or by the administrator. The breadcrumb must report what was read, never expected_mode.
        observed_mode = self._mode_or_unknown()
        self.store.delete_metadata()
        self._record_policy_notice(state, policy_lock, observed_mode)
        self._announce(
            f"lease ownership lost to WARP policy ({policy_lock}); WARP left unchanged "
            f"(mode={observed_mode}, status={self._status_or_unknown()})",
            self.stderr,
        )
        return ReconcileOutcome.OWNERSHIP_LOST

    def _record_policy_notice(
        self, state: LeaseState, policy_lock: str, observed_mode: str
    ) -> None:
        notice = (
            f"lease was dropped by WARP policy ({policy_lock}) at "
            f"{_format_epoch(self.clock())}; WARP was left as it was found "
            f"(mode={observed_mode}) and the mode before the lease was {state.previous_mode}. "
            "This note is advisory only — pub will not restore that mode."
        )
        # Yielding to an administrator must not be able to fail.
        with contextlib.suppress(OSError):
            self.store.write_policy_notice(notice)

    def _policy_allows_activation(self) -> bool:
        policy_lock = self._policy_lock()
        if policy_lock is None:
            self._fail("could not inspect WARP policy")
            return False
        if policy_lock != "unlocked":
            self._fail(f"WARP policy {policy_lock} prevents a restorable pub lease")
            return False
        return True

    def _previous_warp_state(self) -> tuple[str, str, str, str] | None:
        previous_mode = self._previous_mode()
        previous_status = self._previous_status()
        previous_protocol = self._previous_protocol()
        if previous_mode is None or previous_status is None or previous_protocol is None:
            return None
        return previous_mode, previous_status, *previous_protocol

    def _previous_mode(self) -> str | None:
        try:
            previous_mode = self.warp.mode()
        except WarpError as error:
            self._remember_warp_failure(error)
            self._fail("could not read WARP mode")
            return None
        if previous_mode not in SUPPORTED_MODES:
            self._fail(f"current WARP mode is unsupported: {previous_mode}")
            return None
        return previous_mode

    def _previous_status(self) -> str | None:
        previous_status = self._settled_warp_status()
        if previous_status is None:
            return None
        if previous_status == STATUS_REGISTRATION_MISSING:
            self._fail("WARP has no registration; no mode change can produce a working tunnel")
            return None
        if previous_status not in KNOWN_STATUSES:
            self._fail(f"WARP is not in a stable state: {previous_status}")
            return None
        if previous_status in DEGRADED_STATUSES:
            self._warn_degraded_previous_state(previous_status)
        return previous_status

    def _previous_protocol(self) -> tuple[str, str] | None:
        try:
            previous_protocol, previous_protocol_source = self.warp.protocol()
        except WarpError as error:
            self._remember_warp_failure(error)
            self._fail("could not read WARP tunnel protocol")
            return None
        if previous_protocol not in SUPPORTED_PROTOCOLS:
            self._fail(f"current WARP tunnel protocol is unsupported: {previous_protocol}")
            return None
        if previous_protocol_source not in SUPPORTED_PROTOCOL_SOURCES:
            self._fail("current WARP tunnel protocol source is unsupported")
            return None
        return previous_protocol, previous_protocol_source

    def _settled_warp_status(self) -> str | None:
        try:
            status = self.warp.status()
            return status if status != STATUS_CONNECTING else self._settle_status()
        except WarpError as error:
            self._remember_warp_failure(error)
            self._fail("could not read WARP status")
            return None

    def _settle_status(self) -> str:
        activity = "waiting for WARP to settle"
        progress = self._progress(activity, SETTLE_WAIT)
        try:
            return self.warp.settle_status(attempts=SETTLE_WAIT.attempts, tick=progress.tick)
        finally:
            progress.finish()

    def _warn_degraded_previous_state(self, previous_status: str) -> None:
        print(
            f"pub: WARP was already degraded before the lease (status={previous_status}); "
            "restore will aim to reconnect but will end the lease even if it cannot",
            file=self.stderr,
        )

    def _handle_failed_reconcile(self, *, force: bool) -> int:
        metadata_unrecoverable = (
            self.store.load_lease() is None and self.store.load_recovery() is None
        )
        if not metadata_unrecoverable:
            return self._fail("WARP restoration failed; valid recovery metadata retained for retry")
        if force:
            return self._force_off_without_snapshot()
        return self._fail(
            "run 'pub off --force' to stop the tunnel without guessing the previous mode"
        )

    def _announce(self, message: str, stream: TextIO) -> None:
        print(f"pub: {message}", file=stream)
        # Only what a human could not have seen: an interactive caller is reading this very line.
        if not self.interactive:
            self.notifier.notify(message)

    def _fail(self, message: str) -> int:
        if self._warp_failure is not None and str(self._warp_failure):
            message = f"{message}: {self._warp_failure}"
        self._warp_failure = None
        print(f"pub: {message}", file=self.stderr)
        return 1

    def _remember_warp_failure(self, error: WarpError) -> None:
        self._warp_failure = error


class FileLock:
    def __init__(
        self,
        path: Path,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.path = path
        self.monotonic = monotonic
        self.sleeper = sleeper
        self._stream: TextIO | None = None

    def acquire(self, timeout: float) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path.parent.chmod(0o700)
        stream = self.path.open("a+", encoding="utf-8")
        deadline = self.monotonic() + timeout
        while True:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._stream = stream
            except BlockingIOError:
                if self.monotonic() >= deadline:
                    stream.close()
                    return False
                self.sleeper(min(0.05, max(0.0, deadline - self.monotonic())))
            else:
                return True

    def release(self) -> None:
        if self._stream is None:
            return
        fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
        self._stream.close()
        self._stream = None


def _renewed_expiry(state: LeaseState, now: int) -> float:
    # The renewal window is a sliding grant; the bound that always holds is the hard ceiling.
    expires_at: float = now + LEASE_SECONDS
    if state.hard_expires_at is None:
        return expires_at
    return min(expires_at, state.hard_expires_at)


def _format_epoch(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _system_boot_session() -> str:
    result = subprocess.run(
        ["/usr/sbin/sysctl", "-n", "kern.bootsessionuuid"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise OSError
    return result.stdout.strip()


def _paths_from_environment(environment: dict[str, str]) -> StatePaths:
    home = Path(environment.get("HOME", str(Path.home())))
    # The state directory is fixed rather than XDG-configurable: the LaunchDaemon passes only HOME,
    # so an XDG override would leave the CLI writing leases the reconciler never inspects.
    default_state = home / ".local/state/pub-lease"
    directory = Path(environment.get("PUB_LEASE_STATE_DIR", str(default_state)))
    log = Path(environment.get("PUB_LEASE_LOG_FILE", str(home / "Library/Logs/pub-lease.log")))
    return StatePaths(directory=directory, log=log)


def _warp_path(environment: dict[str, str]) -> Path | None:
    configured = environment.get("PUB_WARP_CLI")
    if configured is not None:
        return Path(configured)
    source_path = environment.get("PATH", "")
    standard_path = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    search_path = f"{source_path}:{standard_path}" if source_path else standard_path
    found = shutil.which("warp-cli", path=search_path)
    return Path(found) if found is not None else None


def _network_from_environment(environment: dict[str, str]) -> NetworkPort:
    override = environment.get("PUB_NETWORK_SIGNATURE")
    if override is None:
        return SystemNetwork()
    return FixedNetwork(override or None)


def _usage(stderr: TextIO) -> int:
    print("usage: pub {on|off [--force]|status}", file=stderr)
    return 2


def _parse_arguments(argv: list[str], stderr: TextIO) -> tuple[str, bool] | None:
    if not argv:
        return "status", False
    if argv == ["off", "--force"]:
        return "off", True
    if len(argv) == 1 and argv[0] in {"on", "off", "status", "reconcile"}:
        return argv[0], False
    _usage(stderr)
    return None


def _report_already_off(store: StateStore, stdout: TextIO) -> int:
    notice = store.read_policy_notice()
    if notice is None:
        print("pub mode is already OFF", file=stdout)
        return 0
    print(f"pub: {notice}", file=stdout)
    store.clear_policy_notice()
    return 0


def _controller_from_environment(
    store: StateStore,
    environment: dict[str, str],
    stdout: TextIO,
    stderr: TextIO,
) -> Controller | None:
    warp_path = _warp_path(environment)
    if warp_path is None or not warp_path.is_file() or not os.access(warp_path, os.X_OK):
        print("pub: warp-cli is not available", file=stderr)
        return None
    try:
        now = (
            int(environment["PUB_LEASE_NOW"])
            if "PUB_LEASE_NOW" in environment
            else int(time.time())
        )
        poll_interval = float(environment.get("PUB_LEASE_POLL_INTERVAL", "1"))
    except ValueError:
        print("pub: invalid pub-lease numeric environment value", file=stderr)
        return None
    boot_id = environment.get("PUB_BOOT_SESSION")
    boot_session = (lambda: cast("str", boot_id)) if boot_id is not None else _system_boot_session
    return Controller(
        store,
        WarpClient(warp_path, poll_interval=poll_interval),
        _network_from_environment(environment),
        CommandNotifier.from_environment(environment),
        readiness=HTTPSReadiness(environment.get("PUB_CURL", "/usr/bin/curl")),
        clock=lambda: now,
        boot_session=boot_session,
        stdout=stdout,
        stderr=stderr,
        interactive=stderr.isatty(),
    )


def _run_locked(
    controller: Controller,
    command: str,
    *,
    force: bool,
    stderr: TextIO,
) -> int:
    store = controller.store
    lock = FileLock(store.paths.lock)
    # The reconciler fires every 60s and must never queue up behind a human operation; contention
    # is a silent no-op for it, whereas a human deserves to wait and then be told.
    timeout = 0.0 if command == "reconcile" else INTERACTIVE_LOCK_TIMEOUT
    try:
        acquired = lock.acquire(timeout)
    except OSError as error:
        print(f"pub: controller lock failed: {error}", file=stderr)
        return 1
    if not acquired:
        if command == "reconcile":
            return 0
        print("pub: another pub operation is already running", file=stderr)
        return 75
    try:
        store.prepare_locked_operation()
        operations: dict[str, Callable[[], int]] = {
            "on": controller.on,
            "off": lambda: controller.off(force=force),
            "reconcile": controller.reconcile,
        }
        return operations[command]()
    except OSError as error:
        print(f"pub: controller state operation failed: {error}", file=stderr)
        return 1
    finally:
        lock.release()


def main(
    arguments: list[str] | None = None,
    *,
    environment: dict[str, str] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    argv = list(sys.argv[1:] if arguments is None else arguments)
    env = dict(os.environ if environment is None else environment)
    parsed = _parse_arguments(argv, stderr)
    if parsed is None:
        return 2
    command, force = parsed
    store = StateStore(_paths_from_environment(env))
    if command == "reconcile" and not store.metadata_exists():
        return 0
    if command == "off" and not store.metadata_exists():
        return _report_already_off(store, stdout)
    controller = _controller_from_environment(store, env, stdout, stderr)
    if controller is None:
        return 1
    if command == "status":
        return controller.status()
    return _run_locked(controller, command, force=force, stderr=stderr)


if __name__ == "__main__":
    raise SystemExit(main())
