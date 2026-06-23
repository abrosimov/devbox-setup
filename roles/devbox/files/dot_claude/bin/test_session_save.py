from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import session_save

if TYPE_CHECKING:
    import pytest


def test_render_working_state_no_files() -> None:
    rendered = session_save.render_working_state(
        {"branch": "main", "sha": "abc1234", "files": []},
        event="SessionEnd",
        now="2026-06-20 12:00",
    )
    assert "## Working State" in rendered
    assert "- **Branch**: main" in rendered
    assert "- **SHA**: abc1234" in rendered
    assert "no uncommitted changes" in rendered
    assert "session ended at 2026-06-20 12:00" in rendered


def test_render_working_state_pre_compact_label() -> None:
    rendered = session_save.render_working_state(
        {"branch": "topic", "sha": "deadbee", "files": ["a.py", "b.py"]},
        event="PreCompact",
        now="2026-06-20 13:00",
    )
    assert "context compacted at 2026-06-20 13:00" in rendered
    assert "a.py, b.py" in rendered


def test_update_memory_replaces_existing_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    memory_file = memory_dir / "MEMORY.md"
    memory_file.write_text(
        "## Working State\n- **Branch**: old\n\n## Other Section\n- still here\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        session_save,
        "collect_git_state",
        lambda _cwd: {"branch": "new", "sha": "abc", "files": ["x.py"]},
    )
    session_save.update_memory(memory_dir, "SessionEnd", tmp_path, "2026-06-20 12:00")

    content = memory_file.read_text(encoding="utf-8")
    assert "- **Branch**: new" in content
    assert "- **Branch**: old" not in content
    assert "## Other Section" in content
    assert "- still here" in content


def test_update_memory_prepends_when_section_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    memory_file = memory_dir / "MEMORY.md"
    memory_file.write_text("## Other\n- content\n", encoding="utf-8")

    monkeypatch.setattr(
        session_save,
        "collect_git_state",
        lambda _cwd: {"branch": "main", "sha": "abc", "files": []},
    )
    session_save.update_memory(memory_dir, "SessionEnd", tmp_path, "2026-06-20 12:00")

    content = memory_file.read_text(encoding="utf-8")
    assert content.startswith("## Working State")
    assert "## Other" in content


def test_update_memory_no_branch_skips_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    memory_file = memory_dir / "MEMORY.md"
    original = "## Working State\n- **Branch**: old\n"
    memory_file.write_text(original, encoding="utf-8")

    monkeypatch.setattr(session_save, "collect_git_state", lambda _cwd: {"branch": ""})
    session_save.update_memory(memory_dir, "SessionEnd", tmp_path, "2026-06-20 12:00")

    assert memory_file.read_text(encoding="utf-8") == original


def test_find_memory_dir_returns_none_when_root_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert session_save.find_memory_dir(tmp_path / "anywhere") is None


def test_find_memory_dir_matches_normalised_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    project = tmp_path / ".claude" / "projects" / "-Users-foo-bar"
    (project / "memory").mkdir(parents=True)
    (project / "memory" / "MEMORY.md").write_text("# m", encoding="utf-8")
    other = tmp_path / ".claude" / "projects" / "-Users-other"
    (other / "memory").mkdir(parents=True)
    (other / "memory" / "MEMORY.md").write_text("# m", encoding="utf-8")

    result = session_save.find_memory_dir(Path("/Users/foo/bar"))
    assert result == project / "memory"


def test_main_writes_additional_context_on_pre_compact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(session_save, "find_memory_dir", lambda _cwd: None)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "cwd": str(tmp_path),
                    "hook_event_name": "PreCompact",
                }
            )
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert session_save.main() == 0
    payload = json.loads(out.getvalue())
    assert "MEMORY.md" in payload["additionalContext"]


def test_main_session_end_no_additional_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(session_save, "find_memory_dir", lambda _cwd: None)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "cwd": str(tmp_path),
                    "hook_event_name": "SessionEnd",
                }
            )
        ),
    )
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert session_save.main() == 0
    assert out.getvalue() == ""
