from __future__ import annotations

import ast
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, StrictUndefined, Template

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = REPO_ROOT / "roles/devbox"
PUB_LEASE = ROLE / "files/.local/bin/pub-lease.py"
TASKS = ROLE / "tasks/darwin/configure_pub_mode.yml"
MAIN_DARWIN = ROLE / "tasks/main_darwin.yml"
PLIST_TEMPLATE = ROLE / "templates/darwin/Library/LaunchDaemons/local.pub-lease.plist.j2"
PERSONAL_PROFILE = REPO_ROOT / "profiles/personal.yml"
WORK_PROFILE = REPO_ROOT / "profiles/work.yml"
INSTALL_CONFIGS = ROLE / "tasks/install_configs.yml"
LEGACY_GUARD = ROLE / "files/.config/fish/conf.d/pub_guard.fish"
PUB_FUNCTION = ROLE / "files/.config/fish/functions/pub.fish"
PUB_PROXY_MIGRATION = ROLE / "files/.config/fish/conf.d/pub_proxy_migration.fish"
PUB_GREETING = ROLE / "files/.config/fish/functions/fish_greeting.fish"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _render_ansible_expression(expression: str, **context: object) -> object:
    environment = Environment(undefined=StrictUndefined, autoescape=True)
    environment.filters["bool"] = bool
    rendered = environment.from_string(expression).render(**context)
    return yaml.safe_load(rendered)


def _ansible_conditions_hold(conditions: list[str] | str, **context: object) -> bool:
    environment = Environment(undefined=StrictUndefined, autoescape=True)
    environment.filters["bool"] = bool
    if isinstance(conditions, str):
        conditions = [conditions]
    return all(
        bool(environment.compile_expression(condition)(**context)) for condition in conditions
    )


class TestPubLeaseLaunchAgent:
    def test_runs_reconcile_at_load_and_every_minute(self) -> None:
        rendered = Template(
            PLIST_TEMPLATE.read_text(encoding="utf-8"),
            undefined=StrictUndefined,
        ).render(
            devbox_pub_home="/Users/pub-test",
            devbox_pub_python_path="/usr/bin/python3",
            ansible_facts={"user_id": "pub-test"},
        )
        plist = plistlib.loads(rendered.encode())

        assert plist["Label"] == "local.pub-lease"
        assert plist["UserName"] == "pub-test"
        assert plist["ProgramArguments"] == [
            "/bin/sh",
            "-c",
            'exec "$1" "$2" reconcile >>"$3" 2>&1',
            "pub-lease-launcher",
            "/usr/bin/python3",
            "/Users/pub-test/.local/bin/pub-lease",
            "/Users/pub-test/Library/Logs/pub-lease.log",
        ]
        assert plist["RunAtLoad"] is True
        assert plist["StartInterval"] == 60
        assert plist["EnvironmentVariables"]["PUB_LEASE_LOG_FILE"] == (
            "/Users/pub-test/Library/Logs/pub-lease.log"
        )
        assert "StandardOutPath" not in plist
        assert "StandardErrorPath" not in plist

    def test_wrapper_opens_the_controller_log_in_append_mode(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        controller = home / ".local/bin/pub-lease"
        controller.parent.mkdir(parents=True)
        controller.write_text(
            """import sys

print(f"stdout:{sys.argv[1]}")
print(f"stderr:{sys.argv[1]}", file=sys.stderr)
""",
            encoding="utf-8",
        )
        log_path = home / "Library/Logs/pub-lease.log"
        log_path.parent.mkdir(parents=True)
        log_path.write_text("existing\n", encoding="utf-8")
        rendered = Template(
            PLIST_TEMPLATE.read_text(encoding="utf-8"),
            undefined=StrictUndefined,
        ).render(
            devbox_pub_home=str(home),
            devbox_pub_python_path=sys.executable,
            ansible_facts={"user_id": "pub-test"},
        )
        arguments = plistlib.loads(rendered.encode())["ProgramArguments"]

        result = subprocess.run(arguments, capture_output=True, text=True, check=False)

        assert result.returncode == 0, result.stderr
        assert result.stdout == ""
        assert result.stderr == ""
        log_lines = log_path.read_text(encoding="utf-8").splitlines()
        assert log_lines[0] == "existing"
        assert set(log_lines[1:]) == {"stdout:reconcile", "stderr:reconcile"}


class TestPubLeaseDeployment:
    def test_source_is_python_39_compatible(self) -> None:
        source = PUB_LEASE.read_text(encoding="utf-8")

        ast.parse(source, filename=str(PUB_LEASE), feature_version=(3, 9))
        compile(source, str(PUB_LEASE), "exec")

    def test_controller_shebang_pins_the_supervisor_interpreter(self) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        interpreter = next(
            task["ansible.builtin.set_fact"]["devbox_pub_python_path"]
            for task in tasks
            if "devbox_pub_python_path" in task.get("ansible.builtin.set_fact", {})
        )
        shebang = PUB_LEASE.read_text(encoding="utf-8").splitlines()[0]

        # Teardown execs the deployed controller directly, so its shebang is the
        # CLI's interpreter while the plist picks the daemon's. They must agree.
        assert interpreter.startswith("/")
        assert shebang == f"#!{interpreter}"

    def test_tasks_deploy_executable_and_launchdaemon_candidate(self) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        python_stat = next(
            task for task in tasks if task["name"] == "Pub mode — inspect Python runtime"
        )
        python_assert = next(
            task for task in tasks if task["name"] == "Pub mode — require Python runtime"
        )
        python_version = next(
            task for task in tasks if task["name"] == "Pub mode — verify Python runtime version"
        )
        controller_deploy = next(
            task for task in tasks if task["name"] == "Pub mode — deploy lease controller"
        )
        copies = [task["ansible.builtin.copy"] for task in tasks if "ansible.builtin.copy" in task]
        templates = [
            task["ansible.builtin.template"] for task in tasks if "ansible.builtin.template" in task
        ]

        assert any(
            copy.get("src") == "{{ role_path }}/files/.local/bin/pub-lease.py"
            and copy.get("dest") == "{{ devbox_pub_home }}/.local/bin/pub-lease"
            and copy.get("mode") == "0755"
            and copy.get("validate") == "{{ devbox_pub_python_path }} -m py_compile %s"
            for copy in copies
        )
        assert python_stat["ansible.builtin.stat"]["path"] == "{{ devbox_pub_python_path }}"
        assert python_assert["ansible.builtin.assert"]["that"] == [
            "devbox_pub_python.stat.exists",
            "devbox_pub_python.stat.executable",
        ]
        assert python_version["ansible.builtin.command"]["argv"] == [
            "{{ devbox_pub_python_path }}",
            "-c",
            "import sys; raise SystemExit(sys.version_info < (3, 9))",
        ]
        assert python_version["changed_when"] is False
        assert python_version["check_mode"] is False
        assert tasks.index(python_stat) < tasks.index(python_assert) < tasks.index(python_version)
        assert tasks.index(python_version) < tasks.index(controller_deploy)
        assert any(
            template.get("src") == "darwin/Library/LaunchDaemons/local.pub-lease.plist.j2"
            and template.get("dest") == "{{ devbox_pub_candidate_plist_path }}"
            and template.get("mode") == "0600"
            for template in templates
        )
        assert any(
            copy.get("src") == "{{ devbox_pub_candidate_plist_path }}"
            and copy.get("dest") == "{{ devbox_pub_plist_path }}"
            and copy.get("remote_src") is True
            and copy.get("mode") == "0644"
            for copy in copies
        )

    @pytest.mark.parametrize(
        ("dev_mode", "profile", "expected_enabled"),
        [
            (False, PERSONAL_PROFILE, True),
            (False, WORK_PROFILE, False),
            (True, PERSONAL_PROFILE, False),
        ],
    )
    def test_main_darwin_passes_the_profile_and_dev_mode_gate_to_pub_tasks(
        self,
        *,
        dev_mode: bool,
        profile: Path,
        expected_enabled: bool,
    ) -> None:
        tasks = yaml.safe_load(MAIN_DARWIN.read_text(encoding="utf-8"))
        include = next(
            task
            for task in tasks
            if task.get("ansible.builtin.include_tasks") == "darwin/configure_pub_mode.yml"
        )
        profile_vars = yaml.safe_load(profile.read_text(encoding="utf-8"))

        assert "when" not in include
        enabled = _render_ansible_expression(
            include["vars"]["devbox_pub_mode_enabled"],
            dev_mode=dev_mode,
            devbox_brew_secondary_casks_no_binaries=[],
            devbox_extra_brew_casks_no_binaries=profile_vars.get(
                "devbox_extra_brew_casks_no_binaries", []
            ),
        )
        assert enabled is expected_enabled

    def test_pub_mode_is_deployed_only_by_the_profile_that_installs_warp(self) -> None:
        personal = yaml.safe_load(PERSONAL_PROFILE.read_text(encoding="utf-8"))
        work = yaml.safe_load(WORK_PROFILE.read_text(encoding="utf-8"))

        assert "cloudflare-warp" in personal["devbox_extra_brew_casks_no_binaries"]
        assert "cloudflare-warp" not in work.get("devbox_extra_brew_casks_no_binaries", [])

    def test_common_pub_wrapper_handles_profile_without_lease_controller(self) -> None:
        tasks = yaml.safe_load(INSTALL_CONFIGS.read_text(encoding="utf-8"))
        deployed_directories = [
            item
            for task in tasks
            if task.get("name") == "Deploy dotfile directories"
            for item in task["loop"]
        ]
        source = PUB_FUNCTION.read_text(encoding="utf-8")

        assert ".config/fish/functions" in deployed_directories
        assert "command -q pub-lease" in source
        assert "pub: unavailable" in source
        assert "command pub-lease $argv" in source

    @pytest.mark.parametrize(
        ("dotfiles_root", "expected_home"),
        [
            ("~", "/Users/pub-test"),
            ("/srv/devbox-home", "/srv/devbox-home"),
            ("debug/dotfiles", "/repo/roles/devbox/../../debug/dotfiles"),
        ],
    )
    def test_deployment_root_follows_devbox_paths(
        self, dotfiles_root: str, expected_home: str
    ) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        resolution = next(
            task["ansible.builtin.set_fact"]["devbox_pub_home"]
            for task in tasks
            if "devbox_pub_home" in task.get("ansible.builtin.set_fact", {})
        )

        rendered = Template(resolution, undefined=StrictUndefined).render(
            lookup=lambda _plugin, _name: "/Users/pub-test",
            devbox_paths={"dotfiles_root_dir": dotfiles_root},
            role_path="/repo/roles/devbox",
        )

        assert rendered.strip() == expected_home

    def test_disabled_pub_mode_boots_out_loaded_agent_and_removes_artifacts(self) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        state_directory = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — ensure lease state directory exists"
        )
        activation_block = next(
            task for task in tasks if task["name"] == "Pub mode — block activation during teardown"
        )
        activation_allow = next(
            task for task in tasks if task["name"] == "Pub mode — allow activation when managed"
        )
        controller_check = next(
            task for task in tasks if task["name"] == "Pub mode — check disabled controller"
        )
        metadata_check = next(
            task for task in tasks if task["name"] == "Pub mode — inspect pending recovery metadata"
        )
        recovery_guard = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — require controller for pending recovery"
        )
        lease_restore = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — restore active lease before removal"
        )
        bootout = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — bootout disabled expiry LaunchDaemon"
        )
        legacy_bootout = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — bootout disabled legacy GUI expiry LaunchAgent"
        )
        removal = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — remove disabled controller and supervisors"
        )

        assert tasks.index(state_directory) < tasks.index(activation_block)
        assert tasks.index(activation_block) < tasks.index(controller_check)
        # Both supervisors must stop before the restore runs: the LaunchDaemon
        # reconciles every 60 seconds and `reconcile` ignores the `disabled`
        # marker, so a reconcile queued behind the interactive `off` would
        # re-enable the lease after teardown had already completed it.
        assert (
            tasks.index(controller_check)
            < tasks.index(metadata_check)
            < tasks.index(recovery_guard)
            < tasks.index(bootout)
            < tasks.index(legacy_bootout)
            < tasks.index(lease_restore)
            < tasks.index(removal)
        )
        assert state_directory["ansible.builtin.file"] == {
            "path": "{{ devbox_pub_home }}/.local/state/pub-lease",
            "state": "directory",
            "mode": "0700",
        }
        assert _ansible_conditions_hold(
            state_directory["when"], devbox_pub_mode_enabled=False, dev_mode=False
        )
        assert not _ansible_conditions_hold(
            state_directory["when"], devbox_pub_mode_enabled=False, dev_mode=True
        )
        assert not _ansible_conditions_hold(
            state_directory["when"], devbox_pub_mode_enabled=True, dev_mode=False
        )
        assert activation_block["ansible.builtin.copy"] == {
            "content": "",
            "dest": "{{ devbox_pub_home }}/.local/state/pub-lease/disabled",
            "force": False,
            "mode": "0600",
        }
        assert _ansible_conditions_hold(
            activation_block["when"], devbox_pub_mode_enabled=False, dev_mode=False
        )
        assert not _ansible_conditions_hold(
            activation_block["when"], devbox_pub_mode_enabled=False, dev_mode=True
        )
        assert activation_allow["ansible.builtin.file"] == {
            "path": "{{ devbox_pub_home }}/.local/state/pub-lease/disabled",
            "state": "absent",
        }
        assert _ansible_conditions_hold(activation_allow["when"], devbox_pub_mode_enabled=True)
        assert not _ansible_conditions_hold(activation_allow["when"], devbox_pub_mode_enabled=False)
        assert controller_check["ansible.builtin.stat"]["path"] == (
            "{{ devbox_pub_home }}/.local/bin/pub-lease"
        )
        assert metadata_check["ansible.builtin.stat"]["path"] == (
            "{{ devbox_pub_home }}/.local/state/pub-lease/{{ item }}"
        )
        assert metadata_check["loop"] == ["lease.json", "recovery.json"]
        assert "ansible.builtin.assert" in recovery_guard
        assert (
            "previous WARP state cannot be restored"
            in recovery_guard["ansible.builtin.assert"]["fail_msg"]
        )
        assert lease_restore["ansible.builtin.command"]["argv"] == [
            "{{ devbox_pub_home }}/.local/bin/pub-lease",
            "off",
        ]
        assert lease_restore["environment"]["HOME"] == "{{ devbox_pub_home }}"
        assert "failed_when" not in lease_restore
        assert not lease_restore.get("ignore_errors", False)
        assert _ansible_conditions_hold(
            lease_restore["when"],
            devbox_pub_mode_enabled=False,
            dev_mode=False,
            devbox_pub_controller={"stat": {"exists": True}},
        )
        assert not _ansible_conditions_hold(
            lease_restore["when"],
            devbox_pub_mode_enabled=False,
            dev_mode=True,
            devbox_pub_controller={"stat": {"exists": True}},
        )
        assert bootout["ansible.builtin.command"]["argv"] == [
            "/bin/launchctl",
            "bootout",
            "system/local.pub-lease",
        ]
        assert _ansible_conditions_hold(
            bootout["when"],
            devbox_pub_mode_enabled=False,
            dev_mode=False,
            devbox_pub_launchagent_status={"rc": 0},
        )
        assert not _ansible_conditions_hold(
            bootout["when"],
            devbox_pub_mode_enabled=False,
            dev_mode=True,
            devbox_pub_launchagent_status={"rc": 0},
        )
        assert removal["ansible.builtin.file"]["state"] == "absent"
        assert set(removal["loop"]) == {
            "{{ devbox_pub_plist_path }}",
            "{{ devbox_pub_home }}/Library/LaunchAgents/local.pub-lease.plist",
            "{{ devbox_pub_home }}/.local/bin/pub-lease",
            "{{ devbox_pub_reload_marker_path }}",
            "{{ devbox_pub_candidate_plist_path }}",
            "{{ devbox_pub_legacy_candidate_plist_path }}",
        }
        assert _ansible_conditions_hold(removal["when"], devbox_pub_mode_enabled=False)

    @pytest.mark.parametrize(
        ("controller_exists", "metadata_exists", "allowed"),
        [
            (True, (True, True), True),
            (True, (True, False), True),
            (False, (False, False), True),
            (False, (True, False), False),
            (False, (False, True), False),
        ],
    )
    def test_disabled_pub_requires_controller_when_recovery_metadata_exists(
        self,
        controller_exists: int,
        metadata_exists: tuple[int, int],
        allowed: int,
    ) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        guard = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — require controller for pending recovery"
        )
        expression = guard["ansible.builtin.assert"]["that"][0]
        result = _render_ansible_expression(
            "{{ " + expression + " }}",
            devbox_pub_controller={"stat": {"exists": controller_exists}},
            devbox_pub_recovery_metadata={
                "results": [{"stat": {"exists": exists}} for exists in metadata_exists]
            },
        )

        assert result == allowed

    def test_pending_reload_marker_survives_until_launchdaemon_reload_completes(self) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        candidate_render = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — render expiry LaunchDaemon candidate"
        )
        candidate_stat = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — check expiry LaunchDaemon candidate"
        )
        installed_stat = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — check installed expiry LaunchDaemon plist"
        )
        live_deployment = next(
            task for task in tasks if task["name"] == "Pub mode — deploy expiry LaunchDaemon"
        )
        marker_create = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — persist pending LaunchDaemon reload"
        )
        marker_stat = next(
            task for task in tasks if task["name"] == "Pub mode — check pending LaunchDaemon reload"
        )
        status = next(
            task for task in tasks if task["name"] == "Pub mode — check expiry LaunchDaemon status"
        )
        bootout = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — bootout changed expiry LaunchDaemon"
        )
        bootstrap = next(
            task for task in tasks if task["name"] == "Pub mode — bootstrap expiry LaunchDaemon"
        )
        marker_clear = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — clear completed LaunchDaemon reload"
        )

        assert (
            tasks.index(candidate_render)
            < tasks.index(candidate_stat)
            < tasks.index(installed_stat)
            < tasks.index(marker_create)
            < tasks.index(live_deployment)
            < tasks.index(marker_stat)
            < tasks.index(status)
            < tasks.index(bootout)
            < tasks.index(bootstrap)
            < tasks.index(marker_clear)
        )
        assert candidate_render["ansible.builtin.template"] == {
            "src": "darwin/Library/LaunchDaemons/local.pub-lease.plist.j2",
            "dest": "{{ devbox_pub_candidate_plist_path }}",
            "owner": "{{ omit if dev_mode | default(false) | bool else 'root' }}",
            "group": "{{ omit if dev_mode | default(false) | bool else 'wheel' }}",
            "mode": "0600",
        }
        assert candidate_stat["ansible.builtin.stat"]["path"] == (
            "{{ devbox_pub_candidate_plist_path }}"
        )
        assert candidate_stat["register"] == "devbox_pub_candidate_plist"
        assert installed_stat["ansible.builtin.stat"]["path"] == "{{ devbox_pub_plist_path }}"
        assert installed_stat["register"] == "devbox_pub_installed_plist"
        assert marker_create["ansible.builtin.copy"] == {
            "content": "",
            "dest": "{{ devbox_pub_reload_marker_path }}",
            "force": False,
            "owner": "root",
            "group": "wheel",
            "mode": "0600",
        }
        assert marker_stat["ansible.builtin.stat"]["path"] == (
            "{{ devbox_pub_reload_marker_path }}"
        )
        assert marker_stat["register"] == "devbox_pub_reload_required"
        assert marker_clear["ansible.builtin.file"] == {
            "path": "{{ devbox_pub_reload_marker_path }}",
            "state": "absent",
        }
        assert live_deployment["ansible.builtin.copy"] == {
            "src": "{{ devbox_pub_candidate_plist_path }}",
            "dest": "{{ devbox_pub_plist_path }}",
            "remote_src": True,
            "owner": "{{ omit if dev_mode | default(false) | bool else 'root' }}",
            "group": "{{ omit if dev_mode | default(false) | bool else 'wheel' }}",
            "mode": "0644",
        }
        for task in (candidate_render, candidate_stat, live_deployment):
            assert (
                _render_ansible_expression(
                    str(task["become"]),
                    dev_mode=False,
                )
                is True
            )
        assert all(
            task["become"] is True
            for task in (installed_stat, marker_create, marker_stat, marker_clear)
        )

        drift_context = {
            "devbox_pub_mode_enabled": True,
            "dev_mode": False,
            "ansible_check_mode": False,
            "devbox_pub_candidate_plist": {"stat": {"checksum": "candidate"}},
        }
        assert _ansible_conditions_hold(
            marker_create["when"],
            **drift_context,
            devbox_pub_installed_plist={"stat": {"exists": False}},
        )
        assert not _ansible_conditions_hold(
            marker_create["when"],
            **drift_context,
            devbox_pub_installed_plist={"stat": {"exists": True, "checksum": "candidate"}},
        )
        assert _ansible_conditions_hold(
            marker_create["when"],
            **drift_context,
            devbox_pub_installed_plist={"stat": {"exists": True, "checksum": "installed"}},
        )

        next_run = {
            **drift_context,
            "devbox_pub_installed_plist": {"stat": {"exists": True, "checksum": "candidate"}},
            "devbox_pub_reload_required": {"stat": {"exists": True}},
            "devbox_pub_launchagent_status": {"rc": 0},
        }
        assert not _ansible_conditions_hold(marker_create["when"], **next_run)
        assert _ansible_conditions_hold(bootout["when"], **next_run)
        assert _ansible_conditions_hold(bootstrap["when"], **next_run)
        assert "failed_when" not in bootstrap
        assert not bootstrap.get("ignore_errors", False)
        assert _ansible_conditions_hold(marker_clear["when"], **next_run)

        clean_run = {
            **next_run,
            "devbox_pub_reload_required": {"stat": {"exists": False}},
        }
        assert not _ansible_conditions_hold(bootout["when"], **clean_run)
        assert not _ansible_conditions_hold(bootstrap["when"], **clean_run)

        check_mode = {
            "devbox_pub_mode_enabled": True,
            "dev_mode": False,
            "ansible_check_mode": True,
            "devbox_pub_installed_plist": {"stat": {"exists": False}},
        }
        assert _ansible_conditions_hold(candidate_render["when"], **check_mode)
        assert not _ansible_conditions_hold(candidate_stat["when"], **check_mode)
        assert not _ansible_conditions_hold(marker_create["when"], **check_mode)
        assert not _ansible_conditions_hold(live_deployment["when"], **check_mode)

    @pytest.mark.parametrize(
        ("dev_mode", "expected_path", "expected_candidate", "expected_marker"),
        [
            (
                False,
                "/Library/LaunchDaemons/local.pub-lease.plist",
                "/Library/Application Support/devbox/local.pub-lease.plist.candidate",
                "/Library/LaunchDaemons/.local.pub-lease-reload-required",
            ),
            (
                True,
                "/debug/home/Library/LaunchDaemons/local.pub-lease.plist",
                "/debug/home/Library/Application Support/devbox/local.pub-lease.plist.candidate",
                "/debug/home/Library/LaunchDaemons/.local.pub-lease-reload-required",
            ),
        ],
    )
    def test_supervisor_path_is_system_owned_only_outside_dev_mode(
        self,
        *,
        dev_mode: bool,
        expected_path: str,
        expected_candidate: str,
        expected_marker: str,
    ) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        resolution = next(
            task["ansible.builtin.set_fact"]
            for task in tasks
            if "devbox_pub_plist_path" in task.get("ansible.builtin.set_fact", {})
        )
        deployment = next(
            task for task in tasks if task["name"] == "Pub mode — deploy expiry LaunchDaemon"
        )

        context = {"devbox_pub_home": "/debug/home", "dev_mode": dev_mode}
        resolved = _render_ansible_expression(resolution["devbox_pub_plist_path"], **context)
        candidate = _render_ansible_expression(
            resolution["devbox_pub_candidate_plist_path"],
            **context,
        )
        marker = _render_ansible_expression(
            resolution["devbox_pub_reload_marker_path"],
            **context,
        )

        assert resolved == expected_path
        assert candidate == expected_candidate
        assert marker == expected_marker
        assert _render_ansible_expression(
            str(deployment["become"]),
            dev_mode=dev_mode,
        ) is (not dev_mode)
        assert _render_ansible_expression(
            deployment["ansible.builtin.copy"]["owner"],
            dev_mode=dev_mode,
            omit="OMIT",
        ) == ("OMIT" if dev_mode else "root")
        assert _render_ansible_expression(
            deployment["ansible.builtin.copy"]["group"],
            dev_mode=dev_mode,
            omit="OMIT",
        ) == ("OMIT" if dev_mode else "wheel")

    @pytest.mark.parametrize("dev_mode", [False, True])
    def test_candidate_is_staged_outside_launchdaemons_and_dropped_after_bootstrap(
        self, *, dev_mode: bool
    ) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        resolution = next(
            task["ansible.builtin.set_fact"]
            for task in tasks
            if "devbox_pub_candidate_plist_path" in task.get("ansible.builtin.set_fact", {})
        )
        staging = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — ensure supervisor staging directory exists"
        )
        candidate_render = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — render expiry LaunchDaemon candidate"
        )
        marker_clear = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — clear completed LaunchDaemon reload"
        )
        cleanup = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — remove staged and legacy LaunchDaemon candidates"
        )

        context = {"devbox_pub_home": "/debug/home", "dev_mode": dev_mode}
        staged_directory = _render_ansible_expression(
            resolution["devbox_pub_staging_dir"], **context
        )
        candidate = _render_ansible_expression(
            resolution["devbox_pub_candidate_plist_path"], **context
        )
        legacy_candidate = _render_ansible_expression(
            resolution["devbox_pub_legacy_candidate_plist_path"], **context
        )

        assert candidate == f"{staged_directory}/local.pub-lease.plist.candidate"
        assert not str(staged_directory).endswith("/Library/LaunchDaemons")
        assert legacy_candidate.endswith("/Library/LaunchDaemons/.local.pub-lease.plist.candidate")
        assert staging["ansible.builtin.file"]["path"] == "{{ devbox_pub_staging_dir }}"
        assert staging["ansible.builtin.file"]["state"] == "directory"
        assert staging["ansible.builtin.file"]["mode"] == "0700"
        assert tasks.index(staging) < tasks.index(candidate_render)
        assert tasks.index(marker_clear) < tasks.index(cleanup)
        assert cleanup["ansible.builtin.file"]["state"] == "absent"
        assert cleanup["loop"] == [
            "{{ devbox_pub_candidate_plist_path }}",
            "{{ devbox_pub_legacy_candidate_plist_path }}",
        ]
        assert _ansible_conditions_hold(cleanup["when"], devbox_pub_mode_enabled=True)
        assert not _ansible_conditions_hold(cleanup["when"], devbox_pub_mode_enabled=False)

    def test_launchdaemon_is_managed_in_the_system_domain_with_legacy_cleanup(self) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        commands = {
            task["name"]: task["ansible.builtin.command"]["argv"]
            for task in tasks
            if "ansible.builtin.command" in task
            and task["ansible.builtin.command"]["argv"][0] == "/bin/launchctl"
        }

        assert commands["Pub mode — check expiry LaunchDaemon status"] == [
            "/bin/launchctl",
            "print",
            "system/local.pub-lease",
        ]
        assert commands["Pub mode — bootout changed expiry LaunchDaemon"] == [
            "/bin/launchctl",
            "bootout",
            "system/local.pub-lease",
        ]
        assert commands["Pub mode — bootstrap expiry LaunchDaemon"] == [
            "/bin/launchctl",
            "bootstrap",
            "system",
            "{{ devbox_pub_plist_path }}",
        ]
        assert commands["Pub mode — bootout disabled expiry LaunchDaemon"] == [
            "/bin/launchctl",
            "bootout",
            "system/local.pub-lease",
        ]
        assert commands["Pub mode — bootout legacy GUI expiry LaunchAgent"] == [
            "/bin/launchctl",
            "bootout",
            "gui/{{ ansible_facts['user_uid'] }}/local.pub-lease",
        ]
        assert commands["Pub mode — bootout disabled legacy GUI expiry LaunchAgent"] == [
            "/bin/launchctl",
            "bootout",
            "gui/{{ ansible_facts['user_uid'] }}/local.pub-lease",
        ]
        bootstrap = next(
            task for task in tasks if task["name"] == "Pub mode — bootstrap expiry LaunchDaemon"
        )
        legacy_bootout = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — bootout legacy GUI expiry LaunchAgent"
        )
        legacy_removal = next(
            task
            for task in tasks
            if task["name"] == "Pub mode — remove migrated GUI LaunchAgent plist"
        )
        assert tasks.index(bootstrap) < tasks.index(legacy_bootout) < tasks.index(legacy_removal)
        assert legacy_removal["ansible.builtin.file"] == {
            "path": "{{ devbox_pub_home }}/Library/LaunchAgents/local.pub-lease.plist",
            "state": "absent",
        }
        assert _ansible_conditions_hold(
            legacy_removal["when"],
            devbox_pub_mode_enabled=True,
        )

    def test_dev_mode_never_runs_live_pub_commands(self) -> None:
        tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
        context = {
            "devbox_pub_mode_enabled": False,
            "dev_mode": True,
            "devbox_pub_controller": {"stat": {"exists": True}},
            "devbox_pub_launchagent": {"changed": True},
            "devbox_pub_launchagent_status": {"rc": 0},
        }
        live_commands = [
            task
            for task in tasks
            if "ansible.builtin.command" in task
            and (
                task["ansible.builtin.command"]["argv"][0] == "/bin/launchctl"
                or task["ansible.builtin.command"]["argv"]
                == ["{{ devbox_pub_home }}/.local/bin/pub-lease", "off"]
            )
        ]

        assert live_commands
        assert all(not _ansible_conditions_hold(task["when"], **context) for task in live_commands)
        marker_tasks = [
            task
            for task in tasks
            if task["name"]
            in {
                "Pub mode — ensure lease state directory exists",
                "Pub mode — block activation during teardown",
                "Pub mode — allow activation when managed",
            }
        ]
        assert all(not _ansible_conditions_hold(task["when"], **context) for task in marker_tasks)

    def test_teardown_dispatches_the_installed_controller_through_its_own_shebang(
        self, tmp_path: Path
    ) -> None:
        # Teardown execs {{ devbox_pub_home }}/.local/bin/pub-lease directly
        # rather than through an explicit interpreter, so whatever controller is
        # already installed runs under its own shebang. The stub below uses
        # /bin/bash purely to prove the dispatch is interpreter-agnostic — no
        # shell controller has ever shipped from this repository.
        controller = tmp_path / "pub-lease"
        _write_executable(
            controller,
            "#!/bin/bash\ntest \"$1\" = off || exit 64\nprintf 'legacy controller restored\\n'\n",
        )

        completed = subprocess.run(
            [str(controller), "off"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 0
        assert completed.stdout == "legacy controller restored\n"


class TestPubLeaseQualityGates:
    def test_controller_does_not_depend_on_shell_json_or_lock_tools(self) -> None:
        source = PUB_LEASE.read_text(encoding="utf-8")

        assert '"jq"' not in source
        assert '["lockf"' not in source
        assert '["flock"' not in source


def _lease_document(**overrides: object) -> str:
    state: dict[str, object] = {
        "version": 1,
        "phase": "active",
        "lease_id": "greeting-fixture",
        "started_at": 1_000_000,
        "expires_at": 1_001_800,
        "boot_session": "boot-a",
        "previous_mode": "proxy",
        "previous_status": "Disconnected",
        "previous_connected": False,
        "expected_mode": "tunnel_only",
        "network_signature": None,
        "network_misses": 0,
        "hard_expires_at": None,
    }
    state.update(overrides)
    return json.dumps(state, indent=2) + "\n"


def _greet(tmp_path: Path, lease: str | None) -> subprocess.CompletedProcess[str]:
    fish = shutil.which("fish")
    assert fish is not None
    state_dir = tmp_path / "lease-state"
    state_dir.mkdir()
    if lease is not None:
        (state_dir / "lease.json").write_text(lease, encoding="utf-8")
    # PATH holds nothing but a recording date, so any other external command the greeting reached
    # for would be reported as unknown on stderr instead of silently succeeding.
    path_dir = tmp_path / "bin"
    path_dir.mkdir()
    _write_executable(
        path_dir / "date",
        f'#!/bin/sh\necho date >>"{tmp_path / "spawned"}"\nexec /bin/date "$@"\n',
    )
    return subprocess.run(
        [fish, "--no-config", "--command", "source $argv[1]; fish_greeting", str(PUB_GREETING)],
        env={
            "PATH": str(path_dir),
            "HOME": str(tmp_path),
            "PUB_LEASE_STATE_DIR": str(state_dir),
        },
        capture_output=True,
        text=True,
        check=False,
    )


class TestPubLeaseGreeting:
    def test_the_greeting_ships_with_the_deployed_fish_functions(self) -> None:
        tasks = yaml.safe_load(INSTALL_CONFIGS.read_text(encoding="utf-8"))
        deployed_directories = [
            item
            for task in tasks
            if task.get("name") == "Deploy dotfile directories"
            for item in task["loop"]
        ]

        assert ".config/fish/functions" in deployed_directories
        assert PUB_GREETING.is_file()

    @pytest.mark.parametrize(
        ("remaining", "expected"),
        [
            (2 * 3600 + 4 * 60 + 30, "pub lease: active, 2h04m remaining\n"),
            (30 * 60 + 30, "pub lease: active, 0h30m remaining\n"),
            (-1, "pub lease: expired, awaiting the reconciler\n"),
        ],
    )
    def test_an_active_lease_is_reported_against_the_clock(
        self, tmp_path: Path, remaining: int, expected: str
    ) -> None:
        lease = _lease_document(expires_at=time.time() + remaining)

        result = _greet(tmp_path, lease)

        assert (result.returncode, result.stderr) == (0, "")
        assert result.stdout == expected
        assert (tmp_path / "spawned").read_text(encoding="utf-8").split() == ["date"]

    @pytest.mark.parametrize(
        ("lease", "expected"),
        [
            (None, ""),
            (_lease_document(phase="activating"), "pub lease: activating\n"),
            (
                _lease_document(phase="restoring"),
                "pub lease: restoring the previous WARP state\n",
            ),
            ("{broken lease", "pub lease: metadata present but unreadable\n"),
            (
                _lease_document(phase="active", expires_at="soon"),
                "pub lease: metadata present but unreadable\n",
            ),
        ],
        ids=["absent", "activating", "restoring", "corrupt", "unparseable-expiry"],
    )
    def test_a_lease_that_needs_no_clock_reports_its_phase_without_spawning_anything(
        self, tmp_path: Path, lease: str | None, expected: str
    ) -> None:
        result = _greet(tmp_path, lease)

        assert (result.returncode, result.stderr) == (0, "")
        assert result.stdout == expected
        assert not (tmp_path / "spawned").exists()


class TestPubProxyMigration:
    def test_install_configs_deploys_migration_and_removes_legacy_guard(self) -> None:
        tasks = yaml.safe_load(INSTALL_CONFIGS.read_text(encoding="utf-8"))
        source_lists = [task["loop"] for task in tasks if isinstance(task.get("loop"), list)]
        removal = next(
            task["ansible.builtin.file"]
            for task in tasks
            if str(task.get("ansible.builtin.file", {}).get("path", "")).endswith(
                "/.config/fish/conf.d/pub_guard.fish"
            )
        )

        assert any(
            ".config/fish/conf.d/pub_proxy_migration.fish" in sources for sources in source_lists
        )
        assert removal["state"] == "absent"
        assert not LEGACY_GUARD.exists()

    def test_interactive_migration_removes_matching_universal_vars_only(
        self, tmp_path: Path
    ) -> None:
        fish = shutil.which("fish")
        assert fish is not None
        home = tmp_path / "home"
        config_home = tmp_path / "config"
        home.mkdir()
        config_home.mkdir()
        command = """
set -U HTTPS_PROXY http://127.0.0.1:8080
set -U HTTP_PROXY http://127.0.0.1:8080
set -U http_proxy http://proxy.example:3128
set -U __pub_proxy_migration_v2 1
source $argv[1]
for var in HTTPS_PROXY HTTP_PROXY http_proxy __pub_proxy_migration_v2 __pub_proxy_migration_v3
    if set -q -U $var
        printf '%s=%s\n' $var $$var
    else
        printf '%s=<unset>\n' $var
    end
end
"""
        env = os.environ.copy()
        for variable in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
            env.pop(variable, None)
        env.update({"HOME": str(home), "XDG_CONFIG_HOME": str(config_home)})

        migrated = subprocess.run(
            [fish, "--interactive", "--command", command, PUB_PROXY_MIGRATION],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert migrated.returncode == 0, migrated.stderr
        assert set(migrated.stdout.splitlines()) == {
            "HTTPS_PROXY=<unset>",
            "HTTP_PROXY=<unset>",
            "http_proxy=http://proxy.example:3128",
            "__pub_proxy_migration_v2=<unset>",
            "__pub_proxy_migration_v3=1",
        }

    def test_shadowed_universal_proxy_defers_migration_until_shadow_is_removed(
        self, tmp_path: Path
    ) -> None:
        fish = shutil.which("fish")
        assert fish is not None
        home = tmp_path / "home"
        config_home = tmp_path / "config"
        home.mkdir()
        config_home.mkdir()
        env = os.environ.copy()
        for variable in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
            env.pop(variable, None)
        env.update(
            {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(config_home),
                "HTTP_PROXY": "http://proxy.example:3128",
            }
        )
        shadowed_command = """
set -U HTTP_PROXY http://127.0.0.1:8080
set -U http_proxy http://unrelated.example:3128
set -U __pub_proxy_migration_v2 1
source $argv[1]
printf 'global=%s\n' $HTTP_PROXY
set -e -g HTTP_PROXY
if set -q -U HTTP_PROXY
    printf 'universal=%s\n' $HTTP_PROXY
else
    printf 'universal=<unset>\n'
end
if set -q -U __pub_proxy_migration_v3
    printf 'marker_v3=%s\n' $__pub_proxy_migration_v3
else
    printf 'marker_v3=<unset>\n'
end
printf 'marker_v2=%s\n' $__pub_proxy_migration_v2
"""

        deferred = subprocess.run(
            [fish, "--interactive", "--command", shadowed_command, PUB_PROXY_MIGRATION],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert deferred.returncode == 0, deferred.stderr
        assert set(deferred.stdout.splitlines()) == {
            "global=http://proxy.example:3128",
            "universal=http://127.0.0.1:8080",
            "marker_v2=1",
            "marker_v3=<unset>",
        }

        env.pop("HTTP_PROXY")
        unshadowed_command = """
source $argv[1]
for var in HTTP_PROXY http_proxy __pub_proxy_migration_v2 __pub_proxy_migration_v3
    if set -q -U $var
        printf '%s=%s\n' $var $$var
    else
        printf '%s=<unset>\n' $var
    end
end
"""
        completed = subprocess.run(
            [fish, "--interactive", "--command", unshadowed_command, PUB_PROXY_MIGRATION],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 0, completed.stderr
        assert set(completed.stdout.splitlines()) == {
            "HTTP_PROXY=<unset>",
            "http_proxy=http://unrelated.example:3128",
            "__pub_proxy_migration_v2=<unset>",
            "__pub_proxy_migration_v3=1",
        }
