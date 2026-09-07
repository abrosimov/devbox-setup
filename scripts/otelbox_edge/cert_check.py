from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Protocol, TextIO

# sysexits codes for the Ansible task that runs this (darwin/install_otelbox_edge.yml):
# any non-zero fails the play, and the code says why — bad invocation, no openssl to
# judge with, or a genuinely broken pair.
EX_USAGE = 64
EX_UNAVAILABLE = 69
EX_CONFIG = 78


class CommandPort(Protocol):
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[bytes]: ...


class CommandRunner:
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(arguments, capture_output=True, check=False)


def resolve_openssl(environment: dict[str, str]) -> Path | None:
    found = shutil.which("openssl", path=environment.get("PATH"))
    if found is not None and os.access(found, os.X_OK):
        return Path(found)
    # Fall back to the LibreSSL macOS always ships: Ansible runs this without the
    # interactive PATH, and both implementations answer the questions asked below.
    fallback = Path("/usr/bin/openssl")
    return fallback if fallback.is_file() and os.access(fallback, os.X_OK) else None


def main(
    arguments: list[str] | None = None,
    *,
    environment: dict[str, str] | None = None,
    runner: CommandPort | None = None,
    stderr: TextIO = sys.stderr,
) -> int:
    argv = list(sys.argv[1:] if arguments is None else arguments)
    if len(argv) != 2:
        print("usage: otelbox-edge-cert-check.py CERT_FILE KEY_FILE", file=stderr)
        return EX_USAGE
    cert_file, key_file = (Path(value) for value in argv)
    for path in (cert_file, key_file):
        if not path.is_file() or not os.access(path, os.R_OK):
            print(
                f"otelbox-edge-cert-check: file is missing or unreadable: {path}",
                file=stderr,
            )
            return EX_CONFIG

    env = dict(os.environ if environment is None else environment)
    openssl = resolve_openssl(env)
    if openssl is None:
        print("otelbox-edge-cert-check: no usable openssl", file=stderr)
        return EX_UNAVAILABLE
    commands = CommandRunner() if runner is None else runner
    return _check_pair(cert_file, key_file, openssl, commands, stderr)


# The two halves are installed as independent files, so the only proof they belong
# together is the public key each one yields — matching paths guarantee nothing.
def _check_pair(
    cert_file: Path,
    key_file: Path,
    openssl: Path,
    commands: CommandPort,
    stderr: TextIO,
) -> int:
    if commands.run(
        [str(openssl), "x509", "-in", str(cert_file), "-noout", "-checkend", "0"]
    ).returncode:
        print(
            f"otelbox-edge-cert-check: certificate is invalid or expired: {cert_file}",
            file=stderr,
        )
        return EX_CONFIG
    cert_key = commands.run([str(openssl), "x509", "-in", str(cert_file), "-pubkey", "-noout"])
    if cert_key.returncode:
        print(
            f"otelbox-edge-cert-check: cannot read certificate public key: {cert_file}",
            file=stderr,
        )
        return EX_CONFIG
    private_key = commands.run([str(openssl), "pkey", "-in", str(key_file), "-pubout"])
    if private_key.returncode:
        print(
            f"otelbox-edge-cert-check: private key is invalid or encrypted: {key_file}",
            file=stderr,
        )
        return EX_CONFIG
    if cert_key.stdout != private_key.stdout:
        print(
            "otelbox-edge-cert-check: certificate and private key do not match",
            file=stderr,
        )
        return EX_CONFIG
    return 0
