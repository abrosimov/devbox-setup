#!/usr/bin/env python3
"""Tests for validate-config.py command-namespace checks.

Run from any directory:
    pytest roles/devbox/files/dot_claude/bin/test_validate_config.py

Focus: the techne- namespace guards added to ``check_commands`` (filename
prefix) and the ``check_command_refs`` check (dangling refs + bare-name
warnings), including the boundary cases that must NOT be flagged.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

# validate-config.py has a hyphen, so it cannot be imported by name.
_SPEC = importlib.util.spec_from_file_location(
    "validate_config", Path(__file__).resolve().parent / "validate-config.py"
)
if _SPEC is None or _SPEC.loader is None:
    msg = "Failed to load validate-config.py module spec"
    raise RuntimeError(msg)
vc: ModuleType = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vc)


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
    # docs/ is excluded from the bare-name scan but kept for dangling refs.
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
    # projects/ is user content — never scanned, even for dangling refs.
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
    # bin/test_*.py carries fixture strings that must not trip the scan.
    root = _build_root(
        tmp_path,
        ["plan"],
        {"bin/test_thing.py": "fixture = '/techne-ghost'\nbare = '/plan'\n"},
    )
    errors, warnings = vc.check_command_refs(root)
    assert _codes(errors).count("CMD_REF") == 0
    assert _codes(warnings).count("CMD_BARE") == 0


def test_test_suffixed_file_excluded(tmp_path: Path) -> None:
    # Defensive: legacy *_test.py naming must also be skipped.
    root = _build_root(
        tmp_path,
        ["plan"],
        {"bin/thing_test.py": "fixture = '/techne-ghost'\nbare = '/plan'\n"},
    )
    errors, warnings = vc.check_command_refs(root)
    assert _codes(errors).count("CMD_REF") == 0
    assert _codes(warnings).count("CMD_BARE") == 0
