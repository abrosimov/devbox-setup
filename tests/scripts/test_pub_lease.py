from __future__ import annotations

import fcntl
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, replace
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
PUB_LEASE = REPO_ROOT / "roles/devbox/files/.local/bin/pub-lease.py"
FIXTURES = Path(__file__).with_name("fixtures") / "pub_lease"
LEASE_SECONDS = 1_800
MAX_LEASE_SECONDS = 43_200
NETWORK_MISS_LIMIT = 2
SIGNATURE_HOME = "a" * 64
SIGNATURE_PUB = "b" * 64


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pub_lease", PUB_LEASE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pub_lease = _load_module()


@dataclass
class FakeWarp:
    current_mode: str = "proxy"
    current_status: str = "Disconnected"
    switch_locked: bool = False
    calls: list[tuple[str, ...]] = field(default_factory=list)
    fail_once: list[str] = field(default_factory=list)
    status_queue: list[str] = field(default_factory=list)
    mode_queue: list[str] = field(default_factory=list)
    failure_detail: str = ""

    def mode(self) -> str:
        self.calls.append(("mode",))
        self._raise_if_requested("read-mode")
        if self.mode_queue:
            return self.mode_queue.pop(0)
        return self.current_mode

    def status(self) -> str:
        self.calls.append(("status",))
        self._raise_if_requested("read-status")
        if self.status_queue:
            return self.status_queue.pop(0)
        return self.current_status

    def policy_lock(self) -> str:
        self.calls.append(("policy",))
        self._raise_if_requested("read-policy")
        return "switch_locked" if self.switch_locked else "unlocked"

    def settle_status(self, *, attempts: int, tick) -> str:
        self.calls.append(("settle", str(attempts)))
        for attempt in range(attempts):
            status = self.status()
            if status != "Connecting":
                return status
            if attempt + 1 < attempts:
                tick()
        return "Connecting"

    def set_mode(self, mode: str) -> None:
        self.calls.append(("set-mode", mode))
        self._raise_if_requested(f"set-mode:{mode}")
        self.current_mode = mode

    def connect(self) -> None:
        self.calls.append(("connect",))
        self._raise_if_requested("connect")
        self.current_status = "Connected"

    def disconnect(self) -> None:
        self.calls.append(("disconnect",))
        self._raise_if_requested("disconnect")
        self.current_status = "Disconnected"

    def wait_for_status(self, expected: str, *, attempts: int, tick) -> bool:
        self.calls.append(("wait", expected, str(attempts)))
        for attempt in range(attempts):
            if self.status() == expected:
                return True
            if attempt + 1 < attempts:
                tick()
        return False

    def _raise_if_requested(self, operation: str) -> None:
        if operation in self.fail_once:
            self.fail_once.remove(operation)
            raise pub_lease.WarpError(self.failure_detail)


@dataclass
class FakeNetwork:
    value: str | None = SIGNATURE_HOME
    reads: int = 0

    def signature(self) -> str | None:
        self.reads += 1
        return self.value


@dataclass
class FakeNotifier:
    messages: list[str] = field(default_factory=list)

    def notify(self, message: str) -> None:
        self.messages.append(message)


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str
    stderr: str


class AtomicWriteError(OSError):
    pass


@dataclass
class FakeReadiness:
    error: str | None = None
    calls: int = 0

    def failure(self) -> str | None:
        self.calls += 1
        return self.error


class Harness:
    def __init__(self, root: Path) -> None:
        self.paths = pub_lease.StatePaths(root / "lease-state", root / "pub-lease.log")
        self.store = pub_lease.StateStore(self.paths)
        self.warp = FakeWarp()
        self.network = FakeNetwork()
        self.notifier = FakeNotifier()
        self.readiness = FakeReadiness()
        self.now = 1_000_000
        self.boot_session = "boot-a"
        self.interactive = True

    def run(self, operation: str, *, force: bool = False) -> Result:
        stdout = StringIO()
        stderr = StringIO()
        controller = pub_lease.Controller(
            self.store,
            self.warp,
            self.network,
            self.notifier,
            readiness=self.readiness,
            clock=lambda: self.now,
            boot_session=lambda: self.boot_session,
            stdout=stdout,
            stderr=stderr,
            interactive=self.interactive,
        )
        if operation == "off":
            returncode = controller.off(force=force)
        else:
            returncode = getattr(controller, operation)()
        return Result(returncode, stdout.getvalue(), stderr.getvalue())

    def lease(self):
        return self.store.load_lease()


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


def _copy_fixture(name: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / name, target)


def _write_policy_probe(directory: Path, answer: str) -> Path:
    executable = directory / "warp-cli"
    executable.write_text(
        f"""#!{sys.executable}
import sys
if sys.argv[1:] != ["settings", "mode-switch-allowed"]:
    raise SystemExit(64)
sys.stdout.write({answer!r})
""",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


class TestPubLeaseLifecycle:
    def test_on_captures_previous_state_and_starts_a_renewable_lease(
        self, harness: Harness
    ) -> None:
        result = harness.run("on")

        state = harness.lease()
        assert result.returncode == 0
        assert result.stdout.startswith("pub mode ON until ")
        assert state is not None
        assert state.phase == "active"
        assert state.started_at == harness.now
        assert state.expires_at == harness.now + LEASE_SECONDS
        assert state.hard_expires_at == harness.now + MAX_LEASE_SECONDS
        assert state.network_signature == SIGNATURE_HOME
        assert state.network_misses == 0
        assert state.previous_mode == "proxy"
        assert state.previous_status == "Disconnected"
        assert state.previous_connected is False
        assert ("wait", "Connected", "25") in harness.warp.calls
        assert harness.warp.current_mode == "warp+doh"
        assert harness.warp.current_status == "Connected"
        assert harness.paths.lease.stat().st_mode & 0o777 == 0o600
        assert harness.paths.recovery.stat().st_mode & 0o777 == 0o600

    @pytest.mark.parametrize("renew", [False, True])
    @pytest.mark.parametrize("failure", ["system DNS unavailable", "HTTPS unavailable"])
    def test_readiness_failure_restores_previous_state(self, harness, renew, failure):
        if renew:
            assert harness.run("on").returncode == 0
        harness.readiness.error = failure

        result = harness.run("on")

        assert result.returncode == 1
        assert failure in result.stderr
        assert "previous state restored" in result.stderr
        assert "ON" not in result.stdout
        assert harness.warp.current_mode == "proxy"
        assert harness.warp.current_status == "Disconnected"
        assert not harness.store.metadata_exists()

    def test_readiness_failure_retains_metadata_until_rollback_succeeds(self, harness):
        harness.readiness.error = "system DNS unavailable"
        harness.warp.fail_once.append("set-mode:proxy")

        result = harness.run("on")

        assert result.returncode == 1
        assert "restoration pending; recovery retained" in result.stderr
        assert harness.lease().phase == "restoring"
        assert harness.store.load_recovery().previous_mode == "proxy"
        assert harness.run("reconcile").returncode == 0
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    def test_only_explicit_on_checks_readiness(self, harness):
        assert harness.run("on").returncode == 0
        assert harness.run("on").returncode == 0
        assert harness.readiness.calls == 2
        harness.readiness.error = "unavailable"
        assert harness.run("status").returncode == 0
        assert harness.run("reconcile").returncode == 0
        assert harness.run("off").returncode == 0
        assert harness.readiness.calls == 2

    def test_tunnel_only_is_supported_as_a_previous_mode(self, harness):
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"
        assert harness.run("on").returncode == 0
        assert harness.warp.current_mode == "warp+doh"
        assert harness.run("off").returncode == 0
        assert harness.warp.current_mode == "tunnel_only"
        assert harness.warp.current_status == "Connected"

    def test_on_refuses_disabled_controller_without_warp_calls(self, harness: Harness) -> None:
        harness.paths.directory.mkdir(parents=True)
        harness.paths.disabled.touch()

        result = harness.run("on")

        assert result.returncode == 1
        assert "disabled" in result.stderr
        assert harness.warp.calls == []
        assert not harness.store.metadata_exists()

    def test_off_preserves_previously_connected_session(self, harness: Harness) -> None:
        harness.warp.current_status = "Connected"

        assert harness.run("on").returncode == 0
        result = harness.run("off")

        assert result.returncode == 0
        assert result.stdout == "pub mode OFF; previous WARP state restored\n"
        assert harness.warp.current_mode == "proxy"
        assert harness.warp.current_status == "Connected"

    @pytest.mark.parametrize("operation", ["off", "reconcile"])
    def test_off_and_expiry_restore_disconnected_mode(
        self, harness: Harness, operation: str
    ) -> None:
        assert harness.run("on").returncode == 0
        if operation == "reconcile":
            harness.now += LEASE_SECONDS

        result = harness.run(operation)

        assert result.returncode == 0
        assert "previous WARP state restored" in result.stdout
        assert harness.warp.current_mode == "proxy"
        assert harness.warp.current_status == "Disconnected"
        assert not harness.store.metadata_exists()

    def test_degraded_restore_ends_the_lease_without_reaching_connected(
        self, harness: Harness
    ) -> None:
        harness.warp.current_status = "Unable to connect"
        assert harness.run("on").returncode == 0
        harness.warp.status_queue = ["Disconnected"] * 20

        result = harness.run("off")

        assert result.returncode == 0
        assert "previous WARP state restored" in result.stdout
        assert ("disconnect",) not in harness.warp.calls
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize("failure", ["connect", "read-status"])
    def test_degraded_restore_ends_the_lease_despite_a_failing_connection_probe(
        self, harness: Harness, failure: str
    ) -> None:
        harness.warp.current_status = "Unable to connect"
        assert harness.run("on").returncode == 0
        harness.warp.fail_once.append(failure)

        result = harness.run("off")

        assert result.returncode == 0
        assert "previous WARP state restored" in result.stdout
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    def test_degraded_restore_keeps_the_lease_when_the_mode_is_not_confirmed(
        self, harness: Harness
    ) -> None:
        harness.warp.current_status = "Unable to connect"
        assert harness.run("on").returncode == 0
        harness.warp.fail_once.append("connect")
        harness.warp.mode_queue = ["warp+doh", "warp"]

        result = harness.run("off")

        assert result.returncode == 1
        assert "restoration failed" in result.stderr
        assert harness.store.metadata_exists()

    def test_connected_restore_still_holds_the_lease_until_it_reconnects(
        self, harness: Harness
    ) -> None:
        harness.warp.current_status = "Connected"
        assert harness.run("on").returncode == 0
        harness.warp.status_queue = ["Disconnected"] * 20

        result = harness.run("off")

        assert result.returncode == 1
        assert "restoration failed" in result.stderr
        assert harness.store.metadata_exists()

    def test_failed_activation_never_disconnects_a_degraded_pre_lease_state(
        self, harness: Harness
    ) -> None:
        harness.warp.current_status = "Unable to connect"
        harness.warp.fail_once.append("connect")

        result = harness.run("on")

        assert result.returncode == 1
        assert "previous state restored" in result.stderr
        assert ("disconnect",) not in harness.warp.calls
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize(
        ("operation", "attempts", "expects_progress"),
        [("off", "20", True), ("reconcile", "60", False)],
    )
    def test_restore_budget_and_progress_follow_the_caller(
        self,
        harness: Harness,
        *,
        operation: str,
        attempts: str,
        expects_progress: bool,
    ) -> None:
        assert harness.run("on").returncode == 0
        if operation == "reconcile":
            harness.now += LEASE_SECONDS
        harness.warp.calls.clear()
        harness.warp.status_queue = ["Connected", "Connected", "Connected"]

        result = harness.run(operation)

        assert result.returncode == 0
        assert ("wait", "Disconnected", attempts) in harness.warp.calls
        assert ("restoring the previous WARP state..." in result.stderr) is expects_progress
        assert "restoring the previous WARP state" not in result.stdout

    def test_progress_is_silent_without_a_terminal(self, harness: Harness) -> None:
        harness.interactive = False
        assert harness.run("on").returncode == 0
        harness.warp.status_queue = ["Connected", "Connected", "Connected"]

        result = harness.run("off")

        assert result.returncode == 0
        assert result.stdout == "pub mode OFF; previous WARP state restored\n"
        assert result.stderr == ""

    def test_reboot_ends_unexpired_lease(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.boot_session = "boot-b"

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "boot session changed" in result.stdout
        assert not harness.store.metadata_exists()

    def test_renewal_reconnects_and_keeps_original_snapshot(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        recovery = harness.paths.recovery.read_bytes()
        lease_id = harness.lease().lease_id
        harness.warp.current_status = "Disconnected"
        harness.now += 60

        result = harness.run("on")

        assert result.returncode == 0
        assert result.stdout.startswith("pub mode renewed until ")
        assert harness.warp.current_status == "Connected"
        assert harness.paths.recovery.read_bytes() == recovery
        assert harness.lease().lease_id == lease_id
        assert harness.lease().started_at == harness.now

    def test_status_is_read_only(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        lease = harness.paths.lease.read_bytes()
        recovery = harness.paths.recovery.read_bytes()

        result = harness.run("status")

        assert result.returncode == 0
        assert "WARP: mode=warp+doh, status=Connected" in result.stdout
        assert "remaining=0h30m" in result.stdout
        assert harness.paths.lease.read_bytes() == lease
        assert harness.paths.recovery.read_bytes() == recovery

    @pytest.mark.parametrize("status", ["Disconnecting", "Unknown"])
    def test_on_refuses_unstable_initial_status(self, harness: Harness, status: str) -> None:
        harness.warp.current_status = status

        result = harness.run("on")

        assert result.returncode == 1
        assert "not in a stable state" in result.stderr
        assert not harness.store.metadata_exists()

    def test_on_refuses_when_warp_registration_is_missing(self, harness: Harness) -> None:
        harness.warp.current_status = "Registration Missing"

        result = harness.run("on")

        assert result.returncode == 1
        assert "no registration" in result.stderr
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize("settled", ["Connected", "Disconnected"])
    def test_on_settles_a_connecting_status_before_capturing_it(
        self, harness: Harness, settled: str
    ) -> None:
        harness.warp.current_status = "Connecting"
        harness.warp.status_queue = ["Connecting", "Connecting", settled]

        result = harness.run("on")

        assert result.returncode == 0
        assert ("settle", "10") in harness.warp.calls
        assert harness.lease().previous_status == settled
        assert "degraded" not in result.stderr

    @pytest.mark.parametrize("status", ["Unable to connect", "Connecting"])
    def test_on_proceeds_from_a_degraded_state_and_says_what_restore_will_do(
        self, harness: Harness, status: str
    ) -> None:
        harness.warp.current_status = status

        result = harness.run("on")

        assert result.returncode == 0
        assert "pub mode ON until " in result.stdout
        assert "already degraded" in result.stderr
        assert f"status={status}" in result.stderr
        assert harness.lease().previous_status == status
        assert harness.lease().previous_connected is False
        assert harness.warp.current_mode == "warp+doh"


class TestPubLeaseOwnership:
    def test_on_refuses_switch_locked_policy_before_ownership(self, harness: Harness) -> None:
        harness.warp.switch_locked = True

        result = harness.run("on")

        assert result.returncode == 1
        assert "switch_locked" in result.stderr
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize("operation", ["reconcile", "off"])
    def test_policy_lock_drops_lease_without_changing_warp(
        self, harness: Harness, operation: str
    ) -> None:
        assert harness.run("on").returncode == 0
        harness.warp.switch_locked = True

        result = harness.run(operation)

        assert result.returncode == 0
        assert "ownership lost to WARP policy" in result.stderr
        assert harness.warp.current_mode == "warp+doh"
        assert not harness.store.metadata_exists()

    def test_policy_drop_leaves_an_advisory_breadcrumb_for_off_and_status(
        self, harness: Harness
    ) -> None:
        assert harness.run("on").returncode == 0
        harness.warp.switch_locked = True
        assert harness.run("reconcile").returncode == 0

        reported = harness.run("status")
        first_off = harness.run("off")
        second_off = harness.run("off")

        assert "dropped by WARP policy (switch_locked)" in reported.stdout
        assert "mode before the lease was proxy" in reported.stdout
        assert "advisory only" in reported.stdout
        assert first_off.returncode == 0
        assert first_off.stdout == reported.stdout.splitlines()[1] + "\n"
        assert second_off.stdout == "pub mode is already OFF\n"
        assert harness.warp.current_mode == "warp+doh"

    @pytest.mark.parametrize(
        ("phase", "observed_mode"),
        [("restoring", "proxy"), ("active", "warp")],
    )
    def test_policy_breadcrumb_reports_the_observed_mode(
        self, harness: Harness, phase: str, observed_mode: str
    ) -> None:
        assert harness.run("on").returncode == 0
        harness.store.write_lease(replace(harness.lease(), phase=phase))
        harness.warp.current_mode = observed_mode
        harness.warp.switch_locked = True

        assert harness.run("reconcile").returncode == 0
        result = harness.run("status")

        assert f"WARP: mode={observed_mode}, " in result.stdout
        assert f"WARP was left as it was found (mode={observed_mode})" in result.stdout
        assert "mode before the lease was proxy" in result.stdout
        assert "tunnel_only" not in result.stdout

    def test_new_lease_supersedes_the_policy_breadcrumb(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.warp.switch_locked = True
        assert harness.run("reconcile").returncode == 0
        harness.warp.switch_locked = False

        assert harness.run("on").returncode == 0
        result = harness.run("status")

        assert "dropped by WARP policy" not in result.stdout
        assert not harness.paths.policy_notice.exists()

    @pytest.mark.parametrize("phase", ["active", "activating", "restoring"])
    def test_mode_drift_drops_ownership_without_changing_warp(
        self, harness: Harness, phase: str
    ) -> None:
        assert harness.run("on").returncode == 0
        harness.store.write_lease(replace(harness.lease(), phase=phase))
        harness.warp.current_mode = "warp"
        harness.warp.current_status = "Disconnected"

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "lease ownership lost" in result.stderr
        assert harness.warp.current_mode == "warp"
        assert not harness.store.metadata_exists()

    def test_restoring_phase_accepts_already_restored_mode(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.store.write_lease(replace(harness.lease(), phase="restoring"))
        harness.warp.current_mode = "proxy"
        harness.warp.current_status = "Connected"

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "ownership lost" not in result.stderr
        assert harness.warp.current_status == "Disconnected"
        assert not harness.store.metadata_exists()

    def test_failed_restore_retains_state_for_retry(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.now += LEASE_SECONDS
        harness.warp.fail_once.append("set-mode:proxy")

        failed = harness.run("reconcile")
        retried = harness.run("reconcile")

        assert failed.returncode == 1
        assert retried.returncode == 0
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize("force", [False, True])
    def test_valid_restore_failure_is_never_quarantined(self, harness: Harness, force) -> None:
        assert harness.run("on").returncode == 0
        harness.warp.fail_once.extend(["set-mode:proxy", "set-mode:proxy"])

        assert harness.run("off").returncode == 1
        result = harness.run("off", force=force)

        assert result.returncode == 1
        assert "retained for retry" in result.stderr
        assert harness.store.metadata_exists()
        assert not list(harness.paths.directory.glob("*.invalid.*"))


class TestPubLeaseNetworkRenewal:
    def test_a_matching_signature_renews_without_moving_the_hard_ceiling(
        self, harness: Harness
    ) -> None:
        assert harness.run("on").returncode == 0
        hard_expires_at = harness.lease().hard_expires_at

        for offset in (60, 120):
            harness.now = 1_000_000 + offset
            assert harness.run("reconcile").returncode == 0
            assert harness.lease().expires_at == harness.now + LEASE_SECONDS
            assert harness.lease().hard_expires_at == hard_expires_at

        assert harness.warp.current_mode == "warp+doh"

    def test_renewal_is_clamped_to_the_hard_ceiling(self, harness: Harness) -> None:
        _copy_fixture("v1-active-capped.json", harness.paths.lease)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"

        assert harness.run("reconcile").returncode == 0

        assert harness.lease().expires_at == 1_000_060
        assert harness.lease().network_misses == 0

    def test_a_single_signature_mismatch_counts_a_miss_and_keeps_the_lease(
        self, harness: Harness
    ) -> None:
        assert harness.run("on").returncode == 0
        expires_at = harness.lease().expires_at
        harness.network.value = SIGNATURE_PUB
        harness.now += 60

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert harness.lease().network_misses == 1
        assert harness.lease().expires_at == expires_at
        assert harness.warp.current_mode == "warp+doh"

    def test_a_second_signature_mismatch_closes_the_lease_and_restores_warp(
        self, harness: Harness
    ) -> None:
        assert harness.run("on").returncode == 0
        harness.network.value = SIGNATURE_PUB

        assert harness.run("reconcile").returncode == 0
        harness.now += 60
        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "network changed; previous WARP state restored" in result.stdout
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    def test_returning_to_the_network_clears_the_miss_counter(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.network.value = SIGNATURE_PUB
        assert harness.run("reconcile").returncode == 0
        harness.network.value = SIGNATURE_HOME
        harness.now += 60

        assert harness.run("reconcile").returncode == 0

        assert harness.lease().network_misses == 0
        assert harness.warp.current_mode == "warp+doh"

    def test_an_unobtainable_signature_neither_renews_nor_counts_a_miss(
        self, harness: Harness
    ) -> None:
        assert harness.run("on").returncode == 0
        expires_at = harness.lease().expires_at
        harness.network.value = None

        for offset in (60, 120):
            harness.now = 1_000_000 + offset
            assert harness.run("reconcile").returncode == 0
            assert harness.lease().expires_at == expires_at
            assert harness.lease().network_misses == 0

        harness.now = int(expires_at)
        result = harness.run("reconcile")

        assert "lease expired; previous WARP state restored" in result.stdout
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    def test_the_hard_ceiling_closes_a_normal_lease_on_its_own_network(
        self, harness: Harness
    ) -> None:
        assert harness.run("on").returncode == 0
        hard_expires_at = harness.lease().hard_expires_at
        assert hard_expires_at is not None
        while harness.now + LEASE_SECONDS < hard_expires_at:
            harness.now += LEASE_SECONDS - 60
            assert harness.run("reconcile").returncode == 0
        harness.now = int(hard_expires_at)

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "maximum lease duration reached; previous WARP state restored" in result.stdout
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    def test_a_matching_signature_never_resurrects_an_expired_lease(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.now = int(harness.lease().expires_at)
        reads = harness.network.reads

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "lease expired; previous WARP state restored" in result.stdout
        assert harness.network.reads == reads
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize("phase", ["activating", "restoring"])
    def test_a_matching_signature_does_not_pre_empt_an_interrupted_transition(
        self, harness: Harness, phase: str
    ) -> None:
        assert harness.run("on").returncode == 0
        harness.store.write_lease(replace(harness.lease(), phase=phase))
        reads = harness.network.reads

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "interrupted WARP transition completed" in result.stdout
        assert harness.network.reads == reads
        assert not harness.store.metadata_exists()

    def test_a_matching_signature_does_not_survive_a_boot_change(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.boot_session = "boot-b"

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "boot session changed; previous WARP state restored" in result.stdout
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    def test_pub_on_rehomes_the_lease_without_moving_the_hard_ceiling(
        self, harness: Harness
    ) -> None:
        assert harness.run("on").returncode == 0
        hard_expires_at = harness.lease().hard_expires_at
        lease_id = harness.lease().lease_id
        harness.network.value = SIGNATURE_PUB
        harness.now += 60

        result = harness.run("on")

        assert result.returncode == 0
        assert result.stdout.startswith("pub mode renewed until ")
        assert harness.lease().lease_id == lease_id
        assert harness.lease().network_signature == SIGNATURE_PUB
        assert harness.lease().network_misses == 0
        assert harness.lease().hard_expires_at == hard_expires_at
        assert harness.lease().expires_at == harness.now + LEASE_SECONDS

    def test_pub_on_adds_a_hard_ceiling_to_a_legacy_lease(self, harness: Harness) -> None:
        _copy_fixture("v1-active.json", harness.paths.lease)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"
        harness.now += 60

        result = harness.run("on")

        assert result.returncode == 0
        assert harness.lease().started_at == harness.now
        assert harness.lease().expires_at == harness.now + LEASE_SECONDS
        assert harness.lease().hard_expires_at == harness.now + MAX_LEASE_SECONDS

    def test_a_failed_renewal_write_leaves_the_lease_on_its_current_expiry(
        self, harness: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert harness.run("on").returncode == 0
        lease = harness.paths.lease.read_bytes()
        harness.now += 60

        def fail_write(_state) -> None:
            raise OSError

        monkeypatch.setattr(harness.store, "write_lease", fail_write)

        result = harness.run("reconcile")

        assert result.returncode == 1
        assert "keeps its current expiry" in result.stderr
        assert harness.paths.lease.read_bytes() == lease


class TestPubLeaseStateCompatibility:
    def test_legacy_on_migrates_without_losing_restore_intent_or_ceiling(self, harness):
        _copy_fixture("v1-active-signature.json", harness.paths.lease)
        original = harness.lease()
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"
        harness.now += 60

        result = harness.run("on")

        assert result.returncode == 0
        state = harness.lease()
        assert state.expected_mode == "warp+doh"
        assert state.lease_id == original.lease_id
        assert state.hard_expires_at == original.hard_expires_at
        assert state.previous_mode == original.previous_mode
        assert state.previous_status == original.previous_status
        assert harness.store.load_recovery().expected_mode == "warp+doh"
        assert harness.warp.calls.index(("set-mode", "proxy")) < harness.warp.calls.index(
            ("set-mode", "warp+doh")
        )
        assert harness.run("off").returncode == 0
        assert harness.warp.current_mode == "proxy"
        assert harness.warp.current_status == "Disconnected"

    def test_legacy_migration_retains_recovery_when_restore_fails(self, harness):
        _copy_fixture("v1-active.json", harness.paths.lease)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"
        harness.warp.fail_once.append("set-mode:proxy")

        result = harness.run("on")

        assert result.returncode == 1
        assert harness.lease().expected_mode == "tunnel_only"
        assert harness.store.load_recovery().previous_mode == "proxy"
        assert ("set-mode", "warp+doh") not in harness.warp.calls
        assert harness.run("reconcile").returncode == 0
        assert harness.warp.current_mode == "proxy"

    def test_legacy_migration_readiness_failure_restores_original_mode(self, harness):
        _copy_fixture("v1-active.json", harness.paths.lease)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"
        harness.readiness.error = "system DNS unavailable"

        result = harness.run("on")

        assert result.returncode == 1
        assert harness.warp.current_mode == "proxy"
        assert harness.warp.current_status == "Disconnected"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize(
        ("fixture_name", "phase"),
        [
            ("v1-active.json", "active"),
            ("v1-activating.json", "activating"),
            ("v1-restoring.json", "restoring"),
        ],
    )
    def test_reads_every_valid_v1_phase(
        self, harness: Harness, fixture_name: str, phase: str
    ) -> None:
        _copy_fixture(fixture_name, harness.paths.lease)

        state = harness.store.load_lease()

        assert state is not None
        assert state.phase == phase
        assert state.expected_mode == "tunnel_only"

    @pytest.mark.parametrize(
        ("fixture_name", "expected_status"),
        [
            ("v1-active.json", "Disconnected"),
            ("v1-recovery.json", "Disconnected"),
            ("v1-degraded.json", "Unable to connect"),
        ],
    )
    def test_restore_intent_is_read_or_derived_from_v1_state(
        self, harness: Harness, fixture_name: str, expected_status: str
    ) -> None:
        _copy_fixture(fixture_name, harness.paths.lease)

        state = harness.store.load_lease()

        assert state is not None
        assert state.previous_status == expected_status
        assert state.previous_connected is False

    def test_degraded_intent_downgrades_to_a_disconnected_boolean_reader(
        self, harness: Harness
    ) -> None:
        harness.warp.current_status = "Unable to connect"
        assert harness.run("on").returncode == 0
        written = json.loads(harness.paths.lease.read_text(encoding="utf-8"))
        del written["previous_status"]
        harness.paths.lease.write_text(json.dumps(written), encoding="utf-8")

        state = harness.store.load_lease()

        assert written["previous_connected"] is False
        assert state is not None
        assert state.previous_status == "Disconnected"

    def test_degraded_v1_state_restores_best_effort(self, harness: Harness) -> None:
        _copy_fixture("v1-degraded.json", harness.paths.lease)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.status_queue = ["Disconnected"] * 20

        result = harness.run("off")

        assert result.returncode == 0
        assert "previous WARP state restored" in result.stdout
        assert ("disconnect",) not in harness.warp.calls
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize("fixture_name", ["v1-activating.json", "v1-restoring.json"])
    def test_reconciles_interrupted_v1_state(self, harness: Harness, fixture_name: str) -> None:
        _copy_fixture(fixture_name, harness.paths.lease)
        _copy_fixture("v1-recovery.json", harness.paths.recovery)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "interrupted WARP transition completed" in result.stdout
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    def test_corrupt_v1_state_restores_from_v1_recovery_snapshot(self, harness: Harness) -> None:
        _copy_fixture("v1-corrupt.json", harness.paths.lease)
        _copy_fixture("v1-recovery.json", harness.paths.recovery)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"

        result = harness.run("reconcile")

        assert result.returncode == 0
        assert "recovered from immutable snapshot" in result.stderr
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("version", 2),
            ("phase", "unknown"),
            ("lease_id", ""),
            ("started_at", True),
            ("expires_at", 999_999),
            ("previous_connected", "false"),
            ("previous_status", "Disconnecting"),
            ("previous_status", True),
            ("previous_status", "Connected"),
            ("expected_mode", "proxy"),
            ("started_at", math.nan),
            ("expires_at", math.inf),
            ("network_misses", "1"),
            ("network_misses", True),
            ("network_misses", -1),
            ("network_misses", 1.0),
            ("network_misses", NETWORK_MISS_LIMIT + 1),
            ("network_misses", None),
            ("hard_expires_at", math.inf),
            ("hard_expires_at", math.nan),
            ("hard_expires_at", 999_999),
            ("hard_expires_at", "1043200"),
            ("network_signature", SIGNATURE_HOME[:-1]),
            ("network_signature", SIGNATURE_HOME.upper()),
            ("network_signature", "z" * 64),
            ("network_signature", 1),
        ],
    )
    def test_rejects_invalid_v1_state(
        self, harness: Harness, field_name: str, value: object
    ) -> None:
        raw = json.loads((FIXTURES / "v1-active.json").read_text(encoding="utf-8"))
        raw[field_name] = value
        harness.paths.directory.mkdir(parents=True)
        harness.paths.lease.write_text(json.dumps(raw), encoding="utf-8")

        result = harness.run("reconcile")

        assert result.returncode == 1
        assert "invalid lease state and recovery snapshot" in result.stderr
        assert harness.warp.calls == []

    def test_a_lease_without_the_network_fields_reconciles_as_before(
        self, harness: Harness
    ) -> None:
        _copy_fixture("v1-active.json", harness.paths.lease)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"

        result = harness.run("reconcile")

        state = harness.lease()
        assert result.returncode == 0
        assert state is not None
        assert (state.network_signature, state.network_misses, state.hard_expires_at) == (
            None,
            0,
            None,
        )
        assert harness.network.reads == 0
        assert harness.store.metadata_exists()

    def test_network_fields_round_trip_through_a_v1_lease(self, harness: Harness) -> None:
        _copy_fixture("v1-active-signature.json", harness.paths.lease)

        state = harness.store.load_lease()
        assert state is not None
        harness.store.write_lease(state)

        assert state.network_signature == SIGNATURE_HOME
        assert state.network_misses == 0
        assert state.hard_expires_at == 1_043_200
        assert harness.store.load_lease() == state

    def test_unknown_v1_fields_survive_phase_and_renewal_updates(self, harness: Harness) -> None:
        raw = json.loads((FIXTURES / "v1-active.json").read_text(encoding="utf-8"))
        raw["future_field"] = {"producer": "future-writer", "revision": 2}
        harness.paths.directory.mkdir(parents=True)
        harness.paths.lease.write_text(json.dumps(raw), encoding="utf-8")
        shutil.copyfile(harness.paths.lease, harness.paths.recovery)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"

        renewed = harness.run("on")
        harness.warp.fail_once.append("set-mode:proxy")
        interrupted = harness.run("off")
        stored = json.loads(harness.paths.lease.read_text(encoding="utf-8"))

        assert renewed.returncode == 0
        assert interrupted.returncode == 1
        assert stored["phase"] == "restoring"
        assert stored["future_field"] == raw["future_field"]

    def test_written_lease_satisfies_v1_contract_under_an_external_reader(
        self, harness: Harness
    ) -> None:
        jq = shutil.which("jq")
        if jq is None:
            pytest.skip("jq is needed only for the external v1 contract check")
        assert harness.run("on").returncode == 0
        predicate = """
            .version == 1
            and (.phase == "activating" or .phase == "active" or .phase == "restoring")
            and (.lease_id | type == "string" and length > 0)
            and (.started_at | type == "number")
            and (.expires_at | type == "number")
            and .expires_at >= .started_at
            and (.boot_session | type == "string")
            and (.previous_mode | type == "string")
            and (.previous_connected | type == "boolean")
            and (.previous_status | type == "string" and length > 0)
            and (.previous_status == "Connected") == .previous_connected
            and .expected_mode == "warp+doh"
        """

        result = subprocess.run(
            [jq, "-e", predicate, str(harness.paths.lease)],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr


class TestHTTPSReadiness:
    @pytest.mark.parametrize("exit_code", [0, 6, 7, 28, 35, 60])
    def test_bounded_proxy_free_head_request_reports_transport_failures(self, tmp_path, exit_code):
        executable = tmp_path / "curl"
        recorded = tmp_path / "arguments.json"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, sys\n"
            "from pathlib import Path\n"
            f"Path({str(recorded)!r}).write_text(json.dumps(sys.argv[1:]))\n"
            f"raise SystemExit({exit_code})\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)

        result = pub_lease.HTTPSReadiness(str(executable)).failure()

        assert json.loads(recorded.read_text()) == [
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
        ]
        if exit_code == 0:
            assert result is None
        elif exit_code == 6:
            assert result == "system DNS could not resolve api.anthropic.com"
        else:
            assert result == f"HTTPS readiness check failed (curl exit {exit_code})"

    def test_outer_timeout_covers_a_stuck_resolver(self, monkeypatch):
        def timeout(command, **kwargs):
            assert kwargs["timeout"] == 12
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        monkeypatch.setattr(pub_lease.subprocess, "run", timeout)
        assert pub_lease.HTTPSReadiness().failure() == "DNS/HTTPS readiness check timed out"

    def test_missing_executable_is_a_readiness_failure(self, tmp_path):
        assert pub_lease.HTTPSReadiness(str(tmp_path / "absent")).failure() == (
            "could not run DNS/HTTPS readiness check"
        )


class TestPubLeaseRecoveryAndMaintenance:
    def test_force_off_quarantines_unrecoverable_state(self, harness: Harness) -> None:
        harness.paths.directory.mkdir(parents=True)
        harness.paths.lease.write_text("{broken lease", encoding="utf-8")
        harness.paths.recovery.write_text("{broken recovery", encoding="utf-8")
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"

        result = harness.run("off", force=True)

        assert result.returncode == 0
        assert "WARNING" in result.stderr
        assert harness.warp.current_status == "Disconnected"
        assert len(list(harness.paths.directory.glob("lease.json.invalid.1000000.*"))) == 1
        assert len(list(harness.paths.directory.glob("recovery.json.invalid.1000000.*"))) == 1

    def test_off_without_force_retains_unrecoverable_state(self, harness: Harness) -> None:
        harness.paths.directory.mkdir(parents=True)
        harness.paths.lease.write_text("{broken", encoding="utf-8")

        result = harness.run("off")

        assert result.returncode == 1
        assert "off --force" in result.stderr
        assert harness.paths.lease.exists()

    def test_cleanup_removes_only_old_quarantines(self, harness: Harness) -> None:
        harness.paths.directory.mkdir(parents=True)
        old = harness.paths.directory / "lease.json.invalid.1.1"
        fresh = harness.paths.directory / "recovery.json.invalid.2.2"
        old.write_text("old", encoding="utf-8")
        fresh.write_text("fresh", encoding="utf-8")
        old_time = time.time() - (8 * 24 * 60 * 60)
        os.utime(old, (old_time, old_time))

        harness.store.cleanup_invalid_state()

        assert not old.exists()
        assert fresh.exists()

    def test_log_rotation_keeps_single_backup(self, harness: Harness) -> None:
        content = b"x" * 1_048_577
        harness.paths.log.write_bytes(content)
        backup = harness.paths.log.with_name("pub-lease.log.1")
        backup.write_bytes(b"old")

        harness.store.rotate_log_if_needed()

        assert harness.paths.log.read_bytes() == b""
        assert backup.read_bytes() == content

    @pytest.mark.parametrize("failure_point", ["fchmod", "replace"])
    def test_atomic_write_failure_preserves_existing_state_and_removes_temporary(
        self,
        harness: Harness,
        monkeypatch: pytest.MonkeyPatch,
        failure_point: str,
    ) -> None:
        assert harness.run("on").returncode == 0
        original = harness.paths.lease.read_bytes()
        updated = replace(harness.lease(), started_at=1_000_060, expires_at=1_021_660)

        if failure_point == "fchmod":
            monkeypatch.setattr(
                pub_lease.os, "fchmod", lambda _descriptor, _mode: _raise_os_error()
            )
        else:
            monkeypatch.setattr(Path, "replace", lambda _source, _target: _raise_os_error())

        with pytest.raises(AtomicWriteError):
            harness.store.write_lease(updated)

        assert harness.paths.lease.read_bytes() == original
        assert not list(harness.paths.directory.glob("state.*"))


class TestPubLeaseFailures:
    def test_activation_write_failure_leaves_warp_unchanged(
        self, harness: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fail_write(_state) -> None:
            raise OSError

        monkeypatch.setattr(harness.store, "write_recovery", fail_write)

        result = harness.run("on")

        assert result.returncode == 1
        assert "activation metadata" in result.stderr
        assert harness.warp.current_mode == "proxy"
        assert not harness.store.metadata_exists()

    def test_second_activation_write_failure_is_recovered_on_reconcile(
        self, harness: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        original_write = harness.store.write_lease
        writes = 0

        def fail_first_write(state) -> None:
            nonlocal writes
            writes += 1
            if writes == 1:
                raise OSError
            original_write(state)

        monkeypatch.setattr(harness.store, "write_lease", fail_first_write)

        enabled = harness.run("on")
        reconciled = harness.run("reconcile")

        assert enabled.returncode == 1
        assert harness.warp.current_mode == "proxy"
        assert reconciled.returncode == 0
        assert "recovered from immutable snapshot" in reconciled.stderr
        assert not harness.store.metadata_exists()

    def test_renewal_write_failure_keeps_previous_expiry(
        self, harness: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert harness.run("on").returncode == 0
        lease = harness.paths.lease.read_bytes()
        # Unobtainable signature keeps the reconciler's own renewal out of this path.
        harness.network.value = None

        def fail_write(_state) -> None:
            raise OSError

        monkeypatch.setattr(harness.store, "write_lease", fail_write)

        result = harness.run("on")

        assert result.returncode == 1
        assert "previous expiry remains unchanged" in result.stderr
        assert harness.paths.lease.read_bytes() == lease

    def test_failed_activation_restores_previous_state(self, harness: Harness) -> None:
        harness.warp.fail_once.append("connect")

        result = harness.run("on")

        assert result.returncode == 1
        assert "previous state restored" in result.stderr
        assert harness.warp.current_mode == "proxy"
        assert harness.warp.current_status == "Disconnected"
        assert not harness.store.metadata_exists()

    @pytest.mark.parametrize("read_failure", ["read-policy", "read-mode"])
    def test_reconcile_retains_lease_on_inspection_failure(
        self, harness: Harness, read_failure: str
    ) -> None:
        assert harness.run("on").returncode == 0
        harness.warp.fail_once.append(read_failure)

        result = harness.run("reconcile")

        assert result.returncode == 1
        assert "retained" in result.stderr
        assert harness.store.metadata_exists()

    def test_status_uses_exact_unknown_values(self, harness: Harness) -> None:
        harness.warp.fail_once.extend(["read-mode", "read-status"])

        result = harness.run("status")

        assert result.returncode == 0
        assert result.stdout == "WARP: mode=unknown, status=unknown\npub lease: inactive\n"

    def test_warp_stderr_is_appended_to_existing_context(self, harness: Harness) -> None:
        harness.warp.fail_once.append("read-mode")
        harness.warp.failure_detail = "IPC service denied the request"

        result = harness.run("on")

        assert result.returncode == 1
        assert result.stderr == ("pub: could not read WARP mode: IPC service denied the request\n")


def _unattended(harness: Harness) -> None:
    harness.notifier.messages.clear()
    harness.interactive = False


class TestPubLeaseNotifications:
    def test_an_expired_lease_notifies_the_restore(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.now += LEASE_SECONDS
        _unattended(harness)

        assert harness.run("reconcile").returncode == 0

        assert harness.notifier.messages == ["lease expired; previous WARP state restored"]

    def test_a_network_change_notifies_the_restore(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.network.value = SIGNATURE_PUB
        assert harness.run("reconcile").returncode == 0
        harness.now += 60
        _unattended(harness)

        assert harness.run("reconcile").returncode == 0

        assert harness.notifier.messages == ["network changed; previous WARP state restored"]

    def test_the_hard_ceiling_notifies_the_restore(self, harness: Harness) -> None:
        _copy_fixture("v1-active-capped.json", harness.paths.lease)
        harness.warp.current_mode = "tunnel_only"
        harness.warp.current_status = "Connected"
        harness.now = 1_000_120
        _unattended(harness)

        assert harness.run("reconcile").returncode == 0

        assert harness.notifier.messages == [
            "maximum lease duration reached; previous WARP state restored"
        ]

    def test_a_boot_change_notifies_the_restore(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.boot_session = "boot-b"
        _unattended(harness)

        assert harness.run("reconcile").returncode == 0

        assert harness.notifier.messages == ["boot session changed; previous WARP state restored"]

    def test_an_interrupted_transition_notifies_once_it_completes(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.now += LEASE_SECONDS
        _unattended(harness)
        harness.warp.fail_once.append("set-mode:proxy")

        failed = harness.run("reconcile")
        assert failed.returncode == 1
        assert harness.notifier.messages == []

        assert harness.run("reconcile").returncode == 0

        assert harness.notifier.messages == [
            "interrupted WARP transition completed; previous WARP state restored"
        ]

    def test_mode_drift_notifies_the_lost_ownership(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.warp.current_mode = "warp"
        harness.warp.current_status = "Disconnected"
        _unattended(harness)

        assert harness.run("reconcile").returncode == 0

        assert harness.notifier.messages == [
            "lease ownership lost; WARP left unchanged (mode=warp, status=Disconnected)"
        ]

    def test_a_policy_drop_notifies_the_lost_ownership(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.warp.switch_locked = True
        _unattended(harness)

        assert harness.run("reconcile").returncode == 0

        assert harness.notifier.messages == [
            (
                "lease ownership lost to WARP policy (switch_locked); WARP left unchanged "
                "(mode=warp+doh, status=Connected)"
            )
        ]

    def test_an_uneventful_tick_notifies_nothing(self, harness: Harness) -> None:
        harness.interactive = False
        assert harness.run("on").returncode == 0
        harness.now += 60

        assert harness.run("reconcile").returncode == 0
        assert harness.run("off").returncode == 0

        assert harness.notifier.messages == []

    def test_a_close_read_on_a_terminal_is_not_also_notified(self, harness: Harness) -> None:
        assert harness.run("on").returncode == 0
        harness.now += LEASE_SECONDS

        result = harness.run("reconcile")

        assert "lease expired; previous WARP state restored" in result.stdout
        assert harness.notifier.messages == []


def _write_notify_recorder(path: Path, record: Path) -> Path:
    path.write_text(
        f"""#!{sys.executable}
import sys
from pathlib import Path
Path({str(record)!r}).write_text("\\n".join(sys.argv[1:]), encoding="utf-8")
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


class TestCommandNotifier:
    def test_title_and_body_travel_as_arguments(self, tmp_path: Path) -> None:
        record = tmp_path / "record"
        notifier = pub_lease.CommandNotifier(
            (str(_write_notify_recorder(tmp_path / "notify", record)),)
        )

        notifier.notify('lease ownership lost to "policy"; $(mode) left unchanged')

        assert record.read_text(encoding="utf-8").splitlines() == [
            "pub mode",
            'lease ownership lost to "policy"; $(mode) left unchanged',
        ]

    @pytest.mark.parametrize(
        "body",
        [
            None,
            "import sys\nprint('noise', file=sys.stderr)\nraise SystemExit(3)\n",
            "import time\ntime.sleep(30)\n",
        ],
        ids=["missing", "failing", "hanging"],
    )
    def test_a_delivery_failure_never_reaches_the_caller(
        self, tmp_path: Path, body: str | None
    ) -> None:
        script = tmp_path / "notify"
        if body is not None:
            script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
            script.chmod(0o755)

        assert pub_lease.CommandNotifier((str(script),), timeout=0.2).notify("ignored") is None

    def test_an_empty_command_spawns_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def refuse(*_arguments: object, **_options: object) -> None:
            raise AssertionError

        monkeypatch.setattr(pub_lease.subprocess, "run", refuse)

        assert pub_lease.CommandNotifier(()).notify("ignored") is None

    def test_the_default_command_bridges_into_the_user_gui_session(self) -> None:
        notifier = pub_lease.CommandNotifier(
            ("/bin/launchctl", "asuser", str(os.getuid()), *pub_lease.OSASCRIPT_NOTIFY)
        )

        assert pub_lease.CommandNotifier.from_environment({}) == notifier
        assert notifier.command[-1] == "--"
        assert "display notification (item 2 of argv) with title (item 1 of argv)" in (
            notifier.command
        )

    @pytest.mark.parametrize(
        ("override", "expected"),
        [("/usr/bin/true", ("/usr/bin/true",)), ("", ())],
    )
    def test_an_override_replaces_the_default_command(
        self, override: str, expected: tuple[str, ...]
    ) -> None:
        environment = {"PUB_NOTIFY_COMMAND": override}

        assert pub_lease.CommandNotifier.from_environment(environment).command == expected


class TestWarpClientAdapter:
    def test_nonzero_exit_keeps_normalised_stderr_and_discards_stdout(self, tmp_path: Path) -> None:
        executable = tmp_path / "warp-cli"
        executable.write_text(
            f"""#!{sys.executable}
import sys
print("SECRET-STDOUT")
print("  daemon   rejected\\nrequest  ", file=sys.stderr)
raise SystemExit(1)
""",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        client = pub_lease.WarpClient(executable, sleeper=lambda _delay: None)

        with pytest.raises(pub_lease.WarpError) as error:
            client.mode()

        assert str(error.value) == "daemon rejected request"
        assert "SECRET-STDOUT" not in str(error.value)

    def test_timeout_is_reported_as_a_warp_error(self, tmp_path: Path) -> None:
        executable = tmp_path / "warp-cli"
        executable.write_text(
            f"#!{sys.executable}\nimport time\ntime.sleep(30)\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        client = pub_lease.WarpClient(executable, timeout=0.05)

        with pytest.raises(pub_lease.WarpError) as error:
            client.mode()

        assert str(error.value) == "warp-cli command timed out"

    def test_spawn_failure_is_reported_as_a_warp_error(self, tmp_path: Path) -> None:
        client = pub_lease.WarpClient(tmp_path / "missing-warp-cli")

        with pytest.raises(pub_lease.WarpError) as error:
            client.mode()

        assert str(error.value) == "warp-cli command could not be started"

    @pytest.mark.parametrize(
        ("answer", "expected"),
        [
            ("true", "unlocked"),
            ("true\n", "unlocked"),
            ("false", "switch_locked"),
            ("false\n", "switch_locked"),
        ],
    )
    def test_policy_lock_asks_the_vendor_mode_switch_probe(
        self, tmp_path: Path, answer: str, expected: str
    ) -> None:
        client = pub_lease.WarpClient(
            _write_policy_probe(tmp_path, answer), sleeper=lambda _delay: None
        )

        assert client.policy_lock() == expected

    @pytest.mark.parametrize("answer", ["", "yes", "true false", "True", "warning: stale\ntrue"])
    def test_policy_lock_refuses_an_answer_it_cannot_classify(
        self, tmp_path: Path, answer: str
    ) -> None:
        client = pub_lease.WarpClient(
            _write_policy_probe(tmp_path, answer), sleeper=lambda _delay: None
        )

        with pytest.raises(pub_lease.WarpError):
            client.policy_lock()


SCUTIL_PRIMARY = (
    "<dictionary> {\n"
    "  PrimaryInterface : en0\n"
    "  PrimaryService : 2262B572-5785-46BF-AE88-7C003BE61B46\n"
    "  Router : 192.168.1.1\n"
    "}\n"
)
ARP_GATEWAY = "? (192.168.1.1) at c4:f:a6:64:be:10 on en0 ifscope [ethernet]\n"


def _write_probe(path: Path, output: str, exit_code: int = 0) -> Path:
    path.write_text(
        f"""#!{sys.executable}
import sys
from pathlib import Path
sys.stdin.read()
Path(__file__ + ".argv").write_text("\\n".join(sys.argv[1:]), encoding="utf-8")
sys.stdout.write({output!r})
raise SystemExit({exit_code})
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def _network(
    directory: Path,
    *,
    scutil: str = SCUTIL_PRIMARY,
    arp: str = ARP_GATEWAY,
    arp_exit: int = 0,
) -> pub_lease.SystemNetwork:
    directory.mkdir(parents=True, exist_ok=True)
    return pub_lease.SystemNetwork(
        scutil=_write_probe(directory / "scutil", scutil),
        arp=_write_probe(directory / "arp", arp, arp_exit),
    )


class TestSystemNetworkSignature:
    def test_gateway_mac_renderings_hash_identically(self, tmp_path: Path) -> None:
        renderings = ["c4:f:a6:64:be:10", "c4:0f:a6:64:be:10", "C4:0F:A6:64:BE:10"]

        digests = {
            _network(
                tmp_path / str(index),
                arp=f"? (192.168.1.1) at {rendering} on en0 ifscope [ethernet]\n",
            ).signature()
            for index, rendering in enumerate(renderings)
        }

        assert len(digests) == 1
        digest = digests.pop()
        assert digest is not None
        assert len(digest) == 64
        assert set(digest) <= set("0123456789abcdef")

    def test_the_same_gateway_over_another_interface_is_the_same_network(
        self, tmp_path: Path
    ) -> None:
        docked = _network(
            tmp_path / "docked",
            scutil=SCUTIL_PRIMARY.replace("en0", "en16"),
            arp="? (192.168.1.1) at c4:0f:a6:64:be:10 on en16 ifscope [ethernet]\n",
        )

        assert docked.signature() == _network(tmp_path / "wifi").signature()

    @pytest.mark.parametrize(
        ("scutil", "arp"),
        [
            (SCUTIL_PRIMARY.replace("192.168.1.1", "192.168.0.1"), ARP_GATEWAY),
            (SCUTIL_PRIMARY, "? (192.168.1.1) at 00:11:22:33:44:55 on en0 ifscope [ethernet]\n"),
        ],
    )
    def test_another_gateway_is_another_network(
        self, tmp_path: Path, scutil: str, arp: str
    ) -> None:
        moved = _network(tmp_path / "moved", scutil=scutil, arp=arp)

        assert moved.signature() != _network(tmp_path / "home").signature()

    def test_the_arp_entry_is_looked_up_on_the_primary_interface(self, tmp_path: Path) -> None:
        network = _network(tmp_path / "probe")

        assert network.signature() is not None
        argv = (tmp_path / "probe" / "arp.argv").read_text(encoding="utf-8").splitlines()
        assert argv == ["-n", "-i", "en0", "192.168.1.1"]

    @pytest.mark.parametrize(
        "scutil",
        [
            "  Permission denied\n  Permission denied\n",
            "<dictionary> {\n  PrimaryInterface : en0\n}\n",
            SCUTIL_PRIMARY.replace("192.168.1.1", "not-an-address"),
            SCUTIL_PRIMARY.replace("en0", "-i"),
        ],
    )
    def test_an_unreadable_primary_route_yields_no_signature(
        self, tmp_path: Path, scutil: str
    ) -> None:
        assert _network(tmp_path / "denied", scutil=scutil).signature() is None

    @pytest.mark.parametrize(
        ("arp", "arp_exit"),
        [
            ("192.168.1.1 (192.168.1.1) -- no entry on en0\n", 1),
            ("? (192.168.1.1) at (incomplete) on en0 ifscope [ethernet]\n", 0),
            ("? (192.168.1.1) at c4:0f:a6:64 on en0 ifscope [ethernet]\n", 0),
            ("? (192.168.1.1) at c4:0f:a6:64:be:zz on en0 ifscope [ethernet]\n", 0),
            ("? (192.168.1.1) at\n", 0),
            ("", 0),
        ],
    )
    def test_an_unresolvable_gateway_yields_no_signature(
        self, tmp_path: Path, arp: str, arp_exit: int
    ) -> None:
        network = _network(tmp_path / "arp-miss", arp=arp, arp_exit=arp_exit)

        assert network.signature() is None

    def test_a_missing_system_binary_yields_no_signature(self, tmp_path: Path) -> None:
        network = pub_lease.SystemNetwork(
            scutil=tmp_path / "absent-scutil", arp=tmp_path / "absent-arp"
        )

        assert network.signature() is None


class TestPubLeaseLocking:
    def test_file_lock_rejects_second_nonblocking_holder(self, tmp_path: Path) -> None:
        first = pub_lease.FileLock(tmp_path / "lease.lock")
        second = pub_lease.FileLock(tmp_path / "lease.lock")

        assert first.acquire(0) is True
        try:
            assert second.acquire(0) is False
        finally:
            first.release()
            second.release()

    def test_lock_creates_private_state_directory(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        lock = pub_lease.FileLock(state_dir / "lease.lock")

        assert lock.acquire(0) is True
        lock.release()

        assert state_dir.stat().st_mode & 0o777 == 0o700

    def test_interactive_timeout_waits_until_deadline(self, tmp_path: Path) -> None:
        first = pub_lease.FileLock(tmp_path / "lease.lock")
        elapsed = 0.0
        sleeps: list[float] = []

        def monotonic() -> float:
            return elapsed

        def sleeper(delay: float) -> None:
            nonlocal elapsed
            sleeps.append(delay)
            elapsed += delay

        second = pub_lease.FileLock(
            tmp_path / "lease.lock",
            monotonic=monotonic,
            sleeper=sleeper,
        )
        assert first.acquire(0) is True
        try:
            assert second.acquire(1.0) is False
        finally:
            first.release()
            second.release()

        assert elapsed >= 1.0
        assert sleeps


def _raise_os_error() -> None:
    raise AtomicWriteError


def _write_fake_warp(path: Path) -> None:
    path.write_text(
        f"""#!{sys.executable}
import json
import os
from pathlib import Path
import sys
state_path = Path(os.environ["FAKE_WARP_STATE"])
state = json.loads(state_path.read_text(encoding="utf-8"))
arguments = [argument for argument in sys.argv[1:] if argument != "-j"]
if arguments == ["settings", "mode-switch-allowed"]:
    print("true")
elif arguments == ["settings"]:
    print(json.dumps({{"settings": {{"operation_mode": state["mode"]}}}}))
elif arguments == ["status"]:
    print(json.dumps({{"status": state["status"], "reason": state.get("reason")}}))
elif arguments[0:1] == ["mode"]:
    state["mode"] = arguments[1]
elif arguments == ["connect"]:
    state["status"] = "Connected"
    if "FAKE_WARP_CONNECT_REASON" in os.environ:
        state["status"] = "Unable to connect"
        state["reason"] = json.loads(os.environ["FAKE_WARP_CONNECT_REASON"])
elif arguments == ["disconnect"]:
    state["status"] = "Disconnected"
else:
    raise SystemExit(64)
state_path.write_text(json.dumps(state), encoding="utf-8")
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


@pytest.fixture
def cli_environment(tmp_path: Path) -> dict[str, str]:
    warp = tmp_path / "warp-cli"
    state = tmp_path / "warp.json"
    _write_fake_warp(warp)
    state.write_text(json.dumps({"mode": "proxy", "status": "Disconnected"}), encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "PUB_WARP_CLI": str(warp),
            "PUB_CURL": "/usr/bin/true",
            # Without an override the CLI would post a real macOS notification from the test suite.
            "PUB_NOTIFY_COMMAND": str(
                _write_notify_recorder(tmp_path / "notify", tmp_path / "notified")
            ),
            "PUB_LEASE_STATE_DIR": str(tmp_path / "lease-state"),
            "PUB_LEASE_LOG_FILE": str(tmp_path / "pub-lease.log"),
            "PUB_LEASE_NOW": "1000000",
            "PUB_BOOT_SESSION": "boot-a",
            "PUB_LEASE_POLL_INTERVAL": "0",
            "PUB_NETWORK_SIGNATURE": SIGNATURE_HOME,
            "FAKE_WARP_STATE": str(state),
        }
    )
    return environment


def _run_cli(environment: dict[str, str], *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PUB_LEASE), *arguments],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


class TestPubLeaseCliParity:
    @pytest.mark.parametrize("reason_key", ["Port53Bound", "UnknownFailure"])
    def test_connection_failure_reports_only_known_reason_and_restores(
        self, cli_environment, reason_key
    ):
        environment = dict(
            cli_environment,
            FAKE_WARP_CONNECT_REASON=json.dumps({reason_key: "PRIVATE-DETAIL"}),
        )

        result = _run_cli(environment, "on")

        assert result.returncode == 1
        assert "previous state restored" in result.stderr
        assert "PRIVATE-DETAIL" not in result.stderr
        assert "UnknownFailure" not in result.stderr
        if reason_key == "Port53Bound":
            assert "local port 53 is already in use (Port53Bound)" in result.stderr
        state = json.loads(Path(environment["FAKE_WARP_STATE"]).read_text())
        assert state["mode"] == "proxy"
        assert state["status"] == "Disconnected"
        assert not (Path(environment["PUB_LEASE_STATE_DIR"]) / "lease.json").exists()

    def test_executable_cli_runs_on_status_and_off(self, cli_environment: dict[str, str]) -> None:
        results = [
            subprocess.run(
                [str(PUB_LEASE), command],
                env=cli_environment,
                capture_output=True,
                text=True,
                check=False,
            )
            for command in ("on", "status", "off")
        ]

        assert [result.returncode for result in results] == [0, 0, 0]
        assert results[0].stdout.startswith("pub mode ON until ")
        assert "remaining=0h30m" in results[1].stdout
        assert results[2].stdout == "pub mode OFF; previous WARP state restored\n"

    def test_cli_renews_while_the_network_signature_matches(
        self, cli_environment: dict[str, str]
    ) -> None:
        state_dir = Path(cli_environment["PUB_LEASE_STATE_DIR"])
        assert _run_cli(cli_environment, "on").returncode == 0

        result = _run_cli(dict(cli_environment, PUB_LEASE_NOW="1000060"), "reconcile")

        lease = json.loads((state_dir / "lease.json").read_text(encoding="utf-8"))
        assert result.returncode == 0
        assert lease["expires_at"] == 1_001_860
        assert lease["hard_expires_at"] == 1_043_200
        assert lease["network_signature"] == SIGNATURE_HOME

    def test_cli_closes_the_lease_once_the_network_signature_changes(
        self, cli_environment: dict[str, str]
    ) -> None:
        state_dir = Path(cli_environment["PUB_LEASE_STATE_DIR"])
        assert _run_cli(cli_environment, "on").returncode == 0
        elsewhere = dict(cli_environment, PUB_NETWORK_SIGNATURE=SIGNATURE_PUB)

        first = _run_cli(dict(elsewhere, PUB_LEASE_NOW="1000060"), "reconcile")
        second = _run_cli(dict(elsewhere, PUB_LEASE_NOW="1000120"), "reconcile")

        assert (first.returncode, second.returncode) == (0, 0)
        assert "network changed; previous WARP state restored" in second.stdout
        assert not (state_dir / "lease.json").exists()

    def test_cli_notifies_an_unattended_close(self, cli_environment: dict[str, str]) -> None:
        notified = Path(cli_environment["PUB_NOTIFY_COMMAND"]).with_name("notified")
        assert _run_cli(cli_environment, "on").returncode == 0
        assert not notified.exists()

        result = _run_cli(dict(cli_environment, PUB_LEASE_NOW="1001800"), "reconcile")

        assert result.returncode == 0
        assert notified.read_text(encoding="utf-8").splitlines() == [
            "pub mode",
            "lease expired; previous WARP state restored",
        ]

    @pytest.mark.parametrize(
        "arguments",
        [
            ["unknown"],
            ["on", "--bad"],
            ["status", "--bad"],
            ["reconcile", "--bad"],
            ["off", "--bad"],
            ["off", "--force", "--bad"],
        ],
    )
    def test_invalid_argument_contract(
        self, cli_environment: dict[str, str], arguments: list[str]
    ) -> None:
        result = subprocess.run(
            [str(PUB_LEASE), *arguments],
            env=cli_environment,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 2
        assert result.stderr == "usage: pub {on|off [--force]|status}\n"

    def test_default_command_is_status(self, cli_environment: dict[str, str]) -> None:
        result = _run_cli(cli_environment)

        assert result.returncode == 0
        assert result.stdout.endswith("pub lease: inactive\n")

    def test_reconcile_without_state_needs_no_warp(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "missing-state"
        environment = {
            "HOME": str(tmp_path),
            "PUB_WARP_CLI": str(tmp_path / "missing-warp"),
            "PUB_LEASE_STATE_DIR": str(state_dir),
        }

        result = subprocess.run(
            [str(PUB_LEASE), "reconcile"],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert result.stdout == result.stderr == ""
        assert not state_dir.exists()

    @pytest.mark.parametrize("arguments", [["off"], ["off", "--force"]])
    def test_off_without_state_needs_no_warp(self, tmp_path: Path, arguments: list[str]) -> None:
        state_dir = tmp_path / "missing-state"
        environment = {
            "HOME": str(tmp_path),
            "PUB_WARP_CLI": str(tmp_path / "missing-warp"),
            "PUB_LEASE_STATE_DIR": str(state_dir),
        }

        result = subprocess.run(
            [str(PUB_LEASE), *arguments],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert result.stdout == "pub mode is already OFF\n"
        assert result.stderr == ""
        assert not state_dir.exists()

    def test_off_with_state_still_requires_warp(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "lease-state"
        _copy_fixture("v1-active.json", state_dir / "lease.json")
        environment = {
            "HOME": str(tmp_path),
            "PUB_WARP_CLI": str(tmp_path / "missing-warp"),
            "PUB_LEASE_STATE_DIR": str(state_dir),
        }

        result = _run_cli(environment, "off")

        assert result.returncode == 1
        assert result.stderr == "pub: warp-cli is not available\n"
        assert (state_dir / "lease.json").exists()

    def test_status_does_not_create_state_or_lock(self, cli_environment: dict[str, str]) -> None:
        state_dir = Path(cli_environment["PUB_LEASE_STATE_DIR"])

        result = subprocess.run(
            [str(PUB_LEASE), "status"],
            env=cli_environment,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert result.stdout.endswith("pub lease: inactive\n")
        assert not state_dir.exists()

    def test_reconcile_contention_is_silent_success(self, cli_environment: dict[str, str]) -> None:
        state_dir = Path(cli_environment["PUB_LEASE_STATE_DIR"])
        _copy_fixture("v1-active.json", state_dir / "lease.json")
        with (state_dir / "lease.lock").open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run(
                [str(PUB_LEASE), "reconcile"],
                env=cli_environment,
                capture_output=True,
                text=True,
                check=False,
            )

        assert result.returncode == 0
        assert result.stdout == result.stderr == ""
