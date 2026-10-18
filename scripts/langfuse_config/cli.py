from __future__ import annotations

import argparse
import getpass
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, TextIO

# Must match the keychain: bindings in roles/devbox/files/dot_claude/settings.ai-config.json.
KEYCHAIN_SERVICE: Final = "devbox-langfuse"
SECURITY: Final = "/usr/bin/security"
ATTEMPTS: Final = 3
SECURITY_TIMEOUT_SECONDS: Final = 300.0
# `security -i` splits its command line on whitespace, so every token must be one word.
_COMMAND_TOKEN: Final = re.compile(r"[^\s\"'\\]+")
HELP: Final = """Store the Langfuse API keys the langfuse Claude Code skill uses.

The keys go into the login Keychain as service 'devbox-langfuse', accounts
'public-key' and 'secret-key'. `scripts/ai-config apply claude --profile personal`
reads them from there into ~/.claude/settings.json; nothing is written to the
repository. Re-run to rotate: both items are replaced in place.

The secret travels to `security` on its standard input, never on a command line.
macOS only; needs a TTY.
"""


class SeedingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class KeySlot:
    account: str
    prompt: str
    pattern: re.Pattern[str]
    hidden: bool


PUBLIC_KEY_SLOT: Final = KeySlot(
    account="public-key",
    prompt="Langfuse public key (pk-lf-...): ",
    pattern=re.compile(r"pk-lf-[A-Za-z0-9-]+"),
    hidden=False,
)
SECRET_KEY_SLOT: Final = KeySlot(
    account="secret-key",
    prompt="Langfuse secret key (sk-lf-..., input hidden): ",
    pattern=re.compile(r"sk-lf-[A-Za-z0-9-]+"),
    hidden=True,
)
SLOTS: Final = (PUBLIC_KEY_SLOT, SECRET_KEY_SLOT)


class Terminal(Protocol):
    def is_tty(self) -> bool: ...

    def read(self, prompt: str, *, hidden: bool) -> str: ...


class CommandRunner(Protocol):
    def __call__(self, arguments: tuple[str, ...], stdin: str, /) -> int: ...


class InteractiveTerminal:
    def __init__(self, stdin: TextIO, stderr: TextIO) -> None:
        self.__stdin = stdin
        self.__stderr = stderr

    def is_tty(self) -> bool:
        return self.__stdin.isatty()

    def read(self, prompt: str, *, hidden: bool) -> str:
        if hidden:
            return getpass.getpass(prompt, stream=self.__stderr)
        print(prompt, end="", file=self.__stderr, flush=True)
        line = self.__stdin.readline()
        if not line:
            raise EOFError
        return line.rstrip("\n")


def run_security(arguments: tuple[str, ...], stdin: str, /) -> int:
    try:
        completed = subprocess.run(
            arguments,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
            timeout=SECURITY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        message = "could not run /usr/bin/security"
        raise SeedingError(message) from error
    return completed.returncode


@dataclass(frozen=True, slots=True)
class LoginKeychain:
    path: Path
    runner: CommandRunner = run_security

    def store(self, account: str, value: str) -> None:
        tokens = (
            "add-generic-password",
            "-U",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            account,
            "-T",
            SECURITY,
            "-w",
            value,
            str(self.path),
        )
        if not all(_COMMAND_TOKEN.fullmatch(token) for token in tokens):
            message = f"refusing to pass whitespace or quotes to security: {self.path}"
            raise SeedingError(message)
        # Interactive mode reads the command from stdin, which keeps the secret out of
        # the process table; its exit status is that of the last command it ran.
        if self.runner((SECURITY, "-i"), " ".join(tokens) + "\n") != 0:
            message = f"could not store {KEYCHAIN_SERVICE}/{account} in the login keychain"
            raise SeedingError(message)


class LangfuseKeySeeder:
    def __init__(self, terminal: Terminal, keychain: LoginKeychain, stderr: TextIO) -> None:
        self.__terminal = terminal
        self.__keychain = keychain
        self.__stderr = stderr

    def run(self) -> int:
        if not self.__terminal.is_tty():
            print(
                "langfuse-config: stdin is not a TTY; run `make langfuse-config` interactively",
                file=self.__stderr,
            )
            return 1
        try:
            keys = [(slot, self.__read_key(slot)) for slot in SLOTS]
            for slot, value in keys:
                self.__keychain.store(slot.account, value)
                print(
                    f"langfuse-config: stored {KEYCHAIN_SERVICE}/{slot.account} "
                    "in the login keychain",
                    file=self.__stderr,
                )
        except EOFError:
            print("langfuse-config: input closed before both keys were read", file=self.__stderr)
            return 1
        except SeedingError as error:
            print(f"langfuse-config: {error}", file=self.__stderr)
            return 1
        print(
            "langfuse-config: deploy with `make personal EXTRA_VARS='--tags claude'`, "
            "then restart Claude Code",
            file=self.__stderr,
        )
        return 0

    def __read_key(self, slot: KeySlot) -> str:
        for attempt in range(1, ATTEMPTS + 1):
            candidate = self.__terminal.read(slot.prompt, hidden=slot.hidden).strip()
            if slot.pattern.fullmatch(candidate):
                return candidate
            print(
                f"  expected {slot.pattern.pattern}, try again ({attempt}/{ATTEMPTS})",
                file=self.__stderr,
            )
        message = f"giving up on {slot.account} after {ATTEMPTS} attempts"
        raise SeedingError(message)


def main(
    arguments: list[str] | None = None,
    *,
    platform_name: str | None = None,
    environment: dict[str, str] | None = None,
    terminal: Terminal | None = None,
    runner: CommandRunner | None = None,
    stdin: TextIO = sys.stdin,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = argparse.ArgumentParser(
        prog="langfuse-config",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.parse_args(arguments)
    if (platform.system() if platform_name is None else platform_name) != "Darwin":
        print("langfuse-config: macOS only (login Keychain).", file=stderr)
        return 0
    home = Path((os.environ if environment is None else environment)["HOME"])
    keychain = LoginKeychain(
        path=home / "Library/Keychains/login.keychain-db",
        runner=run_security if runner is None else runner,
    )
    seeder = LangfuseKeySeeder(
        InteractiveTerminal(stdin, stderr) if terminal is None else terminal,
        keychain,
        stderr,
    )
    return seeder.run()
