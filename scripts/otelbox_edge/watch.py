from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TextIO

from otelbox_edge.smoke import (
    METRICS_URL,
    LoopbackHttpClient,
    MetricsSnapshot,
    ProbeError,
    SystemPort,
    SystemRunner,
)

if TYPE_CHECKING:
    from collections.abc import Callable

GIB = 1024**3
WARNING_FILL = 0.5
CRITICAL_FILL = 0.8
STALL_SECONDS = 30 * 60
# A longer gap between runs means the Mac slept, so nothing was observed not draining.
OBSERVATION_GAP_SECONDS = 15 * 60
STATE_PATH = ".local/state/otelbox/watch.json"
NOTIFICATION_TITLE = "otelbox edge"
LEVELS = ("ok", "warning", "critical")
SENT_PREFIXES = {
    "traces": "otelcol_exporter_sent_spans",
    "metrics": "otelcol_exporter_sent_metric_points",
    "logs": "otelcol_exporter_sent_log_records",
    "profiles": "otelcol_exporter_sent_profile_samples",
}
DATA_TYPE_LABEL = re.compile(r'data_type="([^"]*)"')


class MetricsPort(Protocol):
    def get(self, url: str) -> str: ...


@dataclass(frozen=True)
class Alert:
    level: str
    message: str


@dataclass
class Drain:
    sent: int
    since: float


@dataclass
class WatchState:
    last_run: float | None = None
    notified: dict[str, str] = field(default_factory=dict)
    drains: dict[str, Drain] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> WatchState:
        try:
            document: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(document, dict):
            return cls()
        state = cls()
        last_run = document.get("last_run")
        if isinstance(last_run, (int, float)):
            state.last_run = float(last_run)
        notified = document.get("notified")
        if isinstance(notified, dict):
            state.notified = {
                str(condition): level for condition, level in notified.items() if level in LEVELS
            }
        drains = document.get("drains")
        if isinstance(drains, dict):
            for signal, drain in drains.items():
                if not isinstance(drain, dict):
                    continue
                sent = drain.get("sent")
                since = drain.get("since")
                if isinstance(sent, int) and isinstance(since, (int, float)):
                    state.drains[str(signal)] = Drain(sent, float(since))
        return state

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "last_run": self.last_run,
            "notified": self.notified,
            "drains": {
                signal: {"sent": drain.sent, "since": drain.since}
                for signal, drain in self.drains.items()
            },
        }
        staging = path.with_name(f".{path.name}.tmp")
        staging.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        staging.replace(path)


class Watch:
    def __init__(
        self,
        http: MetricsPort,
        system: SystemPort,
        *,
        storage_dir: Path,
        state_path: Path,
        clock: Callable[[], float],
        disk_free: Callable[[Path], int | None],
        stdout: TextIO,
        stderr: TextIO,
    ) -> None:
        self.http = http
        self.system = system
        self.storage_dir = storage_dir
        self.state_path = state_path
        self.clock = clock
        self.disk_free = disk_free
        self.stdout = stdout
        self.stderr = stderr

    def run(self) -> int:
        try:
            snapshot = MetricsSnapshot.parse(self.http.get(METRICS_URL))
        except ProbeError:
            print(
                "otelbox-edge-watch: metrics :8888 unavailable; nothing checked", file=self.stderr
            )
            return 1
        series = snapshot.queue_series()
        if not series:
            print("otelbox-edge-watch: no finite exporter queue metrics on :8888", file=self.stderr)
            return 1
        now = self.clock()
        state = WatchState.load(self.state_path)
        alerts = {
            "queue_fill": self.queue_fill(series),
            "stall": self.stall(snapshot, series, state, now),
            "disk": self.disk(series),
        }
        failed = False
        for condition, alert in alerts.items():
            level = "ok" if alert is None else alert.level
            previous = state.notified.get(condition, "ok")
            if alert is not None and LEVELS.index(level) > LEVELS.index(previous):
                if not self.notify(alert.message):
                    print(
                        f"otelbox-edge-watch: notification failed: {alert.message}",
                        file=self.stderr,
                    )
                    failed = True
                    continue
                print(f"otelbox-edge-watch: {level}: {alert.message}", file=self.stdout)
            state.notified[condition] = level
        state.last_run = now
        try:
            state.save(self.state_path)
        except OSError as error:
            print(f"otelbox-edge-watch: cannot save {self.state_path}: {error}", file=self.stderr)
            failed = True
        return 1 if failed else 0

    def queue_fill(self, series: dict[str, tuple[float, float]]) -> Alert | None:
        key, (size, capacity) = max(series.items(), key=lambda item: item[1][0] / item[1][1])
        fill = size / capacity
        if fill < WARNING_FILL:
            return None
        message = (
            f"{signal_of(key) or 'A'} queue is {fill:.0%} full; "
            "the edge refuses telemetry once it is full."
        )
        return Alert("critical" if fill >= CRITICAL_FILL else "warning", message)

    def stall(
        self,
        snapshot: MetricsSnapshot,
        series: dict[str, tuple[float, float]],
        state: WatchState,
        now: float,
    ) -> Alert | None:
        observed = state.last_run is not None and now - state.last_run <= OBSERVATION_GAP_SECONDS
        stalled: list[tuple[str, float]] = []
        for key, (size, _capacity) in series.items():
            signal = signal_of(key)
            prefix = SENT_PREFIXES.get(signal)
            if prefix is None:
                continue
            sent = snapshot.sum_prefix(prefix)
            if sent is None:
                continue
            drain = state.drains.get(signal)
            if size <= 0 or not observed or drain is None or drain.sent != sent:
                state.drains[signal] = Drain(sent, now)
            elif now - drain.since >= STALL_SECONDS:
                stalled.append((signal, now - drain.since))
        if not stalled:
            return None
        signals = ", ".join(signal for signal, _seconds in stalled)
        minutes = round(max(seconds for _signal, seconds in stalled) / 60)
        return Alert(
            "warning",
            f"Nothing sent for {minutes} min while the {signals} queue holds data; "
            "the gateway looks unreachable.",
        )

    def disk(self, series: dict[str, tuple[float, float]]) -> Alert | None:
        free = self.disk_free(self.storage_dir)
        if free is None:
            print(
                f"otelbox-edge-watch: cannot read free space for {self.storage_dir}",
                file=self.stderr,
            )
            return None
        headroom = sum(max(capacity - size, 0.0) for size, capacity in series.values())
        if free >= headroom:
            return None
        return Alert(
            "warning",
            f"{free / GIB:.0f} GiB free on the WAL volume, but the queues may still claim "
            f"{headroom / GIB:.0f} GiB; a long outage fills the disk first.",
        )

    def notify(self, message: str) -> bool:
        result = self.system.run(
            [
                "/usr/bin/osascript",
                "-e",
                "on run argv",
                "-e",
                "display notification (item 1 of argv) with title (item 2 of argv)",
                "-e",
                "end run",
                message,
                NOTIFICATION_TITLE,
            ]
        )
        return result.returncode == 0


def signal_of(series_key: str) -> str:
    match = DATA_TYPE_LABEL.search(series_key)
    return match.group(1) if match else ""


def free_bytes(path: Path) -> int | None:
    try:
        stats = os.statvfs(path)
    except OSError:
        return None
    return stats.f_bavail * stats.f_frsize


def main(
    *,
    platform_name: str | None = None,
    environment: dict[str, str] | None = None,
    http: MetricsPort | None = None,
    system: SystemPort | None = None,
    disk_free: Callable[[Path], int | None] = free_bytes,
    clock: Callable[[], float] = time.time,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    current_platform = platform.system() if platform_name is None else platform_name
    if current_platform != "Darwin":
        print("otelbox-edge-watch: macOS only.", file=stderr)
        return 0
    env = dict(os.environ if environment is None else environment)
    storage_dir = env.get("OTELBOX_STORAGE_DIR")
    if not storage_dir:
        print("otelbox-edge-watch: OTELBOX_STORAGE_DIR is not set", file=stderr)
        return 2
    watch = Watch(
        LoopbackHttpClient() if http is None else http,
        SystemRunner() if system is None else system,
        storage_dir=Path(storage_dir),
        state_path=Path(env["HOME"]) / STATE_PATH,
        clock=clock,
        disk_free=disk_free,
        stdout=stdout,
        stderr=stderr,
    )
    return watch.run()
