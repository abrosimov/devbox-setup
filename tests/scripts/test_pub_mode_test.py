from __future__ import annotations

import importlib.util
import json
import signal
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("pub_mode_test", ROOT / "scripts/pub-mode-test.py")
assert SPEC is not None
assert SPEC.loader is not None
gate_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate_module
SPEC.loader.exec_module(gate_module)


class Commands:
    def __init__(self):
        self.mode = "proxy"
        self.status = "Disconnected"
        self.protocol = "masque"
        self.protocol_source = "network_policy"
        self.settings_queue = []
        self.calls = []
        self.curl_calls = 0
        self.fail_curl_at = 0
        self.interrupt_connect = False
        self.fail_restore = False

    def run(self, command, **kwargs):
        assert 0 < kwargs["timeout"] <= (35 if Path(command[0]).name == "curl" else 15)
        self.calls.append(command)
        executable = Path(command[0]).name
        arguments = [argument for argument in command[1:] if argument != "-j"]
        output = ""
        code = 0
        if executable == "curl":
            self.curl_calls += 1
            code = 6 if self.curl_calls == self.fail_curl_at else 0
            if "input" in kwargs:
                output = b"401 16384"
        elif executable == "sysctl":
            output = "boot-a"
        elif executable == "warp-cli":
            output, code = self.warp(arguments)
        elif executable not in {"scutil", "arp"}:
            raise AssertionError(command)
        return subprocess.CompletedProcess(command, code, output, "")

    def warp(self, arguments):
        if arguments == ["settings"]:
            mode, protocol, protocol_source = (
                self.settings_queue.pop(0)
                if self.settings_queue
                else (self.mode, self.protocol, self.protocol_source)
            )
            return (
                json.dumps(
                    {
                        "settings": {
                            "operation_mode": mode,
                            "warp_tunnel_protocol": protocol,
                        },
                        "sources": {"warp_tunnel_protocol": protocol_source},
                    }
                ),
                0,
            )
        if arguments == ["status"]:
            return json.dumps({"status": self.status}), 0
        if arguments == ["settings", "mode-switch-allowed"]:
            return "true", 0
        if arguments[0] == "mode":
            if self.fail_restore and arguments[1] == "proxy":
                return "", 1
            self.mode = arguments[1]
        elif arguments[:2] == ["tunnel", "protocol"]:
            self.change_protocol(arguments)
        elif arguments == ["connect"]:
            self.status = "Connected"
            if self.interrupt_connect:
                raise KeyboardInterrupt
        elif arguments == ["disconnect"]:
            self.status = "Disconnected"
        else:
            raise AssertionError(arguments)
        return "", 0

    def change_protocol(self, arguments):
        if arguments[:3] == ["tunnel", "protocol", "set"]:
            self.protocol = arguments[3].lower()
            self.protocol_source = "consumer_overrides"
        elif arguments == ["tunnel", "protocol", "reset"]:
            self.protocol = "masque"
            self.protocol_source = "network_policy"
        else:
            raise AssertionError(arguments)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    commands = Commands()
    monkeypatch.setattr(gate_module.subprocess, "run", commands.run)
    candidate = gate_module.load_controller(gate_module.CANDIDATE, "pub_mode_test_candidate")
    return gate_module.RuntimeGate(tmp_path, candidate), commands


class TestRuntimeGate:
    def test_connected_dns_mode_still_requires_working_dns_and_https(self, runtime):
        gate, commands = runtime
        commands.mode = "warp+doh"
        commands.status = "Connected"
        commands.fail_curl_at = 1
        with pytest.raises(gate_module.GateError):
            gate.live()
        assert commands.mode == "warp+doh"
        assert commands.status == "Connected"
        assert not gate.store.metadata_exists()

    def test_preflight_does_not_mutate_warp_or_create_state(self, runtime):
        gate, commands = runtime
        assert gate.baseline() == ("proxy", "Disconnected", "masque", "network_policy")
        assert not gate.store.paths.directory.exists()
        assert commands.mode == "proxy"
        assert commands.curl_calls == 1

    def test_live_uses_candidate_and_restores_standard_snapshot(self, runtime):
        gate, commands = runtime
        gate.live()
        assert commands.mode == "proxy"
        assert commands.status == "Disconnected"
        assert commands.protocol == "masque"
        assert commands.protocol_source == "network_policy"
        assert commands.curl_calls == 3
        assert not gate.store.metadata_exists()
        assert not gate.standard_store.metadata_exists()

    @pytest.mark.parametrize("fail_at", [1, 2, 3])
    def test_dns_failure_prevents_success_and_restores_if_needed(self, runtime, fail_at):
        gate, commands = runtime
        commands.fail_curl_at = fail_at
        with pytest.raises(gate_module.GateError):
            gate.live()
        assert commands.mode == "proxy"
        assert commands.status == "Disconnected"
        assert commands.protocol == "masque"
        assert not gate.store.metadata_exists()
        if fail_at == 1:
            assert not any("mode" in command[1:] for command in commands.calls)

    def test_interrupt_after_mutation_runs_off(self, runtime):
        gate, commands = runtime
        commands.interrupt_connect = True
        with pytest.raises(KeyboardInterrupt):
            gate.live()
        assert commands.mode == "proxy"
        assert commands.status == "Disconnected"
        assert not gate.store.metadata_exists()
        assert (gate.store.paths.directory / "rollback.json").exists()

    def test_failed_restore_retains_real_recovery_metadata(self, runtime):
        gate, commands = runtime
        commands.fail_restore = True
        with pytest.raises(gate_module.GateError):
            gate.live()
        assert gate.store.paths.recovery.exists()
        assert gate.store.load_lease().phase == "restoring"
        assert (gate.store.paths.directory / "rollback.json").exists()

    @pytest.mark.parametrize("protocol_source", ["network_policy", "consumer_overrides"])
    def test_guardian_waits_for_settings_then_restores_with_head_only(
        self, runtime, protocol_source
    ):
        gate, commands = runtime
        commands.mode = "warp+doh"
        commands.status = "Connected"
        commands.protocol = "wireguard"
        commands.protocol_source = "consumer_overrides"
        expected = ("proxy", "masque", protocol_source)
        commands.settings_queue = [
            ("warp+doh", "wireguard", "consumer_overrides"),
            expected,
        ]

        gate_module.restore_snapshot(
            gate.module,
            ("proxy", "Connected", "masque", protocol_source),
        )

        assert (commands.mode, commands.status) == ("proxy", "Connected")
        assert (commands.protocol, commands.protocol_source) == ("masque", protocol_source)
        curl = [call for call in commands.calls if Path(call[0]).name == "curl"]
        assert len(curl) == 1
        assert "--head" in curl[0]
        assert "--data-binary" not in curl[0]

    def test_restart_recovers_stale_run_before_removing_rollback(self, runtime):
        gate, commands = runtime
        home = gate.standard_store.paths.directory.parents[2]
        root = home / ".local/state/pub-mode-test"
        stale = root / "run.stale"
        rollback = stale / "rollback.json"
        gate_module.write_snapshot(
            rollback,
            ("proxy", "Connected", "masque", "network_policy"),
        )
        commands.mode = "warp+doh"
        commands.status = "Connected"
        commands.protocol = "wireguard"
        commands.protocol_source = "consumer_overrides"

        gate_module.recover_stale_runs(home, gate.module, root)

        assert (commands.mode, commands.status) == ("proxy", "Connected")
        assert (commands.protocol, commands.protocol_source) == ("masque", "network_policy")
        assert not stale.exists()

    def test_failed_stale_recovery_retains_directory_and_marker(self, runtime):
        gate, commands = runtime
        home = gate.standard_store.paths.directory.parents[2]
        root = home / ".local/state/pub-mode-test"
        stale = root / "run.stale"
        rollback = stale / "rollback.json"
        gate_module.write_snapshot(
            rollback,
            ("proxy", "Connected", "masque", "network_policy"),
        )
        commands.mode = "warp+doh"
        commands.status = "Connected"
        commands.protocol = "wireguard"
        commands.protocol_source = "consumer_overrides"
        commands.fail_restore = True

        with pytest.raises(RuntimeError):
            gate_module.recover_stale_runs(home, gate.module, root)

        assert rollback.exists()
        assert stale.exists()

    def test_disabled_marker_does_not_block_stale_recovery(self, runtime):
        gate, commands = runtime
        home = gate.standard_store.paths.directory.parents[2]
        gate.standard_store.paths.directory.mkdir(parents=True)
        gate.standard_store.paths.disabled.touch()
        root = home / ".local/state/pub-mode-test"
        stale = root / "run.stale"
        rollback = stale / "rollback.json"
        gate_module.write_snapshot(
            rollback,
            ("proxy", "Connected", "masque", "network_policy"),
        )
        commands.mode = "warp+doh"
        commands.status = "Connected"
        commands.protocol = "wireguard"
        commands.protocol_source = "consumer_overrides"

        gate_module.recover_stale_runs(home, gate.module, root)

        assert gate.standard_store.paths.disabled.exists()
        assert not stale.exists()
        assert (commands.mode, commands.status) == ("proxy", "Connected")

    def test_guardian_recovers_stale_run_before_prerequisite_failure(self, runtime, monkeypatch):
        gate, commands = runtime
        home = gate.standard_store.paths.directory.parents[2]
        root = home / ".local/state/pub-mode-test"
        stale = root / "run.stale"
        gate_module.write_snapshot(
            stale / "rollback.json",
            ("proxy", "Connected", "masque", "network_policy"),
        )
        commands.mode = "warp+doh"
        commands.status = "Connected"
        commands.protocol = "wireguard"
        commands.protocol_source = "consumer_overrides"

        def missing_prerequisite(_home, *, live=False):
            assert live is True
            message = "missing prerequisite"
            raise gate_module.GateError(message)

        monkeypatch.setattr(gate_module, "check_environment", missing_prerequisite)

        with pytest.raises(gate_module.GateError, match="missing prerequisite"):
            gate_module.guardian(home)

        assert not stale.exists()
        assert (commands.mode, commands.status) == ("proxy", "Connected")

    def test_guardian_restoration_has_an_overall_deadline(self, runtime, monkeypatch):
        gate, _commands = runtime

        def never_returns(_module, _snapshot):
            signal.pause()

        monkeypatch.setattr(gate_module, "restore_snapshot", never_returns)

        with pytest.raises(gate_module.GateError, match="exceeded"):
            gate_module.restore_with_deadline(
                gate.module,
                ("proxy", "Connected", "masque", "network_policy"),
                timeout=0.01,
            )

    @pytest.mark.parametrize("filename", ["lease.json", "recovery.json", "disabled"])
    def test_existing_state_is_never_touched(self, runtime, filename):
        gate, commands = runtime
        gate.store.paths.directory.mkdir(parents=True)
        path = gate.store.paths.directory / filename
        path.write_text("user-owned", encoding="utf-8")
        with pytest.raises(gate_module.GateError):
            gate.live()
        assert path.read_text() == "user-owned"
        assert commands.calls == []

    @pytest.mark.parametrize("filename", ["lease.json", "recovery.json", "disabled"])
    def test_active_standard_state_is_never_used_for_candidate_metadata(self, runtime, filename):
        gate, commands = runtime
        gate.standard_store.paths.directory.mkdir(parents=True)
        path = gate.standard_store.paths.directory / filename
        path.write_text("standard-user-owned", encoding="utf-8")

        with pytest.raises(gate_module.GateError):
            gate.live()

        assert path.read_text() == "standard-user-owned"
        assert not gate.store.metadata_exists()
        assert commands.calls == []

    def test_connection_must_be_stable_before_mutation(self, runtime):
        gate, commands = runtime
        commands.status = "Connecting"
        with pytest.raises(gate_module.GateError):
            gate.live()
        assert commands.mode == "proxy"
        assert not gate.store.metadata_exists()


class TestPrerequisites:
    @pytest.mark.parametrize(
        ("mode", "status", "allowed"),
        [
            ("warp", "Connected", True),
            ("doh", "Connected", True),
            ("warp+doh", "Connected", True),
            ("dot", "Connected", True),
            ("warp+dot", "Connected", True),
            ("warp+doh", "Disconnected", False),
            ("warp+doh", "Connecting", False),
            ("tunnel_only", "Connected", False),
            ("proxy", "Connected", False),
        ],
    )
    def test_existing_dns_listener_requires_connected_warp_dns_mode(
        self, monkeypatch, mode, status, allowed
    ):
        def output(command):
            if command[0] == "/usr/sbin/netstat":
                return "udp4 0 0 *.53 *.*"
            if command[-1] == "settings":
                return json.dumps({"settings": {"operation_mode": mode}})
            return json.dumps({"status": status})

        monkeypatch.setattr(gate_module, "run", output)
        if allowed:
            gate_module.check_port_53("udp")
        else:
            with pytest.raises(gate_module.GateError):
                gate_module.check_port_53("udp")

    @pytest.fixture
    def machine(self, tmp_path, monkeypatch):
        warp = tmp_path / "warp-cli"
        warp.touch(mode=0o755)
        monkeypatch.setattr(gate_module, "WARP", warp)
        monkeypatch.setattr(gate_module.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(gate_module.os, "environ", {"HOME": str(tmp_path)})
        monkeypatch.setattr(gate_module, "run", lambda _command: "")
        return tmp_path

    def test_default_preflight_without_docker_or_installed_controller(self, machine):
        gate_module.check_environment(machine)

    def test_live_requires_bootstrap_controller(self, machine):
        with pytest.raises(gate_module.GateError) as error:
            gate_module.check_environment(machine, live=True)
        assert "supervisor" in str(error.value)

    def test_reports_docker_and_both_port_failures_together(self, machine, monkeypatch):
        settings = machine / "Library/Group Containers/group.com.docker/settings-store.json"
        settings.parent.mkdir(parents=True)
        settings.write_text('{"KernelForUDP": true}', encoding="utf-8")
        monkeypatch.setattr(
            gate_module, "run", lambda command: f"{command[-1]}4 0 0 *.53 *.* LISTEN"
        )
        with pytest.raises(gate_module.GateError) as error:
            gate_module.check_environment(machine)
        assert "KernelForUDP" in str(error.value)
        assert "tcp4 *.53" in str(error.value)
        assert "udp4 *.53" in str(error.value)

    def test_missing_docker_still_checks_real_ports(self, machine, monkeypatch):
        monkeypatch.setattr(gate_module, "run", lambda _command: "udp4 0 0 *.53 *.*")
        with pytest.raises(gate_module.GateError):
            gate_module.check_environment(machine)

    @pytest.mark.parametrize("kernel_udp", [False, True, None, "false"])
    def test_docker_setting_requires_exact_false(self, tmp_path, monkeypatch, kernel_udp):
        settings = tmp_path / "Library/Group Containers/group.com.docker/settings-store.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"KernelForUDP": kernel_udp}), encoding="utf-8")
        warp = tmp_path / "warp-cli"
        warp.touch(mode=0o755)
        monkeypatch.setattr(gate_module, "WARP", warp)
        monkeypatch.setattr(gate_module.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(gate_module.os, "environ", {"HOME": str(tmp_path)})
        monkeypatch.setattr(gate_module, "run", lambda _command: "")
        monkeypatch.setattr(gate_module, "check_supervisor", lambda _home: None)
        if kernel_udp is False:
            gate_module.check_environment(tmp_path)
        else:
            with pytest.raises(gate_module.GateError):
                gate_module.check_environment(tmp_path)

    def test_live_refuses_fake_warp_override_before_commands(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gate_module.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(
            gate_module.os, "environ", {"HOME": str(tmp_path), "PUB_WARP_CLI": "fake"}
        )
        with pytest.raises(gate_module.GateError):
            gate_module.check_environment(tmp_path)

    @pytest.mark.parametrize("protocol", ["tcp4", "tcp6", "udp4", "udp6"])
    def test_netstat_detects_port53_even_without_process_visibility(self, protocol):
        output = f"{protocol} 0 0 *.53 *.* LISTEN\n{protocol} 0 0 127.0.0.1.5053 *.*\n"
        assert gate_module.port_53_listeners(output) == [f"{protocol} *.53"]

    def test_failed_bounded_command_never_prints_captured_private_output(self, monkeypatch):
        def fail(command, **kwargs):
            assert kwargs["timeout"] == 15
            return subprocess.CompletedProcess(command, 1, "private stdout", "private stderr")

        monkeypatch.setattr(gate_module.subprocess, "run", fail)
        with pytest.raises(gate_module.GateError) as error:
            gate_module.run(["/usr/bin/tool"])
        assert "private" not in str(error.value)

    def test_subprocess_timeout_fails_closed(self, monkeypatch):
        def timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        monkeypatch.setattr(gate_module.subprocess, "run", timeout)
        with pytest.raises(gate_module.GateError):
            gate_module.run(["/usr/bin/tool"])

    def test_live_missing_prerequisite_is_failure(self, monkeypatch):
        monkeypatch.setattr(gate_module.platform, "system", lambda: "Linux")
        assert gate_module.main(["--live"]) == 1
