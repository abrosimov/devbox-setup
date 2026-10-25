"""Durable Langfuse OTLP exporter tests without a live endpoint."""

from __future__ import annotations

import os
import time
import urllib.error
from email.message import Message
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

pytest.importorskip("opentelemetry.sdk")

from vendor import durable_otel_exporter as spool

TracerProvider = pytest.importorskip("opentelemetry.sdk.trace").TracerProvider
SimpleSpanProcessor = pytest.importorskip("opentelemetry.sdk.trace.export").SimpleSpanProcessor

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spool_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("CC_LANGFUSE_STATE_DIR", str(tmp_path))
    return tmp_path / "langfuse_otlp_spool"


def emit_test_span(exporter: spool.DurableSpoolExporter) -> None:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    with provider.get_tracer("devbox-langfuse-test").start_as_current_span("durable-test"):
        pass
    assert provider.force_flush()


def spool_test_span() -> None:
    exporter = spool.DurableSpoolExporter()
    emit_test_span(exporter)
    exporter.commit()


@pytest.mark.usefixtures("spool_home")
def test_otel_span_is_fsynced_before_export_ack() -> None:
    exporter = spool.DurableSpoolExporter()
    emit_test_span(exporter)
    staged = list(exporter.staging.glob("*.otlp"))
    assert len(staged) == 1
    assert staged[0].stat().st_size > 0
    assert exporter.failed is None


def test_staged_spans_reach_the_outbox_only_on_commit(spool_home: Path) -> None:
    exporter = spool.DurableSpoolExporter()
    emit_test_span(exporter)
    assert not list(spool_home.glob("*.otlp"))

    exporter.commit()

    assert len(list(spool_home.glob("*.otlp"))) == 1
    assert not exporter.staging.exists()


def test_discarded_exporter_drops_staged_and_later_spans(spool_home: Path) -> None:
    exporter = spool.DurableSpoolExporter()
    emit_test_span(exporter)

    exporter.discard()
    emit_test_span(exporter)
    exporter.commit()

    assert not list(spool_home.rglob("*.otlp"))


@pytest.mark.usefixtures("spool_home")
def test_drain_sweeps_staging_left_by_a_killed_hook() -> None:
    abandoned = spool.DurableSpoolExporter()
    emit_test_span(abandoned)
    live = spool.DurableSpoolExporter()
    emit_test_span(live)
    expired = time.time() - spool.STALE_STAGING_SECONDS - 1
    os.utime(abandoned.staging, (expired, expired))

    assert spool.drain_spool("http://127.0.0.1:14318") == (0, 0)

    assert not abandoned.staging.exists()
    assert live.staging.is_dir()


def test_failure_to_persist_otlp_is_not_acknowledged(
    monkeypatch: pytest.MonkeyPatch,
    spool_home: Path,
) -> None:
    exporter = spool.DurableSpoolExporter()

    def reject_save(*_args, **_kwargs):
        message = "injected outbox disk error"
        raise OSError(message)

    monkeypatch.setattr(spool, "_durable_save", reject_save)
    emit_test_span(exporter)
    assert isinstance(exporter.failed, OSError)
    assert not list(spool_home.glob("*.otlp"))


def test_otel_spool_delivery_removes_payload_after_http_ack(
    monkeypatch: pytest.MonkeyPatch,
    spool_home: Path,
) -> None:
    spool_test_span()
    sent: list[bytes] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def receive(request, timeout):
        assert timeout > 0
        assert request.full_url == "http://127.0.0.1:14318/api/public/otel/v1/traces"
        sent.append(request.data)
        return Response()

    monkeypatch.setattr(spool.urllib.request, "urlopen", receive)
    assert spool.drain_spool("http://127.0.0.1:14318") == (1, 0)
    assert len(sent) == 1
    assert not list(spool_home.glob("*.otlp"))


def test_failed_http_delivery_never_deletes_queued_payload(
    monkeypatch: pytest.MonkeyPatch,
    spool_home: Path,
) -> None:
    spool_test_span()

    def unavailable(*_args, **_kwargs):
        message = "injected outage"
        raise urllib.error.URLError(message)

    monkeypatch.setattr(spool.urllib.request, "urlopen", unavailable)
    assert spool.drain_spool("http://127.0.0.1:14318") == (0, 1)
    assert len(list(spool_home.glob("*.otlp"))) == 1


def queue_payloads(spool_home: Path, count: int) -> list[Path]:
    spool_home.mkdir(parents=True, exist_ok=True)
    paths = [spool_home / f"{index:020d}-{uuid4().hex}.otlp" for index in range(count)]
    for path in paths:
        path.write_bytes(path.name.encode())
    return paths


def reply_per_payload(statuses: dict[bytes, int], sent: list[bytes]):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def receive(request, **_kwargs):
        sent.append(request.data)
        status = statuses.get(request.data, 200)
        if status != 200:
            raise urllib.error.HTTPError(request.full_url, status, "rejected", Message(), None)
        return Response()

    return receive


def test_permanently_rejected_batch_is_quarantined_and_drain_continues(
    monkeypatch: pytest.MonkeyPatch,
    spool_home: Path,
) -> None:
    rejected, accepted = queue_payloads(spool_home, 2)
    sent: list[bytes] = []
    receive = reply_per_payload({rejected.read_bytes(): 400}, sent)
    monkeypatch.setattr(spool.urllib.request, "urlopen", receive)

    assert spool.drain_spool("http://127.0.0.1:14318") == (1, 0)

    assert sent == [rejected.name.encode(), accepted.name.encode()]
    assert not list(spool_home.glob("*.otlp"))
    quarantine = spool_home.parent / "langfuse_otlp_quarantine"
    assert [path.name for path in quarantine.iterdir()] == [rejected.name]


@pytest.mark.parametrize("status", [408, 429, 500, 503])
def test_transiently_rejected_batch_stays_queued_and_stops_the_pass(
    monkeypatch: pytest.MonkeyPatch,
    spool_home: Path,
    status: int,
) -> None:
    oldest, newest = queue_payloads(spool_home, 2)
    sent: list[bytes] = []
    receive = reply_per_payload({oldest.read_bytes(): status}, sent)
    monkeypatch.setattr(spool.urllib.request, "urlopen", receive)

    assert spool.drain_spool("http://127.0.0.1:14318") == (0, 2)

    assert sent == [oldest.name.encode()]
    assert oldest.is_file()
    assert newest.is_file()
    assert not (spool_home.parent / "langfuse_otlp_quarantine").exists()


def test_langfuse_sdk_can_use_durable_span_exporter(spool_home: Path) -> None:
    langfuse = pytest.importorskip("langfuse")
    exporter = spool.DurableSpoolExporter()
    client = langfuse.Langfuse(
        public_key=f"test-{uuid4().hex}",
        secret_key=f"local-{uuid4().hex}",
        host="http://127.0.0.1:14318",
        span_exporter=exporter,
    )
    with client.start_as_current_observation(as_type="span", name="sdk-spool-smoke"):
        pass
    client.flush()
    exporter.commit()
    assert list(spool_home.glob("*.otlp"))
    client.shutdown()
