"""One scrape of the edge's :8888/metrics, read by the watcher's parser and by the bar's Lua module.

Both readers must agree on which queues exist and how full the fullest is, because the macOS
notification (scripts/otelbox_edge) and the SketchyBar item (bar_edge.lua) report the same queue.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from typing import TYPE_CHECKING, Final, cast

from generation import REPO_ROOT
from otelbox_edge import smoke

if TYPE_CHECKING:
    from pathlib import Path

BAR_EDGE: Final = REPO_ROOT / "roles/devbox/files/.hammerspoon/modules/bar_edge.lua"
JSON_OUT: Final = REPO_ROOT / "tests/deploy/lua/json_out.lua"
LUA_INTERPRETERS: Final = ("lua5.4", "lua")
LUA_SECONDS: Final = 30.0
QUEUE_GAUGES: Final = ("otelcol_exporter_queue_size", "otelcol_exporter_queue_capacity")
LABEL: Final = re.compile(r'(\w+)="([^"]*)"')
CONTRACT_LABEL_KEYS: Final = frozenset({"data_type", "exporter"})
CONTRACT_QUEUES: Final = frozenset(
    {
        ("logs", "otlp_grpc/gateway"),
        ("metrics", "otlp_grpc/gateway"),
        ("traces", "otlp_grpc/gateway"),
        ("metrics", "otlp_grpc/gateway_self"),
    }
)

READ_SCRIPT: Final = """
local encode = dofile(arg[1])
local edge = dofile(arg[2])
local file = assert(io.open(arg[3], "rb"))
local text = file:read("a")
file:close()
local series = edge.queue_series(text)
print(encode({
  series = series,
  fill = edge.max_fill(series),
  summary = edge.summarise(text, {}),
}))
"""


def find_lua() -> str | None:
    for name in LUA_INTERPRETERS:
        located = shutil.which(name)
        if located is not None:
            return located
    return None


def queues_in(text: str) -> dict[str, tuple[float, float]]:
    return smoke.MetricsSnapshot.parse(text).queue_series() or {}


def read_in_lua(
    lua: str, text: str, directory: Path, bar_edge: Path = BAR_EDGE
) -> dict[str, object]:
    metrics = directory / "metrics.txt"
    metrics.write_text(text, encoding="utf-8")
    done = subprocess.run(
        [lua, "-", str(JSON_OUT), str(bar_edge), str(metrics)],
        input=READ_SCRIPT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=LUA_SECONDS,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return cast("dict[str, object]", json.loads(done.stdout))


def series_labels(text: str, metric: str) -> list[dict[str, str]]:
    samples = smoke.MetricsSnapshot.parse(text).samples
    return [
        dict(LABEL.findall(sample.partition("{")[2]))
        for sample, _value in samples
        if sample.partition("{")[0] == metric
    ]


def check_queue_contract(text: str) -> None:
    """Each queue gauge has exactly the contract's four series, labelled data_type and exporter."""
    for metric in QUEUE_GAUGES:
        labels = series_labels(text, metric)
        wrong_keys = [found for found in labels if set(found) != CONTRACT_LABEL_KEYS]
        assert not wrong_keys, f"{metric} labels other than data_type and exporter: {wrong_keys}"
        pairs = [(found["data_type"], found["exporter"]) for found in labels]
        assert len(pairs) == len(set(pairs)), f"{metric} repeats a (data_type, exporter): {pairs}"
        assert set(pairs) == CONTRACT_QUEUES, f"{metric} series are {sorted(pairs)}"


def why_not_ready(text: str) -> str | None:
    """What keeps a scrape from passing check_bar_agrees_with_watcher's inputs, or None."""
    if not queues_in(text):
        return "the scrape holds no finite exporter queue with a positive capacity"
    try:
        check_queue_contract(text)
    except AssertionError as error:
        return str(error)
    return None


def check_bar_agrees_with_watcher(
    lua: str, text: str, directory: Path, bar_edge: Path = BAR_EDGE
) -> None:
    expected = queues_in(text)
    assert expected, "the scrape holds no finite exporter queue with a positive capacity"
    check_queue_contract(text)
    for size, capacity in expected.values():
        assert math.isfinite(size)
        assert math.isfinite(capacity)
        assert capacity > 0

    read = read_in_lua(lua, text, directory, bar_edge)

    assert read["series"] == {
        key: {"size": size, "capacity": capacity} for key, (size, capacity) in expected.items()
    }
    fill = max(size / capacity for size, capacity in expected.values())
    assert read["fill"] == fill
    assert read["summary"] == {
        "state": "ok",
        "percent": math.floor(100 * fill + 0.5),
        "level": "ok",
        "markers": [],
    }
