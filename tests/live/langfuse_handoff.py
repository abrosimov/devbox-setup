"""Real processes for the Claude -> spool -> otelbox edge -> gateway handoff tests.

Everything here is a production artefact run as deployed: the Stop hook command
from the generated settings.json, the replay runner exactly as the rendered
LaunchAgent plist starts it, and the pinned `otelcol-otelbox` release running
the repository's edge.yaml. The test owns only the gateway end: a TLS OTLP/gRPC
recipient that records every span it is handed.
"""

from __future__ import annotations

import contextlib
import datetime
import hashlib
import http.client
import http.server
import ipaddress
import json
import os
import platform
import plistlib
import pwd
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
import urllib.parse
from collections import Counter
from concurrent import futures
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol, Self

import grpc
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from generation import REPO_ROOT
from jinja2 import Environment, StrictUndefined
from jinja2.utils import select_autoescape

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterator, Mapping

    from throwaway import ThrowawayHome

EDGE: Final = "otelbox-edge"
PACKAGES: Final = REPO_ROOT / "roles/devbox/defaults/main/packages.yml"
EDGE_PROFILE: Final = REPO_ROOT / "roles/devbox/files/.config/otelbox/edge/edge.yaml"
LAUNCH_AGENTS: Final = REPO_ROOT / "roles/devbox/templates/darwin/Library/LaunchAgents"
EDGE_PLIST: Final = LAUNCH_AGENTS / "local.otelbox-edge.plist.j2"
REPLAY_PLIST: Final = LAUNCH_AGENTS / "local.langfuse-replay.plist.j2"
CLAUDE_BIN: Final = REPO_ROOT / "roles/devbox/files/dot_claude/bin"
FAULT_LAUNCHER: Final = Path(__file__).resolve().parent / "langfuse_fault_launcher.py"
# Fixed by edge.yaml (and the health endpoint by the edge plist), so not free ports.
EDGE_PORTS: Final = (4317, 4318, 8888, 13133, 14318)
LANGFUSE_RECEIVER: Final = ("127.0.0.1", 14318)
# launchd's PATH for a per-user agent whose plist declares none.
LAUNCHD_PATH: Final = "/usr/bin:/bin:/usr/sbin:/sbin"
LINUX_ASSETS: Final = {"x86_64": "otelcol-otelbox_linux_amd64"}
GATEWAY_CREDENTIAL: Final = "langfuse-handoff-e2e"
DOWNLOAD_TIMEOUT_SECONDS: Final = 120.0
MAX_REDIRECTS: Final = 5
EDGE_START_SECONDS: Final = 60.0
EDGE_STOP_SECONDS: Final = 30.0
HOOK_SECONDS: Final = 120.0
REPLAY_SECONDS: Final = 300.0
DELIVERY_SECONDS: Final = 120.0
POLL_SECONDS: Final = 0.05
HTTP_OK: Final = 200
HTTP_REDIRECTS: Final = frozenset({301, 302, 303, 307, 308})
HTTP_BAD_GATEWAY: Final = 502
WIRE_VARINT: Final = 0
WIRE_FIXED64: Final = 1
WIRE_LENGTH_DELIMITED: Final = 2
WIRE_FIXED32: Final = 5
SHA256_HEX: Final = re.compile(r"[0-9a-f]{64}")
OTLP_SERVICES: Final = (
    "opentelemetry.proto.collector.trace.v1.TraceService",
    "opentelemetry.proto.collector.metrics.v1.MetricsService",
    "opentelemetry.proto.collector.logs.v1.LogsService",
)
IGNORED_IN_BIN: Final = shutil.ignore_patterns(".venv", "__pycache__", ".DS_Store")


class EdgeUnavailableError(RuntimeError):
    pass


def deadline_wait(condition: Callable[[], bool], seconds: float, what: str) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            message = f"timed out after {seconds}s waiting for {what}"
            raise TimeoutError(message)
        time.sleep(POLL_SECONDS)


@dataclass(frozen=True, order=True, slots=True)
class SpanIdentity:
    trace_id: str
    span_id: str
    parent_span_id: str
    start: int
    end: int


def _varint(data: bytes, offset: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7


def _fields(data: bytes) -> Iterator[tuple[int, int | bytes]]:
    offset = 0
    while offset < len(data):
        key, offset = _varint(data, offset)
        number, wire = key >> 3, key & 7
        value: int | bytes
        if wire == WIRE_VARINT:
            value, offset = _varint(data, offset)
        elif wire == WIRE_FIXED64:
            value, offset = int.from_bytes(data[offset : offset + 8], "little"), offset + 8
        elif wire == WIRE_LENGTH_DELIMITED:
            length, offset = _varint(data, offset)
            value, offset = data[offset : offset + length], offset + length
        elif wire == WIRE_FIXED32:
            value, offset = int.from_bytes(data[offset : offset + 4], "little"), offset + 4
        else:
            message = f"unsupported protobuf wire type {wire}"
            raise ValueError(message)
        yield number, value


def _messages(data: bytes, number: int) -> Iterator[bytes]:
    for field_number, value in _fields(data):
        if field_number == number and isinstance(value, bytes):
            yield value


def _span_identity(span: bytes) -> SpanIdentity:
    ids: dict[int, bytes] = {}
    times: dict[int, int] = {}
    for number, value in _fields(span):
        if isinstance(value, bytes):
            ids[number] = value
        else:
            times[number] = value
    # Span: 1 trace_id, 2 span_id, 4 parent_span_id, 7/8 start/end unix nanos.
    return SpanIdentity(
        ids.get(1, b"").hex(),
        ids.get(2, b"").hex(),
        ids.get(4, b"").hex(),
        times.get(7, 0),
        times.get(8, 0),
    )


def decode_spans(request: bytes) -> list[SpanIdentity]:
    """Identities in an OTLP ExportTraceServiceRequest, read off the wire format.

    Request -> 1 ResourceSpans -> 2 ScopeSpans -> 2 Span; no generated code, so
    the root dev venv needs no OpenTelemetry packages.
    """
    return [
        _span_identity(span)
        for resource_spans in _messages(request, 1)
        for scope_spans in _messages(resource_spans, 2)
        for span in _messages(scope_spans, 2)
    ]


@dataclass(frozen=True, slots=True)
class EdgePin:
    version: str
    release_base: str

    def url(self, asset: str) -> str:
        return f"{self.release_base}/v{self.version}/{asset}"


def edge_pin(packages: Path = PACKAGES) -> EdgePin:
    defaults = yaml.safe_load(packages.read_text(encoding="utf-8"))
    pinned = defaults["devbox_packages"]["otelbox_edge"]
    return EdgePin(version=str(pinned["version"]), release_base=str(pinned["release_base"]))


def linux_asset(system: str, machine: str) -> str:
    # The edge's gateway leg trusts only the platform store: on Linux Go reads
    # SSL_CERT_FILE, on macOS it asks the Keychain, which a test must not touch.
    if system != "Linux":
        message = f"needs Linux to trust a test CA via SSL_CERT_FILE, not {system}"
        raise EdgeUnavailableError(message)
    asset = LINUX_ASSETS.get(machine)
    if asset is None:
        message = f"the release publishes no Linux asset for {machine}"
        raise EdgeUnavailableError(message)
    return asset


class Opener(Protocol):
    def __call__(self, url: str, timeout: float) -> bytes: ...


def download(url: str, timeout: float) -> bytes:
    """GET over HTTPS only, following the release CDN's redirects."""
    for _ in range(MAX_REDIRECTS + 1):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            message = f"refusing a non-HTTPS release URL: {url}"
            raise EdgeUnavailableError(message)
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port, timeout=timeout)
        try:
            target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
            connection.request("GET", target, headers={"User-Agent": "devbox-langfuse-e2e"})
            response = connection.getresponse()
            location = response.getheader("Location")
            body = response.read()
        except (OSError, http.client.HTTPException) as error:
            message = f"cannot download {url}: {error}"
            raise EdgeUnavailableError(message) from error
        finally:
            connection.close()
        if response.status in HTTP_REDIRECTS and location:
            url = urllib.parse.urljoin(url, location)
            continue
        if response.status != HTTP_OK:
            message = f"cannot download {url}: HTTP {response.status}"
            raise EdgeUnavailableError(message)
        return body
    message = f"too many redirects fetching {url}"
    raise EdgeUnavailableError(message)


def verified_release_asset(pin: EdgePin, asset: str, cache: Path, opener: Opener) -> Path:
    """The pinned asset, checked against its published .sha256 as get_url does."""
    target = cache / pin.version / asset
    recorded = target.with_name(f"{asset}.sha256")
    if (
        target.is_file()
        and recorded.is_file()
        and hashlib.sha256(target.read_bytes()).hexdigest() == recorded.read_text().strip()
    ):
        return target
    digest = opener(pin.url(f"{asset}.sha256"), DOWNLOAD_TIMEOUT_SECONDS).decode().strip()
    if not SHA256_HEX.fullmatch(digest):
        message = f"{pin.url(asset)}.sha256 is not one bare SHA-256 digest"
        raise EdgeUnavailableError(message)
    binary = opener(pin.url(asset), DOWNLOAD_TIMEOUT_SECONDS)
    actual = hashlib.sha256(binary).hexdigest()
    if actual != digest:
        message = f"checksum mismatch for {pin.url(asset)}: published {digest}, got {actual}"
        raise EdgeUnavailableError(message)
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(f".{asset}.partial")
    staged.write_bytes(binary)
    staged.chmod(0o755)
    staged.replace(target)
    recorded.write_text(f"{digest}\n")
    return target


def pinned_edge_binary(cache: Path, opener: Opener = download) -> Path:
    pin = edge_pin()
    asset = linux_asset(platform.system(), platform.machine())
    busy = busy_ports(EDGE_PORTS)
    if busy:
        message = f"edge.yaml's fixed loopback ports {busy} are taken (a running edge?)"
        raise EdgeUnavailableError(message)
    binary = verified_release_asset(pin, asset, cache, opener)
    completed = subprocess.run(
        [str(binary), "--version"], capture_output=True, text=True, timeout=60, check=False
    )
    expected = f"otelcol-otelbox version {pin.version}"
    if completed.stdout.strip() != expected:
        message = f"{binary} reports {completed.stdout.strip()!r}, not {expected!r}"
        raise EdgeUnavailableError(message)
    return binary


def busy_ports(ports: Collection[int]) -> list[int]:
    busy = []
    for port in ports:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                busy.append(port)
    return busy


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def deploy_claude_bin(destination: Path, uv: str) -> Path:
    """The playbook's Block 1b: rsync bin/, then `uv sync --frozen --no-dev` beside it."""
    shutil.copytree(CLAUDE_BIN, destination, ignore=IGNORED_IN_BIN)
    completed = subprocess.run(
        [uv, "sync", "--frozen", "--no-dev"],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=destination,
        check=False,
    )
    if completed.returncode != 0:
        message = f"uv sync of the deployed bin failed:\n{completed.stderr}"
        raise RuntimeError(message)
    return destination


@dataclass(frozen=True, slots=True)
class Tls:
    ca: Path
    certificate: bytes
    key: bytes


def _certificate(
    subject: str, issuer: x509.Name, public_key: ec.EllipticCurvePublicKey
) -> x509.CertificateBuilder:
    now = datetime.datetime.now(datetime.UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)]))
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(hours=1))
        .not_valid_after(now + datetime.timedelta(days=1))
    )


def issue_loopback_tls(directory: Path) -> Tls:
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "langfuse-handoff-e2e CA")])
    ca = (
        _certificate("langfuse-handoff-e2e CA", ca_name, ca_key.public_key())
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )
    key = ec.generate_private_key(ec.SECP256R1())
    leaf = (
        _certificate("127.0.0.1", ca_name, key.public_key())
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]),
            critical=False,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    directory.mkdir(parents=True, exist_ok=True)
    ca_file = directory / "ca.pem"
    ca_file.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    return Tls(
        ca=ca_file,
        certificate=leaf.public_bytes(serialization.Encoding.PEM),
        key=key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )


@dataclass
class Recipient:
    """The gateway's OTLP/gRPC receiver, owned by the test."""

    port: int
    tls: Tls
    spans: list[SpanIdentity] = field(default_factory=list)
    authorizations: set[str] = field(default_factory=set)
    arrived: threading.Condition = field(default_factory=threading.Condition)
    server: grpc.Server | None = None

    @property
    def endpoint(self) -> str:
        return f"127.0.0.1:{self.port}"

    def start(self) -> None:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        server.add_generic_rpc_handlers(tuple(self._handler(name) for name in OTLP_SERVICES))
        credentials = grpc.ssl_server_credentials([(self.tls.key, self.tls.certificate)])
        if server.add_secure_port(self.endpoint, credentials) != self.port:
            message = f"recipient could not bind {self.endpoint}"
            raise RuntimeError(message)
        server.start()
        self.server = server

    def stop(self) -> None:
        if self.server is not None:
            self.server.stop(grace=None).wait(timeout=EDGE_STOP_SECONDS)
            self.server = None

    def received(self) -> Counter[SpanIdentity]:
        with self.arrived:
            return Counter(self.spans)

    def wait_for_each(self, expected: Collection[SpanIdentity], copies: int = 1) -> None:
        def delivered() -> bool:
            seen = Counter(self.spans)
            return all(seen[span] >= copies for span in expected)

        with self.arrived:
            if not self.arrived.wait_for(delivered, timeout=DELIVERY_SECONDS):
                message = (
                    f"recipient holds {len(self.spans)} spans after {DELIVERY_SECONDS}s, "
                    f"expected {copies} of each of {len(expected)}"
                )
                raise TimeoutError(message)

    def _handler(self, service: str) -> grpc.GenericRpcHandler:
        tracing = service == OTLP_SERVICES[0]

        def export(request: bytes, context: grpc.ServicerContext) -> bytes:
            metadata = dict(context.invocation_metadata())
            with self.arrived:
                self.authorizations.add(str(metadata.get("authorization", "")))
                if tracing:
                    self.spans.extend(decode_spans(request))
                self.arrived.notify_all()
            return b""

        return grpc.method_handlers_generic_handler(
            service, {"Export": grpc.unary_unary_rpc_method_handler(export)}
        )


def render_plist(template: Path, home: Path) -> dict[str, object]:
    defaults = yaml.safe_load(PACKAGES.read_text(encoding="utf-8"))
    jinja = Environment(
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
    )
    rendered = jinja.from_string(template.read_text(encoding="utf-8")).render(
        ansible_facts={"env": {"HOME": str(home)}},
        devbox_packages=defaults["devbox_packages"],
    )
    loaded = plistlib.loads(rendered.encode())
    if not isinstance(loaded, dict):
        message = f"{template} does not render to a plist dictionary"
        raise TypeError(message)
    return loaded


def launchd_environment(home: Path, plist: Mapping[str, object]) -> dict[str, str]:
    user = pwd.getpwuid(os.getuid()).pw_name
    declared = plist.get("EnvironmentVariables", {})
    if not isinstance(declared, dict):
        message = "EnvironmentVariables must be a dictionary"
        raise TypeError(message)
    return {
        "HOME": str(home),
        "USER": user,
        "LOGNAME": user,
        "SHELL": "/bin/sh",
        "PATH": LAUNCHD_PATH,
        "TMPDIR": str(home / "tmp"),
        **{str(key): str(value) for key, value in declared.items()},
    }


@dataclass(frozen=True, slots=True)
class LaunchAgentJob:
    arguments: tuple[str, ...]
    environment: Mapping[str, str]
    log: Path


def replay_job(home: Path) -> LaunchAgentJob:
    plist = render_plist(REPLAY_PLIST, home)
    arguments = plist["ProgramArguments"]
    if not isinstance(arguments, list) or plist["StandardOutPath"] != plist["StandardErrorPath"]:
        message = f"{REPLAY_PLIST} no longer has one argv and one shared log"
        raise TypeError(message)
    return LaunchAgentJob(
        arguments=tuple(str(argument) for argument in arguments),
        environment=launchd_environment(home, plist),
        log=Path(str(plist["StandardErrorPath"])),
    )


@dataclass(frozen=True, slots=True)
class JobRun:
    returncode: int
    output: str


def run_job(job: LaunchAgentJob) -> JobRun:
    job.log.parent.mkdir(parents=True, exist_ok=True)
    Path(job.environment["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    offset = job.log.stat().st_size if job.log.exists() else 0
    with job.log.open("ab") as log:
        completed = subprocess.run(
            job.arguments,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            env=dict(job.environment),
            timeout=REPLAY_SECONDS,
            check=False,
        )
    with job.log.open("rb") as log:
        log.seek(offset)
        return JobRun(completed.returncode, log.read().decode(errors="replace"))


class Edge:
    """The pinned edge binary as local.otelbox-edge supervises it, minus launchd."""

    def __init__(self, binary: Path, home: Path, upstream: str, tls: Tls) -> None:
        plist = render_plist(EDGE_PLIST, home)
        header = home / "tmp" / "otelbox-edge" / "upstream-auth-header"
        header.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        header.write_text(f"Bearer {GATEWAY_CREDENTIAL}\n")
        # What otelbox-edge-run adds from endpoint.env and the Keychain, and the
        # two Linux-only differences: a test CA and a codec grpcio can decode.
        self.environment = launchd_environment(home, plist) | {
            "OTELBOX_UPSTREAM_ENDPOINT": upstream,
            "OTELBOX_UPSTREAM_AUTH_HEADER_FILE": str(header),
            "SSL_CERT_FILE": str(tls.ca),
            "OTELBOX_UPSTREAM_COMPRESSION": "gzip",
        }
        # install_otelbox_edge.yml creates the WAL root before the agent starts.
        Path(self.environment["OTELBOX_STORAGE_DIR"]).mkdir(parents=True, exist_ok=True)
        self.binary = binary
        self.log = Path(str(plist["StandardErrorPath"]))
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        self.log.parent.mkdir(parents=True, exist_ok=True)
        with self.log.open("ab") as log:
            process = subprocess.Popen(
                [str(self.binary), "--config", str(EDGE_PROFILE)],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                env=self.environment,
            )
        self.process = process
        deadline_wait(
            lambda: process.poll() is not None or receiver_accepts(),
            EDGE_START_SECONDS,
            f"the edge to listen on {LANGFUSE_RECEIVER}",
        )
        if process.poll() is not None:
            message = f"edge exited with {process.returncode}\n{self.log_tail()}"
            raise RuntimeError(message)

    def kill(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.send_signal(signal.SIGKILL)
            self.process.wait(timeout=EDGE_STOP_SECONDS)
        self.process = None

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=EDGE_STOP_SECONDS)
            except subprocess.TimeoutExpired:
                self.kill()
        self.process = None

    def log_tail(self, lines: int = 40) -> str:
        if not self.log.is_file():
            return "(no edge log)"
        return "\n".join(self.log.read_text(errors="replace").splitlines()[-lines:])


def receiver_accepts() -> bool:
    with contextlib.suppress(OSError), socket.create_connection(LANGFUSE_RECEIVER, timeout=1):
        return True
    return False


@dataclass(frozen=True, slots=True)
class Witness:
    status: int
    on_disk_at_arrival: bool
    on_disk_at_answer: bool


def forward_to_edge(path: str, body: bytes, headers: Mapping[str, str]) -> int:
    host, port = LANGFUSE_RECEIVER
    connection = http.client.HTTPConnection(host, port, timeout=30)
    try:
        relayed = {key: value for key, value in headers.items() if key.lower() != "host"}
        connection.request("POST", path, body=body, headers=relayed)
        response = connection.getresponse()
        response.read()
    except (OSError, http.client.HTTPException):
        return HTTP_BAD_GATEWAY
    else:
        return response.status
    finally:
        connection.close()


class SpoolWitnessProxy:
    """A loopback hop in front of the edge that looks at the spool around each answer."""

    def __init__(self, spool: Path, refuse_with: int | None = None) -> None:
        self.witnesses: list[Witness] = []
        witnesses = self.witnesses

        def on_disk(body: bytes) -> bool:
            return any(path.read_bytes() == body for path in spool.glob("*.otlp"))

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers["Content-Length"]))
                arrival = on_disk(body)
                status = refuse_with or forward_to_edge(self.path, body, dict(self.headers))
                witnesses.append(Witness(status, arrival, on_disk(body)))
                self.send_response(status)
                self.send_header("Content-Length", "0")
                self.end_headers()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=EDGE_STOP_SECONDS)


# No subagents: snapshot replay does not carry their transcripts (a known, separate gap).
def write_transcript(path: Path, session_id: str) -> None:
    def user(uuid: str, at: str, content: object) -> dict[str, object]:
        message = {"role": "user", "content": content}
        return {
            "type": "user",
            "uuid": uuid,
            "sessionId": session_id,
            "timestamp": at,
            "message": message,
        }

    def assistant(message_id: str, at: str, content: list[object]) -> dict[str, object]:
        message = {
            "id": message_id,
            "role": "assistant",
            "model": "claude-test",
            "content": content,
        }
        return {"type": "assistant", "sessionId": session_id, "timestamp": at, "message": message}

    def text(value: str) -> dict[str, str]:
        return {"type": "text", "text": value}

    read = {"type": "tool_use", "id": "toolu_read", "name": "Read", "input": {"file_path": "a"}}
    result = {"type": "tool_result", "tool_use_id": "toolu_read", "content": "notes"}
    rows = [
        user("row-1", "2026-10-01T10:00:00.000Z", "Read the notes"),
        assistant("msg_1", "2026-10-01T10:00:01.000Z", [text("Reading"), read]),
        user("row-2", "2026-10-01T10:00:02.000Z", [result]),
        assistant("msg_2", "2026-10-01T10:00:03.000Z", [text("Done")]),
        user("row-3", "2026-10-01T10:01:00.000Z", "Thanks"),
        assistant("msg_3", "2026-10-01T10:01:01.000Z", [text("Welcome")]),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def langfuse_stop_command(settings: Mapping[str, object]) -> str:
    hooks = settings["hooks"]
    if not isinstance(hooks, dict):
        message = "settings.json hooks must be an object"
        raise TypeError(message)
    commands = [
        str(hook["command"])
        for group in hooks["Stop"]
        for hook in group["hooks"]
        if "langfuse_trace_hook.py" in str(hook.get("command", ""))
    ]
    if len(commands) != 1:
        message = f"expected one Langfuse Stop hook, found {commands}"
        raise ValueError(message)
    return commands[0]


@dataclass
class Stack:
    """One deployed home, its transcript, the edge and the gateway recipient."""

    home: ThrowawayHome
    settings: dict[str, object]
    transcript: Path
    session_id: str
    recipient: Recipient
    edge: Edge
    hooks: list[subprocess.Popen[str]] = field(default_factory=list)

    @property
    def state(self) -> Path:
        return self.home.path / ".claude" / "state"

    @property
    def spool(self) -> Path:
        return self.state / "langfuse_otlp_spool"

    @property
    def pending(self) -> Path:
        return self.state / "langfuse_pending"

    @property
    def signals(self) -> Path:
        return self.home.directory("fault-signals")

    def payload(self) -> str:
        return json.dumps(
            {
                "session_id": self.session_id,
                "transcript_path": str(self.transcript),
                "hook_event_name": "Stop",
                "cwd": str(self.home.path),
            }
        )

    def claude_environment(self) -> dict[str, str]:
        configured = self.settings["env"]
        if not isinstance(configured, dict):
            message = "settings.json env must be an object"
            raise TypeError(message)
        return {
            "HOME": str(self.home.path),
            "PATH": os.environ.get("PATH", LAUNCHD_PATH),
            **{str(key): str(value) for key, value in configured.items()},
        }

    def write_settings(self) -> None:
        self.home.write(".claude/settings.json", json.dumps(self.settings, indent=2))

    def point_replay_at(self, base_url: str) -> None:
        configured = self.settings["env"]
        if not isinstance(configured, dict):
            message = "settings.json env must be an object"
            raise TypeError(message)
        configured["CC_LANGFUSE_BASE_URL"] = base_url
        self.write_settings()

    def stop_hook(self) -> subprocess.CompletedProcess[str]:
        """The Stop hook as Claude Code runs a command hook: through a shell."""
        return subprocess.run(
            ["/bin/sh", "-c", langfuse_stop_command(self.settings)],
            input=self.payload(),
            text=True,
            capture_output=True,
            timeout=HOOK_SECONDS,
            env=self.claude_environment(),
            cwd=self.home.path,
            check=False,
        )

    def faulted_hook(self, fault: str) -> subprocess.Popen[str]:
        bin_directory = self.home.path / ".claude" / "bin"
        process = subprocess.Popen(
            [
                str(bin_directory / ".venv" / "bin" / "python"),
                str(FAULT_LAUNCHER),
                str(bin_directory),
                fault,
                str(self.signals),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.claude_environment(),
            cwd=self.home.path,
        )
        if process.stdin is None:
            message = "the faulted hook has no stdin"
            raise RuntimeError(message)
        process.stdin.write(self.payload())
        process.stdin.close()
        self.hooks.append(process)
        return process

    def replay(self) -> JobRun:
        return run_job(replay_job(self.home.path))

    def committed_batches(self) -> dict[str, bytes]:
        return {path.name: path.read_bytes() for path in sorted(self.spool.glob("*.otlp"))}

    def spooled_spans(self) -> list[SpanIdentity]:
        return sorted(
            span for batch in self.committed_batches().values() for span in decode_spans(batch)
        )

    def markers(self) -> list[Path]:
        return sorted(self.pending.glob("*.json"))

    def diagnostics(self) -> str:
        def text(path: Path) -> str:
            return path.read_text(errors="replace") if path.is_file() else "(none)"

        hook_log = text(self.state / "langfuse_hook.log")
        replay_log = text(replay_job(self.home.path).log)
        return (
            f"--- hook log ---\n{hook_log}\n--- replay log ---\n{replay_log}\n"
            f"--- edge log ---\n{self.edge.log_tail()}"
        )

    def close(self) -> None:
        for hook in self.hooks:
            if hook.poll() is None:
                hook.kill()
                hook.wait(timeout=EDGE_STOP_SECONDS)
            for stream in (hook.stdout, hook.stderr):
                if stream is not None:
                    stream.close()
        self.edge.stop()
        self.recipient.stop()
