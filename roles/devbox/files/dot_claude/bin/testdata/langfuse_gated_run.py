"""Run one Langfuse hook firing whose span exports wait until the hook flushes.

Holding every export back leaves the firing's spans in the SDK's in-process
queue at once, so the queue's bound decides alone whether a span is dropped.
Usage: langfuse_gated_run.py <bin-dir> wrapper|vendored < hook-payload
"""

from __future__ import annotations

import importlib
import runpy
import sys
import threading
from pathlib import Path


def hold_exports_until_flush() -> None:
    # Imported at run time: the root project's type-check venv has no OTel SDK.
    exporter = importlib.import_module("durable_otel_exporter").DurableSpoolExporter
    tracer_provider = importlib.import_module("opentelemetry.sdk.trace").TracerProvider
    flushing = threading.Event()
    export = exporter.export
    force_flush = tracer_provider.force_flush

    def held_export(self: object, spans: object) -> object:
        flushing.wait()
        return export(self, spans)

    def releasing_force_flush(self: object, timeout_millis: int = 30_000) -> bool:
        flushing.set()
        return force_flush(self, timeout_millis)

    exporter.export = held_export
    tracer_provider.force_flush = releasing_force_flush


def main() -> None:
    bin_directory, entry = Path(sys.argv[1]), sys.argv[2]
    vendor = bin_directory / "vendor"
    sys.path[0:0] = [str(vendor), str(bin_directory)]
    hold_exports_until_flush()
    if entry == "wrapper":
        importlib.import_module("langfuse_trace_hook").main()
    else:
        runpy.run_path(str(vendor / "langfuse_hook.py"), run_name="__main__")


if __name__ == "__main__":
    main()
