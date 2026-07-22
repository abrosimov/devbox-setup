"""Tests for scripts/apply_w2_frontmatter.py.

Focus: idempotency, safe-by-default (no overwrite without --force), and
correct placement of new fields inside the frontmatter block.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "apply_w2_frontmatter.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("apply_w2_frontmatter", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["apply_w2_frontmatter"] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def _make_patch(tmp_path: Path, kind: str, name: str, body: str, **kwargs):
    file = tmp_path / f"{name}.md"
    file.write_text(body)
    return mod.Patch(
        kind=kind,
        name=name,
        file=file,
        problem=kwargs.get("problem", "Problem statement."),
        related=kwargs.get("related", ["alpha", "beta"]),
    )


BASE = """---
name: test
description: t
---

# Body
"""


def test_adds_fields_when_absent(tmp_path: Path) -> None:
    patch = _make_patch(tmp_path, "skill", "s", BASE)
    new, changed, notes = mod.apply_patch(BASE, patch, force=False)
    assert changed is True
    assert notes == []
    assert 'problem: "Problem statement."' in new
    assert "related: [alpha, beta]" in new
    assert new.index("problem:") < new.index("\n---\n", new.index("problem:"))


def test_idempotent_second_run(tmp_path: Path) -> None:
    patch = _make_patch(tmp_path, "skill", "s", BASE)
    first, _, _ = mod.apply_patch(BASE, patch, force=False)
    second, changed, notes = mod.apply_patch(first, patch, force=False)
    assert changed is False
    assert first == second
    assert any("problem: already set" in n for n in notes)


def test_refuse_overwrite_without_force(tmp_path: Path) -> None:
    body = '---\nname: s\ndescription: d\nproblem: "old"\nrelated: [old]\n---\nbody\n'
    patch = _make_patch(tmp_path, "skill", "s", body, problem="new", related=["fresh"])
    new, changed, notes = mod.apply_patch(body, patch, force=False)
    assert changed is False
    assert new == body
    assert any("problem:" in n for n in notes)
    assert any("related:" in n for n in notes)


def test_force_overwrites(tmp_path: Path) -> None:
    body = '---\nname: s\ndescription: d\nproblem: "old"\nrelated: [old]\n---\nbody\n'
    patch = _make_patch(tmp_path, "skill", "s", body, problem="new", related=["fresh"])
    new, changed, _ = mod.apply_patch(body, patch, force=True)
    assert changed is True
    assert 'problem: "new"' in new
    assert "related: [fresh]" in new
    assert "old" not in new


def test_empty_problem_skipped(tmp_path: Path) -> None:
    patch = _make_patch(tmp_path, "skill", "s", BASE, problem="", related=["a"])
    new, changed, _ = mod.apply_patch(BASE, patch, force=False)
    assert changed is True
    assert "problem:" not in new
    assert "related: [a]" in new


def test_empty_related_renders_bracket(tmp_path: Path) -> None:
    patch = _make_patch(tmp_path, "skill", "s", BASE, problem="p", related=[])
    new, _, _ = mod.apply_patch(BASE, patch, force=False)
    assert "related: []" in new


def test_preserves_block_style_triggers(tmp_path: Path) -> None:
    body = "---\nname: s\ndescription: d\ntriggers:\n  - foo\n  - bar\n---\nbody\n"
    patch = _make_patch(tmp_path, "skill", "s", body)
    new, changed, _ = mod.apply_patch(body, patch, force=False)
    assert changed is True
    assert "  - foo" in new
    assert "  - bar" in new
    assert "triggers:" in new
    assert "problem:" in new


def test_no_frontmatter_leaves_content_untouched(tmp_path: Path) -> None:
    body = "no frontmatter here\n"
    patch = _make_patch(tmp_path, "skill", "s", body)
    new, changed, notes = mod.apply_patch(body, patch, force=False)
    assert changed is False
    assert new == body
    assert any("no frontmatter" in n for n in notes)


def test_quote_escaping_double_quote() -> None:
    quoted = mod._quote_yaml_string('has "quote" inside')
    assert quoted == r'"has \"quote\" inside"'


def test_quote_escaping_backslash() -> None:
    quoted = mod._quote_yaml_string(r"has \backslash")
    assert quoted == r'"has \\backslash"'


def test_format_related_flow_style() -> None:
    assert mod._format_related(["a", "b", "c"]) == "[a, b, c]"
    assert mod._format_related([]) == "[]"
