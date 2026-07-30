"""Tests for scripts/lint_ansible_semantics.py.

Focus: the intra-task set_fact self-reference rule flags a value that references a
sibling key of the same set_fact, and leaves the two-task (correct) form alone.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lint_ansible_semantics.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lint_ansible_semantics", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["lint_ansible_semantics"] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()

BAD = """\
- name: resolve
  ansible.builtin.set_fact:
    my_version: "{{ (lookup('file', 'x') | from_yaml).v }}"
    my_url: "{{ base }}/{{ my_version }}/bin"
"""

CLEAN = """\
- name: resolve version
  ansible.builtin.set_fact:
    my_version: "{{ (lookup('file', 'x') | from_yaml).v }}"

- name: resolve url
  ansible.builtin.set_fact:
    my_url: "{{ base }}/{{ my_version }}/bin"
"""


def test_flags_intra_task_self_reference(tmp_path: Path) -> None:
    path = tmp_path / "bad.yml"
    path.write_text(BAD)

    findings, inspected = mod.check_file(path)

    assert inspected == 1
    assert len(findings) == 1
    finding = findings[0]
    assert (
        finding.message == "set_fact key 'my_url' references sibling key 'my_version' defined in "
        "the same task — split into two set_fact tasks"
    )
    assert finding.line == 1


def test_clean_two_task_form_passes(tmp_path: Path) -> None:
    path = tmp_path / "clean.yml"
    path.write_text(CLEAN)

    findings, inspected = mod.check_file(path)

    assert findings == []
    assert inspected == 2


def test_word_boundary_ignores_prefix_siblings(tmp_path: Path) -> None:
    path = tmp_path / "prefix.yml"
    path.write_text(
        "- name: prefix\n"
        "  set_fact:\n"
        '    my_version: "1"\n'
        '    my_version_extra: "{{ my_version }}-extra"\n'
        '    plain: "{{ my_version_extra }}"\n'
    )

    findings, _ = mod.check_file(path)

    referenced = {(f.message.split("'")[1], f.message.split("'")[3]) for f in findings}
    assert ("my_version_extra", "my_version") in referenced
    assert ("plain", "my_version_extra") in referenced
    assert ("plain", "my_version") not in referenced


def test_non_task_mapping_file_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "vars.yml"
    path.write_text("some_key: value\nother_key: '{{ some_key }}'\n")

    findings, inspected = mod.check_file(path)

    assert findings == []
    assert inspected == 0
