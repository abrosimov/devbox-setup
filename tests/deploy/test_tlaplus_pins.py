"""Static contract of the TLA+ pins: every tool is pinned by release tag only.

Upstream reissues assets under an unchanged tag, so the playbook follows the
digest GitHub reports for the pinned tag instead of declaring one. That digest
is shape-checked before anything uses it; the download is verified against it,
it is recorded as the installed digest, and a reinstall happens when the
recorded digest differs from it.
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
ENTRY_TASKS = ROOT / "roles/devbox/tasks/darwin/install_tlaplus.yml"
BLOCK_KEYS = ("block", "rescue", "always")
REPORTED = "devbox_tlaplus_asset.digest"
GH_AUTH = "devbox_tlaplus_gh_auth"

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


def _entry_tasks() -> list[Doc]:
    loaded = yaml.safe_load(ENTRY_TASKS.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    return loaded


def _condition(task: Doc) -> str:
    when = task["when"]
    return " ".join(when) if isinstance(when, list) else str(when)


def _lookup_tasks() -> tuple[Doc, Doc]:
    return _find("via authenticated gh"), _find("via anonymous API")


class TestPinShape:
    def test_every_tool_has_exactly_the_pin_keys(self) -> None:
        for tool in _tools():
            assert set(tool) == {"name", "repository", "tag", "asset"}, tool["name"]

    def test_tags_are_strings(self) -> None:
        for tool in _tools():
            assert isinstance(tool["tag"], str), tool["name"]

    def test_tool_names_are_unique(self) -> None:
        tools = _tools()
        assert len({tool["name"] for tool in tools}) == len(tools)


class TestInstallFollowsTheReportedDigest:
    def test_reported_digest_is_shape_checked(self) -> None:
        task = _find("Require a sha256 digest")
        conditions = task["ansible.builtin.assert"]["that"]
        assert any("devbox_tlaplus_asset.browser_download_url is defined" in c for c in conditions)
        assert any(
            REPORTED in c and "is match" in c and "^sha256:[0-9a-f]{64}$" in c for c in conditions
        )

    def test_shape_check_names_the_release_and_asset_on_failure(self) -> None:
        message = _find("Require a sha256 digest")["ansible.builtin.assert"]["fail_msg"]
        for needle in (
            "devbox_tlaplus_tool.repository",
            "devbox_tlaplus_tool.tag",
            "devbox_tlaplus_tool.asset",
        ):
            assert needle in message

    def test_shape_check_follows_asset_selection_and_precedes_every_use(self) -> None:
        names = [str(task.get("name", "")) for task in _tasks()]

        def position(prefix: str) -> int:
            return next(i for i, name in enumerate(names) if name.startswith(prefix))

        check = position("Require a sha256 digest")
        assert position("Select asset") < check
        assert check < position("Compare installed and released digest")
        assert check < position("Report pending release")
        assert check < position("Install new release")

    def test_download_is_checked_against_the_reported_digest(self) -> None:
        task = _find("Download")
        assert task["ansible.builtin.get_url"]["checksum"] == "{{ " + REPORTED + " }}"

    def test_recorded_digest_is_the_reported_digest(self) -> None:
        task = _find("Record digest")
        assert REPORTED in task["ansible.builtin.copy"]["content"]

    def test_reinstall_decision_compares_with_the_reported_digest(self) -> None:
        task = _find("Compare installed and released digest")
        expression = task["ansible.builtin.set_fact"]["devbox_tlaplus_outdated"]
        assert "devbox_tlaplus_installed.content" in expression
        assert REPORTED in expression
        assert "devbox_tlaplus_tool" not in expression

    def test_nothing_reads_a_digest_from_the_tool_entry(self) -> None:
        for task in _flatten(_tasks()):
            assert not re.search(r"devbox_tlaplus_tool(\.|\[\s*['\"])sha256", str(task)), task.get(
                "name"
            )

    def test_no_pinned_digest_fact_survives(self) -> None:
        for task in _flatten(_tasks()):
            assert "devbox_tlaplus_pinned" not in str(task), task.get("name")


class TestDryRun:
    def test_check_mode_reports_instead_of_staging(self) -> None:
        report = _find("Report pending release")
        assert "ansible_check_mode" in report["when"]
        assert "not ansible_check_mode" not in report["when"]
        install = _find("Install new release")
        assert "not ansible_check_mode" in install["when"]


class TestReleaseLookupPrefersAuthenticatedGh:
    def test_auth_check_runs_once_before_the_per_tool_include(self) -> None:
        tasks = _entry_tasks()
        check = next(task for task in tasks if task.get("register") == GH_AUTH)
        include = next(task for task in tasks if "ansible.builtin.include_tasks" in task)
        assert tasks.index(check) < tasks.index(include)
        assert "loop" not in check
        assert "with_items" not in check

    def test_auth_check_asks_gh_about_the_github_com_login(self) -> None:
        check = next(task for task in _entry_tasks() if task.get("register") == GH_AUTH)
        argv = check["ansible.builtin.command"]["argv"]
        assert argv[:3] == ["gh", "auth", "status"]
        assert argv[argv.index("--hostname") + 1] == "github.com"

    def test_a_missing_login_degrades_instead_of_failing_the_run(self) -> None:
        check = next(task for task in _entry_tasks() if task.get("register") == GH_AUTH)
        assert check["failed_when"] is False
        assert check["changed_when"] is False
        assert check["check_mode"] is False

    def test_auth_status_output_stays_out_of_the_log(self) -> None:
        check = next(task for task in _entry_tasks() if task.get("register") == GH_AUTH)
        assert check["no_log"] is True

    def test_authenticated_lookup_reads_the_pinned_tag_through_gh_api(self) -> None:
        gh, _ = _lookup_tasks()
        argv = gh["ansible.builtin.command"]["argv"]
        assert argv[:2] == ["gh", "api"]
        assert len(argv) == 3
        assert argv[2] == (
            "repos/{{ devbox_tlaplus_tool.repository }}/releases/tags/{{ devbox_tlaplus_tool.tag }}"
        )

    def test_both_lookups_read_the_same_release_as_each_other(self) -> None:
        gh, anon = _lookup_tasks()
        url = re.sub(r"\s+", "", anon["ansible.builtin.uri"]["url"])
        endpoint = gh["ansible.builtin.command"]["argv"][2].replace(" ", "")
        assert url == f"https://api.github.com/{endpoint}"

    def test_lookups_are_complementary_on_the_auth_result(self) -> None:
        gh, anon = _lookup_tasks()
        assert _condition(gh) == f"{GH_AUTH}.rc == 0"
        assert _condition(anon) == f"{GH_AUTH}.rc != 0"

    def test_lookups_register_distinct_results(self) -> None:
        gh, anon = _lookup_tasks()
        assert gh["register"] != anon["register"]

    def test_lookups_run_in_check_mode_and_never_report_change(self) -> None:
        for task in _lookup_tasks():
            assert task["check_mode"] is False, task["name"]
            assert task["changed_when"] is False, task["name"]

    def test_both_lookups_precede_asset_selection(self) -> None:
        names = [str(task.get("name", "")) for task in _tasks()]
        gh, anon = _lookup_tasks()
        select = next(i for i, name in enumerate(names) if name.startswith("Select asset"))
        assert names.index(gh["name"]) < select
        assert names.index(anon["name"]) < select

    def test_asset_selection_uses_whichever_lookup_ran(self) -> None:
        gh, anon = _lookup_tasks()
        select = _find("Select asset")
        expression = select["ansible.builtin.set_fact"]["devbox_tlaplus_asset"]
        assert f"{gh['register']}.stdout | from_json" in expression
        assert f"{anon['register']}.json" in expression
        assert f"{GH_AUTH}.rc == 0" in expression
        assert expression.index(gh["register"]) < expression.index(anon["register"])

    def test_asset_selection_is_not_gated_so_it_runs_after_either_lookup(self) -> None:
        assert "when" not in _find("Select asset")

    def test_no_other_task_reads_a_release_result_that_may_not_exist(self) -> None:
        gh, anon = _lookup_tasks()
        allowed = {_find("Select asset")["name"], gh["name"], anon["name"]}
        for task in _flatten(_tasks()):
            if task.get("name") in allowed:
                continue
            assert gh["register"] not in str(task), task.get("name")
            assert anon["register"] not in str(task), task.get("name")
