from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import suggest_checkpoint

if TYPE_CHECKING:
    import pytest


def test_state_path_uses_session_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    path = suggest_checkpoint.state_path_for("abc")
    assert path.name == "claude-checkpoint-abc"
    assert path.parent == tmp_path


def test_load_state_missing_returns_zero(tmp_path: Path) -> None:
    state = suggest_checkpoint.load_state(tmp_path / "missing")
    assert state == suggest_checkpoint.CheckpointState(count=0, last_suggestion=0)


def test_load_state_malformed_returns_zero(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    target.write_text("garbage{", encoding="utf-8")
    state = suggest_checkpoint.load_state(target)
    assert state == suggest_checkpoint.CheckpointState(count=0, last_suggestion=0)


def test_load_state_parses_count_and_last(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    target.write_text('{"count": 5, "lastSuggestion": 3}', encoding="utf-8")
    state = suggest_checkpoint.load_state(target)
    assert state == suggest_checkpoint.CheckpointState(count=5, last_suggestion=3)


def test_save_state_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    suggest_checkpoint.save_state(
        target, suggest_checkpoint.CheckpointState(count=7, last_suggestion=2)
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data == {"count": 7, "lastSuggestion": 2}


def test_next_state_first_suggestion_at_threshold() -> None:
    current = suggest_checkpoint.CheckpointState(count=39, last_suggestion=0)
    updated, suggest = suggest_checkpoint.next_state(current)
    assert suggest is True
    assert updated.count == 40
    assert updated.last_suggestion == 40


def test_next_state_no_suggestion_before_first_threshold() -> None:
    current = suggest_checkpoint.CheckpointState(count=5, last_suggestion=0)
    updated, suggest = suggest_checkpoint.next_state(current)
    assert suggest is False
    assert updated.count == 6
    assert updated.last_suggestion == 0


def test_next_state_repeat_after_interval() -> None:
    current = suggest_checkpoint.CheckpointState(count=64, last_suggestion=40)
    updated, suggest = suggest_checkpoint.next_state(current)
    assert suggest is True
    assert updated.count == 65
    assert updated.last_suggestion == 65


def test_next_state_no_repeat_within_interval() -> None:
    current = suggest_checkpoint.CheckpointState(count=50, last_suggestion=40)
    updated, suggest = suggest_checkpoint.next_state(current)
    assert suggest is False
    assert updated.count == 51
    assert updated.last_suggestion == 40


def test_main_ignores_non_work_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "s1",
                    "tool_name": "Read",
                }
            )
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert suggest_checkpoint.main() == 0
    assert out.getvalue() == ""
    assert not (tmp_path / "claude-checkpoint-s1").exists()


def test_main_writes_state_for_work_tool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "s2",
                    "tool_name": "Edit",
                }
            )
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert suggest_checkpoint.main() == 0
    state_path = tmp_path / "claude-checkpoint-s2"
    assert state_path.exists()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data == {"count": 1, "lastSuggestion": 0}
    assert out.getvalue() == ""


def test_main_emits_suggestion_at_threshold(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    state_path = tmp_path / "claude-checkpoint-s3"
    state_path.write_text('{"count": 39, "lastSuggestion": 0}', encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "s3",
                    "tool_name": "Write",
                }
            )
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert suggest_checkpoint.main() == 0
    payload = json.loads(out.getvalue())
    assert "additionalContext" in payload
    assert "40 tool calls" in payload["additionalContext"]
