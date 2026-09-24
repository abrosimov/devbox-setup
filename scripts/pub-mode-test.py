from __future__ import annotations

import argparse
import importlib.machinery
import importlib.util
import json
import os
import platform
import plistlib
import pwd
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "roles/devbox/files/.local/bin/pub-lease.py"
WARP = Path("/Applications/Cloudflare WARP.app/Contents/Resources/warp-cli")
SUPERVISOR = Path("/Library/LaunchDaemons/local.pub-lease.plist")
LIVE_TIMEOUT = 360
RESTORE_TIMEOUT = 120


class GateError(RuntimeError):
    pass


def run(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        msg = f"{Path(command[0]).name}: command unavailable or timed out"
        raise GateError(msg) from error
    if result.returncode != 0:
        msg = f"{Path(command[0]).name}: command failed (exit {result.returncode})"
        raise GateError(msg)
    return result.stdout


def load_controller(path: Path, name: str) -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        msg = "could not load pub controller"
        raise GateError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def port_53_listeners(output: str) -> list[str]:
    listeners = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].startswith(("tcp", "udp")) and fields[3].endswith(".53"):
            listeners.append(f"{fields[0]} {fields[3]}")
    return listeners


def check_supervisor(home: Path) -> None:
    installed = home / ".local/bin/pub-lease"
    if not SUPERVISOR.is_file():
        msg = "standard pub supervisor plist is not installed"
        raise GateError(msg)
    if not installed.is_file():
        msg = "standard pub supervisor references a missing installed controller"
        raise GateError(msg)
    with SUPERVISOR.open("rb") as stream:
        plist = plistlib.load(stream)
    if not isinstance(plist, dict):
        msg = "pub supervisor plist is invalid"
        raise GateError(msg)
    environment = plist.get("EnvironmentVariables", {})
    if (
        not isinstance(environment, dict)
        or plist.get("UserName") != pwd.getpwuid(os.getuid()).pw_name
        or environment.get("HOME") != str(home)
        or str(installed) not in plist.get("ProgramArguments", [])
        or any(key.startswith("PUB_") and key != "PUB_LEASE_LOG_FILE" for key in environment)
    ):
        msg = "standard pub supervisor configuration does not match the current user"
        raise GateError(msg)
    try:
        run(["/bin/launchctl", "print", "system/local.pub-lease"])
    except GateError as error:
        msg = "standard pub supervisor is not loaded"
        raise GateError(msg) from error


def check_docker(home: Path) -> None:
    settings = home / "Library/Group Containers/group.com.docker/settings-store.json"
    if not settings.exists():
        return
    value = json.loads(settings.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("KernelForUDP") is not False:
        msg = (
            "Docker Desktop KernelForUDP must be explicitly false; restart Docker after changing it"
        )
        raise GateError(msg)


def warp_dns_active() -> bool:
    try:
        settings = json.loads(run([str(WARP), "-j", "settings"]))
        status = json.loads(run([str(WARP), "-j", "status"]))
    except (GateError, ValueError):
        return False
    if not isinstance(settings, dict) or not isinstance(status, dict):
        return False
    values = settings.get("settings")
    return (
        isinstance(values, dict)
        and values.get("operation_mode") in {"warp", "doh", "warp+doh", "dot", "warp+dot"}
        and status.get("status") == "Connected"
    )


def check_port_53(protocol: str) -> None:
    listeners = port_53_listeners(run(["/usr/sbin/netstat", "-an", "-p", protocol]))
    if listeners and not warp_dns_active():
        raise GateError(
            "local DNS port 53 is occupied (including possible mDNSResponder sockets): "
            + ", ".join(listeners)
        )


def check_environment(home: Path, *, live: bool = False) -> None:
    if platform.system() != "Darwin":
        msg = "pub runtime verification requires macOS"
        raise GateError(msg)
    if Path(os.environ.get("HOME", "")).resolve() != home:
        msg = "HOME must match the current user's real home"
        raise GateError(msg)
    if any(key.startswith("PUB_") for key in os.environ):
        msg = "remove PUB_* overrides before runtime verification"
        raise GateError(msg)
    failures = []
    if not WARP.is_file() or not os.access(WARP, os.X_OK):
        failures.append("the installed Cloudflare WARP application CLI is missing")
    checks = [
        lambda: check_docker(home),
        lambda: check_port_53("tcp"),
        lambda: check_port_53("udp"),
    ]
    if live:
        checks.append(lambda: check_supervisor(home))
    for check in checks:
        try:
            check()
        except (OSError, ValueError, RuntimeError) as error:
            failures.append(str(error))
    if failures:
        raise GateError("; ".join(failures))


def boot_session() -> str:
    value = run(["/usr/sbin/sysctl", "-n", "kern.bootsessionuuid"]).strip()
    if not value:
        msg = "boot session is unavailable"
        raise GateError(msg)
    return value


class RuntimeGate:
    def __init__(self, home: Path, module: ModuleType, state_directory: Path | None = None) -> None:
        self.module = module
        standard_directory = home / ".local/state/pub-lease"
        isolated_directory = state_directory or home / ".local/state/pub-mode-test"
        self.standard_store = module.StateStore(
            module.StatePaths(standard_directory, home / "Library/Logs/pub-lease.log")
        )
        self.store = module.StateStore(
            module.StatePaths(isolated_directory, isolated_directory / "pub-mode-test.log")
        )
        self.warp = module.WarpClient(WARP)
        self.readiness = module.HTTPSReadiness(strong=False)
        self.controller = module.Controller(
            self.store,
            self.warp,
            module.SystemNetwork(),
            module.CommandNotifier(()),
            readiness=module.HTTPSReadiness(),
            clock=lambda: int(time.time()),
            boot_session=boot_session,
            interactive=True,
        )

    def baseline(self) -> tuple[str, str, str, str]:
        if self.standard_store.metadata_exists() or self.standard_store.paths.disabled.exists():
            msg = "active standard pub lease or disabled marker: runtime test refused"
            raise GateError(msg)
        if self.store.metadata_exists() or self.store.paths.disabled.exists():
            msg = "existing isolated test metadata or disabled marker: runtime test refused"
            raise GateError(msg)
        protocol, protocol_source = self.warp.protocol()
        snapshot = (self.warp.mode(), self.warp.status(), protocol, protocol_source)
        if snapshot[0] not in self.module.SUPPORTED_MODES or snapshot[1] not in {
            "Connected",
            "Disconnected",
        }:
            msg = "WARP must have a supported mode and stable connection state"
            raise GateError(msg)
        if self.warp.policy_lock() != "unlocked":
            msg = "WARP mode is controlled by policy"
            raise GateError(msg)
        self.check_readiness()
        return snapshot

    def check_readiness(self) -> None:
        failure = self.readiness.failure()
        if failure is not None:
            raise GateError(failure)

    def live(self, rollback: Path | None = None) -> None:
        lock = self.module.FileLock(self.standard_store.paths.lock)
        if not lock.acquire(10):
            msg = "another pub operation holds the standard controller lock"
            raise GateError(msg)
        try:
            snapshot = self.baseline()
            rollback_path = rollback or self.store.paths.directory / "rollback.json"
            write_snapshot(rollback_path, snapshot)
            self.store.prepare_locked_operation()
            try:
                if self.controller.on() != 0:
                    msg = "candidate pub on failed"
                    raise GateError(msg)
                if (*self.warp.protocol(), self.warp.mode(), self.warp.status()) != (
                    "wireguard",
                    "consumer_overrides",
                    "warp+doh",
                    "Connected",
                ):
                    msg = "candidate pub on did not establish WireGuard warp+doh/Connected"
                    raise GateError(msg)
            finally:
                self.restore(snapshot)
            rollback_path.unlink()
        finally:
            lock.release()

    def restore(self, snapshot: tuple[str, str, str, str]) -> None:
        previous_handlers = {
            signum: signal.signal(signum, signal.SIG_IGN)
            for signum in (signal.SIGINT, signal.SIGTERM)
        }
        try:
            if self.controller.off() != 0:
                msg = "candidate pub off failed; isolated recovery retained for guardian"
                raise GateError(msg)
            observed = (self.warp.mode(), self.warp.status(), *self.warp.protocol())
            if observed != snapshot or self.store.metadata_exists():
                msg = "WARP snapshot or metadata restoration verification failed"
                raise GateError(msg)
            self.check_readiness()
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)


def write_snapshot(path: Path, snapshot: tuple[str, str, str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    payload = {
        "mode": snapshot[0],
        "status": snapshot[1],
        "protocol": snapshot[2],
        "protocol_source": snapshot[3],
    }
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_snapshot(path: Path) -> tuple[str, str, str, str]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    invalid = "rollback snapshot is invalid"
    if not isinstance(value, dict):
        raise GateError(invalid)
    expected = ("mode", "status", "protocol", "protocol_source")
    if set(value) != set(expected) or not all(isinstance(value[key], str) for key in expected):
        raise GateError(invalid)
    return tuple(value[key] for key in expected)


def restore_snapshot(module: ModuleType, snapshot: tuple[str, str, str, str]) -> None:
    mode, status, protocol, protocol_source = snapshot
    warp = module.WarpClient(WARP)
    warp.disconnect()
    if not warp.wait_for_status("Disconnected", attempts=60, tick=lambda: None):
        message = "guardian could not disconnect WARP for restoration"
        raise GateError(message)
    if protocol_source == "network_policy":
        warp.reset_protocol()
    elif protocol_source == "consumer_overrides" and protocol in module.SUPPORTED_PROTOCOLS:
        warp.set_protocol(protocol)
    else:
        message = "guardian refuses an unsupported protocol restoration"
        raise GateError(message)
    warp.set_mode(mode)
    if not warp.wait_for_settings(
        (mode, protocol, protocol_source),
        attempts=30,
        tick=lambda: None,
    ):
        message = "guardian could not restore WARP tunnel settings"
        raise GateError(message)
    if status == "Connected":
        warp.connect()
    elif status == "Disconnected":
        warp.disconnect()
    else:
        message = "guardian refuses an unstable status restoration"
        raise GateError(message)
    if not warp.wait_for_status(status, attempts=60, tick=lambda: None):
        message = "guardian could not restore WARP connection state"
        raise GateError(message)
    observed_mode, observed_protocol, observed_source = warp.tunnel_settings()
    if (observed_mode, warp.status(), observed_protocol, observed_source) != snapshot:
        message = "guardian WARP snapshot verification failed"
        raise GateError(message)
    failure = module.HTTPSReadiness(strong=False).failure()
    if failure is not None:
        raise GateError(failure)


def restore_with_deadline(
    module: ModuleType,
    snapshot: tuple[str, str, str, str],
    *,
    timeout: float = RESTORE_TIMEOUT,
) -> None:
    def deadline_expired(_signum: int, _frame: object) -> None:
        msg = f"guardian restoration exceeded {timeout:g} seconds"
        raise GateError(msg)

    previous_handler = signal.signal(signal.SIGALRM, deadline_expired)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        restore_snapshot(module, snapshot)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def recover_stale_runs(home: Path, module: ModuleType, root: Path) -> None:
    store = module.StateStore(
        module.StatePaths(home / ".local/state/pub-lease", home / "Library/Logs/pub-lease.log")
    )
    lock = module.FileLock(store.paths.lock)
    if not lock.acquire(10):
        msg = "guardian could not acquire the standard controller lock"
        raise GateError(msg)
    try:
        if store.metadata_exists():
            msg = "active standard pub lease or recovery metadata: stale recovery refused"
            raise GateError(msg)
        for state_directory in sorted(root.glob("run.*")):
            if not state_directory.is_dir():
                continue
            rollback = state_directory / "rollback.json"
            if rollback.exists():
                restore_with_deadline(module, read_snapshot(rollback))
                rollback.unlink()
            shutil.rmtree(state_directory)
    finally:
        lock.release()


def worker(home: Path, state_directory: Path) -> int:
    check_environment(home, live=True)
    module = load_controller(CANDIDATE, "pub_mode_candidate_worker")
    gate = RuntimeGate(home, module, state_directory)
    gate.live(state_directory / "rollback.json")
    return 0


def guardian(home: Path) -> int:
    module = load_controller(CANDIDATE, "pub_mode_candidate_guardian")
    root = home / ".local/state/pub-mode-test"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    recover_stale_runs(home, module, root)
    check_environment(home, live=True)
    state_directory = Path(tempfile.mkdtemp(prefix="run.", dir=root))
    rollback = state_directory / "rollback.json"
    process = subprocess.Popen(
        [
            "/usr/bin/python3",
            "-u",
            str(Path(__file__).resolve()),
            "--worker",
            "--state-dir",
            str(state_directory),
        ],
        start_new_session=True,
    )
    interrupted = False

    def stop_worker(_signum: int, _frame: object) -> None:
        nonlocal interrupted
        interrupted = True
        process.terminate()

    previous_handlers = {
        signum: signal.signal(signum, stop_worker) for signum in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        try:
            try:
                returncode = process.wait(timeout=LIVE_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=RESTORE_TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=15)
                returncode = 1
            if interrupted:
                returncode = 1
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
            if rollback.exists():
                standard_paths = module.StatePaths(
                    home / ".local/state/pub-lease", home / "Library/Logs/pub-lease.log"
                )
                lock = module.FileLock(standard_paths.lock)
                if not lock.acquire(10):
                    message = "guardian could not acquire the standard controller lock"
                    raise GateError(message)
                try:
                    restore_with_deadline(module, read_snapshot(rollback))
                    rollback.unlink()
                finally:
                    lock.release()
            shutil.rmtree(state_directory)
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    return returncode


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify pub prerequisites; --live also tests on/off."
    )
    parser.add_argument(
        "--live", action="store_true", help="temporarily activate candidate pub mode"
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--state-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(arguments)
    home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    try:
        if args.worker:
            if args.state_dir is None:
                message = "worker state directory is required"
                raise GateError(message)
            return worker(home, args.state_dir)
        if args.live:
            if guardian(home) != 0:
                message = "live candidate worker failed; restoration attempted"
                raise GateError(message)
        else:
            check_environment(home)
            gate = RuntimeGate(home, load_controller(CANDIDATE, "pub_mode_candidate"))
            gate.baseline()
    except KeyboardInterrupt:
        print(
            "pub-mode-test: interrupted; live restoration attempted if activation began",
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError, RuntimeError) as error:
        print(f"pub-mode-test: FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "pub-mode-test: PASS: "
        + ("live on/off and restoration" if args.live else "read-only preflight")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
