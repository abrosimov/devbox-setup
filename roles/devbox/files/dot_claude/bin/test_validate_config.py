#!/usr/bin/env python3
"""Tests for validate_config.py command-namespace checks.

Run from any directory:
    pytest roles/devbox/files/dot_claude/bin/test_validate_config.py

Focus: the techne- namespace guards added to ``check_commands`` (filename
prefix) and the ``check_command_refs`` check (dangling refs + bare-name
warnings), including the boundary cases that must NOT be flagged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import validate_config as vc

if TYPE_CHECKING:
    from pathlib import Path


def _codes(messages: list[str]) -> list[str]:
    return [m[m.index("[") + 1 : m.index("]")] for m in messages if "[" in m]


def _build_root(tmp_path: Path, stems: list[str], files: dict[str, str]) -> Path:
    (tmp_path / "commands").mkdir()
    for stem in stems:
        (tmp_path / "commands" / f"techne-{stem}.md").write_text(
            f"---\ndescription: {stem}\n---\nbody\n"
        )
    for rel, content in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return tmp_path


# --- check_commands: techne- filename prefix ----------------------------------


def test_prefixed_file_passes(tmp_path: Path) -> None:
    root = _build_root(tmp_path, ["plan"], {})
    errors, _ = vc.check_commands(root)
    assert "CMD_PREFIX" not in _codes(errors)


def test_unprefixed_file_errors(tmp_path: Path) -> None:
    root = _build_root(tmp_path, ["plan"], {})
    (root / "commands" / "deploy.md").write_text("---\ndescription: bad\n---\nbody\n")
    errors, _ = vc.check_commands(root)
    assert "CMD_PREFIX" in _codes(errors)


def test_missing_description_still_errors(tmp_path: Path) -> None:
    root = _build_root(tmp_path, [], {})
    (root / "commands" / "techne-x.md").write_text("---\nname: x\n---\nbody\n")
    errors, _ = vc.check_commands(root)
    assert "CMD_FIELD" in _codes(errors)


# --- check_command_refs: dangling /techne-<x> references ---------------------


def test_valid_techne_ref_passes(tmp_path: Path) -> None:
    root = _build_root(tmp_path, ["plan"], {"agents/a.md": "See `/techne-plan` here.\n"})
    errors, _ = vc.check_command_refs(root)
    assert "CMD_REF" not in _codes(errors)


def test_dangling_techne_ref_errors(tmp_path: Path) -> None:
    root = _build_root(tmp_path, ["plan"], {"agents/a.md": "Run `/techne-deploy`.\n"})
    errors, _ = vc.check_command_refs(root)
    assert "CMD_REF" in _codes(errors)


def test_dangling_ref_in_docs_still_errors(tmp_path: Path) -> None:
    root = _build_root(tmp_path, ["plan"], {"docs/spec.md": "uses `/techne-ghost`\n"})
    errors, _ = vc.check_command_refs(root)
    assert "CMD_REF" in _codes(errors)


# --- check_command_refs: bare-name warnings -----------------------------------


def test_bare_command_warns(tmp_path: Path) -> None:
    root = _build_root(tmp_path, ["plan", "test"], {"agents/a.md": "Run `/plan` then `/test`.\n"})
    _, warnings = vc.check_command_refs(root)
    assert _codes(warnings).count("CMD_BARE") == 2


def test_bare_name_in_docs_not_flagged(tmp_path: Path) -> None:
    root = _build_root(tmp_path, ["audit"], {"docs/spec.md": "expose endpoint `/audit` here\n"})
    _, warnings = vc.check_command_refs(root)
    assert "CMD_BARE" not in _codes(warnings)


def test_host_only_dir_not_scanned(tmp_path: Path) -> None:
    root = _build_root(tmp_path, ["plan"], {"projects/p.md": "Run `/plan` and `/techne-ghost`.\n"})
    errors, warnings = vc.check_command_refs(root)
    assert "CMD_BARE" not in _codes(warnings)
    assert "CMD_REF" not in _codes(errors)


# --- check_command_refs: no false positives ----------------------------------


def test_path_and_url_tokens_clean(tmp_path: Path) -> None:
    content = (
        "Refs: `/techne-plan`, `/techne-test`.\n"
        "Paths: commands/techne-plan.md, plan.md, the design/ dir, "
        "schema_field, http://test/x, src/test, a/plan/b.\n"
    )
    root = _build_root(tmp_path, ["plan", "test", "design", "schema"], {"agents/a.md": content})
    errors, warnings = vc.check_command_refs(root)
    assert _codes(errors).count("CMD_REF") == 0
    assert _codes(warnings).count("CMD_BARE") == 0


def test_hyphenated_stem_resolves(tmp_path: Path) -> None:
    root = _build_root(
        tmp_path,
        ["api-design", "full-cycle"],
        {"agents/a.md": "Use `/techne-api-design` and `/techne-full-cycle`.\n"},
    )
    errors, _ = vc.check_command_refs(root)
    assert _codes(errors).count("CMD_REF") == 0


def test_test_prefixed_file_excluded(tmp_path: Path) -> None:
    root = _build_root(
        tmp_path,
        ["plan"],
        {"bin/test_thing.py": "fixture = '/techne-ghost'\nbare = '/plan'\n"},
    )
    errors, warnings = vc.check_command_refs(root)
    assert _codes(errors).count("CMD_REF") == 0
    assert _codes(warnings).count("CMD_BARE") == 0


def test_test_suffixed_file_excluded(tmp_path: Path) -> None:
    root = _build_root(
        tmp_path,
        ["plan"],
        {"bin/thing_test.py": "fixture = '/techne-ghost'\nbare = '/plan'\n"},
    )
    errors, warnings = vc.check_command_refs(root)
    assert _codes(errors).count("CMD_REF") == 0
    assert _codes(warnings).count("CMD_BARE") == 0


# --- parse_yaml_list: inline + block YAML lists -------------------------------


def test_parse_yaml_list_inline() -> None:
    content = "---\nrelated: [alpha, beta, gamma]\n---\nbody\n"
    assert vc.parse_yaml_list(content, "related") == ["alpha", "beta", "gamma"]


def test_parse_yaml_list_inline_empty() -> None:
    content = "---\nrelated: []\n---\nbody\n"
    assert vc.parse_yaml_list(content, "related") == []


def test_parse_yaml_list_absent() -> None:
    content = "---\nname: x\n---\nbody\n"
    assert vc.parse_yaml_list(content, "related") == []


def test_parse_yaml_list_block() -> None:
    content = "---\ntriggers:\n  - lint\n  - noqa\n  - eslint-disable\n---\nbody\n"
    assert vc.parse_yaml_list(content, "triggers") == ["lint", "noqa", "eslint-disable"]


def test_parse_yaml_list_block_stops_at_next_key() -> None:
    content = "---\ntriggers:\n  - lint\nname: x\n---\nbody\n"
    assert vc.parse_yaml_list(content, "triggers") == ["lint"]


def test_parse_yaml_list_strips_quotes() -> None:
    content = "---\nrelated: [\"alpha\", 'beta']\n---\nbody\n"
    assert vc.parse_yaml_list(content, "related") == ["alpha", "beta"]


# --- check_related_links: dangling related: refs ------------------------------


def _build_related_root(tmp_path: Path) -> Path:
    (tmp_path / "skills" / "alpha").mkdir(parents=True)
    (tmp_path / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: a\n---\nbody\n"
    )
    (tmp_path / "skills" / "beta").mkdir(parents=True)
    (tmp_path / "skills" / "beta" / "SKILL.md").write_text(
        "---\nname: beta\ndescription: b\n---\nbody\n"
    )
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "agent_one.md").write_text(
        "---\nname: agent-one\ndescription: a\ntools: Read\n"
        "model: sonnet\nskills: alpha\n---\nbody\n"
    )
    return tmp_path


def test_related_ref_resolves_to_skill(tmp_path: Path) -> None:
    root = _build_related_root(tmp_path)
    (root / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: a\nrelated: [beta]\n---\nbody\n"
    )
    errors, _ = vc.check_related_links(root)
    assert _codes(errors).count("RELATED_REF") == 0


def test_related_ref_resolves_to_agent(tmp_path: Path) -> None:
    root = _build_related_root(tmp_path)
    (root / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: a\nrelated: [agent_one]\n---\nbody\n"
    )
    errors, _ = vc.check_related_links(root)
    assert _codes(errors).count("RELATED_REF") == 0


def test_related_ref_dangling_errors(tmp_path: Path) -> None:
    root = _build_related_root(tmp_path)
    (root / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: a\nrelated: [nonexistent]\n---\nbody\n"
    )
    errors, _ = vc.check_related_links(root)
    assert _codes(errors).count("RELATED_REF") == 1


def test_related_empty_is_ok(tmp_path: Path) -> None:
    root = _build_related_root(tmp_path)
    (root / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: a\nrelated: []\n---\nbody\n"
    )
    errors, _ = vc.check_related_links(root)
    assert _codes(errors).count("RELATED_REF") == 0


def test_related_absent_is_ok(tmp_path: Path) -> None:
    root = _build_related_root(tmp_path)
    errors, _ = vc.check_related_links(root)
    assert _codes(errors).count("RELATED_REF") == 0


def test_related_dangling_on_agent(tmp_path: Path) -> None:
    root = _build_related_root(tmp_path)
    (root / "agents" / "agent_one.md").write_text(
        "---\nname: agent-one\ndescription: a\ntools: Read\nmodel: sonnet\n"
        "skills: alpha\nrelated: [ghost]\n---\nbody\n"
    )
    errors, _ = vc.check_related_links(root)
    assert _codes(errors).count("RELATED_REF") == 1


# --- check_trigger_consistency: unreachable triggers --------------------------


def _build_trigger_root(tmp_path: Path) -> Path:
    (tmp_path / "skills" / "referenced").mkdir(parents=True)
    (tmp_path / "skills" / "referenced" / "SKILL.md").write_text(
        "---\nname: referenced\ndescription: r\ntriggers:\n  - foo\n---\nbody\n"
    )
    (tmp_path / "skills" / "orphan").mkdir(parents=True)
    (tmp_path / "skills" / "orphan" / "SKILL.md").write_text(
        "---\nname: orphan\ndescription: o\ntriggers:\n  - bar\n---\nbody\n"
    )
    (tmp_path / "skills" / "always").mkdir(parents=True)
    (tmp_path / "skills" / "always" / "SKILL.md").write_text(
        "---\nname: always\ndescription: a\nalwaysApply: true\n---\nbody\n"
    )
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "user.md").write_text(
        "---\nname: user\ndescription: u\ntools: Read\nmodel: sonnet\n"
        "skills: referenced\n---\nbody\n"
    )
    return tmp_path


def test_trigger_orphan_warns(tmp_path: Path) -> None:
    root = _build_trigger_root(tmp_path)
    _, warnings = vc.check_trigger_consistency(root)
    codes = _codes(warnings)
    assert codes.count("TRIGGER_CONSISTENCY") == 1
    assert any("orphan" in w for w in warnings)
    assert not any("referenced" in w for w in warnings)


def test_trigger_alwaysapply_skipped(tmp_path: Path) -> None:
    root = _build_trigger_root(tmp_path)
    _, warnings = vc.check_trigger_consistency(root)
    assert not any("always" in w for w in warnings)


def test_trigger_no_triggers_skipped(tmp_path: Path) -> None:
    (tmp_path / "skills" / "plain").mkdir(parents=True)
    (tmp_path / "skills" / "plain" / "SKILL.md").write_text(
        "---\nname: plain\ndescription: p\n---\nbody\n"
    )
    (tmp_path / "agents").mkdir()
    _, warnings = vc.check_trigger_consistency(tmp_path)
    assert _codes(warnings).count("TRIGGER_CONSISTENCY") == 0
