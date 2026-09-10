from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from jinja2 import StrictUndefined, Template

ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / "roles/devbox/tasks/darwin/configure_docker_desktop.yml"
SETTINGS = "Library/Group Containers/group.com.docker/settings-store.json"


@pytest.mark.integration
class TestDockerDesktopSettings:
    @pytest.fixture
    def fixture(self, tmp_path):
        home = tmp_path / "home"
        settings = home / SETTINGS
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"KernelForUDP": True, "private": "secret-fixture"}))
        commands = tmp_path / "commands.jsonl"
        executable = tmp_path / "docker"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, pathlib, sys\n"
            f"commands = pathlib.Path({str(commands)!r})\n"
            "with commands.open('a') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[2] == 'processes':\n"
            "    print('/Applications/Docker.app/Contents/MacOS/com.docker.backend')\n"
            "elif sys.argv[2] == 'stop':\n"
            f"    settings = pathlib.Path({str(settings)!r})\n"
            "    data = json.loads(settings.read_text())\n"
            "    data['savedDuringShutdown'] = {'keep': True}\n"
            "    settings.write_text(json.dumps(data))\n"
        )
        executable.chmod(0o700)
        return tmp_path, home, settings, commands, executable

    def run_playbook(self, fixture, *, check=False, dev=False, relative=False):
        tmp_path, home, _, _, executable = fixture
        playbook = tmp_path / "playbook.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            "ansible_python_interpreter": sys.executable,
                            "ansible_facts": {"env": {"HOME": str(home)}},
                            "devbox_paths": {
                                "dotfiles_root_dir": "dev" if relative else str(tmp_path / "dev")
                            },
                            "devbox_docker_process_argv": [str(executable), "fixture", "processes"],
                            "dev_mode": dev,
                        },
                        "tasks": [{"ansible.builtin.include_tasks": str(TASKS)}],
                    }
                ]
            )
        )
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": str(tmp_path) + os.pathsep + environment["PATH"],
                "ANSIBLE_LOCAL_TEMP": str(tmp_path / "ansible-local"),
                "ANSIBLE_REMOTE_TEMP": str(tmp_path / "ansible-remote"),
                "ANSIBLE_NOCOLOR": "1",
            }
        )
        result = subprocess.run(
            [
                "ansible-playbook",
                "-i",
                "localhost,",
                str(playbook),
                *(["--check"] if check else []),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
            cwd=tmp_path,
            check=False,
        )
        assert "secret-fixture" not in result.stdout + result.stderr
        return result

    def test_running_desktop_preserves_shutdown_settings_and_second_run_is_idle(self, fixture):
        _, _, settings, commands, _ = fixture
        result = self.run_playbook(fixture)
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(settings.read_text()) == {
            "KernelForUDP": False,
            "private": "secret-fixture",
            "savedDuringShutdown": {"keep": True},
        }
        assert [json.loads(line) for line in commands.read_text().splitlines()] == [
            ["fixture", "processes"],
            ["desktop", "stop", "--timeout", "60"],
            ["desktop", "start", "--timeout", "60"],
        ]
        before = commands.read_text(), settings.read_bytes(), settings.stat().st_mtime_ns
        result = self.run_playbook(fixture)
        assert result.returncode == 0, result.stdout + result.stderr
        assert before == (commands.read_text(), settings.read_bytes(), settings.stat().st_mtime_ns)

    def test_stopped_desktop_is_not_started(self, fixture):
        _, _, settings, commands, executable = fixture
        executable.write_text(
            executable.read_text().replace(
                "/Applications/Docker.app/Contents/MacOS/com.docker.backend", "/usr/bin/unrelated"
            )
        )
        result = self.run_playbook(fixture)
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(settings.read_text())["KernelForUDP"] is False
        assert len(commands.read_text().splitlines()) == 1

    def test_check_mode_reports_change_without_writes_or_commands(self, fixture):
        _, _, settings, commands, _ = fixture
        before = settings.read_bytes(), settings.stat().st_mtime_ns
        result = self.run_playbook(fixture, check=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "changed=1" in result.stdout
        assert before == (settings.read_bytes(), settings.stat().st_mtime_ns)
        assert not commands.exists()

    @pytest.mark.parametrize("relative", [False, True])
    def test_dev_mode_only_changes_isolated_settings_without_commands(self, fixture, relative):
        tmp_path, _, settings, commands, _ = fixture
        isolated = tmp_path / "dev" / SETTINGS
        isolated.parent.mkdir(parents=True)
        isolated.write_bytes(settings.read_bytes())
        result = self.run_playbook(fixture, dev=True, relative=relative)
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(isolated.read_text())["KernelForUDP"] is False
        assert json.loads(settings.read_text())["KernelForUDP"] is True
        assert not commands.exists()

    def test_final_settings_failure_still_restores_running_state(self, fixture):
        _, _, settings, commands, executable = fixture
        executable.write_text(
            executable.read_text().replace(
                "settings.write_text(json.dumps(data))", "settings.write_text('broken-json')"
            )
        )
        result = self.run_playbook(fixture)
        assert result.returncode != 0
        assert settings.read_text() == "broken-json"
        assert json.loads(commands.read_text().splitlines()[-1]) == [
            "desktop",
            "start",
            "--timeout",
            "60",
        ]

    @pytest.mark.parametrize("content", ["broken-json", "[]", "null"])
    def test_invalid_settings_fail_without_mutation_or_commands(self, fixture, content):
        _, _, settings, commands, _ = fixture
        settings.write_text(content)
        result = self.run_playbook(fixture)
        assert result.returncode != 0
        assert settings.read_text() == content
        assert not commands.exists()

    def test_absent_settings_report_initialisation_without_creating_file(self, fixture):
        _, _, settings, commands, _ = fixture
        settings.unlink()
        result = self.run_playbook(fixture)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "KernelForUDP has not been configured" in result.stdout
        assert not settings.exists()
        assert not commands.exists()


class TestDockerDesktopProfile:
    @pytest.mark.parametrize(
        ("casks", "enabled"), [(["docker-desktop"], True), (["orbstack"], False)]
    )
    def test_cask_gate_precedes_pub(self, casks, enabled):
        tasks = yaml.safe_load((ROOT / "roles/devbox/tasks/main_darwin.yml").read_text())
        include = next(
            task
            for task in tasks
            if task.get("ansible.builtin.include_tasks") == "darwin/configure_docker_desktop.yml"
        )
        pub = next(
            task
            for task in tasks
            if task.get("ansible.builtin.include_tasks") == "darwin/configure_pub_mode.yml"
        )
        assert tasks.index(include) < tasks.index(pub)
        rendered = Template("{{ " + include["when"] + " }}", undefined=StrictUndefined).render(
            devbox_extra_brew_casks_no_binaries=casks
        )
        assert rendered == str(enabled)
