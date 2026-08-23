"""Behavioural tests for the otelbox edge wrapper (files/.config/otelbox/edge/otelbox-edge-run).

The real artifact runs as a subprocess against a throwaway HOME, the same way
launchd runs it. The wrapper hard-codes two absolute tool paths — /usr/bin/security
and /usr/bin/getconf — which PATH cannot intercept, so _stage_wrapper rewrites those
two call sites to stubs. Nothing here reads the login Keychain, writes to the real
per-user temporary directory, or touches the real ~/.config.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "roles/devbox/files/.config/otelbox/edge/otelbox-edge-run"

EX_CONFIG = 78
VALID_ENDPOINT = "OTELBOX_UPSTREAM_ENDPOINT=otel.example.com:443\n"
COLLECTOR_MARKER = "COLLECTOR-STARTED"


@dataclass(frozen=True)
class Stage:
    wrapper: Path
    collector: Path


@dataclass(frozen=True)
class Edge:
    home: Path
    wrapper: Path

    @property
    def conf(self) -> Path:
        return self.home / ".config/otelbox/edge"

    def write_endpoint(self, body: str) -> None:
        (self.conf / "endpoint.env").write_text(body, encoding="utf-8")

    def write_client_half(self, name: str) -> Path:
        path = self.conf / "client" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"stub {name}\n", encoding="utf-8")
        return path

    def run(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.wrapper)],
            env={"HOME": str(self.home), "USER": "edge-test", "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _stage_wrapper(dest: Path, stub_dir: Path) -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    # Count assertion, not a bare replace: a moved call site would silently leave the
    # test talking to the real Keychain and the real temporary directory.
    for tool in ("security", "getconf"):
        assert source.count(f"/usr/bin/{tool}") == 1, f"/usr/bin/{tool} call site moved"
        source = source.replace(f"/usr/bin/{tool}", str(stub_dir / tool))
    _write_executable(dest, source)


# Session-scoped: macOS spends ~1.5s vetting each freshly written executable on
# first exec, so the stub tree is built once and the per-test HOME symlinks to it.
@pytest.fixture(scope="session")
def stage(tmp_path_factory: pytest.TempPathFactory) -> Stage:
    root = tmp_path_factory.mktemp("otelbox-edge-stage")
    runtime_root = root / "runtime"
    runtime_root.mkdir()

    _write_executable(root / "security", "#!/bin/sh\necho stub-token\n")
    _write_executable(root / "getconf", f"#!/bin/sh\nprintf '%s\\n' '{runtime_root}'\n")
    collector = root / "otelcol-otelbox"
    _write_executable(collector, f"#!/bin/sh\necho '{COLLECTOR_MARKER}' \"$@\"\nexec env\n")

    wrapper = root / "otelbox-edge-run"
    _stage_wrapper(wrapper, root)
    return Stage(wrapper=wrapper, collector=collector)


@pytest.fixture
def edge(tmp_path: Path, stage: Stage) -> Edge:
    home = tmp_path / "home"
    conf = home / ".config/otelbox/edge"
    conf.mkdir(parents=True)
    (home / ".local/bin").mkdir(parents=True)
    (home / ".local/bin/otelcol-otelbox").symlink_to(stage.collector)
    (conf / "edge.yaml").write_text("# stub profile\n", encoding="utf-8")

    harness = Edge(home=home, wrapper=stage.wrapper)
    harness.write_endpoint(VALID_ENDPOINT)
    return harness


def test_both_certificate_halves_reach_the_collector(edge: Edge) -> None:
    crt = edge.write_client_half("client.crt")
    key = edge.write_client_half("client.key")

    result = edge.run()

    assert result.returncode == 0, result.stderr
    assert f"OTELBOX_UPSTREAM_TLS_CERT_FILE={crt}" in result.stdout
    assert f"OTELBOX_UPSTREAM_TLS_KEY_FILE={key}" in result.stdout


def test_absent_certificate_starts_the_collector_without_tls_variables(edge: Edge) -> None:
    result = edge.run()

    assert result.returncode == 0, result.stderr
    assert COLLECTOR_MARKER in result.stdout
    assert "OTELBOX_UPSTREAM_TLS_CERT_FILE" not in result.stdout
    assert "OTELBOX_UPSTREAM_TLS_KEY_FILE" not in result.stdout


@pytest.mark.parametrize(
    ("present", "missing"), [("client.crt", "client.key"), ("client.key", "client.crt")]
)
def test_half_a_certificate_pair_is_refused(edge: Edge, present: str, missing: str) -> None:
    edge.write_client_half(present)

    result = edge.run()

    assert result.returncode == EX_CONFIG
    assert "incomplete client certificate pair" in result.stderr
    assert str(edge.conf / "client" / missing) in result.stderr
    assert COLLECTOR_MARKER not in result.stdout


def test_valid_endpoint_is_exported(edge: Edge) -> None:
    result = edge.run()

    assert result.returncode == 0, result.stderr
    assert "OTELBOX_UPSTREAM_ENDPOINT=otel.example.com:443" in result.stdout


@pytest.mark.parametrize(
    ("case", "body"),
    [
        ("v1 variable name", "OTELBOX_EDGE_ENDPOINT=otel.example.com:443\n"),
        ("missing port", "OTELBOX_UPSTREAM_ENDPOINT=otel.example.com\n"),
    ],
)
def test_malformed_endpoint_file_is_refused(edge: Edge, case: str, body: str) -> None:
    edge.write_endpoint(body)

    result = edge.run()

    assert result.returncode == EX_CONFIG, case
    assert "expected OTELBOX_UPSTREAM_ENDPOINT=host:port" in result.stderr
    assert COLLECTOR_MARKER not in result.stdout


def test_scheme_prefixed_endpoint_is_refused(edge: Edge) -> None:
    edge.write_endpoint("OTELBOX_UPSTREAM_ENDPOINT=https://otel.example.com:443\n")

    result = edge.run()

    assert result.returncode == EX_CONFIG
    assert "expected OTELBOX_UPSTREAM_ENDPOINT=host:port" in result.stderr
    assert "no scheme prefix" in result.stderr
    assert COLLECTOR_MARKER not in result.stdout


@pytest.mark.parametrize(
    ("case", "body", "count"),
    [
        ("second line", VALID_ENDPOINT + "OTELBOX_UPSTREAM_COMPRESSION=gzip\n", 2),
        ("empty file", "", 0),
    ],
)
def test_endpoint_file_must_hold_exactly_one_line(
    edge: Edge, case: str, body: str, count: int
) -> None:
    edge.write_endpoint(body)

    result = edge.run()

    assert result.returncode == EX_CONFIG, case
    assert f"must hold exactly one line, found {count}" in result.stderr
    # A distinct failure from the malformed-line path, which never runs here.
    assert "expected OTELBOX_UPSTREAM_ENDPOINT=host:port" not in result.stderr
    assert COLLECTOR_MARKER not in result.stdout


def test_endpoint_line_without_a_trailing_newline_still_counts_as_one(edge: Edge) -> None:
    edge.write_endpoint(VALID_ENDPOINT.rstrip("\n"))

    result = edge.run()

    assert result.returncode == 0, result.stderr
    assert "OTELBOX_UPSTREAM_ENDPOINT=otel.example.com:443" in result.stdout
