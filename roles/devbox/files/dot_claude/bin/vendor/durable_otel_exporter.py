"""Durable OTLP span outbox for Langfuse's OpenTelemetry SpanExporter API.

The exporter only acknowledges a batch after fsync-backed local persistence.
Batches stay in a private staging directory until the hook commits them, so a
failed firing, whose turns replay re-emits, never reaches the outbox.
Delivery to the loopback otelbox edge is a separate retryable operation.
"""
from __future__ import annotations

import contextlib
import http.client
import os
import shutil
import sys
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
SPOOL_MAX_BYTES_ENV = "CC_LANGFUSE_SPOOL_MAX_BYTES"
# Fills only while the loopback edge is unreachable: a week of heavy Langfuse output.
DEFAULT_SPOOL_MAX_BYTES = 2 * 1024 * 1024 * 1024
OTLP_TRACE_PATH = "/api/public/otel/v1/traces"
STAGING_DIRECTORY = ".staging"
# Hook firings are killed well inside this; older staging belongs to a dead process.
STALE_STAGING_SECONDS = 3600
TRANSIENT_HTTP_STATUSES = frozenset({408, 429})


def spool_directory() -> Path:
    state = Path(os.environ.get("CC_LANGFUSE_STATE_DIR") or Path.home() / ".claude/state")
    return state.expanduser() / "langfuse_otlp_spool"


def quarantine_directory() -> Path:
    return spool_directory().parent / "langfuse_otlp_quarantine"


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


def _spool_bytes(directory: Path) -> int:
    # Every hook's staging counts: concurrent firings share one cap.
    total = 0
    for path in (*directory.glob("*.otlp"), *directory.glob(f"{STAGING_DIRECTORY}/*/*.otlp")):
        with contextlib.suppress(FileNotFoundError):
            total += path.stat().st_size
    return total


def _encode(spans: Sequence[ReadableSpan]) -> bytes:
    return encode_spans(spans).SerializeToString()


class DurableSpoolExporter(SpanExporter):
    """Write completed spans to a local durable outbox, never directly to network."""

    def __init__(self) -> None:
        self.directory = spool_directory()
        self.staging = self.directory / STAGING_DIRECTORY / uuid.uuid4().hex
        self.failed: BaseException | None = None
        self.discarded = False
        self.max_bytes = int(os.environ.get(SPOOL_MAX_BYTES_ENV) or DEFAULT_SPOOL_MAX_BYTES)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if not spans or self.discarded:
            return SpanExportResult.SUCCESS
        try:
            self._persist(spans)
        except BaseException as exc:
            if self.failed is None:
                # The hook logs only to a file; a refused span must reach the operator.
                print(f"durable_otel_exporter: {exc}", file=sys.stderr)
            self.failed = exc
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def commit(self) -> None:
        if self.discarded or not self.staging.is_dir():
            return
        staged = sorted(self.staging.glob("*.otlp"))
        for path in staged:
            path.replace(self.directory / path.name)
        if staged:
            _fsync_directory(self.directory)
        shutil.rmtree(self.staging, ignore_errors=True)

    def discard(self) -> None:
        self.discarded = True
        shutil.rmtree(self.staging, ignore_errors=True)

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
        (self.directory / STAGING_DIRECTORY).mkdir(exist_ok=True, mode=0o700)
        allocated = _spool_bytes(self.directory)
        if allocated + len(payload) > self.max_bytes:
            raise OSError(
                f"Langfuse OTLP spool full: {allocated} bytes queued plus a {len(payload)}-byte "
                f"batch exceeds {SPOOL_MAX_BYTES_ENV}={self.max_bytes} at {self.directory}; "
                "refusing new spans until replay drains it, nothing was deleted"
            )
        free = shutil.disk_usage(self.directory).free
        if free <= len(payload) + MAX_BATCH_BYTES:
            raise OSError(
                f"Langfuse OTLP spool refused a {len(payload)}-byte batch: only {free} bytes "
                f"free on the volume holding {self.directory}; nothing was deleted"
            )
        _durable_save(self.staging, payload)

    def shutdown(self, timeout_millis: int = 30_000) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return self.failed is None


def _is_permanent_rejection(status: int) -> bool:
    return 400 <= status < 500 and status not in TRANSIENT_HTTP_STATUSES


def _quarantine(path: Path, status: int) -> None:
    quarantine = quarantine_directory()
    quarantine.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.replace(quarantine / path.name)
    _fsync_directory(quarantine)
    _fsync_directory(path.parent)
    print(
        f"Langfuse OTLP batch rejected with HTTP {status}, quarantined: {quarantine / path.name}",
        file=sys.stderr,
    )


def _sweep_stale_staging(directory: Path) -> None:
    staging = directory / STAGING_DIRECTORY
    if not staging.is_dir():
        return
    cutoff = time.time() - STALE_STAGING_SECONDS
    for owner in staging.iterdir():
        with contextlib.suppress(OSError):
            if owner.stat().st_mtime < cutoff:
                shutil.rmtree(owner)


def drain_spool(base_url: str, timeout: float = 10.0) -> tuple[int, int]:
    """Return (delivered, pending).

    A transient failure stops the pass to preserve order; a permanently rejected
    batch is quarantined so that it cannot block the batches behind it.
    """
    if not base_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("OTLP replay must target a loopback receiver")
    directory = spool_directory()
    if not directory.exists():
        return 0, 0
    _sweep_stale_staging(directory)
    delivered = quarantined = 0
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
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
        except (OSError, http.client.HTTPException):
            break
        if 200 <= status < 300:
            path.unlink()
            _fsync_directory(directory)
            delivered += 1
        elif _is_permanent_rejection(status):
            _quarantine(path, status)
            quarantined += 1
        else:
            break
    return delivered, len(files) - delivered - quarantined
