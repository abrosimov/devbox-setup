from __future__ import annotations

import getpass
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TextIO

EX_USAGE = 64
KEYCHAIN_ITEM = "otelbox-edge-token"
DEFAULT_CERT_DAYS = "825"
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
ENDPOINT_PATTERN = re.compile(r"^[^\s/]+:[0-9]+$")
ENDPOINT_ATTEMPTS_EXHAUSTED = "giving up on endpoint after 3 attempts"
CREDENTIAL_ATTEMPTS_EXHAUSTED = "giving up on token after 3 attempts"
INPUT_CLOSED = "input closed before configuration completed"
KEYCHAIN_WRITE_FAILED = "could not store token in login keychain"
TEMP_DIR_LOOKUP_FAILED = "could not resolve DARWIN_USER_TEMP_DIR"
FINGERPRINT_FAILED = "could not read generated certificate fingerprint"
TTY_REQUIRED = "stdin is not a TTY — run interactively."
OPENSSL_UNAVAILABLE = "no usable openssl (PATH and /usr/bin/openssl)"
OPENSSL_GENERATION_FAILED = "openssl certificate generation failed"
HELP = """Interactive one-time machine-local setup for the durable otelbox edge collector.

This command fills values that are deliberately not tracked in the repository.
It is macOS-only because it integrates with launchd and the login Keychain.
Run it from a TTY; endpoint, token and certificate confirmation require input.

Endpoint
  The remote gateway authority in host:port form, without https://.
  It is written to both:
    roles/devbox/local/.config/otelbox/edge/endpoint.env
    ~/.config/otelbox/edge/endpoint.env
  The overlay is the deployment source of truth; the live copy applies locally.

Token
  A non-empty Bearer ingestion key containing only A-Z, a-z, 0-9, _ or -.
  The login Keychain item 'otelbox-edge-token' is authoritative.
  A private mode-0600 Bearer header is refreshed below DARWIN_USER_TEMP_DIR.
  The collector watches that header file, so token rotation needs no restart.

Certificate
  An optional client certificate and private key for an mTLS gateway front end.
  Both halves are installed into the overlay and live client directories:
    roles/devbox/local/.config/otelbox/edge/client/
    ~/.config/otelbox/edge/client/
  Only client.crt is meant to travel. The private key stays on this machine.
  Existing pairs require confirmation before regeneration.
  OTELBOX_CERT_DAYS overrides the default certificate validity of 825 days.

Usage
  ./scripts/otelbox-edge-config.py
      Configure endpoint first, then token. Certificate generation is excluded.
  ./scripts/otelbox-edge-config.py --only endpoint
  ./scripts/otelbox-edge-config.py --only=endpoint
  ./scripts/otelbox-edge-config.py --only token
  ./scripts/otelbox-edge-config.py --only=token
  ./scripts/otelbox-edge-config.py --only cert
  ./scripts/otelbox-edge-config.py --only=cert
  ./scripts/otelbox-edge-config.py -h
  ./scripts/otelbox-edge-config.py --help

Certificate generation is intentionally excluded from a bare run: regenerating
the client identity invalidates what the gateway front end already trusts.
"""


class ConfigurationError(RuntimeError):
    pass


class InputPort(Protocol):
    def is_tty(self) -> bool: ...

    def read(self, prompt: str, *, secret: bool = False) -> str: ...


class CommandPort(Protocol):
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]: ...


class TerminalInput:
    def __init__(self, stdin: TextIO, stderr: TextIO) -> None:
        self.stdin = stdin
        self.stderr = stderr

    def is_tty(self) -> bool:
        return self.stdin.isatty()

    def read(self, prompt: str, *, secret: bool = False) -> str:
        if secret:
            return getpass.getpass(prompt, stream=self.stderr)
        print(prompt, end="", file=self.stderr, flush=True)
        value = self.stdin.readline()
        if value == "":
            raise EOFError
        return value.rstrip("\n")


class CommandRunner:
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(arguments, capture_output=True, text=True, check=False)


@dataclass(frozen=True)
class ConfigPaths:
    overlay_env: Path
    live_env: Path
    overlay_client: Path
    live_client: Path

    @classmethod
    def create(cls, repo_root: Path, home: Path) -> ConfigPaths:
        overlay_root = repo_root / "roles/devbox/local/.config/otelbox/edge"
        live_root = home / ".config/otelbox/edge"
        return cls(
            overlay_env=overlay_root / "endpoint.env",
            live_env=live_root / "endpoint.env",
            overlay_client=overlay_root / "client",
            live_client=live_root / "client",
        )


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    content: bytes | None
    mode: int | None


class PairInstaller:
    def install(self, key: Path, cert: Path, paths: ConfigPaths) -> None:
        targets = [
            (key, paths.overlay_client / "client.key", 0o600),
            (cert, paths.overlay_client / "client.crt", 0o644),
            (key, paths.live_client / "client.key", 0o600),
            (cert, paths.live_client / "client.crt", 0o644),
        ]
        # 0700 on both: the overlay directory is what Ansible's filetree copy takes the
        # deployed mode from, so the private half never widens in transit.
        for directory in (paths.overlay_client, paths.live_client):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
        snapshots = [self._snapshot(target) for _source, target, _mode in targets]
        staged: list[tuple[Path, Path]] = []
        replaced: list[FileSnapshot] = []
        try:
            for source, target, mode in targets:
                staged.append((self._stage(source.read_bytes(), target, mode), target))
            for temporary, target in staged:
                snapshot = next(item for item in snapshots if item.path == target)
                temporary.replace(target)
                replaced.append(snapshot)
        except OSError:
            self._rollback(replaced)
            raise
        finally:
            for temporary, _target in staged:
                temporary.unlink(missing_ok=True)

    def _snapshot(self, path: Path) -> FileSnapshot:
        if not path.exists():
            return FileSnapshot(path, None, None)
        return FileSnapshot(path, path.read_bytes(), path.stat().st_mode & 0o777)

    def _stage(self, content: bytes, target: Path, mode: int) -> Path:
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        temporary = Path(name)
        try:
            os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return temporary

    def _rollback(self, snapshots: list[FileSnapshot]) -> None:
        for snapshot in reversed(snapshots):
            if snapshot.content is None:
                snapshot.path.unlink(missing_ok=True)
                continue
            temporary = self._stage(snapshot.content, snapshot.path, snapshot.mode or 0o600)
            temporary.replace(snapshot.path)


class Configurator:
    def __init__(
        self,
        paths: ConfigPaths,
        terminal: InputPort,
        commands: CommandPort,
        installer: PairInstaller,
        *,
        environment: dict[str, str],
        stderr: TextIO,
    ) -> None:
        self.paths = paths
        self.terminal = terminal
        self.commands = commands
        self.installer = installer
        self.environment = environment
        self.stderr = stderr

    def execute(self, only: str) -> int:
        try:
            if only in {"", "endpoint"}:
                self.set_endpoint()
            if only in {"", "token"}:
                self.set_token()
            # `cert` is deliberately excluded from a bare run: regenerating the client
            # identity invalidates whatever the gateway front end already trusts.
            if only == "cert":
                self.set_certificate()
        except EOFError:
            print(f"otelbox-edge-config: {INPUT_CLOSED}", file=self.stderr)
            return 1
        except (ConfigurationError, OSError) as error:
            print(f"otelbox-edge-config: {error}", file=self.stderr)
            return 1
        self.print_restart_guidance(only)
        return 0

    def set_endpoint(self) -> None:
        self._require_tty()
        endpoint = ""
        for attempt in range(1, 4):
            candidate = self.terminal.read(
                "Remote gateway endpoint (host:port, no https://): "
            ).strip()
            if not candidate:
                print(f"  empty input, try again ({attempt}/3)", file=self.stderr)
            elif "://" in candidate:
                print(
                    "  drop the scheme — give host:port only (e.g. otel.example.com:443)",
                    file=self.stderr,
                )
            elif ENDPOINT_PATTERN.fullmatch(candidate) is None:
                print(
                    "  expected host:numeric-port (e.g. otel.example.com:443)",
                    file=self.stderr,
                )
            else:
                endpoint = candidate
                break
        if not endpoint:
            raise ConfigurationError(ENDPOINT_ATTEMPTS_EXHAUSTED)
        content = f"OTELBOX_UPSTREAM_ENDPOINT={endpoint}\n"
        for path in (self.paths.overlay_env, self.paths.live_env):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            path.chmod(0o644)
        print(
            f"otelbox-edge-config: wrote endpoint to overlay + live ({endpoint})",
            file=self.stderr,
        )

    def set_token(self) -> None:
        self._require_tty()
        token: str | None = None
        for attempt in range(1, 4):
            candidate = self.terminal.read(
                "Bearer ingestion token (input hidden): ",
                secret=True,
            )
            if TOKEN_PATTERN.fullmatch(candidate) is not None:
                token = candidate
                break
            print(
                f"  expected a non-empty [A-Za-z0-9_-] token, try again ({attempt}/3)",
                file=self.stderr,
            )
        if token is None:
            raise ConfigurationError(CREDENTIAL_ATTEMPTS_EXHAUSTED)
        home = Path(self.environment["HOME"])
        security = self.commands.run(
            [
                "/usr/bin/security",
                "add-generic-password",
                "-U",
                "-a",
                self.environment["USER"],
                "-s",
                KEYCHAIN_ITEM,
                "-w",
                token,
                "-T",
                "/usr/bin/security",
                str(home / "Library/Keychains/login.keychain-db"),
            ]
        )
        if security.returncode:
            raise ConfigurationError(KEYCHAIN_WRITE_FAILED)
        runtime = self.commands.run(["/usr/bin/getconf", "DARWIN_USER_TEMP_DIR"])
        if runtime.returncode or not runtime.stdout.strip():
            raise ConfigurationError(TEMP_DIR_LOOKUP_FAILED)
        auth_dir = Path(runtime.stdout.strip()) / "otelbox-edge"
        auth_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        auth_dir.chmod(0o700)
        auth_file = auth_dir / "upstream-auth-header"
        _write_private_header(auth_file, f"Bearer {token}\n")
        print(f"otelbox-edge-config: stored '{KEYCHAIN_ITEM}' in login keychain", file=self.stderr)
        print(
            "otelbox-edge-config: refreshed the private watched header file",
            file=self.stderr,
        )

    def set_certificate(self) -> None:
        self._require_tty()
        openssl = self._resolve_openssl()
        overlay_cert = self.paths.overlay_client / "client.crt"
        overlay_key = self.paths.overlay_client / "client.key"
        if (overlay_cert.exists() or overlay_key.exists()) and not self._confirm_regeneration():
            print(
                "otelbox-edge-config: keeping the existing client certificate",
                file=self.stderr,
            )
            return
        subject = self._certificate_subject()
        cert_days = self.environment.get("OTELBOX_CERT_DAYS", DEFAULT_CERT_DAYS)
        with tempfile.TemporaryDirectory() as temporary_directory:
            workdir = Path(temporary_directory)
            key = workdir / "client.key"
            cert = workdir / "client.crt"
            config = workdir / "openssl.cnf"
            config.write_text(_openssl_config(subject), encoding="utf-8")
            # Two steps rather than one `req -newkey`: `ecparam -genkey` is the form both
            # OpenSSL 3 and the LibreSSL that ships with macOS accept, so this does not
            # depend on which of the two ends up first on PATH.
            self._checked(
                [
                    str(openssl),
                    "ecparam",
                    "-name",
                    "prime256v1",
                    "-genkey",
                    "-noout",
                    "-out",
                    str(key),
                ]
            )
            self._checked(
                [
                    str(openssl),
                    "req",
                    "-new",
                    "-x509",
                    "-key",
                    str(key),
                    "-out",
                    str(cert),
                    "-days",
                    cert_days,
                    "-sha256",
                    "-config",
                    str(config),
                    "-extensions",
                    "v3_client",
                ]
            )
            fingerprint_result = self.commands.run(
                [
                    str(openssl),
                    "x509",
                    "-in",
                    str(cert),
                    "-noout",
                    "-fingerprint",
                    "-sha256",
                ]
            )
            if fingerprint_result.returncode:
                raise ConfigurationError(FINGERPRINT_FAILED)
            fingerprint = fingerprint_result.stdout.strip().partition("=")[2]
            self.installer.install(key, cert, self.paths)
        print(f"otelbox-edge-config: generated client certificate CN={subject}", file=self.stderr)
        print(f"  overlay (source of truth): {overlay_cert}", file=self.stderr)
        print(
            f"  live:                      {self.paths.live_client / 'client.crt'}",
            file=self.stderr,
        )
        print(f"  validity:                  {cert_days} days", file=self.stderr)
        print(f"  SHA-256 fingerprint:       {fingerprint}", file=self.stderr)
        print(
            "  Only client.crt is meant to travel; the key stays on this machine.", file=self.stderr
        )

    def print_restart_guidance(self, only: str) -> None:
        if only in {"", "endpoint"}:
            print(
                "otelbox-edge-config: restart the service to apply the endpoint:", file=self.stderr
            )
            print("  launchctl kickstart -k gui/$(id -u)/local.otelbox-edge", file=self.stderr)
        elif only == "cert":
            # A collector that started without a pair holds empty cert paths for its
            # lifetime; reload_interval only re-reads paths it was configured with. So
            # the first generation needs a restart and a later rotation does not.
            print(
                "otelbox-edge-config: restart once so the collector picks the pair up at all:",
                file=self.stderr,
            )
            print("  launchctl kickstart -k gui/$(id -u)/local.otelbox-edge", file=self.stderr)
            print(
                "  Later regenerations are re-read within "
                "OTELBOX_UPSTREAM_TLS_RELOAD_INTERVAL (1h).",
                file=self.stderr,
            )
        else:
            print(
                "otelbox-edge-config: token rotated; the running collector watches "
                "the header file.",
                file=self.stderr,
            )

    def _require_tty(self) -> None:
        if not self.terminal.is_tty():
            raise ConfigurationError(TTY_REQUIRED)

    def _resolve_openssl(self) -> Path:
        found = shutil.which("openssl", path=self.environment.get("PATH"))
        if found is not None and os.access(found, os.X_OK):
            return Path(found)
        # Fall back to the LibreSSL macOS always ships: a caller without the interactive
        # PATH still has /usr/bin/openssl, and the generation below works on either.
        fallback = Path("/usr/bin/openssl")
        if fallback.is_file() and os.access(fallback, os.X_OK):
            return fallback
        raise ConfigurationError(OPENSSL_UNAVAILABLE)

    # The subject is cosmetic to the protocol — a front end pinning a leaf compares the
    # whole certificate — but it is what identifies this machine in the front end's logs,
    # so keep it DNS-shaped.
    def _certificate_subject(self) -> str:
        host = ""
        scutil = Path("/usr/sbin/scutil")
        if scutil.is_file() and os.access(scutil, os.X_OK):
            result = self.commands.run([str(scutil), "--get", "LocalHostName"])
            if result.returncode == 0:
                host = result.stdout.strip()
        if not host:
            host = socket.gethostname().split(".", maxsplit=1)[0]
        safe_host = re.sub(r"[^A-Za-z0-9-]", "-", host).rstrip("-")
        return f"otelbox-edge-{safe_host or 'unknown'}"

    def _confirm_regeneration(self) -> bool:
        print(
            f"otelbox-edge-config: a client pair already exists at {self.paths.overlay_client}",
            file=self.stderr,
        )
        print(
            "  Regenerating invalidates whatever the gateway front end already trusts.",
            file=self.stderr,
        )
        return self.terminal.read("Regenerate? [y/N]: ").lower() == "y"

    def _checked(self, arguments: list[str]) -> None:
        if self.commands.run(arguments).returncode:
            raise ConfigurationError(OPENSSL_GENERATION_FAILED)


# A config file rather than -addext, for the same OpenSSL/LibreSSL portability reason.
def _openssl_config(subject: str) -> str:
    return f"""[req]
distinguished_name = dn
prompt = no

[dn]
CN = {subject}

[v3_client]
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature
extendedKeyUsage = clientAuth
subjectAltName = DNS:{subject}
subjectKeyIdentifier = hash
"""


def _write_private_header(path: Path, content: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        path.chmod(0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _parse_arguments(arguments: list[str], stderr: TextIO) -> tuple[str | None, int]:
    only = ""
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in {"-h", "--help"}:
            return None, 0
        if argument == "--only":
            if index + 1 >= len(arguments):
                print("otelbox-edge-config: --only requires a value", file=stderr)
                return None, EX_USAGE
            only = arguments[index + 1]
            index += 2
            continue
        if argument.startswith("--only="):
            only = argument.partition("=")[2]
            index += 1
            continue
        print(f"otelbox-edge-config: unknown argument: {argument}", file=stderr)
        return None, EX_USAGE
    if only not in {"", "endpoint", "token", "cert"}:
        print(
            f"otelbox-edge-config: --only takes 'endpoint', 'token' or 'cert', got '{only}'",
            file=stderr,
        )
        return None, EX_USAGE
    return only, 0


def main(
    arguments: list[str] | None = None,
    *,
    platform_name: str | None = None,
    repo_root: Path | None = None,
    environment: dict[str, str] | None = None,
    terminal: InputPort | None = None,
    commands: CommandPort | None = None,
    installer: PairInstaller | None = None,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    current_platform = platform.system() if platform_name is None else platform_name
    if current_platform != "Darwin":
        print("otelbox-edge-config: macOS only (launchd + login keychain).", file=stderr)
        return 0
    argv = list(sys.argv[1:] if arguments is None else arguments)
    only, parse_status = _parse_arguments(argv, stderr)
    if only is None:
        if parse_status == 0:
            print(HELP, end="", file=stdout)
        return parse_status
    env = dict(os.environ if environment is None else environment)
    root = Path(__file__).resolve().parents[2] if repo_root is None else repo_root
    paths = ConfigPaths.create(root, Path(env["HOME"]))
    configurator = Configurator(
        paths,
        TerminalInput(stdin, stderr) if terminal is None else terminal,
        CommandRunner() if commands is None else commands,
        PairInstaller() if installer is None else installer,
        environment=env,
        stderr=stderr,
    )
    return configurator.execute(only)
