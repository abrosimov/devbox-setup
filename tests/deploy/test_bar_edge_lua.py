"""Behaviour of bar_edge, the pure-Lua reader of the otelbox edge's state for the SketchyBar item.

It runs under the plain `lua` interpreters tests/deploy/conftest.py finds. Its contract is to
agree with scripts/otelbox_edge: the same exposition text and the same watch.json that the
Python side parses and writes must give the same fill, level and alerts in Lua, because the
bar and the macOS notification must never disagree about a queue.
"""

from __future__ import annotations

import io
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

import pytest
from otelbox_edge import smoke, watch

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

type RunLua = Callable[..., object]
type Doc = dict[str, object]
type Series = dict[str, dict[str, float]]

MODULES: Final = Path(__file__).resolve().parents[2] / "roles/devbox/files/.hammerspoon/modules"
EDGE: Final = str(MODULES / "bar_edge.lua")
RENDER: Final = str(MODULES / "bar_render.lua")

PLENTY: Final = 1024 * 1024**3
GATEWAY: Final = 'data_type="metrics",exporter="otlp_grpc/gateway"'
SELF: Final = 'data_type="metrics",exporter="otlp_grpc/gateway_self"'

SHOW_NUMBER: Final = """
local function show(v)
  if v == nil then return "nil" end
  if v ~= v then return "nan" end
  if v == math.huge then return "inf" end
  if v == -math.huge then return "-inf" end
  return v
end
"""


def _sample(name: str, value: str, labels: str = "") -> str:
    return f"{name}{{{labels}}} {value}" if labels else f"{name} {value}"


def _size(value: str, labels: str = GATEWAY) -> str:
    return _sample("otelcol_exporter_queue_size", value, labels)


def _capacity(value: str, labels: str = GATEWAY) -> str:
    return _sample("otelcol_exporter_queue_capacity", value, labels)


def _text(*lines: str) -> str:
    return "\n".join(lines) + "\n"


def _queue(size: float, capacity: float, labels: str = GATEWAY) -> str:
    return _text(_size(repr(size), labels), _capacity(repr(capacity), labels))


def _lua_series(run_lua: RunLua, text: object) -> Series | None:
    script = "local edge = dofile(DATA.edge)\nprint(encode(edge.queue_series(DATA.text)))"
    result = run_lua(script, {"edge": EDGE, "text": text})
    if result == []:
        return {}
    return cast("Series | None", result)


def _python_series(text: str) -> Series | None:
    series = smoke.MetricsSnapshot.parse(text).queue_series()
    if series is None:
        return None
    return {key: {"size": size, "capacity": capacity} for key, (size, capacity) in series.items()}


def _lua_max_fill(run_lua: RunLua, text: str) -> float | None:
    script = """
local edge = dofile(DATA.edge)
print(encode(edge.max_fill(edge.queue_series(DATA.text))))
"""
    return cast("float | None", run_lua(script, {"edge": EDGE, "text": text}))


def _python_max_fill(text: str) -> float | None:
    series = _python_series(text)
    if not series:
        return None
    return max(q["size"] / q["capacity"] for q in series.values())


def _summary(run_lua: RunLua, text: object, alerts: object = None) -> Doc:
    script = "local edge = dofile(DATA.edge)\nprint(encode(edge.summarise(DATA.text, DATA.alerts)))"
    return cast("Doc", run_lua(script, {"edge": EDGE, "text": text, "alerts": alerts}))


class TestSampleValue:
    ACCEPTED: Final = [
        "0",
        "1",
        "42",
        "-7",
        "+7",
        "1.5",
        ".5",
        "5.",
        "-0",
        "1e3",
        "1E3",
        "1e-3",
        "1.5e+3",
        "4.294967296e+09",
        "1e400",
        "inf",
        "Inf",
        "+Inf",
        "-inf",
        "-Inf",
        "INF",
        "infinity",
        "Infinity",
        "+infinity",
        "-INFINITY",
        "nan",
        "NaN",
        "+NaN",
        "-nan",
    ]
    REJECTED: Final = [
        "",
        "abc",
        "0x10",
        "0X1F",
        "0x1p4",
        "1e",
        "e5",
        "--1",
        "+-1",
        "1,5",
        "1.2.3",
        "inf1",
        "infin",
        "nanx",
        "+",
        "-",
        ".",
        "1e+",
        "0b11",
    ]

    @staticmethod
    def _lua(run_lua: RunLua, text: str) -> object:
        script = (
            "local edge = dofile(DATA.edge)\n"
            + SHOW_NUMBER
            + "print(encode(show(edge.sample_value(DATA.text))))"
        )
        return run_lua(script, {"edge": EDGE, "text": text})

    @staticmethod
    def _python(text: str) -> object:
        try:
            value = float(text)
        except ValueError:
            return "nil"
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return value

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("1", 1),
            ("1e3", 1000),
            ("+Inf", "inf"),
            ("-inf", "-inf"),
            ("NaN", "nan"),
            ("0x10", "nil"),
            ("abc", "nil"),
        ],
    )
    def test_reads_a_sample_the_way_a_prometheus_value_is_written(
        self, run_lua: RunLua, text: str, expected: object
    ) -> None:
        assert self._lua(run_lua, text) == expected

    @pytest.mark.parametrize("text", [*ACCEPTED, *REJECTED])
    def test_agrees_with_pythons_float_on_every_form(self, run_lua: RunLua, text: str) -> None:
        assert self._lua(run_lua, text) == self._python(text)

    @pytest.mark.parametrize("text", ACCEPTED)
    def test_every_accepted_form_has_a_value(self, run_lua: RunLua, text: str) -> None:
        assert self._lua(run_lua, text) != "nil"

    @pytest.mark.parametrize("text", REJECTED)
    def test_every_rejected_form_has_no_value(self, run_lua: RunLua, text: str) -> None:
        assert self._lua(run_lua, text) == "nil"

    def test_anything_that_is_not_a_string_has_no_value(self, run_lua: RunLua) -> None:
        script = (
            "local edge = dofile(DATA.edge)\n"
            + SHOW_NUMBER
            + "print(encode({ show(edge.sample_value(nil)), show(edge.sample_value(42)),"
            + " show(edge.sample_value({})), show(edge.sample_value(true)) }))"
        )

        assert run_lua(script, {"edge": EDGE}) == ["nil", "nil", "nil", "nil"]


class TestQueueSeries:
    def test_a_size_and_a_capacity_with_the_same_labels_make_one_queue(
        self, run_lua: RunLua
    ) -> None:
        text = _text(_capacity("1000"), _size("250"))

        assert _lua_series(run_lua, text) == {
            f"{{{GATEWAY}}}": {"size": 250, "capacity": 1000},
        }

    def test_each_exporter_and_data_type_is_its_own_queue(self, run_lua: RunLua) -> None:
        text = _text(
            _size("10", GATEWAY),
            _capacity("100", GATEWAY),
            _size("30", SELF),
            _capacity("60", SELF),
        )

        assert _lua_series(run_lua, text) == {
            f"{{{GATEWAY}}}": {"size": 10, "capacity": 100},
            f"{{{SELF}}}": {"size": 30, "capacity": 60},
        }

    def test_an_unlabelled_pair_is_a_queue_keyed_by_the_empty_string(self, run_lua: RunLua) -> None:
        text = _text(_sample("otelcol_exporter_queue_size", "5"), _capacity("10", ""))

        assert _lua_series(run_lua, text) == {"": {"size": 5, "capacity": 10}}

    def test_a_labelled_size_does_not_pair_with_an_unlabelled_capacity(
        self, run_lua: RunLua
    ) -> None:
        text = _text(_size("5", GATEWAY), _capacity("10", ""))

        assert _lua_series(run_lua, text) == {}

    def test_a_size_and_a_capacity_with_different_labels_make_no_queue(
        self, run_lua: RunLua
    ) -> None:
        text = _text(_size("5", GATEWAY), _capacity("10", SELF))

        assert _lua_series(run_lua, text) == {}

    @pytest.mark.parametrize(
        "capacity",
        ["0", "-1", "-4294967296", "0.0"],
        ids=["zero", "minus-one", "negative", "float"],
    )
    def test_a_queue_without_positive_capacity_is_dropped(
        self, run_lua: RunLua, capacity: str
    ) -> None:
        assert _lua_series(run_lua, _text(_size("5"), _capacity(capacity))) == {}

    def test_a_size_without_a_capacity_is_dropped(self, run_lua: RunLua) -> None:
        assert _lua_series(run_lua, _text(_size("5"))) == {}

    def test_a_capacity_without_a_size_is_dropped(self, run_lua: RunLua) -> None:
        assert _lua_series(run_lua, _text(_capacity("5"))) == {}

    def test_a_dropped_queue_does_not_hide_a_good_one(self, run_lua: RunLua) -> None:
        text = _text(_size("5", SELF), _capacity("0", SELF), _size("1", GATEWAY), _capacity("2"))

        assert _lua_series(run_lua, text) == {f"{{{GATEWAY}}}": {"size": 1, "capacity": 2}}

    @pytest.mark.parametrize("value", ["NaN", "+Inf", "-Inf", "nan", "inf", "-infinity"])
    @pytest.mark.parametrize("which", ["size", "capacity"])
    def test_a_sample_that_is_not_finite_voids_the_whole_reading(
        self, run_lua: RunLua, which: str, value: str
    ) -> None:
        good = _text(_size("1", SELF), _capacity("2", SELF))
        broken = _size(value) if which == "size" else _capacity(value)
        other = _capacity("10") if which == "size" else _size("5")

        assert _lua_series(run_lua, good + _text(broken, other)) is None
        assert _lua_series(run_lua, _text(broken, other) + good) is None

    def test_a_sample_that_is_not_finite_in_an_unrelated_metric_is_ignored(
        self, run_lua: RunLua
    ) -> None:
        text = _text(
            _sample("otelcol_process_cpu_seconds_total", "NaN"),
            _sample("otelcol_exporter_sent_spans", "+Inf", 'exporter="otlp_grpc/gateway"'),
            _size("5"),
            _capacity("10"),
        )

        assert _lua_series(run_lua, text) == {f"{{{GATEWAY}}}": {"size": 5, "capacity": 10}}

    @pytest.mark.parametrize(
        "name",
        [
            "otelcol_exporter_queue_size_total",
            "otelcol_exporter_queue_sizes",
            "otelcol_exporter_queue_capacity_bytes",
            "otelcol_receiver_queue_size",
            "xotelcol_exporter_queue_size",
        ],
    )
    def test_only_the_exact_queue_metric_names_count(self, run_lua: RunLua, name: str) -> None:
        text = _text(_sample(name, "5", GATEWAY), _capacity("10"))

        assert _lua_series(run_lua, text) == {}

    def test_comments_blank_lines_and_indentation_are_skipped_or_trimmed(
        self, run_lua: RunLua
    ) -> None:
        text = (
            "# HELP otelcol_exporter_queue_size 99\n"
            "# TYPE otelcol_exporter_queue_size gauge\n"
            "\n"
            "   \n"
            f"  # {_size('99')}\n"
            f"   {_size('25')}   \n"
            f"\t{_capacity('100')}\t\n"
            "# EOF\n"
        )

        assert _lua_series(run_lua, text) == {f"{{{GATEWAY}}}": {"size": 25, "capacity": 100}}

    def test_windows_line_endings_are_read_like_unix_ones(self, run_lua: RunLua) -> None:
        text = _text(_size("25"), _capacity("100"))

        assert _lua_series(run_lua, text.replace("\n", "\r\n")) == _lua_series(run_lua, text)
        assert _lua_series(run_lua, text.replace("\n", "\r\n")) == {
            f"{{{GATEWAY}}}": {"size": 25, "capacity": 100}
        }

    def test_a_missing_final_newline_still_reads_the_last_line(self, run_lua: RunLua) -> None:
        text = _text(_size("25"), _capacity("100")).rstrip("\n")

        assert _lua_series(run_lua, text) == {f"{{{GATEWAY}}}": {"size": 25, "capacity": 100}}

    def test_exposition_numbers_in_scientific_notation_are_read(self, run_lua: RunLua) -> None:
        text = _text(_size("1.5e+03"), _capacity("4.294967296e+09"))

        assert _lua_series(run_lua, text) == {
            f"{{{GATEWAY}}}": {"size": 1500, "capacity": 4294967296},
        }

    def test_a_later_sample_of_the_same_series_replaces_an_earlier_one(
        self, run_lua: RunLua
    ) -> None:
        text = _text(_size("1"), _size("7"), _capacity("10"), _capacity("20"))

        assert _lua_series(run_lua, text) == {f"{{{GATEWAY}}}": {"size": 7, "capacity": 20}}

    def test_a_value_that_is_not_a_number_leaves_no_reading_for_that_line(
        self, run_lua: RunLua
    ) -> None:
        text = _text(_size("abc"), _capacity("10"))

        assert _lua_series(run_lua, text) == {}

    def test_a_line_with_no_value_is_skipped(self, run_lua: RunLua) -> None:
        text = _text("otelcol_exporter_queue_size", _size("5"), _capacity("10"))

        assert _lua_series(run_lua, text) == {f"{{{GATEWAY}}}": {"size": 5, "capacity": 10}}

    @pytest.mark.parametrize("text", ["", "\n", "   \n\t\n"], ids=["empty", "newline", "blank"])
    def test_text_without_samples_has_no_queues(self, run_lua: RunLua, text: str) -> None:
        assert _lua_series(run_lua, text) == {}

    def test_a_missing_body_has_no_reading(self, run_lua: RunLua) -> None:
        script = "local edge = dofile(DATA.edge)\nprint(encode(edge.queue_series(nil)))"

        assert run_lua(script, {"edge": EDGE}) is None

    def test_a_body_that_is_not_text_has_no_reading(self, run_lua: RunLua) -> None:
        script = "local edge = dofile(DATA.edge)\nprint(encode({ edge.queue_series(42) }))"

        assert run_lua(script, {"edge": EDGE}) == []


FULL_EXPOSITION: Final = _text(
    "# HELP otelcol_exporter_queue_capacity Fixed capacity of the retry queue (in bytes) [alpha]",
    "# TYPE otelcol_exporter_queue_capacity gauge",
    _capacity("4.294967296e+09", 'data_type="metrics",exporter="otlp_grpc/gateway"'),
    _capacity("4.294967296e+09", 'data_type="traces",exporter="otlp_grpc/gateway"'),
    _capacity("5.36870912e+08", 'data_type="metrics",exporter="otlp_grpc/gateway_self"'),
    "# HELP otelcol_exporter_queue_size Current size of the retry queue (in bytes) [alpha]",
    "# TYPE otelcol_exporter_queue_size gauge",
    _size("1.2e+06", 'data_type="metrics",exporter="otlp_grpc/gateway"'),
    _size("0", 'data_type="traces",exporter="otlp_grpc/gateway"'),
    _size("4.8e+08", 'data_type="metrics",exporter="otlp_grpc/gateway_self"'),
    "# TYPE otelcol_exporter_sent_spans counter",
    'otelcol_exporter_sent_spans{exporter="otlp_grpc/gateway"} 17',
    "otelcol_process_uptime_seconds_total 13.5",
    "# EOF",
)

PARITY_TEXTS: Final = {
    "realistic-edge-scrape": FULL_EXPOSITION,
    "unlabelled-pair": _text(_sample("otelcol_exporter_queue_size", "5"), _capacity("10", "")),
    "two-queues": _text(
        _size("10", GATEWAY), _capacity("100", GATEWAY), _size("90", SELF), _capacity("100", SELF)
    ),
    "empty": "",
    "no-queue-metrics": _text(_sample("otelcol_process_uptime_seconds_total", "1")),
    "capacity-zero": _text(_size("5"), _capacity("0")),
    "capacity-negative": _text(_size("5"), _capacity("-3")),
    "size-negative": _text(_size("-5"), _capacity("10")),
    "size-above-capacity": _text(_size("15"), _capacity("10")),
    "nan-size": _text(_size("NaN"), _capacity("10")),
    "inf-capacity": _text(_size("1"), _capacity("+Inf")),
    "neg-inf-size": _text(_size("-Inf"), _capacity("10")),
    "nan-after-good-queue": _text(
        _size("1", SELF), _capacity("2", SELF), _size("nan"), _capacity("9")
    ),
    "crlf": _text(_size("25"), _capacity("100")).replace("\n", "\r\n"),
    "comments-and-blanks": _text("# HELP x y", "", _size("25"), "   ", _capacity("100"), "# EOF"),
    "indented": _text(f"   {_size('25')}", f"\t{_capacity('100')}"),
    "trailing-timestamp": _text(_size("25 1700000000000"), _capacity("100 1700000000000")),
    "value-with-exemplar-comment": _text(_size('25 # {trace_id="a"} 1'), _capacity("100")),
    "label-value-with-a-space": _text(
        _size("25", 'exporter="a b"'), _capacity("100", 'exporter="a b"')
    ),
    "duplicate-series": _text(_size("1"), _size("7"), _capacity("10"), _capacity("20")),
    "unparseable-value": _text(_size("abc"), _capacity("10")),
    "single-field-line": _text("otelcol_exporter_queue_size", _size("5"), _capacity("10")),
    "hex-value": _text(_size("0x10"), _capacity("100")),
    "overflowing-value": _text(_size("1e400"), _capacity("100")),
    "similar-names": _text(
        _sample("otelcol_exporter_queue_size_total", "9", GATEWAY), _size("1"), _capacity("2")
    ),
    "fraction-one-third": _queue(1, 3),
    "fraction-two-thirds": _queue(2, 3),
    "just-under-warning": _queue(0.4999999999999999, 1),
    "warning": _queue(0.5, 1),
    "just-under-critical": _queue(0.7999999999999999, 1),
    "critical": _queue(0.8, 1),
    "full": _queue(1, 1),
}


WATCHABLE: Final = [name for name, text in PARITY_TEXTS.items() if _python_series(text)]


class TestParityWithTheWatcher:
    @pytest.mark.parametrize("name", PARITY_TEXTS)
    def test_the_queues_are_the_ones_the_watcher_reads(self, run_lua: RunLua, name: str) -> None:
        text = PARITY_TEXTS[name]
        expected = _python_series(text)

        assert _lua_series(run_lua, text) == expected

    @pytest.mark.parametrize("name", PARITY_TEXTS)
    def test_the_fill_is_the_one_the_watcher_computes_unrounded(
        self, run_lua: RunLua, name: str
    ) -> None:
        text = PARITY_TEXTS[name]

        assert _lua_max_fill(run_lua, text) == _python_max_fill(text)

    @pytest.mark.parametrize("name", WATCHABLE)
    def test_the_level_is_the_one_the_watcher_notifies_for(
        self, run_lua: RunLua, tmp_path: Path, name: str
    ) -> None:
        text = PARITY_TEXTS[name]
        script = """
local edge = dofile(DATA.edge)
print(encode(edge.fill_level(edge.max_fill(edge.queue_series(DATA.text)))))
"""

        level = run_lua(script, {"edge": EDGE, "text": text})

        assert level == _watch_run(tmp_path, [(0.0, text)]).notified["queue_fill"]

    def test_every_exporters_queue_counts_and_the_fullest_one_wins(self, run_lua: RunLua) -> None:
        text = _text(
            _size("10", GATEWAY),
            _capacity("100", GATEWAY),
            _size("90", SELF),
            _capacity("100", SELF),
        )

        assert _lua_max_fill(run_lua, text) == 0.9
        assert _summary(run_lua, text)["level"] == "critical"

    def test_the_thresholds_and_level_names_are_the_watchers(self, run_lua: RunLua) -> None:
        script = """
local edge = dofile(DATA.edge)
print(encode({ edge.WARNING_FILL, edge.CRITICAL_FILL, edge.LEVELS }))
"""

        warning, critical, levels = cast("list[object]", run_lua(script, {"edge": EDGE}))

        assert warning == watch.WARNING_FILL
        assert critical == watch.CRITICAL_FILL
        assert levels == list(watch.LEVELS)

    @pytest.mark.parametrize(
        ("size", "capacity"),
        [(1, 3), (2, 3), (7, 9), (123456789, 987654321), (1, 7), (6, 7)],
    )
    def test_the_percentage_shown_is_the_one_the_smoke_check_prints(
        self, run_lua: RunLua, size: int, capacity: int
    ) -> None:
        text = _queue(size, capacity)

        shown = _summary(run_lua, text)["percent"]

        assert shown == smoke.MetricsSnapshot.parse(text).max_queue_percent()

    def test_a_percentage_ending_in_one_half_rounds_up_unlike_the_smoke_checks_even_rounding(
        self, run_lua: RunLua
    ) -> None:
        text = _queue(125, 1000)

        assert _summary(run_lua, text)["percent"] == 13
        assert smoke.MetricsSnapshot.parse(text).max_queue_percent() == 12


class _ScriptedHttp:
    def __init__(self, bodies: Iterator[str]) -> None:
        self.bodies = bodies

    def get(self, url: str) -> str:
        assert url == smoke.METRICS_URL
        return next(self.bodies)


class _AcceptingSystem:
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(arguments, 0, "", "")


@dataclass(frozen=True)
class _Recorded:
    document: Doc

    @property
    def notified(self) -> dict[str, str]:
        return cast("dict[str, str]", self.document["notified"])


def _watch_run(
    tmp_path: Path, runs: list[tuple[float, str]], *, free: int | None = PLENTY
) -> _Recorded:
    """Run the real watcher once per (clock, body) and return what it last wrote to watch.json."""
    clock = iter([moment for moment, _ in runs])
    bodies = iter([body for _, body in runs])
    state_path = tmp_path / "otelbox" / "watch.json"
    for _ in runs:
        runner = watch.Watch(
            _ScriptedHttp(bodies),
            _AcceptingSystem(),
            storage_dir=tmp_path,
            state_path=state_path,
            clock=lambda: next(clock),
            disk_free=lambda _path: free,
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
        assert runner.run() == 0
    return _Recorded(cast("Doc", json.loads(state_path.read_text(encoding="utf-8"))))


WATCHER_CLOCK: Final = 1800.0
FRESH: Final = 60.0


def _stamped(notified: object, last_run: float = WATCHER_CLOCK) -> Doc:
    return {"last_run": last_run, "notified": notified}


def _just_after(document: Doc, seconds: float = FRESH) -> float:
    return cast("float", document["last_run"]) + seconds


class TestWatchAlerts:
    @staticmethod
    def _alerts(run_lua: RunLua, document: object, now: float | None) -> dict[str, str]:
        script = """
local edge = dofile(DATA.edge)
print(encode(edge.watch_alerts(DATA.document, DATA.now)))
"""
        result = run_lua(script, {"edge": EDGE, "document": document, "now": now})
        return {} if result == [] else cast("dict[str, str]", result)

    def _fresh(self, run_lua: RunLua, notified: object) -> dict[str, str]:
        return self._alerts(run_lua, _stamped(notified), WATCHER_CLOCK + FRESH)

    def test_every_condition_with_a_level_the_watcher_accepts_is_returned(
        self, run_lua: RunLua
    ) -> None:
        document = {"queue_fill": "warning", "stall": "critical", "disk": "ok"}

        assert self._fresh(run_lua, document) == {
            "queue_fill": "warning",
            "stall": "critical",
            "disk": "ok",
        }

    @pytest.mark.parametrize(
        "level",
        ["bogus", "WARNING", "Warning", "", " ok", 3, 0, True, False, [], {}, ["ok"]],
        ids=repr,
    )
    def test_a_level_the_watcher_would_reject_is_dropped(
        self, run_lua: RunLua, level: object
    ) -> None:
        assert self._fresh(run_lua, {"stall": level, "disk": "warning"}) == {"disk": "warning"}

    @pytest.mark.parametrize(
        "document",
        [
            pytest.param(None, id="nil"),
            pytest.param("watch.json", id="string"),
            pytest.param(7, id="number"),
            pytest.param(True, id="boolean"),
            pytest.param([], id="empty-array"),
            pytest.param(["notified"], id="array"),
            pytest.param({}, id="empty-object"),
            pytest.param({"last_run": WATCHER_CLOCK, "drains": {}}, id="no-notified"),
            pytest.param(_stamped(None), id="notified-null"),
            pytest.param(_stamped("disk"), id="notified-string"),
            pytest.param(_stamped(3), id="notified-number"),
            pytest.param(_stamped(["warning", "critical"]), id="notified-array"),
            pytest.param(_stamped([]), id="notified-empty-array"),
            pytest.param(_stamped({}), id="notified-empty-object"),
        ],
    )
    def test_anything_unreadable_yields_no_alerts(self, run_lua: RunLua, document: object) -> None:
        assert self._alerts(run_lua, document, WATCHER_CLOCK + FRESH) == {}

    def test_other_fields_of_the_document_are_ignored(self, run_lua: RunLua) -> None:
        document = {
            "last_run": WATCHER_CLOCK,
            "drains": {"traces": {"sent": 3, "since": 1.0}},
            "notified": {"disk": "warning"},
        }

        assert self._alerts(run_lua, document, WATCHER_CLOCK + FRESH) == {"disk": "warning"}

    def test_the_age_limit_is_the_watchers_observation_gap(self, run_lua: RunLua) -> None:
        script = "local edge = dofile(DATA.edge)\nprint(encode(edge.WATCH_MAX_AGE))"

        assert run_lua(script, {"edge": EDGE}) == watch.OBSERVATION_GAP_SECONDS

    @pytest.mark.parametrize(
        ("age", "kept"),
        [
            pytest.param(0, True, id="same-instant"),
            pytest.param(watch.OBSERVATION_GAP_SECONDS - 1, True, id="just-inside"),
            pytest.param(watch.OBSERVATION_GAP_SECONDS, True, id="exactly-the-limit"),
            pytest.param(watch.OBSERVATION_GAP_SECONDS + 1, False, id="just-outside"),
            pytest.param(watch.OBSERVATION_GAP_SECONDS + 0.5, False, id="half-second-outside"),
            pytest.param(3600, False, id="an-hour-old"),
            pytest.param(-5, True, id="last-run-in-the-future"),
        ],
    )
    def test_verdicts_older_than_the_watchers_observation_gap_are_dropped(
        self, run_lua: RunLua, age: float, *, kept: bool
    ) -> None:
        alerts = self._alerts(
            run_lua, _stamped({"stall": "warning", "disk": "critical"}), WATCHER_CLOCK + age
        )

        assert alerts == ({"stall": "warning", "disk": "critical"} if kept else {})

    @pytest.mark.parametrize(
        "last_run",
        [
            pytest.param(None, id="null"),
            pytest.param("1800.0", id="numeric-string"),
            pytest.param("yesterday", id="string"),
            pytest.param(True, id="boolean"),
            pytest.param([], id="array"),
            pytest.param({}, id="object"),
        ],
    )
    def test_a_missing_or_non_numeric_last_run_yields_no_alerts(
        self, run_lua: RunLua, last_run: object
    ) -> None:
        document = _stamped({"stall": "warning"}, cast("float", last_run))

        assert self._alerts(run_lua, document, WATCHER_CLOCK + FRESH) == {}

    def test_an_absent_last_run_yields_no_alerts(self, run_lua: RunLua) -> None:
        document = {"notified": {"stall": "warning"}}

        assert self._alerts(run_lua, document, WATCHER_CLOCK + FRESH) == {}

    def test_a_missing_now_yields_no_alerts(self, run_lua: RunLua) -> None:
        assert self._alerts(run_lua, _stamped({"stall": "warning"}), None) == {}

    def test_a_now_that_is_not_a_number_yields_no_alerts(self, run_lua: RunLua) -> None:
        script = """
local edge = dofile(DATA.edge)
print(encode({
  edge.watch_alerts(DATA.document, "1860"),
  edge.watch_alerts(DATA.document, true),
}))
"""

        result = run_lua(script, {"edge": EDGE, "document": _stamped({"stall": "warning"})})

        assert result == [[], []]

    @pytest.mark.parametrize(
        "notified",
        [
            {"queue_fill": "warning", "stall": "ok", "disk": "ok"},
            {"queue_fill": "critical", "stall": "bogus", "disk": "warning"},
            {"queue_fill": "ok", "stall": 1, "disk": None, "other": "critical"},
            {"queue_fill": ["warning"], "stall": {"x": "ok"}},
            {"stall": "critical"},
        ],
    )
    def test_agrees_with_what_the_watcher_loads_from_the_same_document(
        self, run_lua: RunLua, tmp_path: Path, notified: dict[str, object]
    ) -> None:
        path = tmp_path / "watch.json"
        document = _stamped(notified)
        path.write_text(json.dumps(document), encoding="utf-8")

        loaded = watch.WatchState.load(path).notified

        assert self._alerts(run_lua, document, _just_after(document)) == loaded

    def test_reads_what_the_watcher_writes(self, run_lua: RunLua, tmp_path: Path) -> None:
        result = _watch_run(tmp_path, [(0.0, FULL_EXPOSITION)])

        assert self._alerts(run_lua, result.document, _just_after(result.document)) == (
            result.notified
        )
        assert set(result.notified) == {"queue_fill", "stall", "disk"}

    def test_the_watchers_own_last_run_is_what_the_age_is_measured_from(
        self, run_lua: RunLua, tmp_path: Path
    ) -> None:
        result = _watch_run(tmp_path, [(0.0, FULL_EXPOSITION), (500.0, FULL_EXPOSITION)])
        limit = float(watch.OBSERVATION_GAP_SECONDS)

        inside = self._alerts(run_lua, result.document, 500.0 + limit)
        outside = self._alerts(run_lua, result.document, 500.0 + limit + 1)

        assert inside == result.notified
        assert outside == {}


STUCK_BODY: Final = _text(
    _size("1000", GATEWAY),
    _capacity("4294967296", GATEWAY),
    'otelcol_exporter_sent_metric_points{exporter="otlp_grpc/gateway"} 12',
)


def _stuck_runs() -> list[tuple[float, str]]:
    ten_minutes = 10 * 60
    return [(float(moment), STUCK_BODY) for moment in range(0, 3 * ten_minutes + 1, ten_minutes)]


def _summary_from_document(
    run_lua: RunLua, text: str, document: Doc, *, seconds_after: float = FRESH
) -> Doc:
    script = """
local edge = dofile(DATA.edge)
print(encode(edge.summarise(DATA.text, edge.watch_alerts(DATA.document, DATA.now))))
"""
    now = _just_after(document, seconds_after)
    return cast(
        "Doc", run_lua(script, {"edge": EDGE, "text": text, "document": document, "now": now})
    )


class TestSummarise:
    def test_an_edge_that_did_not_answer_is_down(self, run_lua: RunLua) -> None:
        script = "local edge = dofile(DATA.edge)\nprint(encode(edge.summarise(nil, DATA.alerts)))"

        result = run_lua(script, {"edge": EDGE, "alerts": {"stall": "critical"}})

        assert result == {"state": "down"}

    def test_an_edge_that_did_not_answer_is_down_without_alerts_too(self, run_lua: RunLua) -> None:
        script = "local edge = dofile(DATA.edge)\nprint(encode(edge.summarise(nil, nil)))"

        assert run_lua(script, {"edge": EDGE}) == {"state": "down"}

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param("", id="empty-body"),
            pytest.param(
                _text(_sample("otelcol_process_uptime_seconds_total", "1")), id="no-queue"
            ),
            pytest.param(_text(_size("5")), id="size-only"),
            pytest.param(_text(_size("5"), _capacity("0")), id="zero-capacity"),
            pytest.param(_text(_size("NaN"), _capacity("10")), id="nan-size"),
            pytest.param(_text(_size("5"), _capacity("+Inf")), id="infinite-capacity"),
            pytest.param("<html>502 Bad Gateway</html>", id="not-metrics"),
        ],
    )
    def test_an_answer_without_a_finite_queue_is_unknown_not_ok(
        self, run_lua: RunLua, body: str
    ) -> None:
        assert _summary(run_lua, body, {"stall": "critical"}) == {"state": "unknown"}

    def test_an_answer_that_is_not_text_is_unknown(self, run_lua: RunLua) -> None:
        script = "local edge = dofile(DATA.edge)\nprint(encode(edge.summarise(42, {})))"

        assert run_lua(script, {"edge": EDGE}) == {"state": "unknown"}

    def test_a_healthy_edge_shows_the_fill_and_no_marker(self, run_lua: RunLua) -> None:
        assert _summary(run_lua, _queue(370, 1000), {}) == {
            "state": "ok",
            "percent": 37,
            "level": "ok",
            "markers": [],
        }

    def test_the_fullest_queue_sets_the_percentage(self, run_lua: RunLua) -> None:
        assert _summary(run_lua, FULL_EXPOSITION, {})["percent"] == 89

    @pytest.mark.parametrize(
        ("size", "capacity", "percent", "level"),
        [
            pytest.param(0, 1000, 0, "ok", id="empty"),
            pytest.param(1, 256, 0, "ok", id="rounds-down"),
            pytest.param(7, 16, 44, "ok", id="rounds-up"),
            pytest.param(1, 8, 13, "ok", id="half-rounds-up"),
            pytest.param(3, 8, 38, "ok", id="half-rounds-up-again"),
            pytest.param(255, 256, 100, "critical", id="almost-full"),
            pytest.param(1000, 1000, 100, "critical", id="full"),
            pytest.param(1500, 1000, 150, "critical", id="over-full"),
            pytest.param(9, 1, 900, "critical", id="below-the-display-bound"),
            pytest.param(10, 1, 1000, "critical", id="at-the-display-bound"),
            pytest.param(11, 1, 1000, "critical", id="just-above-the-display-bound"),
            pytest.param(1e300, 1, 1000, "critical", id="astronomical"),
            pytest.param(-1, 1, -100, "ok", id="negative-size"),
            pytest.param(-10, 1, -1000, "ok", id="at-the-negative-bound"),
            pytest.param(-11, 1, -1000, "ok", id="just-below-the-negative-bound"),
            pytest.param(-1e300, 1, -1000, "ok", id="astronomically-negative"),
            pytest.param(4999, 10000, 50, "ok", id="shows-fifty-but-is-below-warning"),
            pytest.param(5000, 10000, 50, "warning", id="warning-boundary"),
            pytest.param(7999, 10000, 80, "warning", id="shows-eighty-but-is-below-critical"),
            pytest.param(8000, 10000, 80, "critical", id="critical-boundary"),
        ],
    )
    def test_the_percentage_is_rounded_and_bounded_but_the_level_uses_the_unrounded_fill(
        self, run_lua: RunLua, size: float, capacity: float, percent: int, level: str
    ) -> None:
        result = _summary(run_lua, _queue(size, capacity), {})

        assert (result["percent"], result["level"]) == (percent, level)

    @pytest.mark.parametrize("size", [0.5, 7, 1e16, 1e300, -1e300, 1e18])
    def test_the_percentage_is_always_a_lua_integer(self, run_lua: RunLua, size: float) -> None:
        script = """
local edge = dofile(DATA.edge)
print(encode(math.type(edge.summarise(DATA.text, {}).percent)))
"""

        assert run_lua(script, {"edge": EDGE, "text": _queue(size, 1)}) == "integer"

    @pytest.mark.parametrize(
        ("alerts", "markers"),
        [
            pytest.param({"stall": "warning"}, ["stall"], id="stall"),
            pytest.param({"disk": "warning"}, ["disk"], id="disk"),
            pytest.param({"disk": "warning", "stall": "warning"}, ["stall", "disk"], id="both"),
            pytest.param({"stall": "critical", "disk": "critical"}, ["stall", "disk"], id="crit"),
        ],
    )
    def test_markers_come_in_display_order_whatever_order_the_alerts_were_recorded(
        self, run_lua: RunLua, alerts: dict[str, str], markers: list[str]
    ) -> None:
        assert _summary(run_lua, _queue(1, 10), alerts)["markers"] == markers

    @pytest.mark.parametrize(
        ("fill", "alerts", "level"),
        [
            pytest.param(0.1, {"stall": "warning"}, "warning", id="stall-lifts-ok"),
            pytest.param(0.1, {"disk": "warning"}, "warning", id="disk-lifts-ok"),
            pytest.param(0.1, {"disk": "critical"}, "critical", id="critical-marker-lifts-ok"),
            pytest.param(0.6, {"disk": "warning"}, "warning", id="warning-keeps-warning"),
            pytest.param(0.6, {"stall": "critical"}, "critical", id="critical-lifts-warning"),
            pytest.param(0.9, {"stall": "warning"}, "critical", id="warning-never-lowers-critical"),
            pytest.param(0.9, {"stall": "critical"}, "critical", id="critical-stays-critical"),
            pytest.param(0.1, {"stall": "warning", "disk": "critical"}, "critical", id="strongest"),
        ],
    )
    def test_the_level_is_the_strongest_of_the_fill_and_the_markers(
        self, run_lua: RunLua, fill: float, alerts: dict[str, str], level: str
    ) -> None:
        assert _summary(run_lua, _queue(fill, 1), alerts)["level"] == level

    @pytest.mark.parametrize(
        "alerts",
        [
            pytest.param({"queue_fill": "critical"}, id="queue-fill-critical"),
            pytest.param({"queue_fill": "warning"}, id="queue-fill-warning"),
            pytest.param({"unrelated": "critical"}, id="unknown-condition"),
            pytest.param({"stall": "ok", "disk": "ok"}, id="ok-alerts"),
            pytest.param({}, id="empty"),
            pytest.param(None, id="nil"),
        ],
    )
    def test_alerts_that_are_not_stall_or_disk_or_are_ok_add_no_marker_and_no_level(
        self, run_lua: RunLua, alerts: dict[str, str] | None
    ) -> None:
        result = _summary(run_lua, _queue(1, 10), alerts)

        assert result["markers"] == []
        assert result["level"] == "ok"

    def test_the_live_fill_outranks_a_stale_queue_fill_alert(self, run_lua: RunLua) -> None:
        result = _summary(run_lua, _queue(9, 10), {"queue_fill": "ok", "stall": "warning"})

        assert result == {"state": "ok", "percent": 90, "level": "critical", "markers": ["stall"]}

    def test_the_result_carries_exactly_the_fields_the_renderer_reads(
        self, run_lua: RunLua
    ) -> None:
        result = _summary(run_lua, _queue(1, 10), {})

        assert set(result) == {"state", "percent", "level", "markers"}

    def test_the_markers_follow_what_the_real_watcher_recorded(
        self, run_lua: RunLua, tmp_path: Path
    ) -> None:
        recorded = _watch_run(tmp_path, _stuck_runs(), free=0)

        result = _summary_from_document(run_lua, STUCK_BODY, recorded.document)

        assert recorded.notified == {"queue_fill": "ok", "stall": "warning", "disk": "warning"}
        assert result == {
            "state": "ok",
            "percent": 0,
            "level": "warning",
            "markers": ["stall", "disk"],
        }

    def test_a_stall_that_cleared_leaves_no_marker(self, run_lua: RunLua, tmp_path: Path) -> None:
        draining = STUCK_BODY.replace("} 12", "} 13")
        recorded = _watch_run(tmp_path, [*_stuck_runs(), (40 * 60.0, draining)])

        result = _summary_from_document(run_lua, draining, recorded.document)

        assert recorded.notified["stall"] == "ok"
        assert result["markers"] == []
        assert result["level"] == "ok"

    def test_the_markers_of_a_watcher_that_stopped_an_hour_ago_are_not_shown(
        self, run_lua: RunLua, tmp_path: Path
    ) -> None:
        recorded = _watch_run(tmp_path, _stuck_runs(), free=0)
        assert recorded.document["last_run"] == WATCHER_CLOCK
        assert recorded.notified == {"queue_fill": "ok", "stall": "warning", "disk": "warning"}

        result = _summary_from_document(run_lua, STUCK_BODY, recorded.document, seconds_after=3600)

        assert result["markers"] == []
        assert result["level"] == "ok"

    @pytest.mark.parametrize(
        ("seconds_after", "markers"),
        [
            (watch.OBSERVATION_GAP_SECONDS, ["stall", "disk"]),
            (watch.OBSERVATION_GAP_SECONDS + 1, []),
        ],
        ids=["at-the-limit", "one-second-past"],
    )
    def test_the_markers_vanish_one_second_after_the_observation_gap(
        self, run_lua: RunLua, tmp_path: Path, seconds_after: int, markers: list[str]
    ) -> None:
        recorded = _watch_run(tmp_path, _stuck_runs(), free=0)

        result = _summary_from_document(
            run_lua, STUCK_BODY, recorded.document, seconds_after=seconds_after
        )

        assert result["markers"] == markers
        assert result["level"] == ("warning" if markers else "ok")

    def test_stale_verdicts_do_not_hide_a_full_queue(self, run_lua: RunLua, tmp_path: Path) -> None:
        recorded = _watch_run(tmp_path, _stuck_runs(), free=0)

        result = _summary_from_document(
            run_lua, _queue(9, 10), recorded.document, seconds_after=3600
        )

        assert result == {"state": "ok", "percent": 90, "level": "critical", "markers": []}


class TestDeclared:
    BAR: Final = {
        "position": "top",
        "height": 32,
        "items": ["ws.1", "front_app", "clock", "battery", "ram", "cpu", "edge", "input"],
    }

    @staticmethod
    def _declared(run_lua: RunLua, bar: object, item: object = "edge") -> bool:
        script = "local edge = dofile(DATA.edge)\nprint(encode(edge.declared(DATA.bar, DATA.item)))"
        return cast("bool", run_lua(script, {"edge": EDGE, "bar": bar, "item": item}))

    def test_an_item_the_bar_lists_is_declared(self, run_lua: RunLua) -> None:
        assert self._declared(run_lua, self.BAR) is True

    def test_an_item_the_bar_does_not_list_is_not(self, run_lua: RunLua) -> None:
        bar = {**self.BAR, "items": ["ws.1", "clock", "cpu", "input"]}

        assert self._declared(run_lua, bar) is False

    def test_the_item_name_must_match_exactly(self, run_lua: RunLua) -> None:
        for name in ("edge2", "xedge", "Edge", "EDGE", "edg", "edge "):
            bar = {"items": ["clock", name]}

            assert self._declared(run_lua, bar) is False, name

    def test_any_item_name_can_be_asked_for(self, run_lua: RunLua) -> None:
        assert self._declared(run_lua, self.BAR, "cpu") is True
        assert self._declared(run_lua, self.BAR, "ws.9") is False

    def test_an_item_listed_among_non_strings_is_still_found(self, run_lua: RunLua) -> None:
        assert self._declared(run_lua, {"items": [1, "edge"]}) is True

    @pytest.mark.parametrize(
        "bar",
        [
            pytest.param({"items": []}, id="no-items"),
            pytest.param({}, id="no-items-key"),
            pytest.param({"position": "top"}, id="other-keys-only"),
            pytest.param({"items": "edge"}, id="items-string"),
            pytest.param({"items": 1}, id="items-number"),
            pytest.param({"items": None}, id="items-null"),
            pytest.param({"items": {"edge": True}}, id="items-object"),
            pytest.param({"items": {"1": "clock"}}, id="items-object-with-numeric-key"),
            pytest.param(["edge"], id="bar-is-an-array-of-items"),
            pytest.param("edge", id="bar-string"),
            pytest.param(7, id="bar-number"),
            pytest.param(True, id="bar-boolean"),
            pytest.param(None, id="bar-nil"),
        ],
    )
    def test_anything_that_is_not_a_list_of_items_declares_nothing(
        self, run_lua: RunLua, bar: object
    ) -> None:
        assert self._declared(run_lua, bar) is False


class TestPipelineIntoTheRenderer:
    @staticmethod
    def _label(run_lua: RunLua, text: str | None, alerts: object = None) -> list[str]:
        script = """
local edge = dofile(DATA.edge)
local render = dofile(DATA.render)
print(encode(render.edge_args(edge.summarise(DATA.text, DATA.alerts))))
"""
        data = {"edge": EDGE, "render": RENDER, "text": text, "alerts": alerts}
        return cast("list[str]", run_lua(script, data))

    def test_a_scrape_becomes_the_text_of_the_edge_item(self, run_lua: RunLua) -> None:
        args = self._label(run_lua, _queue(620, 1000), {"disk": "warning", "stall": "warning"})

        assert "label=62% stall disk" in args

    @pytest.mark.parametrize(
        ("size", "capacity"),
        [
            pytest.param(1e16, 1, id="percent-fits-an-integer"),
            pytest.param(1e18, 1, id="percent-exceeds-an-integer"),
            pytest.param(1e300, 1, id="percent-is-astronomical"),
            pytest.param(-1e18, 1, id="negative-percent-exceeds-an-integer"),
            pytest.param(-1e300, 1, id="negative-percent-is-astronomical"),
            pytest.param(1, 1e-300, id="tiny-capacity"),
        ],
    )
    def test_a_wildly_large_fill_still_renders(
        self, run_lua: RunLua, size: float, capacity: float
    ) -> None:
        args = self._label(run_lua, _queue(size, capacity))

        assert args[:2] == ["--set", "edge"]

    @pytest.mark.parametrize(
        ("size", "label"), [(1e300, "label=1000%"), (-1e300, "label=-1000%"), (1.5, "label=150%")]
    )
    def test_the_label_shows_the_bounded_percentage(
        self, run_lua: RunLua, size: float, label: str
    ) -> None:
        assert label in self._label(run_lua, _queue(size, 1))

    def test_no_answer_becomes_the_cross(self, run_lua: RunLua) -> None:
        assert "label=✕" in self._label(run_lua, None)

    def test_an_answer_without_a_queue_becomes_dashes(self, run_lua: RunLua) -> None:
        assert "label=--" in self._label(run_lua, "")
