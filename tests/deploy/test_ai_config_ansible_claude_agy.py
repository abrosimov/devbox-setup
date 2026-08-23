from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_PATH = REPO_ROOT / "roles/devbox/tasks/install_configs.yml"
AGY_SETTINGS_PATH = REPO_ROOT / "roles/devbox/files/dot_agy/cli/settings.json.j2"
CLAUDE_DEFAULTS_PATH = REPO_ROOT / "roles/devbox/defaults/main/claude.yml"
CLAUDE_SETTINGS_PATH = REPO_ROOT / "roles/devbox/files/dot_claude/settings.json"
AI_ROOT = REPO_ROOT / "roles/devbox/files/dot_ai"

type Task = dict[str, object]


def load_tasks() -> tuple[Task, ...]:
    loaded: object = yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert all(isinstance(task, dict) for task in loaded)
    return tuple(cast("Task", task) for task in loaded)


def task_named(tasks: tuple[Task, ...], name: str) -> Task:
    return next(task for task in tasks if task.get("name") == name)


class TestClaudeSettingsWriter:
    @pytest.fixture
    def tasks(self) -> tuple[Task, ...]:
        return load_tasks()

    def test_root_copy_keeps_hooks_and_config_only(self, tasks: tuple[Task, ...]) -> None:
        task = task_named(tasks, "Deploy .claude root files")
        loop = task["loop"]

        assert isinstance(loop, list)
        assert loop == [
            {"src": "hooks.json", "dest": "hooks.json"},
            {"src": "config.md", "dest": "config.md"},
        ]

    def test_wholesale_settings_copy_is_absent(self, tasks: tuple[Task, ...]) -> None:
        copy_sources: list[str] = []
        for task in tasks:
            loop: object = task.get("loop")
            if "ansible.builtin.copy" not in task or not isinstance(loop, list):
                continue
            for entry in loop:
                if not isinstance(entry, dict):
                    continue
                source: object = entry.get("src")
                if isinstance(source, str):
                    copy_sources.append(source)

        assert "settings.json" not in copy_sources

    def test_repository_settings_match_declared_plugin_state(self) -> None:
        defaults = yaml.safe_load(CLAUDE_DEFAULTS_PATH.read_text(encoding="utf-8"))
        settings = json.loads(CLAUDE_SETTINGS_PATH.read_text(encoding="utf-8"))
        marketplaces = defaults["devbox_claude_plugin_marketplaces"]
        plugins = defaults["devbox_claude_plugins"]

        expected_marketplaces = {
            marketplace["name"]: {"source": {"source": "github", "repo": marketplace["repo"]}}
            for marketplace in marketplaces
        }
        expected_plugins = {
            "@".join(
                (
                    plugin["name"],
                    plugin.get("marketplace", "claude-plugins-official"),
                )
            ): True
            for plugin in plugins
        }

        assert settings["extraKnownMarketplaces"] == expected_marketplaces
        assert settings["enabledPlugins"] == expected_plugins


class TestAgySettingsWriter:
    @pytest.fixture
    def tasks(self) -> tuple[Task, ...]:
        return load_tasks()

    def test_legacy_render_and_merge_writers_are_absent(self, tasks: tuple[Task, ...]) -> None:
        serialised_tasks = json.dumps(tasks)

        assert ".settings.managed.json" not in serialised_tasks
        assert "merge_settings.py" not in serialised_tasks

    def test_repository_template_excludes_local_workspace_state(self) -> None:
        settings: object = json.loads(AGY_SETTINGS_PATH.read_text(encoding="utf-8"))

        assert isinstance(settings, dict)
        assert set(settings) == {
            "allowNonWorkspaceAccess",
            "colorScheme",
            "model",
            "permissions",
        }
        assert "trustedWorkspaces" not in settings


class TestSharedDiagnosticProtocol:
    @pytest.fixture
    def tasks(self) -> tuple[Task, ...]:
        return load_tasks()

    def test_shared_skill_and_authority_reach_claude_and_agy(
        self,
        tasks: tuple[Task, ...],
    ) -> None:
        skill = AI_ROOT / "skills/diagnose-and-repair/SKILL.md"
        authority = AI_ROOT / "USER_AUTHORITY_PROTOCOL.md"

        assert skill.is_file()
        assert "`diagnose-and-repair` skill" in authority.read_text(encoding="utf-8")

        for task_name in (
            "Sync shared AI directories (dot_ai) to Claude (one-way, --delete)",
            "Sync shared AI directories (dot_ai) to Antigravity (one-way)",
        ):
            task = task_named(tasks, task_name)
            assert task["loop"] == "{{ devbox_ai_managed_dirs }}"
            assert "files/dot_ai/{{ item }}/" in json.dumps(task)

        for task_name in (
            "Deploy shared AI root rules (USER_AUTHORITY_PROTOCOL) to Claude",
            "Deploy shared AI root rules (USER_AUTHORITY_PROTOCOL) to Antigravity",
        ):
            task = task_named(tasks, task_name)
            assert "files/dot_ai/USER_AUTHORITY_PROTOCOL.md" in json.dumps(task)


class TestAiConfigApplyTasks:
    @pytest.fixture
    def tasks(self) -> tuple[Task, ...]:
        return load_tasks()

    @pytest.mark.parametrize(
        ("task_name", "engine", "register", "tags"),
        [
            (
                "Reconcile Claude settings",
                "claude",
                "devbox_ai_config_claude",
                ["configs", "claude"],
            ),
            (
                "Reconcile Antigravity settings",
                "agy",
                "devbox_ai_config_agy",
                ["configs", "agy"],
            ),
        ],
    )
    def test_uses_repo_local_apply_contract(
        self,
        tasks: tuple[Task, ...],
        task_name: str,
        engine: str,
        register: str,
        tags: list[str],
    ) -> None:
        task = task_named(tasks, task_name)
        command = task["ansible.builtin.command"]

        assert isinstance(command, dict)
        argv = command["argv"]
        assert isinstance(argv, str)
        assert "role_path ~ '/../../scripts/ai-config'" in argv
        assert "'apply'" in argv
        assert f"'{engine}'" in argv
        assert "'--repo-root'" in argv
        assert "role_path ~ '/../..'" in argv
        assert "'--home'" in argv
        assert "devbox_paths.dotfiles_root_dir" in argv
        assert "lookup('env', 'HOME')" in argv
        assert "'--profile'" in argv
        assert "devbox_active_profile" in argv
        assert "'--json'" in argv
        assert task["register"] == register
        assert task["tags"] == tags

    @pytest.mark.parametrize(
        ("task_name", "register"),
        [
            ("Reconcile Claude settings", "devbox_ai_config_claude"),
            ("Reconcile Antigravity settings", "devbox_ai_config_agy"),
        ],
    )
    def test_check_mode_is_forwarded_to_read_only_apply(
        self,
        tasks: tuple[Task, ...],
        task_name: str,
        register: str,
    ) -> None:
        task = task_named(tasks, task_name)
        command = task["ansible.builtin.command"]

        assert isinstance(command, dict)
        argv = command["argv"]
        assert isinstance(argv, str)
        assert "+ (['--check'] if ansible_check_mode else [])" in argv
        assert task["check_mode"] is False
        assert task["changed_when"] == (
            f"{register}.rc == 0 and ({register}.stdout | from_json).changed | bool"
        )
        assert task["failed_when"] == f"{register}.rc not in [0]"
