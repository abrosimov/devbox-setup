from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_edit_repo_boundary
from _claude_lib import paths


@pytest.fixture
def layout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Path]:
    home = tmp_path / "home"
    project = tmp_path / "work" / "project"
    neighbour = tmp_path / "work" / "neighbour"
    scratch = tmp_path / "scratch"
    for directory in (home, project / ".git", project / "pkg", neighbour / ".git", scratch):
        directory.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr(paths, "temp_roots", lambda: (scratch.resolve(),))
    return {"home": home, "project": project, "neighbour": neighbour, "scratch": scratch}


def _decide(
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    target: Path | str,
    cwd: Path,
) -> dict[str, object] | None:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    payload = {"tool_name": tool, "tool_input": {key: str(target)}, "cwd": str(cwd)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    assert pre_edit_repo_boundary.main() == 0
    return json.loads(stdout.getvalue()) if stdout.getvalue() else None


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit", "NotebookEdit"])
def test_edit_in_a_neighbouring_repository_asks(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
    tool: str,
) -> None:
    decision = _decide(
        monkeypatch, tool, layout["neighbour"] / "main.go", layout["project"] / "pkg"
    )

    assert decision is not None
    output = decision["hookSpecificOutput"]
    assert isinstance(output, dict)
    reason = output["permissionDecisionReason"]
    assert output == {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": reason,
    }
    assert str(layout["project"].resolve()) in reason


def test_edit_inside_the_session_repository_is_allowed_from_a_subdirectory(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
) -> None:
    target = layout["project"] / "README.md"
    assert _decide(monkeypatch, "Edit", target, layout["project"] / "pkg") is None


def test_relative_path_resolves_against_the_hook_cwd(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
) -> None:
    assert _decide(monkeypatch, "Write", "../../neighbour/x.py", layout["project"] / "pkg")
    assert _decide(monkeypatch, "Write", "new.py", layout["project"] / "pkg") is None


def test_dot_dot_escape_from_the_project_asks(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
) -> None:
    target = layout["project"] / ".." / "neighbour" / "x.py"
    assert _decide(monkeypatch, "Edit", target, layout["project"]) is not None


def test_cwd_outside_a_repository_is_the_boundary(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
) -> None:
    workdir = layout["home"] / "notes"
    workdir.mkdir()
    assert _decide(monkeypatch, "Write", workdir / "a.md", workdir) is None
    assert _decide(monkeypatch, "Write", layout["home"] / "b.md", workdir) is not None


def test_session_start_directory_wins_over_a_later_cwd(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(layout["project"]))
    target = layout["neighbour"] / "x.py"
    assert _decide(monkeypatch, "Edit", target, layout["neighbour"]) is not None


def test_temp_directory_is_exempt(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
) -> None:
    target = layout["scratch"] / "probe.py"
    assert _decide(monkeypatch, "Write", target, layout["project"]) is None


@pytest.mark.parametrize("state_dir", ["memory", "plans", "projects"])
def test_claude_state_directories_are_exempt(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
    state_dir: str,
) -> None:
    target = layout["home"] / ".claude" / state_dir / "x" / "MEMORY.md"
    assert _decide(monkeypatch, "Write", target, layout["project"]) is None


def test_other_claude_config_is_not_exempt(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
) -> None:
    target = layout["home"] / ".claude" / "skills" / "x" / "SKILL.md"
    assert _decide(monkeypatch, "Edit", target, layout["project"]) is not None


def test_non_edit_tools_are_ignored(
    monkeypatch: pytest.MonkeyPatch,
    layout: dict[str, Path],
) -> None:
    assert _decide(monkeypatch, "Read", layout["neighbour"] / "x.py", layout["project"]) is None


def test_empty_input_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    assert pre_edit_repo_boundary.main() == 0
    assert stdout.getvalue() == ""
