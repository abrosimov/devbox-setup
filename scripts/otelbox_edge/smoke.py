from __future__ import annotations

import http.client
import json
import math
import os
import platform
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TextIO

if TYPE_CHECKING:
    from collections.abc import Callable

HEALTH_URL = "http://127.0.0.1:13133/status"
METRICS_URL = "http://127.0.0.1:8888/metrics"
LOGS_URL = "http://127.0.0.1:4318/v1/logs"
LOG_MARKER: dict[str, object] = {
    "resourceLogs": [
        {"scopeLogs": [{"logRecords": [{"body": {"stringValue": "otelbox-edge-test"}}]}]}
    ]
}


class ProbeError(RuntimeError):
    pass


class SystemPort(Protocol):
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]: ...


class HttpPort(Protocol):
    def get(self, url: str) -> str: ...

    def post_json(self, url: str, payload: dict[str, object]) -> None: ...


class SystemRunner:
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(arguments, capture_output=True, text=True, check=False)
        except OSError:
            return subprocess.CompletedProcess(arguments, 127, "", "")


class LoopbackHttpClient:
    def __init__(self, timeout: float = 3.0) -> None:
        self.timeout = timeout

    def get(self, url: str) -> str:
        return self._request("GET", url, None)

    def post_json(self, url: str, payload: dict[str, object]) -> None:
        self._request("POST", url, json.dumps(payload).encode())

    def _request(self, method: str, url: str, body: bytes | None) -> str:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port is None:
            raise ProbeError
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=self.timeout)
        try:
            headers = {"Content-Type": "application/json"} if body is not None else {}
            connection.request(method, parsed.path, body=body, headers=headers)
            response = connection.getresponse()
            content = response.read()
            if not 200 <= response.status < 300:
                raise ProbeError
            return content.decode("utf-8")
        except (OSError, UnicodeError, http.client.HTTPException) as error:
            raise ProbeError from error
        finally:
            connection.close()


@dataclass(frozen=True)
class MetricsSnapshot:
    samples: tuple[tuple[str, float], ...]

    @classmethod
    def parse(cls, content: str) -> MetricsSnapshot:
        samples: list[tuple[str, float]] = []
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) < 2:
                continue
            try:
                value = float(fields[-1])
            except ValueError:
                continue
            samples.append((fields[0], value))
        return cls(tuple(samples))

    def contains_otelcol_metrics(self) -> bool:
        return any(name.startswith("otelcol_") for name, _value in self.samples)

    def sum_prefix(self, prefix: str) -> int | None:
        total = sum(value for name, value in self.samples if name.startswith(prefix))
        return int(total) if math.isfinite(total) else None

    def max_queue_percent(self) -> int | None:
        capacities: dict[str, float] = {}
        sizes: dict[str, float] = {}
        for sample, value in self.samples:
            name, separator, labels = sample.partition("{")
            key = f"{{{labels}" if separator else ""
            if name == "otelcol_exporter_queue_capacity":
                if not math.isfinite(value):
                    return None
                capacities[key] = value
            elif name == "otelcol_exporter_queue_size":
                if not math.isfinite(value):
                    return None
                sizes[key] = value
        percentages = [
            100 * size / capacities[key]
            for key, size in sizes.items()
            if capacities.get(key, 0) > 0
        ]
        return round(max(percentages)) if percentages else -1


class Smoke:
    def __init__(
        self,
        repo_root: Path,
        home: Path,
        system: SystemPort,
        http: HttpPort,
        *,
        sleeper: Callable[[float], None],
        stdout: TextIO,
        stderr: TextIO,
    ) -> None:
        self.repo_root = repo_root
        self.home = home
        self.system = system
        self.http = http
        self.sleeper = sleeper
        self.stdout = stdout
        self.stderr = stderr
        self.failed = False

    # Every check runs even when an earlier probe fails; the exit status is driven by
    # the accumulated `failed` flag, not by the first failure.
    def run(self) -> int:
        self.check_binary()
        self.check_service()
        self.check_health()
        before = self.fetch_metrics()
        if before is not None and before.contains_otelcol_metrics():
            self.ok("metrics :8888")
        else:
            self.bad("metrics :8888 not serving otelcol_ metrics")
        posted = self.post_marker()
        if posted:
            self.sleeper(1)
        after = self.fetch_metrics()
        self.check_round_trip(before, after, posted=posted)
        self.check_delivery(after)
        if not self.failed:
            print("otelbox-edge: all checks passed", file=self.stdout)
            return 0
        print(
            "otelbox-edge: FAILED — see above; tail ~/Library/Logs/otelbox-edge.log",
            file=self.stderr,
        )
        return 1

    def check_binary(self) -> None:
        pinned = read_pinned_version(self.repo_root / "roles/devbox/defaults/main/packages.yml")
        binary = self.home / ".local/bin/otelcol-otelbox"
        if pinned is None:
            self.bad(
                "cannot read devbox_packages.otelbox_edge.version from defaults/main/packages.yml"
            )
            return
        if not binary.is_file() or not os.access(binary, os.X_OK):
            self.bad(f"binary missing or not v{pinned}: {binary}")
            return
        result = self.system.run([str(binary), "--version"])
        if result.returncode == 0 and f"version {pinned}" in result.stdout:
            self.ok(f"binary v{pinned}: {binary}")
        else:
            self.bad(f"binary missing or not v{pinned}: {binary}")

    def check_service(self) -> None:
        result = self.system.run(
            ["/bin/launchctl", "print", f"gui/{os.getuid()}/local.otelbox-edge"]
        )
        if result.returncode:
            self.bad("service not loaded (launchctl print failed)")
            return
        state = "unknown"
        for line in result.stdout.splitlines():
            if "state = " in line:
                state = line.partition("state = ")[2]
                break
        self.ok(f"service state: {state}")

    def check_health(self) -> None:
        for attempt in range(5):
            try:
                self.http.get(HEALTH_URL)
            except ProbeError:
                if attempt < 4:
                    self.sleeper(1)
            else:
                self.ok("lifecycle health :13133/status")
                return
        self.bad("lifecycle health :13133/status not responding")

    def fetch_metrics(self) -> MetricsSnapshot | None:
        try:
            return MetricsSnapshot.parse(self.http.get(METRICS_URL))
        except ProbeError:
            return None

    def post_marker(self) -> bool:
        try:
            self.http.post_json(LOGS_URL, LOG_MARKER)
        except ProbeError:
            self.bad("OTLP/HTTP :4318 rejected the test log")
            return False
        return True

    def check_round_trip(
        self,
        before: MetricsSnapshot | None,
        after: MetricsSnapshot | None,
        *,
        posted: bool,
    ) -> None:
        if before is None or after is None or not posted:
            self.bad("receiver_accepted_log_records could not be measured")
            return
        before_count = before.sum_prefix("otelcol_receiver_accepted_log_records")
        after_count = after.sum_prefix("otelcol_receiver_accepted_log_records")
        if before_count is None or after_count is None:
            self.bad("receiver_accepted_log_records could not be measured")
            return
        if after_count > before_count:
            self.ok(
                f"OTLP round-trip: receiver accepted the test log ({before_count} -> {after_count})"
            )
        else:
            self.bad(
                f"receiver_accepted_log_records did not increase ({before_count} -> {after_count})"
            )

    # Local counterpart of the artefact repository's TestEdgeToGatewayDelivery. Do NOT
    # weaken it into a liveness check: it exists because a wrong ingestion token once
    # left every other check on this list green while telemetry went nowhere for days.
    def check_delivery(self, snapshot: MetricsSnapshot | None) -> None:
        if snapshot is None:
            self.bad("gateway delivery: metrics snapshot unavailable")
            return
        dropped = snapshot.sum_prefix("otelcol_exporter_send_failed_")
        enqueue_failed = snapshot.sum_prefix("otelcol_exporter_enqueue_failed_")
        refused = snapshot.sum_prefix("otelcol_receiver_refused_")
        queue_percent = snapshot.max_queue_percent()
        if dropped is None or enqueue_failed is None or refused is None or queue_percent is None:
            self.bad("gateway delivery: non-finite metric sample")
            return
        if not any((dropped, enqueue_failed, refused)) and 0 <= queue_percent < 80:
            self.ok(
                f"gateway delivery: max queue {queue_percent}%; "
                "no send, enqueue or receive failures"
            )
            return
        self.bad(
            "gateway delivery: "
            f"send_failed={dropped}, enqueue_failed={enqueue_failed}, refused={refused}, "
            f"max_queue={queue_percent}%"
        )

    def ok(self, message: str) -> None:
        print(f"  ok    {message}", file=self.stdout)

    def bad(self, message: str) -> None:
        print(f"  FAIL  {message}", file=self.stderr)
        self.failed = True


# The pin lives in devbox_packages.otelbox_edge.version in defaults/main/packages.yml and
# nowhere else. Repeating the literal here is how a version bump ends up asserting the
# previous release.
def read_pinned_version(path: Path) -> str | None:
    in_otelbox_block = False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if line == "  otelbox_edge:":
            in_otelbox_block = True
            continue
        if in_otelbox_block and line.startswith("    version:"):
            return line.partition(":")[2].strip().strip('"')
        if in_otelbox_block and line.startswith("  ") and not line.startswith("    "):
            return None
    return None


def main(
    *,
    platform_name: str | None = None,
    repo_root: Path | None = None,
    environment: dict[str, str] | None = None,
    system: SystemPort | None = None,
    http: HttpPort | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    current_platform = platform.system() if platform_name is None else platform_name
    if current_platform != "Darwin":
        print("otelbox-edge-test: macOS only.", file=stderr)
        return 0
    env = dict(os.environ if environment is None else environment)
    root = Path(__file__).resolve().parents[2] if repo_root is None else repo_root
    smoke = Smoke(
        root,
        Path(env["HOME"]),
        SystemRunner() if system is None else system,
        LoopbackHttpClient() if http is None else http,
        sleeper=sleeper,
        stdout=stdout,
        stderr=stderr,
    )
    return smoke.run()
