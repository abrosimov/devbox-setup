#!/usr/bin/env python3
"""Tests for validate_config.py command-namespace checks.

Run from any directory:
    pytest roles/devbox/files/dot_claude/bin/test_validate_config.py

Focus: the techne- namespace guards added to ``check_commands`` (filename
prefix) and the ``check_command_refs`` check (dangling refs + bare-name
warnings), including the boundary cases that must NOT be flagged.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
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


def test_skill_reference_files_are_not_command_scanned(tmp_path: Path) -> None:
    root = _build_root(
        tmp_path,
        ["audit"],
        {"skills/fpf-thinking/references/spec.md": "Use `/audit`, not `/techne-ghost`.\n"},
    )
    errors, warnings = vc.check_command_refs(root)
    assert "CMD_BARE" not in _codes(warnings)
    assert "CMD_REF" not in _codes(errors)


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


def test_hidden_dir_not_scanned(tmp_path: Path) -> None:
    # Tool caches like .hypothesis/, .pytest_cache/, .venv/ harvest string
    # literals from source and store them in nested files. Those blobs must not
    # be scanned — they would report dangling refs for every command mentioned
    # anywhere in the code base.
    root = _build_root(
        tmp_path,
        ["plan"],
        {
            "agents/.hypothesis/constants/blob": (
                "# file: skills/x/scan.py\n"
                "somewhere in a harvested literal: /techne-ghost and /techne-plan\n"
            ),
            "skills/foo/.pytest_cache/v/cache/nodeids": "/techne-ghost::x\n",
        },
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


# --- check_fpf_spec_refs: skill ids resolve in the vendored spec --------------


_SPEC = """# First Principles Framework (FPF)
## A.1 - Holon Ontic Foundation
### A.1:4 - Solution
### A.1:End
## C.32.P2S - Problem to Structure
## E.11.PUA \u2014 Pattern Use in a Working Situation
## **A.22.CGUS** - Constraint-Governed Unfolding Structure
# **Part H - Reserved**
"""


def _build_fpf_root(tmp_path: Path, skill_body: str, spec: str | None = _SPEC) -> Path:
    skill_dir = tmp_path / "skills" / "fpf-thinking"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: fpf-thinking\ndescription: f\n---\n{skill_body}\n"
    )
    if spec is not None:
        references = skill_dir / "references"
        references.mkdir()
        (references / "FPF-Spec.md").write_text(spec)
    return tmp_path


def test_fpf_refs_resolved_ids_pass(tmp_path: Path) -> None:
    root = _build_fpf_root(tmp_path, "Route via `C.32.P2S`, then A.1 and `E.11.PUA`.")
    errors, warnings = vc.check_fpf_spec_refs(root)
    assert errors == []
    assert warnings == []


def test_fpf_refs_dangling_id_errors(tmp_path: Path) -> None:
    root = _build_fpf_root(tmp_path, "Inspect `C.99.GONE` for this.")
    errors, _ = vc.check_fpf_spec_refs(root)
    assert _codes(errors) == ["FPF_REFS"]
    assert "C.99.GONE" in errors[0]


def test_fpf_refs_bold_header_defines_id(tmp_path: Path) -> None:
    root = _build_fpf_root(tmp_path, "See `A.22.CGUS`.")
    errors, _ = vc.check_fpf_spec_refs(root)
    assert errors == []


_NSTD_SPEC = """# Narrativization framework
## NSTD.1 - Source-Structure Intake
### NSTD.1:4 - Solution
### NSTD.1:End
## NSTD.6 — Rendering Quality Evaluation
"""


def _build_nstd_root(tmp_path: Path, skill_body: str, spec: str | None = _NSTD_SPEC) -> Path:
    fpf_dir = tmp_path / "skills" / "fpf-thinking"
    references = fpf_dir / "references"
    references.mkdir(parents=True)
    (fpf_dir / "SKILL.md").write_text(
        "---\nname: fpf-thinking\ndescription: f\n---\nNo ids here.\n"
    )
    (references / "FPF-Spec.md").write_text(_SPEC)
    if spec is not None:
        (references / "Narrativization-and-Narrative-Studies-Principles-Framework.md").write_text(
            spec
        )

    narrative_dir = tmp_path / "skills" / "narrative-thinking"
    narrative_dir.mkdir()
    (narrative_dir / "SKILL.md").write_text(
        f"---\nname: narrative-thinking\ndescription: n\n---\n{skill_body}\n"
    )
    return tmp_path


def test_nstd_refs_resolved_ids_pass(tmp_path: Path) -> None:
    root = _build_nstd_root(tmp_path, "Start at `NSTD.1`, evaluate through NSTD.6.")
    errors, warnings = vc.check_fpf_spec_refs(root)
    assert errors == []
    assert warnings == []


def test_nstd_refs_dangling_id_errors(tmp_path: Path) -> None:
    root = _build_nstd_root(tmp_path, "Inspect `NSTD.99`.")
    errors, _ = vc.check_fpf_spec_refs(root)
    assert _codes(errors) == ["NSTD_REFS"]
    assert "NSTD.99" in errors[0]


def test_nstd_refs_missing_spec_warns(tmp_path: Path) -> None:
    root = _build_nstd_root(tmp_path, "Inspect `NSTD.1`.", spec=None)
    errors, warnings = vc.check_fpf_spec_refs(root)
    assert errors == []
    assert _codes(warnings) == ["NSTD_REFS"]


def test_fpf_refs_ignores_grep_patterns_and_fences(tmp_path: Path) -> None:
    body = (
        "Grep `^#+ C\\.11:` to list slots, or `^#+ [A-G]\\.` for any part.\n"
        "```\n"
        'Grep(pattern="^#+ Z.9 ")\n'
        "C.98.NOPE\n"
        "```\n"
    )
    root = _build_fpf_root(tmp_path, body)
    errors, _ = vc.check_fpf_spec_refs(root)
    assert errors == []


def test_fpf_refs_missing_spec_warns(tmp_path: Path) -> None:
    root = _build_fpf_root(tmp_path, "See A.1.", spec=None)
    errors, warnings = vc.check_fpf_spec_refs(root)
    assert errors == []
    assert _codes(warnings) == ["FPF_REFS"]


def test_fpf_refs_no_skill_is_silent(tmp_path: Path) -> None:
    errors, warnings = vc.check_fpf_spec_refs(tmp_path)
    assert errors == []
    assert warnings == []


def test_fpf_refs_unparsable_spec_errors(tmp_path: Path) -> None:
    root = _build_fpf_root(tmp_path, "See A.1.", spec="# FPF\n\nno pattern headers here\n")
    errors, _ = vc.check_fpf_spec_refs(root)
    assert _codes(errors) == ["FPF_REFS"]
    assert "format changed" in errors[0]


# ---------------------------------------------------------------------------
# check_hook_hermeticity
# ---------------------------------------------------------------------------


def _build_hooks_root(tmp_path: Path, command: str) -> Path:
    document = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": command}]}]}}
    (tmp_path / "hooks.json").write_text(json.dumps(document), encoding="utf-8")
    return tmp_path


def _no_plugins(tmp_path: Path) -> Path:
    """An absent plugin cache — keeps the check independent of machine state."""
    return tmp_path / "absent-plugin-cache"


_PINNED = "~/.claude/bin/.venv/bin/python ~/.claude/bin/vendor/langfuse_hook.py"


def test_hermeticity_accepts_the_pinned_venv_interpreter(tmp_path: Path) -> None:
    root = _build_hooks_root(tmp_path, _PINNED)
    errors, warnings = vc.check_hook_hermeticity(root, _no_plugins(tmp_path))
    assert errors == []
    assert warnings == []


def test_hermeticity_accepts_a_plain_executable(tmp_path: Path) -> None:
    root = _build_hooks_root(tmp_path, "~/.claude/bin/worktree-create")
    errors, _ = vc.check_hook_hermeticity(root, _no_plugins(tmp_path))
    assert errors == []


@pytest.mark.parametrize(
    "command",
    [
        'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}"/hooks/langfuse_hook.py',
        "uvx ruff check .",
        "npx some-hook",
        "pip install thing && thing",
    ],
)
def test_hermeticity_rejects_invocation_time_resolution(tmp_path: Path, command: str) -> None:
    root = _build_hooks_root(tmp_path, command)
    errors, _ = vc.check_hook_hermeticity(root, _no_plugins(tmp_path))
    assert _codes(errors) == ["HOOK_HERMETICITY"]
    assert "resolves dependencies at invocation time" in errors[0]


@pytest.mark.parametrize(
    "command",
    [
        "python3 ~/.claude/bin/universal_logger.py Stop",
        "/usr/bin/env python3 ~/.codex/bin/universal_logger.py Stop",
        "node ~/.claude/bin/thing.mjs",
    ],
)
def test_hermeticity_rejects_ambient_interpreters(tmp_path: Path, command: str) -> None:
    root = _build_hooks_root(tmp_path, command)
    errors, _ = vc.check_hook_hermeticity(root, _no_plugins(tmp_path))
    assert _codes(errors) == ["HOOK_HERMETICITY"]
    assert "ambient interpreter" in errors[0]


def test_hermeticity_ignores_unparsable_documents(tmp_path: Path) -> None:
    (tmp_path / "hooks.json").write_text("{not json", encoding="utf-8")
    errors, warnings = vc.check_hook_hermeticity(tmp_path, _no_plugins(tmp_path))
    assert errors == []
    assert warnings == []


def test_hermeticity_reports_every_event(tmp_path: Path) -> None:
    document = {
        "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "uv run --script x.py"}]}],
            "SessionEnd": [{"hooks": [{"type": "command", "command": _PINNED}]}],
        }
    }
    (tmp_path / "hooks.json").write_text(json.dumps(document), encoding="utf-8")
    errors, _ = vc.check_hook_hermeticity(tmp_path, _no_plugins(tmp_path))
    assert len(errors) == 1
    assert "(Stop)" in errors[0]


def _build_codex_root(tmp_path: Path, command: str) -> Path:
    codex_root = tmp_path / "dot_codex"
    codex_root.mkdir()
    (codex_root / "config.toml.j2").write_text(
        f'[[hooks.Stop]]\n[[hooks.Stop.hooks]]\ntype = "command"\ncommand = "{command}"\n',
        encoding="utf-8",
    )
    return codex_root


def test_hermeticity_accepts_the_codex_pinned_venv(tmp_path: Path) -> None:
    codex_root = _build_codex_root(
        tmp_path,
        "~/.codex/bin/.venv/bin/python ~/.codex/bin/universal_logger.py Stop",
    )
    errors, _ = vc.check_hook_hermeticity(tmp_path, _no_plugins(tmp_path), codex_root=codex_root)
    assert errors == []


def test_hermeticity_rejects_codex_ambient_interpreter(tmp_path: Path) -> None:
    codex_root = _build_codex_root(
        tmp_path,
        "/usr/bin/env python3 ~/.codex/bin/universal_logger.py Stop",
    )
    errors, _ = vc.check_hook_hermeticity(tmp_path, _no_plugins(tmp_path), codex_root=codex_root)
    assert _codes(errors) == ["HOOK_HERMETICITY"]
    assert "config.toml.j2 (Stop)" in errors[0]


def test_hermeticity_skips_codex_when_root_is_absent(tmp_path: Path) -> None:
    errors, warnings = vc.check_hook_hermeticity(
        tmp_path, _no_plugins(tmp_path), codex_root=tmp_path / "missing"
    )
    assert errors == []
    assert warnings == []
