from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

import pytest
from otelbox_edge import config


@dataclass
class FakeTerminal:
    values: list[str | EOFError]
    tty: bool = True
    reads: list[tuple[str, bool]] = field(default_factory=list)

    def is_tty(self) -> bool:
        return self.tty

    def read(self, prompt: str, *, secret: bool = False) -> str:
        self.reads.append((prompt, secret))
        value = self.values.pop(0) if self.values else ""
        if isinstance(value, EOFError):
            raise value
        return value


class FakeCommands:
    def __init__(self, runtime_root: Path, *, fingerprint_status: int = 0) -> None:
        self.runtime_root = runtime_root
        self.fingerprint_status = fingerprint_status
        self.calls: list[list[str]] = []

    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(arguments)
        stdout = ""
        if arguments[:2] == ["/usr/bin/getconf", "DARWIN_USER_TEMP_DIR"]:
            stdout = f"{self.runtime_root}\n"
        elif "ecparam" in arguments:
            Path(arguments[arguments.index("-out") + 1]).write_text("new-key\n", encoding="utf-8")
        elif "req" in arguments:
            Path(arguments[arguments.index("-out") + 1]).write_text("new-cert\n", encoding="utf-8")
        elif "-fingerprint" in arguments:
            stdout = "sha256 Fingerprint=AA:BB\n"
        elif arguments[:3] == ["/usr/sbin/scutil", "--get", "LocalHostName"]:
            stdout = "work-mac\n"
        status = self.fingerprint_status if "-fingerprint" in arguments else 0
        return subprocess.CompletedProcess(arguments, status, stdout, "")


@dataclass
class ConfigHarness:
    repo_root: Path
    home: Path
    runtime_root: Path
    openssl: Path

    def run(
        self,
        arguments: list[str],
        values: list[str | EOFError],
        *,
        tty: bool = True,
        installer: config.PairInstaller | None = None,
        fingerprint_status: int = 0,
    ):
        terminal = FakeTerminal(list(values), tty=tty)
        commands = FakeCommands(self.runtime_root, fingerprint_status=fingerprint_status)
        stdout = StringIO()
        stderr = StringIO()
        result = config.main(
            arguments,
            platform_name="Darwin",
            repo_root=self.repo_root,
            environment={
                "HOME": str(self.home),
                "USER": "edge-user",
                "PATH": str(self.openssl.parent),
            },
            terminal=terminal,
            commands=commands,
            installer=installer,
            stdout=stdout,
            stderr=stderr,
        )
        return result, stdout.getvalue(), stderr.getvalue(), terminal, commands


@pytest.fixture
def config_harness(tmp_path: Path) -> ConfigHarness:
    openssl = tmp_path / "bin/openssl"
    openssl.parent.mkdir()
    openssl.write_text("", encoding="utf-8")
    openssl.chmod(0o755)
    return ConfigHarness(
        repo_root=tmp_path / "repo",
        home=tmp_path / "home",
        runtime_root=tmp_path / "runtime",
        openssl=openssl,
    )


class TestTerminalInput:
    def test_plain_eof_is_distinguished_from_empty_input(self) -> None:
        terminal = config.TerminalInput(StringIO(), StringIO())

        with pytest.raises(EOFError):
            terminal.read("Prompt: ")


class TestConfigCli:
    def test_non_darwin_returns_before_parsing_bad_arguments(self, tmp_path: Path) -> None:
        stderr = StringIO()

        result = config.main(
            ["--bad"],
            platform_name="Linux",
            repo_root=tmp_path,
            environment={},
            stderr=stderr,
        )

        assert result == 0
        assert stderr.getvalue() == "otelbox-edge-config: macOS only (launchd + login keychain).\n"

    @pytest.mark.parametrize(
        "arguments",
        [["--bad"], ["--only"], ["--only", "bad"], ["--only=bad"]],
    )
    def test_bad_arguments_exit_64(
        self, config_harness: ConfigHarness, arguments: list[str]
    ) -> None:
        result, _stdout, stderr, _terminal, _commands = config_harness.run(arguments, [])

        assert result == 64
        assert stderr.startswith("otelbox-edge-config:")

    @pytest.mark.parametrize("argument", ["-h", "--help"])
    def test_help_exits_zero(self, config_harness: ConfigHarness, argument: str) -> None:
        result, stdout, stderr, terminal, commands = config_harness.run([argument], [])

        assert result == 0
        assert "Endpoint\n" in stdout
        assert "overlay is the deployment source of truth" in stdout
        assert "Token\n" in stdout
        assert "login Keychain item 'otelbox-edge-token'" in stdout
        assert "mode-0600 Bearer header" in stdout
        assert "Certificate\n" in stdout
        assert "Only client.crt is meant to travel" in stdout
        assert "private key stays on this machine" in stdout
        assert "OTELBOX_CERT_DAYS" in stdout
        assert "macOS-only" in stdout
        assert "Run it from a TTY" in stdout
        assert "./scripts/otelbox-edge-config.py --only=cert" in stdout
        assert "Certificate generation is intentionally excluded from a bare run" in stdout
        assert ".sh" not in stdout
        assert stderr == ""
        assert terminal.reads == []
        assert commands.calls == []

    @pytest.mark.parametrize(
        ("arguments", "expected_secret"),
        [
            (["--only", "endpoint"], False),
            (["--only=endpoint"], False),
            (["--only", "token"], True),
            (["--only=token"], True),
        ],
    )
    def test_both_only_forms_select_one_operation(
        self,
        config_harness: ConfigHarness,
        arguments: list[str],
        expected_secret,
    ) -> None:
        value = "token_value" if expected_secret else "otel.example.com:443"

        result, _stdout, _stderr, terminal, _commands = config_harness.run(arguments, [value])

        assert result == 0
        assert [secret for _prompt, secret in terminal.reads] == [expected_secret]

    def test_no_arguments_runs_endpoint_then_token(self, config_harness: ConfigHarness) -> None:
        result, _stdout, _stderr, terminal, _commands = config_harness.run(
            [],
            ["otel.example.com:443", "valid_token"],
        )

        assert result == 0
        assert [secret for _prompt, secret in terminal.reads] == [False, True]

    def test_non_tty_refuses_before_reading(self, config_harness: ConfigHarness) -> None:
        result, _stdout, stderr, terminal, commands = config_harness.run(
            ["--only", "endpoint"], [], tty=False
        )

        assert result == 1
        assert "stdin is not a TTY" in stderr
        assert terminal.reads == []
        assert commands.calls == []

    @pytest.mark.parametrize("only", ["endpoint", "token"])
    def test_eof_exits_cleanly_without_retrying(
        self,
        config_harness: ConfigHarness,
        only: str,
    ) -> None:
        result, _stdout, stderr, terminal, commands = config_harness.run(
            ["--only", only], [EOFError()]
        )
        secret = only == "token"

        assert result == 1
        assert stderr == "otelbox-edge-config: input closed before configuration completed\n"
        assert terminal.reads == [
            (
                "Bearer ingestion token (input hidden): "
                if secret
                else "Remote gateway endpoint (host:port, no https://): ",
                secret,
            )
        ]
        assert commands.calls == []


class TestEndpointConfiguration:
    def test_valid_endpoint_is_written_to_overlay_and_live(
        self, config_harness: ConfigHarness
    ) -> None:
        result, _stdout, stderr, _terminal, _commands = config_harness.run(
            ["--only", "endpoint"], ["otel.example.com:443"]
        )
        paths = config.ConfigPaths.create(config_harness.repo_root, config_harness.home)

        assert result == 0
        assert "wrote endpoint to overlay + live" in stderr
        for path in (paths.overlay_env, paths.live_env):
            assert path.read_text(encoding="utf-8") == (
                "OTELBOX_UPSTREAM_ENDPOINT=otel.example.com:443\n"
            )
            assert path.stat().st_mode & 0o777 == 0o644

    def test_endpoint_stops_after_three_invalid_attempts(
        self, config_harness: ConfigHarness
    ) -> None:
        result, _stdout, stderr, terminal, commands = config_harness.run(
            ["--only", "endpoint"], ["", "https://otel.example:443", "foo/bar:443"]
        )
        paths = config.ConfigPaths.create(config_harness.repo_root, config_harness.home)

        assert result == 1
        assert "giving up on endpoint after 3 attempts" in stderr
        assert len(terminal.reads) == 3
        assert commands.calls == []
        assert not paths.overlay_env.exists()
        assert not paths.live_env.exists()


class TestTokenConfiguration:
    def test_third_invalid_nonempty_token_is_never_persisted(
        self, config_harness: ConfigHarness
    ) -> None:
        result, _stdout, stderr, terminal, commands = config_harness.run(
            ["--only", "token"], ["bad token", "!", "still.invalid"]
        )
        auth_file = config_harness.runtime_root / "otelbox-edge/upstream-auth-header"

        assert result == 1
        assert "giving up on token after 3 attempts" in stderr
        assert len(terminal.reads) == 3
        assert commands.calls == []
        assert not auth_file.exists()

    def test_token_uses_exact_security_contract_and_private_atomic_header(
        self, config_harness: ConfigHarness
    ) -> None:
        auth_dir = config_harness.runtime_root / "otelbox-edge"
        auth_dir.mkdir(parents=True)
        auth_file = auth_dir / "upstream-auth-header"
        auth_file.write_text("old\n", encoding="utf-8")
        auth_file.chmod(0o666)

        result, _stdout, _stderr, _terminal, commands = config_harness.run(
            ["--only", "token"], ["valid_Token-1"]
        )

        assert result == 0
        assert commands.calls[0] == [
            "/usr/bin/security",
            "add-generic-password",
            "-U",
            "-a",
            "edge-user",
            "-s",
            "otelbox-edge-token",
            "-w",
            "valid_Token-1",
            "-T",
            "/usr/bin/security",
            str(config_harness.home / "Library/Keychains/login.keychain-db"),
        ]
        assert commands.calls[1] == ["/usr/bin/getconf", "DARWIN_USER_TEMP_DIR"]
        assert auth_file.read_text(encoding="utf-8") == "Bearer valid_Token-1\n"
        assert auth_file.stat().st_mode & 0o777 == 0o600
        assert auth_dir.stat().st_mode & 0o777 == 0o700
        assert not list(auth_dir.glob(".upstream-auth-header.*"))


class TestCertificateConfiguration:
    def test_generation_preserves_openssl_contract_and_file_modes(
        self, config_harness: ConfigHarness
    ) -> None:
        result, _stdout, stderr, _terminal, commands = config_harness.run(["--only", "cert"], [])
        paths = config.ConfigPaths.create(config_harness.repo_root, config_harness.home)

        assert result == 0
        assert "generated client certificate CN=" in stderr
        assert any("ecparam" in call and "prime256v1" in call for call in commands.calls)
        assert any(
            "req" in call
            and "-extensions" in call
            and call[call.index("-extensions") + 1] == "v3_client"
            for call in commands.calls
        )
        fingerprint_call = next(call for call in commands.calls if "-fingerprint" in call)
        assert fingerprint_call[1:3] == ["x509", "-in"]
        assert Path(fingerprint_call[3]).name == "client.crt"
        assert fingerprint_call[4:] == ["-noout", "-fingerprint", "-sha256"]
        assert Path(fingerprint_call[3]).parent not in {
            paths.overlay_client,
            paths.live_client,
        }
        for directory in (paths.overlay_client, paths.live_client):
            assert directory.stat().st_mode & 0o777 == 0o700
            assert (directory / "client.key").read_text(encoding="utf-8") == "new-key\n"
            assert (directory / "client.key").stat().st_mode & 0o777 == 0o600
            assert (directory / "client.crt").read_text(encoding="utf-8") == "new-cert\n"
            assert (directory / "client.crt").stat().st_mode & 0o777 == 0o644

    def test_install_failure_rolls_back_every_pair_copy(
        self, config_harness: ConfigHarness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        paths = config.ConfigPaths.create(config_harness.repo_root, config_harness.home)
        old = {
            paths.overlay_client / "client.key": b"overlay-old-key\n",
            paths.overlay_client / "client.crt": b"overlay-old-cert\n",
            paths.live_client / "client.key": b"live-old-key\n",
            paths.live_client / "client.crt": b"live-old-cert\n",
        }
        for path, content in old.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        original_replace = Path.replace
        failed = False

        def fail_overlay_cert(source: Path, target: Path) -> Path:
            nonlocal failed
            if target == paths.overlay_client / "client.crt" and not failed:
                failed = True
                raise OSError
            return original_replace(source, target)

        monkeypatch.setattr(Path, "replace", fail_overlay_cert)

        result, _stdout, _stderr, _terminal, _commands = config_harness.run(
            ["--only", "cert"], ["y"]
        )

        assert result == 1
        assert failed is True
        for path, content in old.items():
            assert path.read_bytes() == content
        assert not list(paths.overlay_client.glob(".client.*.*"))
        assert not list(paths.live_client.glob(".client.*.*"))

    def test_fingerprint_failure_keeps_existing_pairs_byte_and_mode_identical(
        self, config_harness: ConfigHarness
    ) -> None:
        paths = config.ConfigPaths.create(config_harness.repo_root, config_harness.home)
        old = {
            paths.overlay_client / "client.key": (b"overlay-old-key\n", 0o640),
            paths.overlay_client / "client.crt": (b"overlay-old-cert\n", 0o600),
            paths.live_client / "client.key": (b"live-old-key\n", 0o400),
            paths.live_client / "client.crt": (b"live-old-cert\n", 0o664),
        }
        for path, (content, mode) in old.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(mode)

        result, _stdout, stderr, _terminal, commands = config_harness.run(
            ["--only", "cert"],
            ["y"],
            fingerprint_status=1,
        )

        assert result == 1
        assert "could not read generated certificate fingerprint" in stderr
        assert any("-fingerprint" in call for call in commands.calls)
        for path, (content, mode) in old.items():
            assert path.read_bytes() == content
            assert path.stat().st_mode & 0o777 == mode
        assert not list(paths.overlay_client.glob(".client.*.*"))
        assert not list(paths.live_client.glob(".client.*.*"))

    def test_first_fingerprint_failure_leaves_no_pair_or_temporary_files(
        self, config_harness: ConfigHarness
    ) -> None:
        paths = config.ConfigPaths.create(config_harness.repo_root, config_harness.home)

        result, _stdout, stderr, _terminal, _commands = config_harness.run(
            ["--only", "cert"],
            [],
            fingerprint_status=1,
        )

        assert result == 1
        assert "could not read generated certificate fingerprint" in stderr
        assert not paths.overlay_client.exists()
        assert not paths.live_client.exists()
