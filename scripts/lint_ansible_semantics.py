#!/usr/bin/env python3
"""Static linter for Ansible semantic footguns invisible to yamllint/ansible-lint.

Ansible templates every key of a single ``set_fact`` against the *pre-task* variable
scope, so a value that references a sibling key defined in the same ``set_fact``
resolves to "undefined" only at run time. ``--syntax-check`` cannot see it.

The rule registry (``_RULES``) is deliberately open: add a checker to grow coverage.
Implemented so far: intra-task ``set_fact`` self-reference.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

import yaml

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_SET_FACT_KEYS: Final = ("set_fact", "ansible.builtin.set_fact")
_CONTROL_KEYS: Final = frozenset({"cacheable"})
_LINE_KEY: Final = "__line__"
# block/rescue/always nest task lists; the *_tasks/handlers keys nest them at play level.
_TASK_LIST_KEYS: Final = (
    "block",
    "rescue",
    "always",
    "tasks",
    "pre_tasks",
    "post_tasks",
    "handlers",
)
_JINJA_EXPR: Final = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
_SCAN_DIRS: Final = ("roles", "playbooks")
_YAML_GLOBS: Final = ("*.yml", "*.yaml")
_MESSAGE: Final = (
    "set_fact key '{key}' references sibling key '{sibling}' defined in the "
    "same task — split into two set_fact tasks"
)


class Finding(NamedTuple):
    path: Path
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


class _LineLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _LineLoader, node: yaml.nodes.MappingNode) -> dict[object, object]:
    mapping = yaml.SafeLoader.construct_mapping(loader, node, deep=True)
    mapping[_LINE_KEY] = node.start_mark.line + 1
    return mapping


_LineLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _load_docs(path: Path) -> list[object]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        return [doc for doc in yaml.load_all(text, Loader=_LineLoader) if doc is not None]
    except yaml.YAMLError:
        return []


def _iter_tasks(node: object) -> Iterator[dict[object, object]]:
    if not isinstance(node, list):
        return
    for item in node:
        if not isinstance(item, dict):
            continue
        yield item
        for key in _TASK_LIST_KEYS:
            yield from _iter_tasks(item.get(key))


def _set_fact_mapping(task: dict[object, object]) -> dict[object, object] | None:
    for name in _SET_FACT_KEYS:
        value = task.get(name)
        if isinstance(value, dict):
            return value
    return None


def _fact_keys(facts: dict[object, object]) -> list[str]:
    return [
        key
        for key in facts
        if isinstance(key, str) and key != _LINE_KEY and key not in _CONTROL_KEYS
    ]


def _task_line(task: dict[object, object], facts: dict[object, object]) -> int:
    for source in (task, facts):
        line = source.get(_LINE_KEY)
        if isinstance(line, int):
            return line
    return 0


def _jinja_haystack(value: object) -> str:
    text = value if isinstance(value, str) else str(value)
    return "\n".join(_JINJA_EXPR.findall(text))


def check_set_fact_self_reference(
    path: Path, tasks: list[dict[object, object]]
) -> Iterator[Finding]:
    for task in tasks:
        facts = _set_fact_mapping(task)
        if facts is None:
            continue
        keys = _fact_keys(facts)
        patterns = {key: re.compile(rf"\b{re.escape(key)}\b") for key in keys}
        line = _task_line(task, facts)
        for key in keys:
            haystack = _jinja_haystack(facts[key])
            if not haystack:
                continue
            for sibling in keys:
                if sibling != key and patterns[sibling].search(haystack):
                    yield Finding(path, line, _MESSAGE.format(key=key, sibling=sibling))


_RULES: Final[tuple[Callable[[Path, list[dict[object, object]]], Iterator[Finding]], ...]] = (
    check_set_fact_self_reference,
)


def check_file(path: Path) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    inspected = 0
    for doc in _load_docs(path):
        tasks = list(_iter_tasks(doc))
        inspected += sum(1 for task in tasks if _set_fact_mapping(task) is not None)
        for rule in _RULES:
            findings.extend(rule(path, tasks))
    return findings, inspected


def iter_yaml_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for scan_dir in _SCAN_DIRS:
        base = root / scan_dir
        if not base.is_dir():
            continue
        for pattern in _YAML_GLOBS:
            files.update(base.rglob(pattern))
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    findings: list[Finding] = []
    inspected = 0
    for path in iter_yaml_files(root):
        file_findings, count = check_file(path)
        findings.extend(file_findings)
        inspected += count
    for finding in findings:
        print(finding.render())
    if findings:
        print(f"FAIL: {len(findings)} intra-task set_fact self-reference(s) found")
        return 1
    print(f"ok: {inspected} set_fact tasks checked, no intra-task self-references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
