"""Durable OTLP span outbox for Langfuse's OpenTelemetry SpanExporter API.

The exporter only acknowledges a batch after fsync-backed local persistence.
Delivery to the loopback otelbox edge is a separate retryable operation.
"""
from __future__ import annotations

import os
import shutil
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Sequence

from opentelemetry.exporter.otlp.proto.common._internal.trace_encoder import encode_spans
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

# Remain below the devbox edge's 1 MiB OTLP/HTTP request body cap.
MAX_BATCH_BYTES = 900_000
DEFAULT_SPOOL_MAX_BYTES = 8 * 1024 * 1024 * 1024
OTLP_TRACE_PATH = "/api/public/otel/v1/traces"


def spool_directory() -> Path:
    state = Path(os.environ.get("CC_LANGFUSE_STATE_DIR") or Path.home() / ".claude/state")
    return state.expanduser() / "langfuse_otlp_spool"


def _fsync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _durable_save(directory: Path, payload: bytes) -> None:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = f"{time.time_ns():020d}-{uuid.uuid4().hex}"
    temporary = directory / f".{name}.tmp"
    target = directory / f"{name}.otlp"
    try:
        with temporary.open("xb") as out:
            temporary.chmod(0o600)
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        temporary.replace(target)
        _fsync_directory(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _encode(spans: Sequence[ReadableSpan]) -> bytes:
    return encode_spans(spans).SerializeToString()


class DurableSpoolExporter(SpanExporter):
    """Write completed spans to a local durable outbox, never directly to network."""

    def __init__(self) -> None:
        self.directory = spool_directory()
        self.failed: BaseException | None = None
        raw = os.environ.get("CC_LANGFUSE_SPOOL_MAX_BYTES", str(DEFAULT_SPOOL_MAX_BYTES))
        self.max_bytes = int(raw)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if not spans:
            return SpanExportResult.SUCCESS
        try:
            self._persist(spans)
        except BaseException as exc:
            self.failed = exc
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def _persist(self, spans: Sequence[ReadableSpan]) -> None:
        group: list[ReadableSpan] = []
        for span in spans:
            proposed = [*group, span]
            if len(_encode(proposed)) > MAX_BATCH_BYTES:
                if not group:
                    raise ValueError("Single OTLP span exceeds local receiver envelope")
                self._persist_batch(group)
                group = [span]
                if len(_encode(group)) > MAX_BATCH_BYTES:
                    raise ValueError("Single OTLP span exceeds local receiver envelope")
            else:
                group = proposed
        if group:
            self._persist_batch(group)

    def _persist_batch(self, spans: Sequence[ReadableSpan]) -> None:
        payload = _encode(spans)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        allocated = sum(p.stat().st_size for p in self.directory.glob("*.otlp"))
        if allocated + len(payload) > self.max_bytes:
            raise OSError("Langfuse OTLP outbox capacity exceeded")
        free = shutil.disk_usage(self.directory).free
        if free <= len(payload) + MAX_BATCH_BYTES:
            raise OSError("Insufficient free disk space for durable OTLP export")
        _durable_save(self.directory, payload)

    def shutdown(self, timeout_millis: int = 30_000) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return self.failed is None


def drain_spool(base_url: str, timeout: float = 10.0) -> tuple[int, int]:
    """Return (delivered, pending). Stop at the first failure to preserve order."""
    if not base_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("OTLP replay must target a loopback receiver")
    directory = spool_directory()
    if not directory.exists():
        return 0, 0
    delivered = 0
    files = sorted(directory.glob("*.otlp"))
    for path in files:
        request = urllib.request.Request(
            base_url.rstrip("/") + OTLP_TRACE_PATH,
            data=path.read_bytes(),
            headers={
                "Content-Type": "application/x-protobuf",
                "x-langfuse-ingestion-version": "4",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if not 200 <= response.status < 300:
                    break
        except (OSError, urllib.error.URLError, TimeoutError):
            break
        path.unlink()
        _fsync_directory(directory)
        delivered += 1
    return delivered, len(files) - delivered
