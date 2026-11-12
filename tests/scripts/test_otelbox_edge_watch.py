from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from io import StringIO
from typing import TYPE_CHECKING

import pytest
from otelbox_edge import smoke, watch

if TYPE_CHECKING:
    from pathlib import Path

GIB = 1024**3
CAPACITY = 100 * GIB
MINUTE = 60.0
SENT_FAMILIES = {
    "traces": "otelcol_exporter_sent_spans_total",
    "metrics": "otelcol_exporter_sent_metric_points_total",
    "logs": "otelcol_exporter_sent_log_records_total",
}


def exposition(
    queued: dict[str, float] | None = None,
    sent: dict[str, int] | None = None,
) -> str:
    queued = queued or {}
    sent = sent or {}
    lines = ["# HELP otelcol_exporter_queue_size Current size of the retry queue"]
    for signal in ("traces", "metrics", "logs"):
        labels = f'{{data_type="{signal}",exporter="otlp_grpc/gateway"}}'
        lines.append(f"otelcol_exporter_queue_capacity{labels} {CAPACITY}")
        lines.append(f"otelcol_exporter_queue_size{labels} {queued.get(signal, 0)}")
        lines.append(
            f'{SENT_FAMILIES[signal]}{{exporter="otlp_grpc/gateway"}} {sent.get(signal, 0)}'
        )
    return "\n".join(lines) + "\n"


@dataclass
class FakeSystem:
    returncode: int = 0
    calls: list[list[str]] = field(default_factory=list)

    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(arguments)
        return subprocess.CompletedProcess(arguments, self.returncode, "", "")

    @property
    def messages(self) -> list[str]:
        return [call[-2] for call in self.calls]


@dataclass
class FakeMetrics:
    content: str | None = None
    urls: list[str] = field(default_factory=list)

    def get(self, url: str) -> str:
        self.urls.append(url)
        if self.content is None:
            raise smoke.ProbeError
        return self.content


@dataclass
class WatchHarness:
    home: Path
    storage_dir: Path
    system: FakeSystem = field(default_factory=FakeSystem)
    metrics: FakeMetrics = field(default_factory=FakeMetrics)
    now: float = 1_000_000.0
    free: int | None = 10_000 * GIB
    stderr: str = ""

    def run(self, content: str | None, *, at_minute: float | None = None) -> int:
        if at_minute is not None:
            self.now = 1_000_000.0 + at_minute * MINUTE
        self.metrics.content = content
        stdout = StringIO()
        stderr = StringIO()
        result = watch.main(
            platform_name="Darwin",
            environment={"HOME": str(self.home), "OTELBOX_STORAGE_DIR": str(self.storage_dir)},
            http=self.metrics,
            system=self.system,
            disk_free=self.disk_free,
            clock=lambda: self.now,
            stdout=stdout,
            stderr=stderr,
        )
        self.stderr = stderr.getvalue()
        return result

    def disk_free(self, path: Path) -> int | None:
        assert path == self.storage_dir
        return self.free

    @property
    def state_path(self) -> Path:
        return self.home / ".local/state/otelbox/watch.json"


@pytest.fixture
def harness(tmp_path: Path) -> WatchHarness:
    return WatchHarness(tmp_path / "home", tmp_path / "home/.local/state/otelbox/edge")


class TestQueueSeries:
    def test_pairs_size_and_capacity_by_label_set(self) -> None:
        snapshot = smoke.MetricsSnapshot.parse(exposition({"traces": 25 * GIB}))

        series = snapshot.queue_series()

        assert series is not None
        assert sorted(series.values()) == [(0, CAPACITY), (0, CAPACITY), (25 * GIB, CAPACITY)]
        assert {watch.signal_of(key) for key in series} == {"traces", "metrics", "logs"}


class TestQueueFill:
    def test_a_queue_below_half_full_is_not_reported(self, harness: WatchHarness) -> None:
        result = harness.run(exposition({"traces": 49 * GIB}, {"traces": 1}))

        assert result == 0
        assert harness.system.calls == []
        assert harness.state_path.is_file()

    def test_half_full_warns_once(self, harness: WatchHarness) -> None:
        harness.run(exposition({"traces": 50 * GIB}, {"traces": 1}), at_minute=0)
        harness.run(exposition({"traces": 60 * GIB}, {"traces": 2}), at_minute=5)

        assert harness.system.messages == [
            "traces queue is 50% full; the edge refuses telemetry once it is full."
        ]

    def test_escalation_to_critical_notifies_again(self, harness: WatchHarness) -> None:
        harness.run(exposition({"logs": 55 * GIB}, {"logs": 1}), at_minute=0)
        harness.run(exposition({"logs": 85 * GIB}, {"logs": 2}), at_minute=5)
        harness.run(exposition({"logs": 90 * GIB}, {"logs": 3}), at_minute=10)

        assert harness.system.messages == [
            "logs queue is 55% full; the edge refuses telemetry once it is full.",
            "logs queue is 85% full; the edge refuses telemetry once it is full.",
        ]

    def test_a_level_that_cleared_is_notified_when_it_returns(self, harness: WatchHarness) -> None:
        harness.run(exposition({"traces": 85 * GIB}, {"traces": 1}), at_minute=0)
        harness.run(exposition({"traces": 10 * GIB}, {"traces": 2}), at_minute=5)
        harness.run(exposition({"traces": 85 * GIB}, {"traces": 3}), at_minute=10)

        assert len(harness.system.messages) == 2


class TestStalledDrain:
    def test_a_non_empty_queue_that_sends_nothing_for_30_minutes_warns(
        self, harness: WatchHarness
    ) -> None:
        stuck = exposition({"traces": GIB}, {"traces": 7})

        for minute in range(0, 30, 5):
            harness.run(stuck, at_minute=minute)
        assert harness.system.calls == []

        harness.run(stuck, at_minute=30)
        harness.run(stuck, at_minute=35)

        assert harness.system.messages == [
            (
                "Nothing sent for 30 min while the traces queue holds data; "
                "the gateway looks unreachable."
            )
        ]

    def test_progress_restarts_the_stall_clock(self, harness: WatchHarness) -> None:
        for step, minute in enumerate(range(0, 60, 5)):
            harness.run(exposition({"traces": GIB}, {"traces": 7 + step // 4}), at_minute=minute)

        assert harness.system.calls == []

    def test_an_empty_queue_never_stalls(self, harness: WatchHarness) -> None:
        for minute in range(0, 65, 5):
            harness.run(exposition({}, {"traces": 7}), at_minute=minute)

        assert harness.system.calls == []

    def test_a_gap_between_runs_restarts_the_stall_clock(self, harness: WatchHarness) -> None:
        stuck = exposition({"metrics": GIB}, {"metrics": 3})

        harness.run(stuck, at_minute=0)
        harness.run(stuck, at_minute=40)
        harness.run(stuck, at_minute=45)

        assert harness.system.calls == []

    def test_drain_resumes_clears_the_warning(self, harness: WatchHarness) -> None:
        stuck = exposition({"traces": GIB}, {"traces": 7})
        for minute in range(0, 35, 5):
            harness.run(stuck, at_minute=minute)
        harness.run(exposition({}, {"traces": 9}), at_minute=35)

        assert json.loads(harness.state_path.read_text(encoding="utf-8"))["notified"]["stall"] == (
            "ok"
        )


class TestVolumeSpace:
    def test_less_free_space_than_queue_headroom_warns(self, harness: WatchHarness) -> None:
        harness.free = 200 * GIB

        harness.run(exposition({"traces": 40 * GIB}), at_minute=0)
        harness.run(exposition({"traces": 40 * GIB}), at_minute=5)

        assert harness.system.messages == [
            (
                "200 GiB free on the WAL volume, but the queues may still claim 260 GiB; "
                "a long outage fills the disk first."
            )
        ]

    def test_free_space_covering_the_headroom_is_quiet(self, harness: WatchHarness) -> None:
        harness.free = 260 * GIB

        harness.run(exposition({"traces": 40 * GIB}))

        assert harness.system.calls == []

    def test_unreadable_free_space_is_reported_not_notified(self, harness: WatchHarness) -> None:
        harness.free = None

        result = harness.run(exposition())

        assert result == 0
        assert harness.system.calls == []
        assert "cannot read free space" in harness.stderr


class TestRunBoundaries:
    def test_unavailable_metrics_check_nothing_and_keep_state(self, harness: WatchHarness) -> None:
        result = harness.run(None)

        assert result == 1
        assert harness.system.calls == []
        assert not harness.state_path.exists()
        assert "metrics :8888 unavailable" in harness.stderr

    def test_metrics_without_queues_check_nothing(self, harness: WatchHarness) -> None:
        result = harness.run("otelcol_process_uptime_seconds_total 5\n")

        assert result == 1
        assert harness.system.calls == []

    def test_failed_notification_is_retried_on_the_next_run(self, harness: WatchHarness) -> None:
        harness.system.returncode = 1
        first = harness.run(exposition({"traces": 85 * GIB}, {"traces": 1}), at_minute=0)
        first_stderr = harness.stderr
        harness.system.returncode = 0
        second = harness.run(exposition({"traces": 85 * GIB}, {"traces": 2}), at_minute=5)

        assert (first, second) == (1, 0)
        assert len(harness.system.calls) == 2
        assert "notification failed" in first_stderr

    def test_message_reaches_osascript_as_an_argument_not_as_script(
        self, harness: WatchHarness
    ) -> None:
        harness.run(exposition({"traces": 85 * GIB}, {"traces": 1}))

        (call,) = harness.system.calls
        scripts = [call[index + 1] for index, argument in enumerate(call) if argument == "-e"]
        assert call[0] == "/usr/bin/osascript"
        assert all("queue" not in script for script in scripts)
        assert call[-1] == "otelbox edge"

    def test_corrupt_state_is_replaced(self, harness: WatchHarness) -> None:
        harness.state_path.parent.mkdir(parents=True)
        harness.state_path.write_text("{not json", encoding="utf-8")

        result = harness.run(exposition({"traces": 85 * GIB}, {"traces": 1}))

        assert result == 0
        assert len(harness.system.calls) == 1
        state = json.loads(harness.state_path.read_text(encoding="utf-8"))
        assert state["notified"]["queue_fill"] == "critical"

    def test_missing_storage_dir_is_a_configuration_error(self, harness: WatchHarness) -> None:
        stderr = StringIO()

        result = watch.main(
            platform_name="Darwin",
            environment={"HOME": str(harness.home)},
            http=harness.metrics,
            system=harness.system,
            stderr=stderr,
        )

        assert result == 2
        assert "OTELBOX_STORAGE_DIR is not set" in stderr.getvalue()
        assert harness.metrics.urls == []

    def test_other_platforms_do_nothing(self, harness: WatchHarness) -> None:
        result = watch.main(
            platform_name="Linux",
            environment={},
            http=harness.metrics,
            system=harness.system,
            stderr=StringIO(),
        )

        assert result == 0
        assert harness.metrics.urls == []
        assert harness.system.calls == []
