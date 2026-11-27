from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/openbao-unseal.py"
EXAMPLE = REPO_ROOT / "roles/devbox/files/.config/openbao-unseal/config.json.example"
UNSEAL_KEY = "c2hhbWlyLWtleS1zaGFyZQ=="
TIMESTAMP = "2026-11-26T10:00:00+01:00"
SERVICE = "openbao-unseal-example-server"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("openbao_unseal", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


unseal = _load_module()


@dataclass
class Call:
    argv: list[str]
    stdin: str | None
    timeout: float


@dataclass
class FakeRunner:
    keychain: subprocess.CompletedProcess[str] | None = None
    ssh: subprocess.CompletedProcess[str] | None = None
    ssh_timeout: bool = False
    calls: list[Call] = field(default_factory=list)

    def run(
        self, argv: Sequence[str], *, stdin: str | None, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(Call(list(argv), stdin, timeout))
        if argv[0] == unseal.SECURITY:
            assert self.keychain is not None
            return self.keychain
        if self.ssh_timeout:
            raise subprocess.TimeoutExpired(list(argv), timeout)
        assert self.ssh is not None
        return self.ssh

    @property
    def ssh_calls(self) -> list[Call]:
        return [call for call in self.calls if call.argv[0] == unseal.SSH]


def _done(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def _key_found() -> subprocess.CompletedProcess[str]:
    return _done(0, UNSEAL_KEY + "\n")


def _answer(**fields: object) -> str:
    return json.dumps(fields) + "\n"


@pytest.fixture
def home(tmp_path: Path) -> Path:
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "ssh_host": "server.example.invalid",
                "ssh_user": "unseal-account",
                "inventory_host": "example-server",
            }
        ),
        encoding="utf-8",
    )
    identity = tmp_path / "openbao_unseal_ed25519"
    identity.write_text("private key\n", encoding="utf-8")
    return tmp_path


def _run(home: Path, runner: FakeRunner, *extra: str) -> tuple[int, list[str]]:
    log = home / "Logs" / "openbao-unseal.log"
    code = unseal.main(
        [
            "--config",
            str(home / "config.json"),
            "--identity",
            str(home / "openbao_unseal_ed25519"),
            "--log",
            str(log),
            *extra,
        ],
        runner=runner,
        clock=lambda: TIMESTAMP,
    )
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return code, lines


class TestKeychain:
    def test_missing_item_exits_zero_without_connecting(self, home: Path) -> None:
        runner = FakeRunner(keychain=_done(44, "", "item could not be found"))

        code, lines = _run(home, runner)

        assert code == 0
        assert runner.ssh_calls == []
        assert lines == [
            (
                f"{TIMESTAMP} openbao-unseal example-server: no Keychain item {SERVICE}; "
                "nothing to do"
            )
        ]

    def test_reads_the_named_generic_password(self, home: Path) -> None:
        runner = FakeRunner(keychain=_done(44))

        _run(home, runner)

        assert runner.calls[0].argv == [
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            SERVICE,
            "-a",
            "openbao",
            "-w",
        ]
        assert runner.calls[0].stdin is None

    def test_other_keychain_error_fails(self, home: Path) -> None:
        runner = FakeRunner(keychain=_done(51, "", "User interaction is not allowed."))

        code, lines = _run(home, runner)

        assert code == 1
        assert runner.ssh_calls == []
        assert "security exited 51: User interaction is not allowed." in lines[0]

    def test_empty_item_fails(self, home: Path) -> None:
        runner = FakeRunner(keychain=_done(0, "\n"))

        code, lines = _run(home, runner)

        assert code == 1
        assert "is empty" in lines[0]


class TestSsh:
    def test_key_travels_on_stdin_only(self, home: Path) -> None:
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(0, _answer(sealed_before=True, sealed_after=False, action="unsealed")),
        )

        _run(home, runner)

        (call,) = runner.ssh_calls
        assert call.stdin == UNSEAL_KEY + "\n"
        assert all(UNSEAL_KEY not in argument for argument in call.argv)

    def test_command_pins_identity_host_key_checking_and_timeouts(self, home: Path) -> None:
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(0, _answer(sealed_before=False, sealed_after=False, action="none")),
        )

        _run(home, runner)

        (call,) = runner.ssh_calls
        argv = call.argv
        assert argv[0] == "/usr/bin/ssh"
        assert argv[argv.index("-i") + 1] == str(home / "openbao_unseal_ed25519")
        options = [argv[index + 1] for index, value in enumerate(argv) if value == "-o"]
        assert "BatchMode=yes" in options
        assert "StrictHostKeyChecking=yes" in options
        assert "IdentitiesOnly=yes" in options
        assert "ConnectTimeout=10" in options
        assert argv[-1] == "unseal-account@server.example.invalid"
        assert "-p" not in argv
        assert call.timeout == unseal.RUN_TIMEOUT_SECONDS

    def test_configured_port_is_passed(self, home: Path) -> None:
        config = home / "config.json"
        document = json.loads(config.read_text(encoding="utf-8"))
        config.write_text(json.dumps({**document, "ssh_port": 2222}), encoding="utf-8")
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(0, _answer(sealed_before=False, sealed_after=False, action="none")),
        )

        _run(home, runner)

        (call,) = runner.ssh_calls
        assert call.argv[call.argv.index("-p") + 1] == "2222"

    def test_missing_identity_fails_without_connecting(self, home: Path) -> None:
        (home / "openbao_unseal_ed25519").unlink()
        runner = FakeRunner(keychain=_key_found())

        code, lines = _run(home, runner)

        assert code == 1
        assert runner.ssh_calls == []
        assert "no SSH key at" in lines[0]

    def test_connection_failure_logs_ssh_stderr(self, home: Path) -> None:
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(255, "", "debug\nHost key verification failed.\n"),
        )

        code, lines = _run(home, runner)

        assert code == 1
        assert lines[0].endswith("ssh failed: Host key verification failed.")

    def test_timeout_fails(self, home: Path) -> None:
        runner = FakeRunner(keychain=_key_found(), ssh_timeout=True)

        code, lines = _run(home, runner)

        assert code == 1
        assert "ssh timed out after 60 s" in lines[0]


class TestResponse:
    def test_unsealed(self, home: Path) -> None:
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(0, _answer(sealed_before=True, sealed_after=False, action="unsealed")),
        )

        code, lines = _run(home, runner)

        assert code == 0
        assert lines == [
            (
                f"{TIMESTAMP} openbao-unseal example-server: unsealed "
                "(sealed_before=true sealed_after=false)"
            )
        ]

    def test_already_unsealed(self, home: Path) -> None:
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(0, _answer(sealed_before=False, sealed_after=False, action="none")),
        )

        code, lines = _run(home, runner)

        assert code == 0
        assert lines[0].endswith("already unsealed (sealed_before=false sealed_after=false)")

    def test_failed_action_logs_server_error(self, home: Path) -> None:
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(
                1,
                _answer(
                    sealed_before=True, sealed_after=True, action="failed", error="invalid key"
                ),
            ),
        )

        code, lines = _run(home, runner)

        assert code == 1
        assert lines[0].endswith(
            "server exited 1, action=failed (sealed_before=true sealed_after=true): invalid key"
        )

    def test_unreachable_bao_fails(self, home: Path) -> None:
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(
                2,
                _answer(
                    sealed_before=True,
                    sealed_after=True,
                    action="failed",
                    error="connection refused",
                ),
            ),
        )

        code, lines = _run(home, runner)

        assert code == 1
        assert "server exited 2" in lines[0]
        assert lines[0].endswith(": connection refused")

    def test_exit_zero_but_still_sealed_fails(self, home: Path) -> None:
        runner = FakeRunner(
            keychain=_key_found(),
            ssh=_done(0, _answer(sealed_before=True, sealed_after=True, action="unsealed")),
        )

        code, _ = _run(home, runner)

        assert code == 1

    @pytest.mark.parametrize(
        "stdout",
        [
            "",
            "not json\n",
            "[1, 2]\n",
            _answer(sealed_before=True, action="none"),
            _answer(sealed_before=True, sealed_after=False, action="rebooted"),
            _answer(sealed_before=True, sealed_after=False, action="none", error=7),
        ],
    )
    def test_malformed_response_fails(self, home: Path, stdout: str) -> None:
        runner = FakeRunner(keychain=_key_found(), ssh=_done(0, stdout))

        code, lines = _run(home, runner)

        assert code == 1
        assert "bad response" in lines[0]

    def test_uses_the_last_line_of_output(self, home: Path) -> None:
        stdout = "banner\n" + _answer(sealed_before=False, sealed_after=False, action="none")
        runner = FakeRunner(keychain=_key_found(), ssh=_done(0, stdout))

        code, _ = _run(home, runner)

        assert code == 0


class TestConfig:
    def test_example_config_is_valid(self) -> None:
        config = unseal.load_config(EXAMPLE)

        assert config.inventory_host == "example-server"
        assert config.keychain_service == SERVICE
        assert config.ssh_host.endswith(".invalid")

    def test_check_config_does_not_touch_keychain_or_log(self, home: Path) -> None:
        runner = FakeRunner()
        stdout = StringIO()

        code = unseal.main(
            ["--config", str(home / "config.json"), "--log", str(home / "x.log"), "--check-config"],
            runner=runner,
            stdout=stdout,
        )

        assert code == 0
        assert runner.calls == []
        assert not (home / "x.log").exists()
        assert "config ok" in stdout.getvalue()

    @pytest.mark.parametrize(
        "document",
        [
            {"ssh_host": "-oProxyCommand=x", "ssh_user": "u", "inventory_host": "s"},
            {"ssh_host": "h.example.invalid", "ssh_user": "-oX=y", "inventory_host": "s"},
            {"ssh_host": "h.example.invalid", "inventory_host": "s"},
            {"ssh_host": "h.example.invalid", "ssh_user": "u", "inventory_host": "a b"},
            {"ssh_host": "h.example.invalid", "ssh_user": "u"},
            {"ssh_host": "h.example.invalid", "ssh_user": "u", "inventory_host": "s", "x": 1},
            {
                "ssh_host": "h.example.invalid",
                "ssh_user": "u",
                "inventory_host": "s",
                "ssh_port": 0,
            },
            {
                "ssh_host": "h.example.invalid",
                "ssh_user": "u",
                "inventory_host": "s",
                "ssh_port": "22",
            },
            {
                "ssh_host": "h.example.invalid",
                "ssh_user": "u",
                "inventory_host": "s",
                "ssh_port": True,
            },
            ["h.example.invalid"],
        ],
    )
    def test_invalid_config_is_rejected(self, tmp_path: Path, document: object) -> None:
        path = tmp_path / "config.json"
        path.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(unseal.ConfigError):
            unseal.load_config(path)

    def test_missing_config_logs_one_line_and_exits_zero(self, tmp_path: Path) -> None:
        runner = FakeRunner()
        log = tmp_path / "openbao-unseal.log"

        code = unseal.main(
            ["--config", str(tmp_path / "absent.json"), "--log", str(log)],
            runner=runner,
            clock=lambda: TIMESTAMP,
        )

        assert code == 0
        assert runner.calls == []
        lines = log.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert lines[0].startswith(f"{TIMESTAMP} openbao-unseal: not configured")

    def test_invalid_config_logs_and_exits_two(self, tmp_path: Path) -> None:
        config = tmp_path / "config.json"
        config.write_text("{", encoding="utf-8")
        log = tmp_path / "openbao-unseal.log"

        code = unseal.main(
            ["--config", str(config), "--log", str(log)],
            runner=FakeRunner(),
            clock=lambda: TIMESTAMP,
        )

        assert code == 2
        assert "is not valid JSON" in log.read_text(encoding="utf-8")

    def test_check_config_fails_on_missing_config(self, tmp_path: Path) -> None:
        stderr = StringIO()

        code = unseal.main(
            ["--config", str(tmp_path / "absent.json"), "--check-config"],
            runner=FakeRunner(),
            stderr=stderr,
        )

        assert code == 2
        assert "not configured" in stderr.getvalue()


class TestLog:
    def test_appends_one_line_per_run(self, home: Path) -> None:
        for _ in range(2):
            _run(home, FakeRunner(keychain=_done(44)))

        _, lines = _run(home, FakeRunner(keychain=_done(44)))

        assert len(lines) == 3

    def test_rotates_an_oversized_log(self, tmp_path: Path) -> None:
        log = tmp_path / "openbao-unseal.log"
        log.write_text("x" * (unseal.LOG_MAX_BYTES + 1), encoding="utf-8")

        unseal.append_log(log, "fresh")

        assert log.read_text(encoding="utf-8") == "fresh\n"
        assert (tmp_path / "openbao-unseal.log.1").stat().st_size == unseal.LOG_MAX_BYTES + 1


def test_parses_as_python_39_for_the_system_interpreter() -> None:
    ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT), feature_version=(3, 9))
