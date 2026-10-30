"""Deployment contract for periodic Claude Langfuse retry without secrets."""

from __future__ import annotations

import plistlib
from pathlib import Path

import yaml
from jinja2 import StrictUndefined, Template

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (
    ROOT / "roles/devbox/templates/darwin/Library/LaunchAgents/local.langfuse-replay.plist.j2"
)
TASKS = ROOT / "roles/devbox/tasks/darwin/configure_langfuse_replay.yml"
MAIN = ROOT / "roles/devbox/tasks/main_darwin.yml"


def test_replay_launchagent_is_periodic_and_unprivileged() -> None:
    rendered = Template(
        TEMPLATE.read_text(encoding="utf-8"),
        undefined=StrictUndefined,
    ).render(ansible_facts={"env": {"HOME": "/Users/ci"}})
    plist = plistlib.loads(rendered.encode("utf-8"))
    assert plist["Label"] == "local.langfuse-replay"
    assert plist["RunAtLoad"] is True
    assert plist["StartInterval"] == 300
    assert plist["ProgramArguments"] == [
        "/Users/ci/.claude/bin/.venv/bin/python",
        "/Users/ci/.claude/bin/langfuse_replay.py",
    ]
    assert "EnvironmentVariables" not in plist
    assert "KeepAlive" not in plist


def test_replay_launchagent_is_deployed_after_hook_runtime() -> None:
    steps = yaml.safe_load(MAIN.read_text(encoding="utf-8"))
    names = [step["name"] for step in steps]
    assert names.index("Install configs") < names.index(
        "Configure durable Langfuse pending replay (LaunchAgent)"
    )
    tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
    task_names = [step["name"] for step in tasks]
    assert "Langfuse replay — install LaunchAgent" in task_names
    assert "Langfuse replay — bootstrap LaunchAgent" in task_names
