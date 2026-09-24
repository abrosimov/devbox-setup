"""Static contract between the drive-backup playbook, its LaunchAgent and the package.

Behavioural coverage of the tool itself lives in packages/drive-backup/tests.
"""

from __future__ import annotations

import plistlib
import tomllib
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = REPO_ROOT / "roles/devbox"
PACKAGE = REPO_ROOT / "packages/drive-backup"
TASKS = ROLE / "tasks/darwin/configure_drive_backup.yml"
MAIN_DARWIN = ROLE / "tasks/main_darwin.yml"
PLIST_TEMPLATE = ROLE / "templates/darwin/Library/LaunchAgents/local.drive-backup.plist.j2"
CORE = ROLE / "defaults/main/core.yml"
EXAMPLE = ROLE / "files/.config/drive-backup/config.toml.example"

_core: dict[str, Any] = yaml.safe_load(CORE.read_text(encoding="utf-8"))
_tasks: list[dict[str, Any]] = yaml.safe_load(TASKS.read_text(encoding="utf-8"))


def _render_plist() -> dict[str, Any]:
    env = Environment(undefined=StrictUndefined, autoescape=False)  # noqa: S701 - XML we own
    rendered = env.from_string(PLIST_TEMPLATE.read_text(encoding="utf-8")).render(
        ansible_facts={"env": {"HOME": "/Users/u"}},
        devbox_drive_backup=_core["devbox_drive_backup"],
        devbox_drive_backup_app_dir="/Users/u/.local/share/drive-backup",
        devbox_drive_backup_workspace="/Users/u/Work",
        devbox_active_profile="work",
    )
    return plistlib.loads(rendered.encode())


def _all_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for task in tasks:
        flat.append(task)
        flat.extend(_all_tasks(task.get("block", [])))
    return flat


def test_schedule_is_friday_to_saturday_night() -> None:
    plist = _render_plist()
    # launchd Weekday: 0 and 7 are Sunday, 6 is Saturday.
    assert plist["StartCalendarInterval"] == {"Weekday": 6, "Hour": 3, "Minute": 0}


def test_agent_runs_the_package_console_script() -> None:
    plist = _render_plist()
    scripts = tomllib.loads((PACKAGE / "pyproject.toml").read_text())["project"]["scripts"]
    assert "drive-backup" in scripts
    assert plist["Label"] == "local.drive-backup"
    assert plist["ProgramArguments"] == [
        "/Users/u/.local/share/drive-backup/.venv/bin/drive-backup",
        "run",
    ]


def test_agent_renders_the_env_the_tool_reads() -> None:
    env = _render_plist()["EnvironmentVariables"]
    assert env["MNEMOSYNE_PERISTASEOS"] == "work"
    assert env["AION_AUTOPOIESEON"] == "/Users/u/Work"
    # git-lfs comes from Homebrew; launchd's default PATH lacks it.
    assert env["PATH"].split(":")[0] == "/opt/homebrew/bin"


def test_workspace_expands_home() -> None:
    fact = _tasks[0]["ansible.builtin.set_fact"]["devbox_drive_backup_workspace"]
    assert "replace('$HOME'" in fact


def test_venv_sync_is_frozen_runtime_only() -> None:
    sync = next(t for t in _all_tasks(_tasks) if t["name"].endswith("materialise the venv"))
    cmd = sync["ansible.builtin.command"]["cmd"]
    assert "sync --frozen --no-default-groups" in cmd


def test_project_sync_excludes_the_venv() -> None:
    sync = next(t for t in _all_tasks(_tasks) if t["name"].endswith("sync the uv project"))
    opts = sync["ansible.posix.synchronize"]
    assert opts["src"].endswith("/packages/drive-backup/")
    assert opts["delete"] is True
    assert "--exclude=.venv" in opts["rsync_opts"]


def test_every_task_is_tagged() -> None:
    for task in _tasks:
        assert "drive-backup" in task["tags"], task["name"]


def test_wired_into_darwin_flow_outside_dev_mode() -> None:
    main = yaml.safe_load(MAIN_DARWIN.read_text(encoding="utf-8"))
    entry = next(
        t
        for t in main
        if t.get("ansible.builtin.include_tasks") == "darwin/configure_drive_backup.yml"
    )
    assert "dev_mode" in entry["when"]


def test_example_config_is_valid_toml_with_the_home_dirs() -> None:
    data = tomllib.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert {d["path"] for d in data["dir"]} >= {"~/.claude", "~/.codex", "~/.gemini"}
