"""Durable Langfuse OTLP exporter tests without a live endpoint."""

from __future__ import annotations

import os
import time
import urllib.error
from email.message import Message
from typing import TYPE_CHECKING
from uuid import uuid4

import langfuse
import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from vendor import durable_otel_exporter as spool

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


def spans_in(batch: bytes) -> int:
    request = ExportTraceServiceRequest.FromString(batch)
    return sum(
        len(scope.spans) for resource in request.resource_spans for scope in resource.scope_spans
    )


OVERSIZED_PAYLOAD = "x" * 4096


def export_with_one_oversized_span(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[spool.DurableSpoolExporter, list[ReadableSpan]]:
    memory = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory))
    tracer = provider.get_tracer("devbox-langfuse-test")
    for index in range(3):
        with tracer.start_as_current_span(f"ordinary-{index}", attributes={"session.id": "s-1"}):
            pass
    oversized = {"session.id": "s-1", "payload": OVERSIZED_PAYLOAD}
    with tracer.start_as_current_span("oversized", attributes=oversized):
        pass
    spans = list(memory.get_finished_spans())
    monkeypatch.setattr(spool, "MAX_BATCH_BYTES", len(spool._encode(spans[:1])) * 2)
    exporter = spool.DurableSpoolExporter()
    assert exporter.export(spans) is SpanExportResult.SUCCESS
    return exporter, spans


def test_an_oversized_span_is_quarantined_whole_and_the_rest_is_committed(
    monkeypatch: pytest.MonkeyPatch,
    spool_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exporter, spans = export_with_one_oversized_span(monkeypatch)
    assert exporter.force_flush()

    exporter.commit()

    committed = [path.read_bytes() for path in spool_home.glob("*.otlp")]
    assert sum(spans_in(batch) for batch in committed) == 3
    (quarantined,) = spool.quarantine_directory().glob("*.otlp")
    assert quarantined.read_bytes() == spool._encode(spans[3:])
    error = capsys.readouterr().err
    assert "session s-1" in error
    assert f"is {len(spool._encode(spans[3:]))} bytes" in error
    assert f"{spool.MAX_BATCH_BYTES}-byte batch cap" in error
    assert str(quarantined) in error
    hook_log = (spool_home.parent / "langfuse_hook.log").read_text(encoding="utf-8")
    assert error.strip() in hook_log


@pytest.mark.usefixtures("spool_home")
def test_a_discarded_firing_quarantines_no_oversized_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter, _ = export_with_one_oversized_span(monkeypatch)

    exporter.discard()
    exporter.commit()

    assert not spool.quarantine_directory().exists()


@pytest.mark.usefixtures("spool_home")
def test_one_export_is_split_into_batches_within_the_receiver_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory))
    tracer = provider.get_tracer("devbox-langfuse-test")
    for index in range(40):
        with tracer.start_as_current_span(f"durable-test-{index}"):
            pass
    spans = memory.get_finished_spans()
    envelope = 5 * len(spool._encode(spans[:1]))
    monkeypatch.setattr(spool, "MAX_BATCH_BYTES", envelope)
    exporter = spool.DurableSpoolExporter()

    assert exporter.export(spans) is SpanExportResult.SUCCESS

    batches = [path.read_bytes() for path in exporter.staging.glob("*.otlp")]
    assert len(batches) > 1
    assert all(len(batch) <= envelope for batch in batches)
    assert sum(spans_in(batch) for batch in batches) == len(spans)


def test_staging_of_a_concurrent_hook_counts_towards_the_spool_cap(
    monkeypatch: pytest.MonkeyPatch,
    spool_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    concurrent = spool.DurableSpoolExporter()
    emit_test_span(concurrent)
    staged = sum(path.stat().st_size for path in concurrent.staging.glob("*.otlp"))
    monkeypatch.setenv(spool.SPOOL_MAX_BYTES_ENV, str(staged + staged // 2))
    exporter = spool.DurableSpoolExporter()

    emit_test_span(exporter)
    emit_test_span(exporter)

    assert isinstance(exporter.failed, OSError)
    assert not list(exporter.staging.glob("*.otlp"))
    refusals = capsys.readouterr().err.splitlines()
    assert len(refusals) == 1
    assert f"{spool.SPOOL_MAX_BYTES_ENV}={staged + staged // 2}" in refusals[0]
    assert str(spool_home) in refusals[0]


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
