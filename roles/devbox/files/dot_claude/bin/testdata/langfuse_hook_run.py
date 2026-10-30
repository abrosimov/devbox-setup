"""Run the vendored Langfuse hook's main() in a scenario, then exit for real.

A subprocess, because the spans at stake are the ones the SDK's atexit handlers flush.
Usage: langfuse_hook_run.py <vendor-dir> <transcript> emission|flush-timeout|success
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from types import ModuleType

FAILING_TURN = 3


class TracingClient(Protocol):
    def flush(self) -> None: ...


def load_hook(vendor: Path) -> ModuleType:
    sys.path.insert(0, str(vendor))
    spec = importlib.util.spec_from_file_location("langfuse_hook_run", vendor / "langfuse_hook.py")
    if spec is None or spec.loader is None:
        message = f"Cannot load the vendored hook from {vendor}"
        raise ImportError(message)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hang(*_args: object, **_kwargs: object) -> bool:
    threading.Event().wait()
    return False


def install_hanging_flush() -> None:
    # Imported at run time: the root project's type-check venv has no OTel SDK.
    trace = importlib.import_module("opentelemetry.trace")
    sdk_trace = importlib.import_module("opentelemetry.sdk.trace")
    processor = type("HangingFlushProcessor", (sdk_trace.SpanProcessor,), {"force_flush": hang})
    trace.get_tracer_provider().add_span_processor(processor())


def emit_turn_span(hook: ModuleType, langfuse: TracingClient, turn: int) -> None:
    # The hook's own creation path: its id generator refuses ids nothing pinned.
    span = vars(hook)["_start_backdated"](
        langfuse,
        name=f"turn-{turn}",
        as_type="span",
        start_time=None,
        span_key=f"turn-{turn}",
        forced_trace_id=hook.derive_turn_trace_id("hook-run-session", turn),
    )
    vars(hook)["_end_backdated"](span, None)


def main() -> int:
    vendor, transcript, scenario = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    hook = load_hook(vendor)

    def fail_on_turn(langfuse: TracingClient, *_args: object, **_kwargs: object) -> int:
        for turn in range(1, FAILING_TURN):
            emit_turn_span(hook, langfuse, turn)
        # The batch processor exports on its own schedule while later turns are emitted.
        langfuse.flush()
        emit_turn_span(hook, langfuse, FAILING_TURN)
        if scenario == "emission":
            message = f"injected emission failure on turn {FAILING_TURN}"
            raise ValueError(message)
        if scenario == "flush-timeout":
            install_hanging_flush()
        hook.flush_and_shutdown_langfuse_client(langfuse)
        return FAILING_TURN

    vars(hook).update(
        read_hook_payload=dict,
        get_session_id_and_transcript_path=lambda _payload: ("hook-run-session", transcript),
        emit_new_turns_from_transcript=fail_on_turn,
    )
    return hook.main()


if __name__ == "__main__":
    sys.exit(main())
