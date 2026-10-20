"""Durable Langfuse OTLP exporter tests without a live endpoint."""

from __future__ import annotations

import urllib.error
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from vendor import durable_otel_exporter as spool

if TYPE_CHECKING:
    from collections.abc import Iterator


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


def test_otel_span_is_fsynced_before_export_ack(spool_home: Path) -> None:
    exporter = spool.DurableSpoolExporter()
    emit_test_span(exporter)
    files = list(spool_home.glob("*.otlp"))
    assert len(files) == 1
    assert files[0].stat().st_size > 0
    assert exporter.failed is None


def test_failure_to_persist_otlp_is_not_acknowledged(
    monkeypatch: pytest.MonkeyPatch, spool_home: Path,
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
    monkeypatch: pytest.MonkeyPatch, spool_home: Path,
) -> None:
    emit_test_span(spool.DurableSpoolExporter())
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
    monkeypatch: pytest.MonkeyPatch, spool_home: Path,
) -> None:
    emit_test_span(spool.DurableSpoolExporter())

    def unavailable(*_args, **_kwargs):
        message = "injected outage"
        raise urllib.error.URLError(message)

    monkeypatch.setattr(spool.urllib.request, "urlopen", unavailable)
    assert spool.drain_spool("http://127.0.0.1:14318") == (0, 1)
    assert len(list(spool_home.glob("*.otlp"))) == 1


def test_langfuse_sdk_can_use_durable_span_exporter(spool_home: Path) -> None:
    langfuse = pytest.importorskip("langfuse")
    exporter = spool.DurableSpoolExporter()
    client = langfuse.Langfuse(
        public_key=f"test-{uuid4().hex}",
        secret_key="test-local-edge-only",
        host="http://127.0.0.1:14318",
        span_exporter=exporter,
    )
    with client.start_as_current_observation(as_type="span", name="sdk-spool-smoke"):
        pass
    client.flush()
    assert list(spool_home.glob("*.otlp"))
    client.shutdown()
