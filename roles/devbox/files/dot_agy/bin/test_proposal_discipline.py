from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import proposal_discipline as pd

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# count_numbered_items
# ---------------------------------------------------------------------------


def test_count_numbered_items_zero_for_prose() -> None:
    assert pd.count_numbered_items("just a sentence with no list") == 0


def test_count_numbered_items_handles_dot_and_paren() -> None:
    assert pd.count_numbered_items("1. one\n2) two\n3. three") == 3


def test_count_numbered_items_requires_line_start() -> None:
    assert pd.count_numbered_items("text 1. inline does not count") == 0


# ---------------------------------------------------------------------------
# detect_feedback — English patterns
# ---------------------------------------------------------------------------


def test_detect_feedback_en_what_about() -> None:
    assert pd.detect_feedback("what about using a marker file instead?")


def test_detect_feedback_en_option_token() -> None:
    assert pd.detect_feedback("Let's go with option 2.")


def test_detect_feedback_en_instead_of() -> None:
    assert pd.detect_feedback("Use mktemp instead of a fixed name.")


def test_detect_feedback_en_scratch_that() -> None:
    assert pd.detect_feedback("Scratch that — try the other approach.")


def test_detect_feedback_en_no_match_for_unrelated_text() -> None:
    assert not pd.detect_feedback("Please summarise the latest commit.")


# ---------------------------------------------------------------------------
# detect_feedback — Russian patterns
# ---------------------------------------------------------------------------


def test_detect_feedback_ru_chto_naschet() -> None:
    assert pd.detect_feedback("Что насчёт варианта с rsync?")  # noqa: RUF001 -- Russian test fixture


def test_detect_feedback_ru_pomenyay() -> None:
    assert pd.detect_feedback("Поменяй порядок шагов.")


def test_detect_feedback_ru_variant_token() -> None:
    assert pd.detect_feedback("Возьмём вариант 3.")


def test_detect_feedback_ru_no_match_for_unrelated_text() -> None:
    assert not pd.detect_feedback("Расскажи про текущее состояние ветки.")


# ---------------------------------------------------------------------------
# detect_numbered_answers
# ---------------------------------------------------------------------------


def test_detect_numbered_answers_two_items_returns_true() -> None:
    assert pd.detect_numbered_answers("1. yes\n2. option B")


def test_detect_numbered_answers_one_item_returns_false() -> None:
    assert not pd.detect_numbered_answers("1. only one")


def test_detect_numbered_answers_no_items_returns_false() -> None:
    assert not pd.detect_numbered_answers("free-form prose with no list")


# ---------------------------------------------------------------------------
# looks_like_proposal
# ---------------------------------------------------------------------------


def test_looks_like_proposal_awaiting_decision_marker() -> None:
    text = "Here is my analysis.\n\n> **[Awaiting your decision]**"
    assert pd.looks_like_proposal(text)


def test_looks_like_proposal_three_numbered_items() -> None:
    text = "1. first\n2. second\n3. third"
    assert pd.looks_like_proposal(text)


def test_looks_like_proposal_two_numbered_items_not_enough_alone() -> None:
    text = "1. first\n2. second"
    assert not pd.looks_like_proposal(text)


def test_looks_like_proposal_option_letter_marker() -> None:
    assert pd.looks_like_proposal("Choose between Option A and Option B.")


def test_looks_like_proposal_section_marker() -> None:
    assert pd.looks_like_proposal("In §3 we discussed the tradeoffs.")


def test_looks_like_proposal_letter_paren_list() -> None:
    text = "A) first\nB) second\nC) third"
    assert pd.looks_like_proposal(text)


def test_looks_like_proposal_plain_prose_returns_false() -> None:
    assert not pd.looks_like_proposal("Just a friendly summary of recent work.")


# ---------------------------------------------------------------------------
# Transcript reader — _read_jsonl_entries
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, entries: list[dict[str, object]]) -> None:
    payload = "\n".join(json.dumps(entry) for entry in entries) + "\n"
    path.write_text(payload, encoding="utf-8")


def test_read_jsonl_entries_skips_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_text('{"a": 1}\nnot-json\n{"b": 2}\n', encoding="utf-8")
    entries = pd._read_jsonl_entries(path)
    assert entries == [{"a": 1}, {"b": 2}]


def test_read_jsonl_entries_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert pd._read_jsonl_entries(tmp_path / "missing.jsonl") == []


def test_read_jsonl_entries_skips_non_dict_lines(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_text('"plain string"\n[1, 2]\n{"k": "v"}\n', encoding="utf-8")
    assert pd._read_jsonl_entries(path) == [{"k": "v"}]


# ---------------------------------------------------------------------------
# Transcript reader — _role_of and _extract_text
# ---------------------------------------------------------------------------


def test_role_of_reads_message_role() -> None:
    entry = {"message": {"role": "assistant", "content": "hi"}}
    assert pd._role_of(entry) == "assistant"


def test_role_of_falls_back_to_entry_type() -> None:
    entry = {"type": "user"}
    assert pd._role_of(entry) == "user"


def test_role_of_returns_empty_when_unknown() -> None:
    assert pd._role_of({}) == ""


def test_extract_text_handles_string_content() -> None:
    entry = {"message": {"role": "user", "content": "hello"}}
    assert pd._extract_text(entry) == "hello"


def test_extract_text_handles_list_with_text_blocks() -> None:
    entry = {
        "message": {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "part one"},
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
                {"type": "text", "text": "part two"},
            ],
        }
    }
    assert pd._extract_text(entry) == "part one\npart two"


def test_extract_text_returns_empty_for_missing_message() -> None:
    assert pd._extract_text({"type": "user"}) == ""


# ---------------------------------------------------------------------------
# Transcript reader — _has_human_text
# ---------------------------------------------------------------------------


def test_has_human_text_string_content_is_human() -> None:
    assert pd._has_human_text({"message": {"role": "user", "content": "hi"}})


def test_has_human_text_tool_result_only_is_not_human() -> None:
    entry = {
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "x", "content": "output"},
            ],
        }
    }
    assert not pd._has_human_text(entry)


def test_has_human_text_mixed_content_with_text_block_is_human() -> None:
    entry = {
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "x", "content": "output"},
                {"type": "text", "text": "follow-up question"},
            ],
        }
    }
    assert pd._has_human_text(entry)


# ---------------------------------------------------------------------------
# read_last_assistant_text / read_last_user_text
# ---------------------------------------------------------------------------


def test_read_last_assistant_text_returns_most_recent(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    _write_jsonl(
        path,
        [
            {"message": {"role": "user", "content": "q1"}},
            {"message": {"role": "assistant", "content": "old answer"}},
            {"message": {"role": "user", "content": "q2"}},
            {"message": {"role": "assistant", "content": "new answer"}},
        ],
    )
    assert pd.read_last_assistant_text(path) == "new answer"


def test_read_last_user_text_skips_tool_result_envelopes(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    _write_jsonl(
        path,
        [
            {"message": {"role": "user", "content": "the real prompt"}},
            {"message": {"role": "assistant", "content": "answer"}},
            {
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "x", "content": "output"},
                    ],
                }
            },
        ],
    )
    assert pd.read_last_user_text(path) == "the real prompt"


def test_read_last_assistant_text_none_when_no_transcript(tmp_path: Path) -> None:
    assert pd.read_last_assistant_text(tmp_path / "missing.jsonl") is None


def test_read_last_assistant_text_none_when_path_none() -> None:
    assert pd.read_last_assistant_text(None) is None


# ---------------------------------------------------------------------------
# handle_user_prompt_submit
# ---------------------------------------------------------------------------


def _make_proposal_transcript(tmp_path: Path) -> Path:
    path = tmp_path / "transcript.jsonl"
    _write_jsonl(
        path,
        [
            {"message": {"role": "user", "content": "give me options"}},
            {
                "message": {
                    "role": "assistant",
                    "content": (
                        "Three options:\n"
                        "1. first\n"
                        "2. second\n"
                        "3. third\n\n"
                        "> **[Awaiting your decision]**"
                    ),
                }
            },
        ],
    )
    return path


def _make_non_proposal_transcript(tmp_path: Path) -> Path:
    path = tmp_path / "transcript.jsonl"
    _write_jsonl(
        path,
        [
            {"message": {"role": "user", "content": "explain the deploy"}},
            {"message": {"role": "assistant", "content": "It runs make personal."}},
        ],
    )
    return path


def test_handle_user_prompt_submit_empty_prompt_returns_none(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "prompt": "",
        "transcript_path": str(_make_proposal_transcript(tmp_path)),
    }
    assert pd.handle_user_prompt_submit(payload) is None


def test_handle_user_prompt_submit_no_prior_assistant_returns_none(tmp_path: Path) -> None:
    empty_transcript = tmp_path / "empty.jsonl"
    empty_transcript.write_text("", encoding="utf-8")
    payload: dict[str, object] = {
        "prompt": "what about option 2?",
        "transcript_path": str(empty_transcript),
    }
    assert pd.handle_user_prompt_submit(payload) is None


def test_handle_user_prompt_submit_non_proposal_prior_returns_none(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "prompt": "what about option 2?",
        "transcript_path": str(_make_non_proposal_transcript(tmp_path)),
    }
    assert pd.handle_user_prompt_submit(payload) is None


def test_handle_user_prompt_submit_feedback_returns_feedback_reminder(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "prompt": "What about option 2 instead?",
        "transcript_path": str(_make_proposal_transcript(tmp_path)),
    }
    result = pd.handle_user_prompt_submit(payload)
    assert result is not None
    assert "Iteration voice mode" in result
    assert "NUMBERED_REMINDER" not in result


def test_handle_user_prompt_submit_numbered_answers_returns_numbered_reminder(
    tmp_path: Path,
) -> None:
    payload: dict[str, object] = {
        "prompt": "1. yes\n2. skip\n3. defer",
        "transcript_path": str(_make_proposal_transcript(tmp_path)),
    }
    result = pd.handle_user_prompt_submit(payload)
    assert result is not None
    assert "numbered open questions" in result


def test_handle_user_prompt_submit_both_signals_joins_reminders(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "prompt": "What about option 2?\n1. yes\n2. confirm",
        "transcript_path": str(_make_proposal_transcript(tmp_path)),
    }
    result = pd.handle_user_prompt_submit(payload)
    assert result is not None
    assert "Iteration voice mode" in result
    assert "numbered open questions" in result


def test_handle_user_prompt_submit_no_transcript_returns_none() -> None:
    payload: dict[str, object] = {
        "prompt": "What about option 2?",
        "transcript_path": "",
    }
    assert pd.handle_user_prompt_submit(payload) is None


# ---------------------------------------------------------------------------
# handle_stop
# ---------------------------------------------------------------------------


def _make_feedback_user_transcript(tmp_path: Path) -> Path:
    path = tmp_path / "transcript.jsonl"
    _write_jsonl(
        path,
        [
            {"message": {"role": "assistant", "content": "proposal"}},
            {"message": {"role": "user", "content": "What about option 2 instead?"}},
        ],
    )
    return path


def _make_non_feedback_user_transcript(tmp_path: Path) -> Path:
    path = tmp_path / "transcript.jsonl"
    _write_jsonl(
        path,
        [
            {"message": {"role": "assistant", "content": "proposal"}},
            {"message": {"role": "user", "content": "Now write the docs section."}},
        ],
    )
    return path


def _long_message(line_count: int) -> str:
    return "\n".join(f"line {i}" for i in range(line_count))


def test_handle_stop_short_message_returns_none(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "assistant_message": _long_message(10),
        "transcript_path": str(_make_feedback_user_transcript(tmp_path)),
    }
    assert pd.handle_stop(payload) is None


def test_handle_stop_long_message_without_feedback_user_returns_none(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "assistant_message": _long_message(80),
        "transcript_path": str(_make_non_feedback_user_transcript(tmp_path)),
    }
    assert pd.handle_stop(payload) is None


def test_handle_stop_long_message_with_feedback_user_returns_reminder(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "assistant_message": _long_message(80),
        "transcript_path": str(_make_feedback_user_transcript(tmp_path)),
    }
    result = pd.handle_stop(payload)
    assert result is not None
    assert "delta against the prior proposal" in result


def test_handle_stop_empty_message_returns_none(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "assistant_message": "",
        "transcript_path": str(_make_feedback_user_transcript(tmp_path)),
    }
    assert pd.handle_stop(payload) is None


def test_handle_stop_missing_transcript_returns_none(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "assistant_message": _long_message(80),
        "transcript_path": str(tmp_path / "missing.jsonl"),
    }
    assert pd.handle_stop(payload) is None


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


def test_dispatch_unknown_event_returns_none() -> None:
    assert pd.dispatch({"hook_event_name": "SomethingElse"}) is None


def test_dispatch_stop_hook_active_returns_none() -> None:
    payload: dict[str, object] = {
        "hook_event_name": "Stop",
        "stop_hook_active": True,
        "assistant_message": "anything",
    }
    assert pd.dispatch(payload) is None


def test_dispatch_user_prompt_submit_routes_to_handler(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "What about option 2?",
        "transcript_path": str(_make_proposal_transcript(tmp_path)),
    }
    result = pd.dispatch(payload)
    assert result is not None
    assert "Iteration voice mode" in result


def test_dispatch_stop_routes_to_handler(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "hook_event_name": "Stop",
        "assistant_message": _long_message(80),
        "transcript_path": str(_make_feedback_user_transcript(tmp_path)),
    }
    result = pd.dispatch(payload)
    assert result is not None
    assert "delta against the prior proposal" in result


# ---------------------------------------------------------------------------
# main — end-to-end stdin/stdout
# ---------------------------------------------------------------------------


def test_main_empty_stdin_returns_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert pd.main() == 0
    assert out.getvalue() == ""


def test_main_writes_additional_context_for_feedback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "What about option 2?",
        "transcript_path": str(_make_proposal_transcript(tmp_path)),
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert pd.main() == 0
    raw = out.getvalue()
    assert raw != ""
    decoded = json.loads(raw)
    assert "additionalContext" in decoded
    assert "Iteration voice mode" in decoded["additionalContext"]


def test_main_silent_for_unrelated_event(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"hook_event_name": "PreCompact", "trigger": "manual"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert pd.main() == 0
    assert out.getvalue() == ""
