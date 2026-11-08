"""The hook keeps observation content whole unless CC_LANGFUSE_MAX_CHARS asks for a cap."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from test_langfuse_deterministic_ids import (
    SESSION_ID,
    assistant_row,
    hook_log,
    run_live_hook,
    text,
    tool_use,
    user_row,
    write_jsonl,
)

if TYPE_CHECKING:
    from types import ModuleType

    import pytest

VENDORED_HOOK = Path(__file__).parent / "vendor" / "langfuse_hook.py"
LONG = 50_000
FORMER_DEFAULT_CAP = 20_000


def load_hook(monkeypatch: pytest.MonkeyPatch, max_chars: str | None) -> ModuleType:
    if max_chars is None:
        monkeypatch.delenv("CC_LANGFUSE_MAX_CHARS", raising=False)
    else:
        monkeypatch.setenv("CC_LANGFUSE_MAX_CHARS", max_chars)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_CC_LANGFUSE_MAX_CHARS", raising=False)
    spec = importlib.util.spec_from_file_location("langfuse_truncation_under_test", VENDORED_HOOK)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def long_text(label: str) -> str:
    return f"<{label}>" + "x" * LONG + f"</{label}>"


def test_default_keeps_every_kind_of_content_whole(monkeypatch: pytest.MonkeyPatch) -> None:
    hook = load_hook(monkeypatch, None)
    whole = long_text("text")
    dict_input = {"command": long_text("dict-input"), "nested": {"value": long_text("nested")}}

    assert hook.truncate_text(whole) == (whole, {"truncated": False, "orig_len": len(whole)})
    assert hook.get_tool_input_for_observation({"input": whole})[0] == whole
    assert hook.get_tool_input_for_observation({"input": dict_input}) == (dict_input, None)
    assert hook.render_tool_result_content(whole)[0] == whole
    block = [{"type": "text", "text": whole}]
    assert whole in hook.render_tool_result_content(block)[0]
    assert hook.render_tool_result_content(block)[1]["truncated"] is False


def test_explicit_cap_keeps_the_existing_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    hook = load_hook(monkeypatch, "100")
    whole = long_text("text")
    dict_input = {"command": long_text("dict-input")}

    head, meta = hook.truncate_text(whole)
    assert head == whole[:100]
    assert meta["truncated"] is True
    assert meta["orig_len"] == len(whole)
    assert hook.get_tool_input_for_observation({"input": whole})[0] == whole[:100]
    assert hook.get_tool_input_for_observation({"input": dict_input}) == (dict_input, None)
    assert len(hook.render_tool_result_content(whole)[0]) == 100


def test_an_unparseable_explicit_cap_falls_back_to_the_former_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook = load_hook(monkeypatch, "lots")
    assert hook.MAX_CHARS == FORMER_DEFAULT_CAP


def write_long_session(directory: Path) -> tuple[Path, list[str]]:
    contents = [long_text(label) for label in ("prompt", "thinking", "reply", "input", "result")]
    prompt, thinking, reply, tool_input, result = contents
    rows = [
        user_row(SESSION_ID, "user-row-1", "2026-10-01T10:00:00.000Z", prompt),
        assistant_row(
            SESSION_ID,
            "msg_1",
            "2026-10-01T10:00:01.000Z",
            [
                {"type": "thinking", "thinking": thinking},
                text(reply),
                tool_use("toolu_bash", "Bash", {"command": tool_input}),
            ],
        ),
        user_row(
            SESSION_ID,
            None,
            "2026-10-01T10:00:02.000Z",
            [{"type": "tool_result", "tool_use_id": "toolu_bash", "content": result}],
        ),
        assistant_row(SESSION_ID, "msg_2", "2026-10-01T10:00:03.000Z", [text("Done")]),
        user_row(SESSION_ID, "user-row-2", "2026-10-01T10:01:00.000Z", "Thanks"),
        assistant_row(SESSION_ID, "msg_3", "2026-10-01T10:01:01.000Z", [text("Welcome")]),
    ]
    transcript = directory / f"{SESSION_ID}.jsonl"
    write_jsonl(transcript, rows)
    return transcript, contents


def spooled_bytes(state: Path) -> bytes:
    return b"".join(path.read_bytes() for path in (state / "langfuse_otlp_spool").glob("*.otlp"))


def test_default_run_spools_every_long_content_whole(tmp_path: Path) -> None:
    transcript, contents = write_long_session(tmp_path / "projects")
    state = tmp_path / "state"
    run_live_hook(transcript, SESSION_ID, state)
    spooled = spooled_bytes(state)
    missing = [content[:12] for content in contents if content.encode() not in spooled]
    assert not missing, hook_log(state)


def test_explicit_cap_run_spools_no_long_content_whole(tmp_path: Path) -> None:
    transcript, contents = write_long_session(tmp_path / "projects")
    state = tmp_path / "state"
    run_live_hook(transcript, SESSION_ID, state, CC_LANGFUSE_MAX_CHARS="1000")
    spooled = spooled_bytes(state)
    # A dict tool input was never truncated, explicit cap or not.
    truncated = contents[:3] + contents[4:]
    assert not [content[:12] for content in truncated if content.encode() in spooled]
    assert contents[3].encode() in spooled
