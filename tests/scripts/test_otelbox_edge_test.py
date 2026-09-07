from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from io import StringIO
from typing import TYPE_CHECKING, ClassVar

import pytest
from otelbox_edge import smoke

if TYPE_CHECKING:
    from pathlib import Path

BEFORE_METRICS = """
# HELP otelcol metrics
otelcol_receiver_accepted_log_records{receiver="otlp"} 5
otelcol_exporter_send_failed_log_records{exporter="otlphttp"} 0
otelcol_exporter_enqueue_failed_log_records{exporter="otlphttp"} 0
otelcol_receiver_refused_log_records{receiver="otlp"} 0
otelcol_exporter_queue_capacity{exporter="logs"} 100
otelcol_exporter_queue_size{exporter="logs"} 10
otelcol_exporter_queue_capacity{exporter="traces"} 200
otelcol_exporter_queue_size{exporter="traces"} 40
"""
AFTER_METRICS = BEFORE_METRICS.replace("} 5", "} 6", 1)


@dataclass
class FakeSystem:
    version: str = "otelcol-otelbox version 2.1.0"
    service_status: int = 0
    calls: list[list[str]] = field(default_factory=list)

    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(arguments)
        if arguments[-1] == "--version":
            return subprocess.CompletedProcess(arguments, 0, self.version, "")
        return subprocess.CompletedProcess(arguments, self.service_status, "state = running\n", "")


class FakeHttp:
    def __init__(self, metrics: list[str | smoke.ProbeError]) -> None:
        self.metrics = list(metrics)
        self.health_failures = 0
        self.post_fails = False
        self.get_calls: list[str] = []
        self.posts: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str) -> str:
        self.get_calls.append(url)
        if url == smoke.HEALTH_URL:
            if self.health_failures:
                self.health_failures -= 1
                raise smoke.ProbeError
            return "ok"
        value = self.metrics.pop(0)
        if isinstance(value, smoke.ProbeError):
            raise value
        return value

    def post_json(self, url: str, payload: dict[str, object]) -> None:
        self.posts.append((url, payload))
        if self.post_fails:
            raise smoke.ProbeError


@dataclass
class SmokeHarness:
    repo_root: Path
    home: Path

    def run(self, system: FakeSystem, http: FakeHttp):
        stdout = StringIO()
        stderr = StringIO()
        sleeps: list[float] = []
        result = smoke.main(
            platform_name="Darwin",
            repo_root=self.repo_root,
            environment={"HOME": str(self.home)},
            system=system,
            http=http,
            sleeper=sleeps.append,
            stdout=stdout,
            stderr=stderr,
        )
        return result, stdout.getvalue(), stderr.getvalue(), sleeps


@pytest.fixture
def smoke_harness(tmp_path: Path) -> SmokeHarness:
    repo_root = tmp_path / "repo"
    packages = repo_root / "roles/devbox/defaults/main/packages.yml"
    packages.parent.mkdir(parents=True)
    packages.write_text(
        'devbox_packages:\n  otelbox_edge:\n    version: "2.1.0"\n  next_package:\n',
        encoding="utf-8",
    )
    home = tmp_path / "home"
    binary = home / ".local/bin/otelcol-otelbox"
    binary.parent.mkdir(parents=True)
    binary.write_text("", encoding="utf-8")
    binary.chmod(0o755)
    return SmokeHarness(repo_root, home)


class TestMetricsSnapshot:
    def test_parser_sums_families_and_pairs_queue_labels(self) -> None:
        snapshot = smoke.MetricsSnapshot.parse(AFTER_METRICS)

        assert snapshot.contains_otelcol_metrics() is True
        assert snapshot.sum_prefix("otelcol_receiver_accepted_log_records") == 6
        assert snapshot.sum_prefix("otelcol_exporter_send_failed_") == 0
        assert snapshot.max_queue_percent() == 20

    def test_missing_or_zero_capacity_queue_is_unavailable(self) -> None:
        snapshot = smoke.MetricsSnapshot.parse(
            'otelcol_exporter_queue_size{exporter="logs"} 4\n'
            'otelcol_exporter_queue_capacity{exporter="logs"} 0\n'
        )

        assert snapshot.max_queue_percent() == -1

    def test_malformed_samples_do_not_become_metrics(self) -> None:
        snapshot = smoke.MetricsSnapshot.parse("# comment\nbroken\notelcol_x not-a-number\n")

        assert snapshot.contains_otelcol_metrics() is False

    @pytest.mark.parametrize("value", ["NaN", "+Inf", "-Inf"])
    def test_non_finite_counter_is_unavailable(self, value: str) -> None:
        snapshot = smoke.MetricsSnapshot.parse(f"otelcol_receiver_accepted_log_records {value}\n")

        assert snapshot.contains_otelcol_metrics() is True
        assert snapshot.sum_prefix("otelcol_receiver_accepted_log_records") is None

    @pytest.mark.parametrize("value", ["NaN", "+Inf", "-Inf"])
    def test_non_finite_queue_sample_is_unavailable(self, value: str) -> None:
        snapshot = smoke.MetricsSnapshot.parse(
            f'otelcol_exporter_queue_size{{exporter="logs"}} {value}\n'
            'otelcol_exporter_queue_capacity{exporter="logs"} 100\n'
        )

        assert snapshot.max_queue_percent() is None


class TestSmokeChecks:
    def test_success_uses_two_temporally_consistent_metrics_snapshots(
        self, smoke_harness: SmokeHarness
    ) -> None:
        system = FakeSystem()
        http = FakeHttp([BEFORE_METRICS, AFTER_METRICS])

        result, stdout, stderr, sleeps = smoke_harness.run(system, http)

        assert result == 0
        assert stderr == ""
        assert "OTLP round-trip: receiver accepted the test log (5 -> 6)" in stdout
        assert "gateway delivery: max queue 20%" in stdout
        assert stdout.endswith("otelbox-edge: all checks passed\n")
        assert http.get_calls.count(smoke.METRICS_URL) == 2
        assert http.posts == [(smoke.LOGS_URL, smoke.LOG_MARKER)]
        assert sleeps == [1]

    def test_failed_metrics_fetch_is_never_interpreted_as_zero(
        self, smoke_harness: SmokeHarness
    ) -> None:
        http = FakeHttp([smoke.ProbeError(), smoke.ProbeError()])

        result, _stdout, stderr, _sleeps = smoke_harness.run(FakeSystem(), http)

        assert result == 1
        assert "metrics :8888 not serving" in stderr
        assert "receiver_accepted_log_records could not be measured" in stderr
        assert "gateway delivery: metrics snapshot unavailable" in stderr
        assert "send_failed=0" not in stderr

    @pytest.mark.parametrize("value", ["NaN", "+Inf", "-Inf"])
    def test_non_finite_counter_reports_failure_and_continues_diagnostics(
        self,
        smoke_harness: SmokeHarness,
        value: str,
    ) -> None:
        after = AFTER_METRICS.replace(
            'otelcol_receiver_accepted_log_records{receiver="otlp"} 6',
            f'otelcol_receiver_accepted_log_records{{receiver="otlp"}} {value}',
        )
        http = FakeHttp([BEFORE_METRICS, after])

        result, stdout, stderr, _sleeps = smoke_harness.run(FakeSystem(), http)

        assert result == 1
        assert "receiver_accepted_log_records could not be measured" in stderr
        assert "gateway delivery: max queue 20%" in stdout
        assert stderr.endswith("tail ~/Library/Logs/otelbox-edge.log\n")

    def test_all_checks_accumulate_after_independent_failures(
        self, smoke_harness: SmokeHarness
    ) -> None:
        system = FakeSystem(version="wrong", service_status=1)
        http = FakeHttp([smoke.ProbeError(), smoke.ProbeError()])
        http.health_failures = 5
        http.post_fails = True

        result, stdout, stderr, sleeps = smoke_harness.run(system, http)

        assert result == 1
        assert stdout == ""
        assert "binary missing or not v2.1.0" in stderr
        assert "service not loaded" in stderr
        assert "lifecycle health" in stderr
        assert "metrics :8888" in stderr
        assert "OTLP/HTTP :4318" in stderr
        assert "gateway delivery" in stderr
        assert stderr.endswith("tail ~/Library/Logs/otelbox-edge.log\n")
        assert sleeps == [1, 1, 1, 1]

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            ('otelcol_exporter_send_failed_log_records{exporter="x"} 1', "send_failed=1"),
            ('otelcol_exporter_enqueue_failed_log_records{exporter="x"} 2', "enqueue_failed=2"),
            ('otelcol_receiver_refused_log_records{receiver="x"} 3', "refused=3"),
            (
                'otelcol_exporter_queue_size{exporter="logs"} 80',
                "max_queue=80%",
            ),
        ],
    )
    def test_delivery_rejects_each_failure_signal(
        self, smoke_harness: SmokeHarness, mutation: str, expected: str
    ) -> None:
        after = AFTER_METRICS + f"\n{mutation}\n"
        http = FakeHttp([BEFORE_METRICS, after])

        result, _stdout, stderr, _sleeps = smoke_harness.run(FakeSystem(), http)

        assert result == 1
        assert expected in stderr

    def test_non_darwin_returns_without_probes(self, tmp_path: Path) -> None:
        stderr = StringIO()

        result = smoke.main(
            platform_name="Linux",
            repo_root=tmp_path,
            environment={},
            stderr=stderr,
        )

        assert result == 0
        assert stderr.getvalue() == "otelbox-edge-test: macOS only.\n"


class FakeHttpResponse:
    status = 200

    def read(self) -> bytes:
        return b"ok"


class FakeHttpConnection:
    created: ClassVar[list[tuple[str, int]]] = []

    def __init__(self, host: str, port: int, *, timeout: float) -> None:
        self.created.append((host, port))
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.request_data = method, path, body, headers

    def getresponse(self) -> FakeHttpResponse:
        return FakeHttpResponse()

    def close(self) -> None:
        return None


class TestLoopbackHttpClient:
    def test_connects_directly_to_loopback_despite_proxy_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:8080")
        monkeypatch.setattr(smoke.http.client, "HTTPConnection", FakeHttpConnection)
        FakeHttpConnection.created.clear()

        result = smoke.LoopbackHttpClient().get(smoke.METRICS_URL)

        assert result == "ok"
        assert FakeHttpConnection.created == [("127.0.0.1", 8888)]

    def test_rejects_non_loopback_urls_without_connecting(self) -> None:
        with pytest.raises(smoke.ProbeError):
            smoke.LoopbackHttpClient().get("http://example.com:8888/metrics")
