from __future__ import annotations

import argparse
import importlib.machinery
import importlib.util
import json
import os
import platform
import plistlib
import pwd
import signal
import subprocess
import sys
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
    if not installed.is_file():
        msg = (
            "live test requires an installed pub controller and supervisor; "
            "bootstrap pub configuration first"
        )
        raise GateError(msg)
    module = load_controller(installed, "pub_mode_installed")
    if "warp+doh" not in getattr(module, "LEASE_MODES", ()):
        msg = (
            "live test requires a supervisor controller that recovers warp+doh leases; "
            "update pub configuration first"
        )
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
        msg = "pub supervisor does not match the current user's standard state"
        raise GateError(msg)
    run(["/bin/launchctl", "print", "system/local.pub-lease"])


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


def interrupt(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


class RuntimeGate:
    def __init__(self, home: Path, module: ModuleType) -> None:
        self.module = module
        self.store = module.StateStore(
            module.StatePaths(home / ".local/state/pub-lease", home / "Library/Logs/pub-lease.log")
        )
        self.warp = module.WarpClient(WARP)
        self.readiness = module.HTTPSReadiness()
        self.controller = module.Controller(
            self.store,
            self.warp,
            module.SystemNetwork(),
            module.CommandNotifier(()),
            readiness=self.readiness,
            clock=lambda: int(time.time()),
            boot_session=boot_session,
            interactive=True,
        )

    def baseline(self) -> tuple[str, str]:
        if self.store.metadata_exists() or self.store.paths.disabled.exists():
            msg = "existing pub metadata or disabled marker: runtime test refused"
            raise GateError(msg)
        snapshot = (self.warp.mode(), self.warp.status())
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

    def live(self) -> None:
        lock = self.module.FileLock(self.store.paths.lock)
        if not lock.acquire(10):
            msg = "another pub operation holds the standard controller lock"
            raise GateError(msg)
        try:
            snapshot = self.baseline()
            self.store.prepare_locked_operation()
            try:
                if self.controller.on() != 0:
                    msg = "candidate pub on failed"
                    raise GateError(msg)
                if (self.warp.mode(), self.warp.status()) != ("warp+doh", "Connected"):
                    msg = "candidate pub on did not establish warp+doh/Connected"
                    raise GateError(msg)
                self.check_readiness()
            finally:
                self.restore(snapshot)
        finally:
            lock.release()

    def restore(self, snapshot: tuple[str, str]) -> None:
        previous_handlers = {
            signum: signal.signal(signum, signal.SIG_IGN)
            for signum in (signal.SIGINT, signal.SIGTERM)
        }
        try:
            if self.controller.off() != 0:
                msg = "candidate pub off failed; recovery metadata retained for supervisor"
                raise GateError(msg)
            if (self.warp.mode(), self.warp.status()) != snapshot or self.store.metadata_exists():
                msg = "WARP snapshot or metadata restoration verification failed"
                raise GateError(msg)
            self.check_readiness()
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify pub prerequisites; --live also tests on/off."
    )
    parser.add_argument(
        "--live", action="store_true", help="temporarily activate candidate pub mode"
    )
    args = parser.parse_args(arguments)
    home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    try:
        check_environment(home, live=args.live)
        gate = RuntimeGate(home, load_controller(CANDIDATE, "pub_mode_candidate"))
        if args.live:
            signal.signal(signal.SIGTERM, interrupt)
            gate.live()
        else:
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
