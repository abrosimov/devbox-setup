"""Static contract of the TLA+ pins: every tool is pinned by tag and by sha256.

Upstream reissues assets under an unchanged tag, so a tag alone does not name
one artefact. The playbook must trust only the pinned digest: it compares the
digest GitHub reports with the pin, downloads against the pin, and decides on a
reinstall by comparing the recorded digest with the pin.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "roles/devbox/defaults/main/packages.yml"
TOOL_TASKS = ROOT / "roles/devbox/tasks/darwin/install_tlaplus_tool.yml"
BLOCK_KEYS = ("block", "rescue", "always")
PINNED = "devbox_tlaplus_pinned"

Doc = dict


def _tools() -> list[Doc]:
    packages = yaml.safe_load(PACKAGES.read_text(encoding="utf-8"))
    return packages["devbox_packages"]["tlaplus"]["tools"]


def _tasks() -> list[Doc]:
    loaded = yaml.safe_load(TOOL_TASKS.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    return loaded


def _flatten(tasks: list[Doc]) -> Iterator[Doc]:
    for task in tasks:
        yield task
        for key in BLOCK_KEYS:
            if key in task:
                yield from _flatten(task[key])


def _find(name_part: str) -> Doc:
    matches = [task for task in _flatten(_tasks()) if name_part in str(task.get("name", ""))]
    assert len(matches) == 1, f"expected one task named like {name_part!r}, got {len(matches)}"
    return matches[0]


class TestPinShape:
    def test_every_tool_has_exactly_the_pin_keys(self) -> None:
        for tool in _tools():
            assert set(tool) == {"name", "repository", "tag", "asset", "sha256"}, tool["name"]

    def test_every_sha256_is_64_lowercase_hex_without_prefix(self) -> None:
        for tool in _tools():
            assert re.fullmatch(r"[0-9a-f]{64}", tool["sha256"]), tool["name"]

    def test_tags_and_digests_are_strings(self) -> None:
        for tool in _tools():
            assert isinstance(tool["tag"], str), tool["name"]
            assert isinstance(tool["sha256"], str), tool["name"]

    def test_tool_names_and_digests_are_unique(self) -> None:
        tools = _tools()
        assert len({tool["name"] for tool in tools}) == len(tools)
        assert len({tool["sha256"] for tool in tools}) == len(tools)


class TestInstallTrustsOnlyThePin:
    def test_pin_shape_is_asserted_before_anything_else(self) -> None:
        first = _tasks()[0]
        assert "ansible.builtin.assert" in first
        assert "devbox_tlaplus_tool.sha256" in str(first["ansible.builtin.assert"]["that"])

    def test_pinned_digest_carries_the_github_prefix(self) -> None:
        task = _find("Resolve install path and pinned digest")
        assert task["ansible.builtin.set_fact"][PINNED] == "sha256:{{ devbox_tlaplus_tool.sha256 }}"

    def test_github_digest_must_equal_the_pin(self) -> None:
        task = _find("Require GitHub to report the pinned digest")
        assertion = task["ansible.builtin.assert"]
        conditions = assertion["that"]
        assert any(PINNED in c and "devbox_tlaplus_asset.digest" in c for c in conditions)
        message = assertion["fail_msg"]
        for needle in ("devbox_tlaplus_tool.tag", "devbox_tlaplus_asset.digest", PINNED):
            assert needle in message

    def test_download_is_checked_against_the_pin(self) -> None:
        task = _find("Download")
        assert task["ansible.builtin.get_url"]["checksum"] == "{{ " + PINNED + " }}"

    def test_recorded_digest_is_the_pin(self) -> None:
        task = _find("Record digest")
        assert PINNED in task["ansible.builtin.copy"]["content"]

    def test_reinstall_decision_compares_with_the_pin(self) -> None:
        task = _find("Compare installed and pinned digest")
        expression = task["ansible.builtin.set_fact"]["devbox_tlaplus_outdated"]
        assert PINNED in expression
        assert "devbox_tlaplus_asset" not in expression

    def test_reported_digest_is_never_trusted_downstream(self) -> None:
        guard = _find("Require GitHub to report the pinned digest")
        for task in _flatten(_tasks()):
            if task.get("name") == guard["name"]:
                continue
            assert "devbox_tlaplus_asset.digest" not in str(task), task.get("name")


class TestDryRun:
    def test_check_mode_reports_instead_of_staging(self) -> None:
        report = _find("Report pending release")
        assert "ansible_check_mode" in report["when"]
        assert "not ansible_check_mode" not in report["when"]
        install = _find("Install new release")
        assert "not ansible_check_mode" in install["when"]
