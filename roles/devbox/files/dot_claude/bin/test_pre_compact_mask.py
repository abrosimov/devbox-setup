from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_compact_mask as pcm
from _claude_lib import proc

if TYPE_CHECKING:
    import pytest


def _ok(stdout: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _err() -> proc.CmdResult:
    return proc.CmdResult(stdout="", stderr="fatal", returncode=128, timed_out=False)


def test_render_minimal_state() -> None:
    state = pcm.State()
    out = pcm.render(state)
    assert "Branch: unknown" in out
    assert "Modified files" not in out
    assert "Staged files" not in out
    assert "Pipeline state" not in out
    assert "Workflow: active" not in out
    assert out.startswith("--- CONTEXT PRESERVED")
    assert "--- END PRESERVED CONTEXT ---" in out


def test_render_with_modified_and_staged() -> None:
    state = pcm.State(branch="topic", modified=["a.py", "b.py"], staged=["c.py"])
    out = pcm.render(state)
    assert "Branch: topic" in out
    assert "Modified files:" in out
    assert "  - a.py" in out
    assert "  - b.py" in out
    assert "Staged files:" in out
    assert "  - c.py" in out


def test_render_with_pipeline_state() -> None:
    state = pcm.State(
        branch="x",
        pipeline_state_path="/path/to/pipeline_state.json",
        pipeline_state_stages=[("plan", "completed"), ("test", "in_progress")],
    )
    out = pcm.render(state)
    assert "Pipeline state: /path/to/pipeline_state.json" in out
    assert "  plan: completed" in out
    assert "  test: in_progress" in out


def test_read_pipeline_stages_filters_pending(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "stages": {
                    "plan": {"status": "completed"},
                    "test": {"status": "pending"},
                    "review": {"status": "in_progress"},
                }
            }
        ),
        encoding="utf-8",
    )
    stages = pcm.read_pipeline_stages(str(state_file))
    keys = {name for name, _ in stages}
    assert "plan" in keys
    assert "review" in keys
    assert "test" not in keys


def test_read_pipeline_stages_handles_invalid_json(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("not json", encoding="utf-8")
    assert pcm.read_pipeline_stages(str(state_file)) == []


def test_read_pipeline_stages_handles_missing_stages_key(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("{}", encoding="utf-8")
    assert pcm.read_pipeline_stages(str(state_file)) == []


def test_find_pipeline_state_picks_first_match(tmp_path: Path) -> None:
    (tmp_path / "docs" / "implementation_plans" / "PROJ-1").mkdir(parents=True)
    state = tmp_path / "docs" / "implementation_plans" / "PROJ-1" / "pipeline_state.json"
    state.write_text("{}", encoding="utf-8")
    assert pcm.find_pipeline_state(tmp_path) == str(state)


def test_find_pipeline_state_falls_back_to_claude_dir(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    state = tmp_path / ".claude" / "pipeline_state.json"
    state.write_text("{}", encoding="utf-8")
    assert pcm.find_pipeline_state(tmp_path) == str(state)


def test_find_pipeline_state_returns_none_when_absent(tmp_path: Path) -> None:
    assert pcm.find_pipeline_state(tmp_path) is None


def test_collect_state_uses_git_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    responses = {
        "git branch --show-current": _ok("feature/topic\n"),
        "git diff --name-only": _ok("a.py\nb.py\n"),
        "git diff --cached --name-only": _ok("c.py\n"),
    }

    def fake(cmd: list[str], **_kwargs: object) -> proc.CmdResult:
        key = " ".join(cmd)
        for prefix, response in responses.items():
            if key.startswith(prefix):
                return response
        return _err()

    monkeypatch.setattr(proc, "run_cmd", fake)
    state = pcm.collect_state(tmp_path)
    assert state.branch == "feature/topic"
    assert state.modified == ["a.py", "b.py"]
    assert state.staged == ["c.py"]


def test_collect_state_when_not_in_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(proc, "run_cmd", lambda *_a, **_kw: _err())
    state = pcm.collect_state(tmp_path)
    assert state.branch == "unknown"
    assert state.modified == []
    assert state.staged == []


def test_main_writes_summary_to_stdout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PWD", str(tmp_path))
    monkeypatch.setattr(proc, "run_cmd", lambda *_a, **_kw: _ok("topic\n"))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert pcm.main() == 0
    assert "Branch:" in out.getvalue()
    assert "END PRESERVED CONTEXT" in out.getvalue()
