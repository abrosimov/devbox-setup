from __future__ import annotations

import json
import os
import selectors
import shutil
import subprocess
import tempfile
import time
from contextlib import AbstractContextManager, contextmanager, suppress
from pathlib import Path
from typing import IO, TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

CLIENT_NAME = "devbox-setup-codex-hook-trust"
CLIENT_VERSION = "1"
DEFAULT_TIMEOUT_SECONDS = 60.0
_READ_CHUNK_BYTES = 65536
_DIAGNOSTICS_TAIL_BYTES = 2000
_SHUTDOWN_GRACE_SECONDS = 5.0


class AppServerError(RuntimeError):
    pass


class AppServerPort(Protocol):
    def request(self, method: str, params: Mapping[str, object]) -> Mapping[str, object]: ...


class ClientFactoryPort(Protocol):
    def __call__(
        self,
        *,
        codex_home: Path,
        timeout: float,
        search_path: str | None,
    ) -> AbstractContextManager[AppServerPort]: ...


class StdioAppServer:
    """Newline-delimited JSON-RPC over `codex app-server`'s stdio transport."""

    def __init__(
        self,
        process: subprocess.Popen[bytes],
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        diagnostics: IO[bytes] | None = None,
    ) -> None:
        if process.stdin is None or process.stdout is None:
            message = "the app-server process must expose piped stdin and stdout"
            raise AppServerError(message)
        self.__process = process
        self.__stdin = process.stdin
        self.__stdout = process.stdout
        self.__timeout = timeout
        self.__diagnostics = diagnostics
        self.__buffer = bytearray()
        self.__identifier = 0
        self.__selector = selectors.DefaultSelector()
        self.__selector.register(self.__stdout.fileno(), selectors.EVENT_READ)

    def request(self, method: str, params: Mapping[str, object]) -> Mapping[str, object]:
        self.__identifier += 1
        identifier = self.__identifier
        self.__send({"jsonrpc": "2.0", "id": identifier, "method": method, "params": dict(params)})
        deadline = time.monotonic() + self.__timeout
        while True:
            payload = self.__receive(deadline, method)
            # Server-initiated requests reuse our id space; only responses lack `method`.
            if "method" in payload or payload.get("id") != identifier:
                continue
            return self.__unwrap(method, payload)

    def notify(self, method: str, params: Mapping[str, object]) -> None:
        self.__send({"jsonrpc": "2.0", "method": method, "params": dict(params)})

    def close(self) -> None:
        self.__selector.close()
        with suppress(OSError, ValueError):
            self.__stdin.close()
        with suppress(OSError):
            self.__process.terminate()
        try:
            self.__process.wait(timeout=_SHUTDOWN_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            self.__process.kill()
            self.__process.wait(timeout=_SHUTDOWN_GRACE_SECONDS)

    def diagnostics_tail(self) -> str:
        if self.__diagnostics is None:
            return ""
        try:
            self.__diagnostics.seek(0)
            captured = self.__diagnostics.read()
        except OSError:
            return ""
        text = captured.decode(errors="replace").strip()
        return f"app-server stderr: {text[-_DIAGNOSTICS_TAIL_BYTES:]}" if text else ""

    def __send(self, payload: Mapping[str, object]) -> None:
        try:
            self.__stdin.write(json.dumps(payload).encode() + b"\n")
            self.__stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as error:
            message = self.__annotate("the app-server closed its input stream")
            raise AppServerError(message) from error

    def __unwrap(self, method: str, payload: Mapping[str, object]) -> Mapping[str, object]:
        error = payload.get("error")
        if error is not None:
            detail = error.get("message") if isinstance(error, dict) else error
            message = self.__annotate(f"{method} was rejected by the app-server: {detail}")
            raise AppServerError(message)
        result = payload.get("result")
        if not isinstance(result, dict):
            message = self.__annotate(f"{method} returned a result that is not an object")
            raise AppServerError(message)
        return result

    def __receive(self, deadline: float, method: str) -> Mapping[str, object]:
        while True:
            line = self.__take_line()
            if line is None:
                self.__fill(deadline, method)
                continue
            if line.strip():
                return self.__decode(line, method)

    def __take_line(self) -> bytes | None:
        index = self.__buffer.find(b"\n")
        if index < 0:
            return None
        line = bytes(self.__buffer[:index])
        del self.__buffer[: index + 1]
        return line

    def __fill(self, deadline: float, method: str) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not self.__selector.select(remaining):
            message = self.__annotate(
                f"timed out after {self.__timeout:g}s waiting for a {method} response"
            )
            raise AppServerError(message)
        chunk = os.read(self.__stdout.fileno(), _READ_CHUNK_BYTES)
        if not chunk:
            message = self.__annotate(f"the app-server exited before answering {method}")
            raise AppServerError(message)
        self.__buffer.extend(chunk)

    def __decode(self, line: bytes, method: str) -> Mapping[str, object]:
        try:
            payload: object = json.loads(line)
        except json.JSONDecodeError as error:
            message = self.__annotate(f"the app-server emitted a non-JSON line answering {method}")
            raise AppServerError(message) from error
        if not isinstance(payload, dict):
            message = self.__annotate(
                f"the app-server emitted a non-object message answering {method}"
            )
            raise AppServerError(message)
        return payload

    def __annotate(self, detail: str) -> str:
        tail = self.diagnostics_tail()
        return f"{detail}\n{tail}" if tail else detail


@contextmanager
def app_server(
    *,
    codex_binary: Path,
    codex_home: Path,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Iterator[StdioAppServer]:
    with tempfile.TemporaryFile() as diagnostics:
        process = _start(codex_binary, codex_home, diagnostics)
        client = StdioAppServer(process, timeout=timeout, diagnostics=diagnostics)
        try:
            initialised = client.request(
                "initialize",
                {"clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION}},
            )
            _assert_codex_home(initialised, codex_home)
            client.notify("initialized", {})
            yield client
        finally:
            client.close()


def spawn_app_server(
    *,
    codex_home: Path,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    search_path: str | None = None,
) -> AbstractContextManager[AppServerPort]:
    located = shutil.which("codex", path=search_path)
    if located is None:
        message = "the codex CLI is not on PATH; cannot reach the app-server"
        raise AppServerError(message)
    return app_server(codex_binary=Path(located), codex_home=codex_home, timeout=timeout)


def _start(
    codex_binary: Path,
    codex_home: Path,
    diagnostics: IO[bytes],
) -> subprocess.Popen[bytes]:
    try:
        return subprocess.Popen(
            [str(codex_binary), "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=diagnostics,
            env={**os.environ, "CODEX_HOME": str(codex_home)},
        )
    except OSError as error:
        message = f"cannot start `{codex_binary} app-server`: {error}"
        raise AppServerError(message) from error


def _assert_codex_home(initialised: Mapping[str, object], expected: Path) -> None:
    reported = initialised.get("codexHome")
    if not isinstance(reported, str):
        message = "the app-server did not report which CODEX_HOME it loaded"
        raise AppServerError(message)
    if Path(reported).resolve() != expected.resolve():
        message = (
            f"the app-server loaded CODEX_HOME {reported}, expected {expected}; "
            "trusting hooks would target the wrong configuration"
        )
        raise AppServerError(message)
