from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml
from jinja2 import StrictUndefined, Template

ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / "roles/devbox/tasks/install_configs.yml"
SOURCE = ROOT / "roles/devbox/files/dot_claude/bin/vendor/langfuse_hook.py"


class TestAgyVendorDeployment:
    @pytest.mark.parametrize("existing_broken_link", [False, True])
    def test_sync_materialises_vendor_hook_and_preserves_venv(self, tmp_path, existing_broken_link):
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        task = next(
            task
            for task in tasks
            if task["name"] == "Sync Antigravity hook scripts from dot_agy/bin (one-way, --delete)"
        )
        sync = task["ansible.posix.synchronize"]
        variables = {
            "role_path": str(ROOT / "roles/devbox"),
            "devbox_paths": {"dotfiles_root_dir": str(tmp_path)},
        }
        source = Template(sync["src"], undefined=StrictUndefined).render(variables)
        destination = Template(sync["dest"], undefined=StrictUndefined).render(variables)
        deployed = Path(destination) / "vendor/langfuse_hook.py"
        deployed.parent.mkdir(parents=True)
        if existing_broken_link:
            deployed.symlink_to("../../../dot_claude/bin/vendor/langfuse_hook.py")
        marker = Path(destination) / ".venv/runtime-marker"
        marker.parent.mkdir()
        marker.write_text("keep", encoding="utf-8")

        command = ["rsync"]
        if sync.get("archive", True):
            command.append("--archive")
        command.extend(
            "--" + option.replace("_", "-")
            for option in ("delete", "recursive", "perms", "copy_links")
            if sync.get(option, False)
        )
        command.extend(sync.get("rsync_opts", []))
        command.extend([source, destination])

        for _deployment in range(2):
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=15, check=False
            )
            assert result.returncode == 0, result.stderr
            assert not deployed.is_symlink()
            assert deployed.read_bytes() == SOURCE.read_bytes()
            assert marker.read_text(encoding="utf-8") == "keep"
