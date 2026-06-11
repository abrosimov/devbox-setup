#!/usr/bin/env python3
"""Tests for validate-config.py command-namespace checks.

Run from any directory:
    python3 bin/validate_config_test.py
or via unittest discovery / pytest:
    python3 -m unittest bin.validate_config_test
    pytest bin/validate_config_test.py

Focus: the techne- namespace guards added to ``check_commands`` (filename
prefix) and the ``check_command_refs`` check (dangling refs + bare-name
warnings), including the boundary cases that must NOT be flagged.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

# validate-config.py has a hyphen, so it cannot be imported by name.
_SPEC = importlib.util.spec_from_file_location(
    "validate_config", Path(__file__).resolve().parent / "validate-config.py"
)
vc = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(vc)


def _codes(messages: list[str]) -> list[str]:
    """Extract the [CODE] tag from each message."""
    return [m[m.index("[") + 1 : m.index("]")] for m in messages if "[" in m]


class _Fixture(unittest.TestCase):
    """Builds a throwaway config root on disk."""

    def _root(self, stems: list[str], files: dict[str, str]) -> Path:
        tmp = tempfile.mkdtemp()
        root = Path(tmp)
        (root / "commands").mkdir()
        for stem in stems:
            (root / "commands" / f"techne-{stem}.md").write_text(
                f"---\ndescription: {stem}\n---\nbody\n"
            )
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return root


class TestCommandPrefix(_Fixture):
    """check_commands enforces the techne- filename prefix."""

    def test_prefixed_file_passes(self):
        root = self._root(["plan"], {})
        errors, _ = vc.check_commands(root)
        self.assertNotIn("CMD_PREFIX", _codes(errors))

    def test_unprefixed_file_errors(self):
        root = self._root(["plan"], {})
        (root / "commands" / "deploy.md").write_text(
            "---\ndescription: bad\n---\nbody\n"
        )
        errors, _ = vc.check_commands(root)
        self.assertIn("CMD_PREFIX", _codes(errors))

    def test_missing_description_still_errors(self):
        root = self._root([], {})
        (root / "commands" / "techne-x.md").write_text("---\nname: x\n---\nbody\n")
        errors, _ = vc.check_commands(root)
        self.assertIn("CMD_FIELD", _codes(errors))


class TestDanglingRefs(_Fixture):
    """check_command_refs flags /techne-<x> with no backing file."""

    def test_valid_techne_ref_passes(self):
        root = self._root(["plan"], {"agents/a.md": "See `/techne-plan` here.\n"})
        errors, _ = vc.check_command_refs(root)
        self.assertNotIn("CMD_REF", _codes(errors))

    def test_dangling_techne_ref_errors(self):
        root = self._root(["plan"], {"agents/a.md": "Run `/techne-deploy`.\n"})
        errors, _ = vc.check_command_refs(root)
        self.assertIn("CMD_REF", _codes(errors))

    def test_dangling_ref_in_docs_still_errors(self):
        # docs/ is excluded from the bare-name scan but kept for dangling refs.
        root = self._root(["plan"], {"docs/spec.md": "uses `/techne-ghost`\n"})
        errors, _ = vc.check_command_refs(root)
        self.assertIn("CMD_REF", _codes(errors))


class TestBareInvocations(_Fixture):
    """check_command_refs warns on bare names missing the prefix."""

    def test_bare_command_warns(self):
        root = self._root(["plan", "test"], {"agents/a.md": "Run `/plan` then `/test`.\n"})
        _, warnings = vc.check_command_refs(root)
        self.assertEqual(_codes(warnings).count("CMD_BARE"), 2)

    def test_bare_name_in_docs_not_flagged(self):
        root = self._root(["audit"], {"docs/spec.md": "expose endpoint `/audit` here\n"})
        _, warnings = vc.check_command_refs(root)
        self.assertNotIn("CMD_BARE", _codes(warnings))

    def test_host_only_dir_not_scanned(self):
        # projects/ is user content — never scanned, even for dangling refs.
        root = self._root(["plan"], {"projects/p.md": "Run `/plan` and `/techne-ghost`.\n"})
        errors, warnings = vc.check_command_refs(root)
        self.assertNotIn("CMD_BARE", _codes(warnings))
        self.assertNotIn("CMD_REF", _codes(errors))


class TestNoFalsePositives(_Fixture):
    """Path / URL / symbol tokens must never be flagged as bare commands."""

    def test_path_and_url_tokens_clean(self):
        content = (
            "Refs: `/techne-plan`, `/techne-test`.\n"
            "Paths: commands/techne-plan.md, plan.md, the design/ dir, "
            "schema_field, http://test/x, src/test, a/plan/b.\n"
        )
        root = self._root(["plan", "test", "design", "schema"], {"agents/a.md": content})
        errors, warnings = vc.check_command_refs(root)
        self.assertEqual(_codes(errors).count("CMD_REF"), 0)
        self.assertEqual(_codes(warnings).count("CMD_BARE"), 0)

    def test_hyphenated_stem_resolves(self):
        root = self._root(
            ["api-design", "full-cycle"],
            {"agents/a.md": "Use `/techne-api-design` and `/techne-full-cycle`.\n"},
        )
        errors, _ = vc.check_command_refs(root)
        self.assertEqual(_codes(errors).count("CMD_REF"), 0)


if __name__ == "__main__":
    unittest.main()
