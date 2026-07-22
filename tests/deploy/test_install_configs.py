from __future__ import annotations

from pathlib import Path

import yaml

TASKS = Path(__file__).resolve().parents[2] / "roles/devbox/tasks/install_configs.yml"

_tasks = yaml.safe_load(TASKS.read_text())


def test_karabiner_assets_tree_is_deployed() -> None:
    copy_loops = [t["loop"] for t in _tasks if "ansible.builtin.copy" in t and "loop" in t]
    assert any(".config/karabiner/assets" in loop for loop in copy_loops)


def test_karabiner_json_is_seed_only() -> None:
    seed = next(
        t["ansible.builtin.copy"]
        for t in _tasks
        if "ansible.builtin.copy" in t
        and str(t["ansible.builtin.copy"].get("dest", "")).endswith(
            ".config/karabiner/karabiner.json"
        )
    )
    assert seed["force"] is False
