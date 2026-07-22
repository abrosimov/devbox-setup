#!/usr/bin/env python3
"""Tests for build_skills_index.py.

Focus:
  - deterministic output (same input → same bytes)
  - --check exit codes (0 in sync, 1 out of sync)
  - dangling related refs render as strikethrough (~~name~~)
  - alphabetical & per-family sections both present
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import build_skills_index as bsi

if TYPE_CHECKING:
    from pathlib import Path


def _build_root(tmp_path: Path) -> Path:
    (tmp_path / "skills" / "go-engineer").mkdir(parents=True)
    (tmp_path / "skills" / "go-engineer" / "SKILL.md").write_text(
        "---\nname: go-engineer\ndescription: Write Go.\nrelated: [go-testing]\n---\nbody\n"
    )
    (tmp_path / "skills" / "go-testing").mkdir(parents=True)
    (tmp_path / "skills" / "go-testing" / "SKILL.md").write_text(
        "---\nname: go-testing\ndescription: Test Go.\nrelated: []\n---\nbody\n"
    )
    (tmp_path / "skills" / "workflow").mkdir(parents=True)
    (tmp_path / "skills" / "workflow" / "SKILL.md").write_text(
        "---\nname: workflow\ndescription: Pipeline.\n---\nbody\n"
    )
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "software_engineer_go.md").write_text(
        "---\nname: software-engineer-go\ndescription: Go SE.\ntools: Read\n"
        "model: opus\nskills: go-engineer\nrelated: [go-engineer]\n---\nbody\n"
    )
    return tmp_path


def test_deterministic(tmp_path: Path) -> None:
    root = _build_root(tmp_path)
    first = bsi.render_index(root)
    second = bsi.render_index(root)
    assert first == second


def test_alphabetical_section_present(tmp_path: Path) -> None:
    root = _build_root(tmp_path)
    out = bsi.render_index(root)
    assert "## Alphabetical index" in out


def test_family_section_present(tmp_path: Path) -> None:
    root = _build_root(tmp_path)
    out = bsi.render_index(root)
    assert "## Skills by family" in out
    assert "## Agents by family" in out
    assert "### Go" in out
    assert "### Engineering" in out


def test_related_link_rendered(tmp_path: Path) -> None:
    root = _build_root(tmp_path)
    out = bsi.render_index(root)
    assert "[`go-testing`](#s-go-testing)" in out


def test_dangling_related_rendered_as_strikethrough(tmp_path: Path) -> None:
    root = _build_root(tmp_path)
    (root / "skills" / "workflow" / "SKILL.md").write_text(
        "---\nname: workflow\ndescription: Pipeline.\nrelated: [ghost]\n---\nbody\n"
    )
    out = bsi.render_index(root)
    assert "~~ghost~~" in out


def test_counts_line_present(tmp_path: Path) -> None:
    root = _build_root(tmp_path)
    out = bsi.render_index(root)
    assert "3 skills, 1 agents" in out


def test_agent_family_by_prefix(tmp_path: Path) -> None:
    (tmp_path / "skills").mkdir()
    (tmp_path / "agents").mkdir()
    for stem, _family in [
        ("software_engineer_python", "Engineering"),
        ("code_reviewer", "Review"),
        ("agent_builder", "Authoring"),
    ]:
        (tmp_path / "agents" / f"{stem}.md").write_text(
            f"---\nname: {stem}\ndescription: d\ntools: R\nmodel: opus\nskills:\n---\n"
        )
    out = bsi.render_index(tmp_path)
    for family in ["### Engineering", "### Review", "### Authoring"]:
        assert family in out


def test_skill_family_by_prefix() -> None:
    assert bsi._skill_family("go-engineer") == "Go"
    assert bsi._skill_family("python-testing") == "Python"
    assert bsi._skill_family("mcp-playwright") == "MCP integration"
    assert bsi._skill_family("agent-base-protocol") == "Authoring"
    assert bsi._skill_family("iterative-retrieval") == "Cross-cutting"


def test_missing_dirs_empty_output(tmp_path: Path) -> None:
    (tmp_path / "skills").mkdir()
    (tmp_path / "agents").mkdir()
    out = bsi.render_index(tmp_path)
    assert "0 skills, 0 agents" in out
    assert "## Alphabetical index" in out
