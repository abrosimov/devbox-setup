"""Deployment contract for the periodic kitty session snapshot (local.kitty-save-session)."""

from __future__ import annotations

import ast
import itertools
import plistlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

import pytest
import yaml
from jinja2 import Environment, StrictUndefined, select_autoescape

if TYPE_CHECKING:
    from collections.abc import Callable

type Doc = dict[str, object]

ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT / "roles/devbox"
TEMPLATE = ROLE / "templates/darwin/Library/LaunchAgents/local.kitty-save-session.plist.j2"
SAVER_TASKS = ROLE / "tasks/darwin/configure_kitty_session_saver.yml"
MAIN_DARWIN = ROLE / "tasks/main_darwin.yml"
INSTALL_CONFIGS = ROLE / "tasks/install_configs.yml"
KITTY_DIR = ROLE / "files/.config/kitty"
KITTY_SESSION = KITTY_DIR / "kitty_session.py"
KITTY_CONF = KITTY_DIR / "kitty.conf"

HOME = "/Users/ci"
USER_UID = 501
LABEL = "local.kitty-save-session"
SAVER_INCLUDE = "Configure periodic kitty session snapshot (LaunchAgent)"


def _bool_filter(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "on"}
    return bool(value)


def _env() -> Environment:
    env = Environment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=select_autoescape(default_for_string=False),
    )
    filters = cast("dict[str, Callable[..., object]]", env.filters)
    filters["bool"] = _bool_filter
    return env


def _tasks(path: Path) -> list[Doc]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    return loaded


def _task(tasks: list[Doc], name: str) -> Doc:
    return next(task for task in tasks if task["name"] == name)


def _names(tasks: list[Doc]) -> list[str]:
    return [str(task["name"]) for task in tasks]


def _argv(task: Doc) -> list[str]:
    command = cast("Doc", task["ansible.builtin.command"])
    return [str(argument) for argument in cast("list[object]", command["argv"])]


def _render(text: str, **context: object) -> str:
    facts = {"env": {"HOME": HOME}, "user_uid": USER_UID}
    return _env().from_string(text).render(ansible_facts=facts, **context)


def _conditions(task: Doc) -> list[str]:
    when = task["when"]
    if isinstance(when, list):
        return [str(item) for item in when]
    return [str(when)]


def _holds(task: Doc, **context: object) -> bool:
    env = _env()
    return all(
        bool(env.compile_expression(condition)(**context)) for condition in _conditions(task)
    )


def _plist() -> Doc:
    return plistlib.loads(_render(TEMPLATE.read_text(encoding="utf-8")).encode("utf-8"))


def _kitty_app_executable() -> str:
    module = ast.parse(KITTY_SESSION.read_text(encoding="utf-8"))
    for node in module.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "KITTY_APP_EXECUTABLE"
            and isinstance(node.value, ast.Constant)
        ):
            return str(node.value.value)
    message = "KITTY_APP_EXECUTABLE is not a module constant of kitty_session.py"
    raise AssertionError(message)


class TestLaunchAgentTemplate:
    def test_the_label_names_the_service_the_tasks_address(self) -> None:
        assert _plist()["Label"] == LABEL
        assert LABEL in " ".join(
            _argv(_task(_tasks(SAVER_TASKS), "Kitty session saver — check current LaunchAgent"))
        )

    def test_it_runs_every_five_minutes(self) -> None:
        assert _plist()["StartInterval"] == 300

    def test_it_does_not_run_at_load_because_kitty_is_still_restoring_then(self) -> None:
        plist = _plist()

        assert "RunAtLoad" not in plist
        assert "KeepAlive" not in plist

    def test_a_success_every_five_minutes_is_not_logged(self) -> None:
        plist = _plist()

        assert "StandardOutPath" not in plist
        assert plist["StandardErrorPath"] == f"{HOME}/Library/Logs/kitty-save-session.log"

    def test_it_runs_the_script_in_kittys_own_interpreter_by_absolute_paths(self) -> None:
        assert _plist()["ProgramArguments"] == [
            "/Applications/kitty.app/Contents/MacOS/kitty",
            "+launch",
            f"{HOME}/.config/kitty/kitty_session.py",
        ]

    def test_the_kitty_path_is_the_one_the_script_falls_back_to(self) -> None:
        program = cast("list[str]", _plist()["ProgramArguments"])

        assert program[0] == _kitty_app_executable()

    def test_the_script_it_runs_is_the_one_the_repository_deploys(self) -> None:
        program = cast("list[str]", _plist()["ProgramArguments"])

        assert program[2].removeprefix(HOME + "/") == ".config/kitty/kitty_session.py"
        assert KITTY_SESSION.is_file()
        deploy = _task(_tasks(INSTALL_CONFIGS), "Deploy dotfile directories")
        assert ".config/kitty" in cast("list[str]", deploy["loop"])

    def test_the_log_directory_is_created_by_the_tasks(self) -> None:
        directories = _task(
            _tasks(SAVER_TASKS), "Kitty session saver — ensure LaunchAgent directories"
        )
        rendered = [_render(item) for item in cast("list[str]", directories["loop"])]

        assert f"{HOME}/Library/LaunchAgents" in rendered
        assert str(Path(cast("str", _plist()["StandardErrorPath"])).parent) in rendered


class TestSocketDirectory:
    def _socket_directory_task(self) -> Doc:
        return _task(
            _tasks(INSTALL_CONFIGS), "Ensure kitty's private remote-control socket directory exists"
        )

    def test_it_is_private_to_the_user(self) -> None:
        directory = cast("Doc", self._socket_directory_task()["ansible.builtin.file"])

        assert directory["state"] == "directory"
        assert directory["mode"] == "0700"

    def test_it_is_the_directory_kitty_conf_listens_in(self) -> None:
        directory = cast("Doc", self._socket_directory_task()["ansible.builtin.file"])
        path = (
            _env()
            .from_string(str(directory["path"]))
            .render(devbox_paths={"dotfiles_root_dir": HOME})
        )
        (listen_on,) = re.findall(
            r"^listen_on unix:(\S+)$", KITTY_CONF.read_text(encoding="utf-8"), re.MULTILINE
        )

        assert Path(listen_on.replace("${HOME}", HOME)).parent == Path(path)


class TestLaunchAgentTasks:
    tasks = _tasks(SAVER_TASKS)

    def test_the_agent_is_written_loaded_checked_then_replaced_in_that_order(self) -> None:
        names = _names(self.tasks)

        assert names.index("Kitty session saver — install LaunchAgent") < names.index(
            "Kitty session saver — check current LaunchAgent"
        )
        assert names.index("Kitty session saver — check current LaunchAgent") < names.index(
            "Kitty session saver — unload old definition after plist change"
        )
        assert names.index(
            "Kitty session saver — unload old definition after plist change"
        ) < names.index("Kitty session saver — bootstrap LaunchAgent")

    def test_the_template_is_rendered_to_the_plist_that_is_bootstrapped(self) -> None:
        install = _task(self.tasks, "Kitty session saver — install LaunchAgent")
        template = cast("Doc", install["ansible.builtin.template"])
        bootstrap = _argv(_task(self.tasks, "Kitty session saver — bootstrap LaunchAgent"))

        assert (ROLE / "templates" / str(template["src"])) == TEMPLATE
        assert template["mode"] == "0644"
        assert _render(str(template["dest"])) == f"{HOME}/Library/LaunchAgents/{LABEL}.plist"
        assert [_render(argument) for argument in bootstrap] == [
            "/bin/launchctl",
            "bootstrap",
            f"gui/{USER_UID}",
            f"{HOME}/Library/LaunchAgents/{LABEL}.plist",
        ]
        assert install["register"] == "devbox_kitty_saver_plist"

    @pytest.mark.parametrize(
        "name",
        [
            "Kitty session saver — check current LaunchAgent",
            "Kitty session saver — unload old definition after plist change",
        ],
    )
    def test_the_service_is_addressed_in_the_users_gui_domain(self, name: str) -> None:
        argv = [_render(argument) for argument in _argv(_task(self.tasks, name))]

        assert argv[0] == "/bin/launchctl"
        assert argv[-1] == f"gui/{USER_UID}/{LABEL}"

    def test_the_status_check_runs_in_check_mode_and_never_fails_the_play(self) -> None:
        status = _task(self.tasks, "Kitty session saver — check current LaunchAgent")

        assert _argv(status)[:2] == ["/bin/launchctl", "print"]
        assert status["check_mode"] is False
        assert status["changed_when"] is False
        assert status["failed_when"] is False
        assert status["register"] == "devbox_kitty_saver_status"

    @pytest.mark.parametrize(
        ("plist_changed", "loaded", "check_mode", "unloads", "loads"),
        [
            pytest.param(False, True, False, False, False, id="unchanged-and-loaded"),
            pytest.param(False, False, False, False, True, id="unchanged-but-not-loaded"),
            pytest.param(True, True, False, True, True, id="changed-and-loaded"),
            pytest.param(True, False, False, False, True, id="changed-and-not-loaded"),
            pytest.param(False, True, True, False, False, id="check-unchanged-loaded"),
            pytest.param(False, False, True, False, False, id="check-unchanged-not-loaded"),
            pytest.param(True, True, True, False, False, id="check-changed-loaded"),
            pytest.param(True, False, True, False, False, id="check-changed-not-loaded"),
        ],
    )
    def test_the_agent_is_unloaded_and_loaded_only_when_needed(
        self,
        *,
        plist_changed: bool,
        loaded: bool,
        check_mode: bool,
        unloads: bool,
        loads: bool,
    ) -> None:
        context = {
            "ansible_check_mode": check_mode,
            "devbox_kitty_saver_plist": {"changed": plist_changed},
            "devbox_kitty_saver_status": {"rc": 0 if loaded else 113},
        }
        unload = _task(self.tasks, "Kitty session saver — unload old definition after plist change")
        load = _task(self.tasks, "Kitty session saver — bootstrap LaunchAgent")

        assert _holds(unload, **context) is unloads
        assert _holds(load, **context) is loads

    @pytest.mark.parametrize(
        ("plist_changed", "loaded"), list(itertools.product([False, True], repeat=2))
    )
    def test_bootstrap_never_meets_a_loaded_old_definition(
        self, *, plist_changed: bool, loaded: bool
    ) -> None:
        context = {
            "ansible_check_mode": False,
            "devbox_kitty_saver_plist": {"changed": plist_changed},
            "devbox_kitty_saver_status": {"rc": 0 if loaded else 113},
        }
        unload = _task(self.tasks, "Kitty session saver — unload old definition after plist change")
        load = _task(self.tasks, "Kitty session saver — bootstrap LaunchAgent")

        still_loaded = loaded and not _holds(unload, **context)

        assert not (_holds(load, **context) and still_loaded)

    @pytest.mark.parametrize(
        "name",
        [
            "Kitty session saver — unload old definition after plist change",
            "Kitty session saver — bootstrap LaunchAgent",
        ],
    )
    def test_the_launchctl_calls_report_a_change(self, name: str) -> None:
        assert _task(self.tasks, name)["changed_when"] is True


class TestIncludedFromTheDarwinFlow:
    steps: Final = _tasks(MAIN_DARWIN)

    def test_it_runs_after_the_configs_it_depends_on_are_installed(self) -> None:
        names = _names(self.steps)

        assert names.index("Install configs") < names.index(SAVER_INCLUDE)

    def test_it_includes_the_saver_task_file(self) -> None:
        include = _task(self.steps, SAVER_INCLUDE)

        assert (
            include["ansible.builtin.include_tasks"] == "darwin/configure_kitty_session_saver.yml"
        )
        assert (ROLE / "tasks/darwin/configure_kitty_session_saver.yml").is_file()

    @pytest.mark.parametrize(
        ("context", "included"),
        [
            pytest.param({"dev_mode": False}, True, id="normal-run"),
            pytest.param({"dev_mode": True}, False, id="dev-mode"),
            pytest.param({"dev_mode": "true"}, False, id="dev-mode-string"),
            pytest.param({"dev_mode": "false"}, True, id="dev-mode-false-string"),
            pytest.param({}, True, id="dev-mode-undefined"),
        ],
    )
    def test_it_is_skipped_in_dev_mode(self, context: Doc, *, included: bool) -> None:
        include = _task(self.steps, SAVER_INCLUDE)

        assert _holds(include, **context) is included
