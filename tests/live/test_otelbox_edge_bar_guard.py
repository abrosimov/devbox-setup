"""The edge-bar check can pass, and can fail for the reasons it exists to catch.

Hermetic: collected with the other guards, so the comparison the live test makes against the real
edge is proven to work on a realistic scrape, without a download or a binary.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

import pytest
from otelbox_edge_bar import (
    BAR_EDGE,
    check_bar_agrees_with_watcher,
    find_lua,
    queues_in,
    read_in_lua,
    why_not_ready,
)

if TYPE_CHECKING:
    from pathlib import Path

GATEWAY: Final = 'data_type="metrics",exporter="otlp_grpc/gateway"'
SELF: Final = 'data_type="metrics",exporter="otlp_grpc/gateway_self"'
LOGS: Final = 'data_type="logs",exporter="otlp_grpc/gateway"'
TRACES: Final = 'data_type="traces",exporter="otlp_grpc/gateway"'
FILL_EXPRESSION: Final = "local fill = q.size / q.capacity"
SIZE: Final = "otelcol_exporter_queue_size"
CAPACITY: Final = "otelcol_exporter_queue_capacity"

CAPACITIES: Final = f"""\
# HELP {CAPACITY} Fixed capacity of the retry queue (in bytes) [alpha]
# TYPE {CAPACITY} gauge
{CAPACITY}{{{GATEWAY}}} 4.294967296e+09
{CAPACITY}{{{LOGS}}} 4.294967296e+09
{CAPACITY}{{{TRACES}}} 4.294967296e+09
{CAPACITY}{{{SELF}}} 5.36870912e+08
"""
SIZES: Final = f"""\
# HELP {SIZE} Current size of the retry queue (in bytes) [alpha]
# TYPE {SIZE} gauge
{SIZE}{{{GATEWAY}}} 0
{SIZE}{{{LOGS}}} 0
{SIZE}{{{TRACES}}} 0
{SIZE}{{{SELF}}} 4.8e+06
"""
OTHER: Final = "otelcol_process_uptime_seconds_total 13.5\n"
SCRAPE: Final = CAPACITIES + SIZES + OTHER


@pytest.fixture
def lua() -> str:
    located = find_lua()
    assert located is not None, "no Lua interpreter on PATH: install `lua5.4` (Ubuntu) or `lua`"
    return located


def test_a_realistic_scrape_is_read_alike_by_the_watcher_and_the_bar(
    lua: str, tmp_path: Path
) -> None:
    check_bar_agrees_with_watcher(lua, SCRAPE, tmp_path)

    assert len(queues_in(SCRAPE)) == 4


def test_a_complete_scrape_is_ready() -> None:
    assert why_not_ready(SCRAPE) is None


@pytest.mark.parametrize(
    ("scrape", "reason"),
    [
        pytest.param("", "no finite exporter queue", id="nothing-yet"),
        pytest.param(OTHER, "no finite exporter queue", id="no-queue-gauges-yet"),
        pytest.param(
            f"{CAPACITY}{{{GATEWAY}}} 4.294967296e+09\n{SIZE}{{{GATEWAY}}} 0\n",
            f"{SIZE} series",
            id="one-of-four-queues",
        ),
        pytest.param(
            f"{CAPACITIES}{SIZE}{{{GATEWAY}}} 0\n", f"{SIZE} series", id="capacities-before-sizes"
        ),
        pytest.param(
            CAPACITIES + SIZES.replace("4.8e+06", "NaN"),
            "no finite exporter queue",
            id="non-finite-size",
        ),
    ],
)
def test_a_scrape_taken_before_every_queue_exists_is_not_ready_and_says_why(
    scrape: str, reason: str
) -> None:
    found = why_not_ready(scrape)

    assert found is not None
    assert reason in found


def _without(text: str, line_start: str) -> str:
    kept = [line for line in text.splitlines() if not line.startswith(line_start)]
    assert len(kept) == len(text.splitlines()) - 1
    return "\n".join(kept) + "\n"


@pytest.mark.parametrize(
    ("scrape", "complaint"),
    [
        pytest.param(
            _without(SCRAPE, f"{SIZE}{{{TRACES}}}"), f"{SIZE} series", id="size-series-missing"
        ),
        pytest.param(
            _without(SCRAPE, f"{CAPACITY}{{{SELF}}}"),
            f"{CAPACITY} series",
            id="capacity-series-missing",
        ),
        pytest.param(
            SCRAPE + f'{SIZE}{{data_type="profiles",exporter="otlp_grpc/gateway"}} 0\n',
            f"{SIZE} series",
            id="extra-pair-without-capacity",
        ),
        pytest.param(
            SCRAPE.replace(GATEWAY, 'data_type="metrics",exporter="otlp_grpc/other"'),
            f"{SIZE} series",
            id="renamed-exporter",
        ),
        pytest.param(
            SCRAPE.replace(f"{{{LOGS}}}", f'{{{LOGS},otel_scope_name="x"}}'),
            "labels other than",
            id="extra-label-key",
        ),
        pytest.param(
            SCRAPE.replace(f"{{{LOGS}}}", '{data_type="logs"}'),
            "labels other than",
            id="exporter-label-missing",
        ),
        pytest.param(
            SCRAPE.replace(f"{SIZE}{{{LOGS}}} 0", f"{SIZE} 0"),
            "labels other than",
            id="unlabelled-series",
        ),
        pytest.param(
            SCRAPE + f"{SIZE}{{{LOGS}}} 1\n", "repeats a (data_type, exporter)", id="repeated-pair"
        ),
    ],
)
def test_a_scrape_off_the_edge_status_contract_fails_the_check(
    lua: str, tmp_path: Path, scrape: str, complaint: str
) -> None:
    with pytest.raises(AssertionError, match=re.escape(complaint)):
        check_bar_agrees_with_watcher(lua, scrape, tmp_path)


@pytest.mark.parametrize(
    "scrape",
    [
        pytest.param("", id="empty"),
        pytest.param("otelcol_process_uptime_seconds_total 13.5\n", id="no-queue-metrics"),
        pytest.param(
            f"otelcol_exporter_queue_size{{{GATEWAY}}} 1\n"
            f"otelcol_exporter_queue_capacity{{{GATEWAY}}} 0\n",
            id="zero-capacity",
        ),
        pytest.param(
            f"otelcol_exporter_queue_size{{{GATEWAY}}} NaN\n"
            f"otelcol_exporter_queue_capacity{{{GATEWAY}}} 10\n",
            id="non-finite-size",
        ),
    ],
)
def test_a_scrape_without_a_finite_queue_fails_the_check(
    lua: str, tmp_path: Path, scrape: str
) -> None:
    with pytest.raises(AssertionError, match="no finite exporter queue"):
        check_bar_agrees_with_watcher(lua, scrape, tmp_path)


def test_a_bar_module_that_misreads_the_fill_fails_the_check_on_the_fill_alone(
    lua: str, tmp_path: Path
) -> None:
    source = BAR_EDGE.read_text(encoding="utf-8")
    assert source.count(FILL_EXPRESSION) == 1
    mutated = tmp_path / "bar_edge.lua"
    mutated.write_text(
        source.replace(FILL_EXPRESSION, "local fill = q.size / (q.capacity + 1)"),
        encoding="utf-8",
    )
    honest = read_in_lua(lua, SCRAPE, tmp_path)
    seeded = read_in_lua(lua, SCRAPE, tmp_path, mutated)

    assert seeded["series"] == honest["series"]
    assert seeded["fill"] != honest["fill"]
    with pytest.raises(AssertionError):
        check_bar_agrees_with_watcher(lua, SCRAPE, tmp_path, mutated)


def test_a_bar_module_that_fails_to_run_reports_the_lua_error(lua: str, tmp_path: Path) -> None:
    broken = tmp_path / "bar_edge.lua"
    broken.write_text("error('boom')\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="boom"):
        read_in_lua(lua, SCRAPE, tmp_path, broken)
