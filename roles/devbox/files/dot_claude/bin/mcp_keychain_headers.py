"""headersHelper for HTTP MCP servers whose bearer token lives in the login Keychain.

Claude Code runs a server's ``headersHelper`` on every connection and reads a
JSON object of headers from stdout. Resolving the token here keeps it out of
``~/.claude.json``, where ``claude mcp add --header`` would store it in plain text.

Usage: mcp_keychain_headers.py --service <keychain service> --account <account>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence

SECURITY_TIMEOUT_SECONDS = 5

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


class KeychainLookupError(RuntimeError):
    pass


def run_security(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        check=False,
        timeout=SECURITY_TIMEOUT_SECONDS,
    )


def read_secret(service: str, account: str, runner: Runner = run_security) -> str:
    argv = ("/usr/bin/security", "find-generic-password", "-s", service, "-a", account, "-w")
    try:
        result = runner(argv)
    except (OSError, subprocess.TimeoutExpired) as exc:
        message = f"keychain lookup failed for {service}/{account}: {exc}"
        raise KeychainLookupError(message) from exc
    if result.returncode != 0:
        message = f"keychain item {service}/{account} is unavailable"
        raise KeychainLookupError(message)
    secret = result.stdout.rstrip("\r\n")
    if not secret or any(ch in secret for ch in "\r\n"):
        message = f"keychain item {service}/{account} is empty or spans several lines"
        raise KeychainLookupError(message)
    return secret


def bearer_headers(secret: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}"}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print MCP bearer headers from the Keychain.")
    parser.add_argument("--service", required=True)
    parser.add_argument("--account", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, runner: Runner = run_security) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        secret = read_secret(args.service, args.account, runner)
    except KeychainLookupError as exc:
        print(f"mcp_keychain_headers: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(bearer_headers(secret)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
