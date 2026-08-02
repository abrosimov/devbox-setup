from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_PATH = REPO_ROOT / "roles/devbox/tasks/install_codex_configs.yml"

type AnsibleTask = dict[str, object]


def load_tasks() -> list[AnsibleTask]:
    loaded: object = yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert all(isinstance(task, dict) for task in loaded)
    return cast("list[AnsibleTask]", loaded)


def task_named(tasks: list[AnsibleTask], name: str) -> AnsibleTask:
    return next(task for task in tasks if task.get("name") == name)


def as_mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast("dict[str, object]", value)


def as_string_list(value: object) -> list[str]:
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)
    return cast("list[str]", value)


class TestCodexAiConfigAnsibleContract:
    @pytest.fixture
    def tasks(self) -> list[AnsibleTask]:
        return load_tasks()

    def test_apply_uses_repo_local_ai_config_with_explicit_context(
        self,
        tasks: list[AnsibleTask],
    ) -> None:
        task = task_named(tasks, "Apply repo-owned Codex settings through ai-config")
        variables = as_mapping(task["vars"])
        arguments = as_string_list(variables["devbox_codex_ai_config_argv"])

        assert arguments == [
            "{{ devbox_codex_repo_root }}/scripts/ai-config",
            "apply",
            "codex",
            "--repo-root",
            "{{ devbox_codex_repo_root }}",
            "--home",
            "{{ devbox_codex_ai_config_home }}",
            "--profile",
            "{{ devbox_active_profile }}",
            "--json",
        ]

    def test_check_mode_runs_read_only_ai_config_plan(
        self,
        tasks: list[AnsibleTask],
    ) -> None:
        task = task_named(tasks, "Apply repo-owned Codex settings through ai-config")
        command = as_mapping(task["ansible.builtin.command"])
        argv_expression = command["argv"]

        assert task["check_mode"] is False
        assert isinstance(argv_expression, str)
        assert "['--check'] if ansible_check_mode else []" in argv_expression

    def test_result_uses_json_changed_flag_and_fails_all_nonzero_codes(
        self,
        tasks: list[AnsibleTask],
    ) -> None:
        task = task_named(tasks, "Apply repo-owned Codex settings through ai-config")

        assert task["register"] == "devbox_codex_reconcile"
        assert task["changed_when"] == (
            "devbox_codex_reconcile.rc == 0 and (devbox_codex_reconcile.stdout | from_json).changed"
        )
        assert task["failed_when"] == "devbox_codex_reconcile.rc != 0"

    def test_home_and_repository_roots_cover_real_and_debug_deploys(
        self,
        tasks: list[AnsibleTask],
    ) -> None:
        task = task_named(tasks, "Resolve Codex config paths")
        facts = as_mapping(task["ansible.builtin.set_fact"])
        home_expression = facts["devbox_codex_ai_config_home"]

        assert facts["devbox_codex_repo_root"] == (
            "{{ (devbox_codex_role_path | default(role_path)) ~ '/../..' }}"
        )
        assert isinstance(home_expression, str)
        assert "lookup('env', 'HOME')" in home_expression
        assert "devbox_paths.dotfiles_root_dir" in home_expression

    def test_legacy_writer_is_absent_and_portable_assets_remain(
        self,
        tasks: list[AnsibleTask],
    ) -> None:
        source = TASKS_PATH.read_text(encoding="utf-8")
        names = {task.get("name") for task in tasks}

        assert "devbox-managed.toml" not in source
        assert "reconcile_config.py" not in source
        assert "Render repo-owned Codex config fragment" not in names
        assert "Install Codex config reconciler" not in names
        assert {
            "Install Codex global authority protocol",
            "Install Codex custom agents",
            "Inspect managed Codex skill destinations",
            "Remove stale symlinks at managed Codex skill destinations",
            "Sync compatible shared skills to Codex",
        } <= names
