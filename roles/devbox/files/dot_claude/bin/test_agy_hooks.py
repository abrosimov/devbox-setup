import json
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[2] / "dot_agy/config/hooks.json.j2"

# The five lifecycle events Antigravity dispatches, per the spec embedded in the
# `agy` binary. An event key outside this set is loaded without complaint and
# then never fired, which is how the whole file sat inert before.
GROUPED_EVENTS = frozenset({"PreToolUse", "PostToolUse"})
FLAT_EVENTS = frozenset({"PreInvocation", "PostInvocation", "Stop"})
SUPPORTED_EVENTS = GROUPED_EVENTS | FLAT_EVENTS


@pytest.fixture(scope="module")
def hooks() -> dict:
    with TEMPLATE.open() as stream:
        return json.load(stream)


def _handlers(body: dict) -> list[tuple[str, dict]]:
    """Yield (event, handler) for every handler under one named hook."""
    found: list[tuple[str, dict]] = []
    for event, entries in body.items():
        if event == "enabled":
            continue
        for entry in entries:
            if event in GROUPED_EVENTS:
                found.extend((event, handler) for handler in entry["hooks"])
            else:
                found.append((event, entry))
    return found


def test_every_event_key_is_dispatched_by_agy(hooks: dict) -> None:
    for name, body in hooks.items():
        events = {key for key in body if key != "enabled"}
        assert events, f"{name} declares no event and can never run"
        unsupported = events - SUPPORTED_EVENTS
        assert not unsupported, f"{name} binds to unknown event(s) {sorted(unsupported)}"


def test_tool_events_are_grouped_and_loop_events_are_flat(hooks: dict) -> None:
    for name, body in hooks.items():
        for event, entries in body.items():
            if event == "enabled":
                continue
            for entry in entries:
                if event in GROUPED_EVENTS:
                    assert set(entry) == {"matcher", "hooks"}, f"{name}/{event}"
                else:
                    assert "hooks" not in entry, f"{name}/{event} must be a flat handler"
                    assert entry["command"], f"{name}/{event}"


def test_handlers_run_from_the_pinned_venv(hooks: dict) -> None:
    for name, body in hooks.items():
        for event, handler in _handlers(body):
            command = handler["command"]
            assert handler.get("type", "command") == "command", f"{name}/{event}"
            assert "uv run" not in command, f"{name}/{event}"
            assert "uvx" not in command, f"{name}/{event}"


def test_no_duplicate_registrations(hooks: dict) -> None:
    seen: set[tuple[str, str]] = set()
    for name, body in hooks.items():
        for event, handler in _handlers(body):
            key = (event, handler["command"])
            assert key not in seen, f"Duplicate hook registration for {key} at {name}"
            seen.add(key)


def test_universal_logger_covers_every_event(hooks: dict) -> None:
    logged = {
        event
        for body in hooks.values()
        if body.get("enabled", True)
        for event, handler in _handlers(body)
        if "universal_logger.py" in handler["command"]
    }
    assert logged == SUPPORTED_EVENTS


def test_logger_argv_matches_the_event_it_is_registered_under(hooks: dict) -> None:
    for name, body in hooks.items():
        for event, handler in _handlers(body):
            command = handler["command"]
            if "universal_logger.py" not in command:
                continue
            assert command.split()[-1] == event, f"{name} logs {event} under a wrong name"
