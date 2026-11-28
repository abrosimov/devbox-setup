"""The bar's edge item reads the pinned otelbox edge's real :8888/metrics as the watcher does.

The pinned release runs the repository's edge.yaml; its own exposition text is scraped once and
handed to scripts/otelbox_edge (the parser behind the macOS notification) and to the pure-Lua
bar_edge module that Hammerspoon runs. A fake exposition cannot show that the metric names, label
sets and number formats the binary really emits are the ones both readers expect.

Linux only, like the Langfuse handoff test: it shares that test's pinned-asset download, its
fixed-port check (edge.yaml fixes :8888, so there is no free port to choose) and its skip rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from engines import unusable
from langfuse_handoff import (
    EDGE,
    EDGE_START_SECONDS,
    Edge,
    EdgeUnavailableError,
    Recipient,
    Tls,
    deadline_wait,
    free_port,
    issue_loopback_tls,
    pinned_edge_binary,
)
from otelbox_edge import smoke
from otelbox_edge_bar import check_bar_agrees_with_watcher, find_lua, why_not_ready
from throwaway import ThrowawayHome

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def edge_binary(request: pytest.FixtureRequest) -> Path:
    cache = request.config.cache
    if cache is None:
        unusable(EDGE, "pytest's cache provider is disabled; nowhere to keep the release asset")
    try:
        return pinned_edge_binary(cache.mkdir("otelbox-edge"))
    except EdgeUnavailableError as error:
        unusable(EDGE, str(error))


@pytest.fixture(scope="session")
def lua() -> str:
    located = find_lua()
    if located is None:
        unusable(EDGE, "no Lua interpreter on PATH (lua5.4 on Ubuntu); the bar module cannot run")
    return located


@pytest.fixture(scope="session")
def tls(tmp_path_factory: pytest.TempPathFactory) -> Tls:
    return issue_loopback_tls(tmp_path_factory.mktemp("tls"))


def scrape() -> str | None:
    try:
        return smoke.LoopbackHttpClient().get(smoke.METRICS_URL)
    except smoke.ProbeError:
        return None


def test_the_bar_reads_the_real_edges_queues_as_the_watcher_does(
    edge_binary: Path, lua: str, tls: Tls, tmp_path: Path
) -> None:
    home = ThrowawayHome.create(tmp_path / "home")
    recipient = Recipient(port=free_port(), tls=tls)
    edge = Edge(edge_binary, home.path, recipient.endpoint, tls)
    scraped: list[str] = []
    last_reason = ["no scrape answered"]

    def has_every_queue() -> bool:
        text = scrape()
        if text is None:
            return False
        reason = why_not_ready(text)
        if reason is not None:
            last_reason[0] = reason
            return False
        scraped.append(text)
        return True

    recipient.start()
    try:
        edge.start()
        try:
            deadline_wait(
                has_every_queue, EDGE_START_SECONDS, "the edge to report all four exporter queues"
            )
        except TimeoutError as error:
            pytest.fail(f"{error}\nlast contract error: {last_reason[0]}\n{edge.log_tail()}")
    finally:
        edge.stop()
        recipient.stop()

    check_bar_agrees_with_watcher(lua, scraped[0], tmp_path)
