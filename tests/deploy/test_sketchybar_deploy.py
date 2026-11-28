"""Deployment contract of the SketchyBar status bar.

Artefacts that have to agree: the Lua rc template (declares the bar and its items), the
renderer in Hammerspoon (sets those items by name), the Rift config (reserves room at the
top of each display and names the workspaces), configure_sketchybar.yml and its include,
and the two NSGlobalDomain keys that hide the macOS menu bar. The rc is rendered the way
Ansible's template module does and executed against a fake `sketchybar` that records its
arguments; nothing here starts a service.
"""

from __future__ import annotations

import copy
import itertools
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

import pytest
import yaml
from jinja2 import Environment, StrictUndefined, Undefined, select_autoescape
from jinja2.nativetypes import NativeEnvironment

if TYPE_CHECKING:
    from collections.abc import Callable

type RunLua = Callable[..., object]
type Doc = dict[str, object]
type Commands = list[tuple[str, list[str]]]

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = REPO_ROOT / "roles/devbox"
DEFAULTS_DIR = ROLE / "defaults/main"
PROFILES_DIR = REPO_ROOT / "profiles"
RC_TEMPLATE = ROLE / "templates/darwin/.config/sketchybar/sketchybarrc.j2"
RIFT_TEMPLATE = ROLE / "templates/darwin/.config/rift/config.toml.j2"
TASKS_FILE = ROLE / "tasks/darwin/configure_sketchybar.yml"
MAIN_DARWIN = ROLE / "tasks/main_darwin.yml"
MAIN_TASKS = ROLE / "tasks/main.yml"
RENDER_LUA = ROLE / "files/.hammerspoon/modules/bar_render.lua"

PROFILE_NAMES: Final = ("personal", "work")
INCLUDE_PATH: Final = "darwin/configure_sketchybar.yml"
WM_INCLUDE_PATH: Final = "darwin/configure_window_manager.yml"
WORKSPACES: Final = [f"ws.{n}" for n in range(1, 10)]
RIGHT_ITEMS: Final = ["clock", "battery", "ram", "cpu", "edge", "input"]
RIGHT_ITEMS_WITHOUT_EDGE: Final = [item for item in RIGHT_ITEMS if item != "edge"]
ITEMS: Final = [*WORKSPACES, "front_app", *RIGHT_ITEMS]
RELOGIN_HINT: Final = "Re-login hint (only when a login-cached setting changed)"
FLAGS: Final = {"--bar", "--default", "--add", "--set", "--subscribe"}
SERVICE: Final = "community.general.homebrew_services"
TEMPLATE: Final = "ansible.builtin.template"
DIRECTORY: Final = "ansible.builtin.file"
COMMAND: Final = "ansible.builtin.command"

FAKE_SKETCHYBAR: Final = """#!/bin/sh
printf '%s\\0' "$@" > "$SKETCHYBAR_RECORD_DIR/call.$$"
exit "${FAKE_SKETCHYBAR_RC:-0}"
"""


def _mapping(path: Path) -> Doc:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _task_list(path: Path) -> list[Doc]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    return loaded


def _role_defaults() -> Doc:
    merged: Doc = {}
    for path in sorted(DEFAULTS_DIR.glob("*.yml")):
        merged.update(_mapping(path))
    return merged


def _profile_vars(profile: str) -> Doc:
    return {**_role_defaults(), **_mapping(PROFILES_DIR / f"{profile}.yml")}


def _render(template: Path, profile: str, **overrides: object) -> str:
    env = Environment(
        undefined=StrictUndefined,
        trim_blocks=True,
        keep_trailing_newline=True,
        autoescape=select_autoescape(default_for_string=False),
    )
    return env.from_string(template.read_text(encoding="utf-8")).render(
        **{**_profile_vars(profile), **overrides}
    )


def _edge_packages(profile: str, **edge: object) -> Doc:
    packages = copy.deepcopy(cast("Doc", _profile_vars(profile)["devbox_packages"]))
    packages["otelbox_edge"] = {**cast("Doc", packages["otelbox_edge"]), **edge}
    return packages


def _rift_workspace_names(profile: str) -> list[str]:
    config = tomllib.loads(_render(RIFT_TEMPLATE, profile))
    names = config["virtual_workspaces"]["workspace_names"]
    assert isinstance(names, list)
    return [str(name) for name in names]


def _to_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "on"}
    return bool(value)


def _changed(result: Doc) -> bool:
    return bool(result.get("changed"))


def _logic_env() -> Environment:
    env = Environment(
        undefined=StrictUndefined, autoescape=select_autoescape(default_for_string=False)
    )
    filters = cast("dict[str, Callable[..., object]]", env.filters)
    tests = cast("dict[str, Callable[..., object]]", env.tests)
    filters["bool"] = _to_bool
    tests["changed"] = _changed
    return env


def _conditions(task: Doc) -> list[str]:
    when = task.get("when")
    if when is None:
        return []
    if isinstance(when, list):
        return [str(item) for item in when]
    return [str(when)]


def _holds(task: Doc, **context: object) -> bool:
    env = _logic_env()
    return all(bool(env.compile_expression(c)(**context)) for c in _conditions(task))


def _module_of(task: Doc) -> str:
    return next(key for key in task if key.startswith(("ansible.", "community.")))


def _by_module(module: str) -> Doc:
    matches = [task for task in _task_list(TASKS_FILE) if module in task]
    assert len(matches) == 1, module
    return matches[0]


def _args_of(module: str) -> Doc:
    args = _by_module(module)[module]
    assert isinstance(args, dict)
    return args


@dataclass(frozen=True)
class RcRun:
    calls: list[list[str]]
    returncode: int
    stderr: str


def _run_rc(
    lua: str,
    workdir: Path,
    text: str,
    *,
    sketchybar_rc: int = 0,
    sketchybar_installed: bool = True,
) -> RcRun:
    bin_dir = workdir / "bin"
    record_dir = workdir / "calls"
    bin_dir.mkdir(parents=True)
    record_dir.mkdir()
    if sketchybar_installed:
        fake = bin_dir / "sketchybar"
        fake.write_text(FAKE_SKETCHYBAR, encoding="utf-8")
        fake.chmod(0o755)
    rc = workdir / "sketchybarrc"
    rc.write_text(text, encoding="utf-8")
    env = {
        "PATH": str(bin_dir),
        "SKETCHYBAR_RECORD_DIR": str(record_dir),
        "FAKE_SKETCHYBAR_RC": str(sketchybar_rc),
    }
    done = subprocess.run(
        [lua, str(rc)], env=env, capture_output=True, text=True, check=False, timeout=30
    )
    calls = [
        path.read_bytes().decode("utf-8").split("\0")[:-1] for path in sorted(record_dir.iterdir())
    ]
    return RcRun(calls, done.returncode, done.stderr)


def _rendered_run(lua: str, workdir: Path, profile: str, **overrides: object) -> RcRun:
    return _run_rc(lua, workdir, _render(RC_TEMPLATE, profile, **overrides))


def _commands(run: RcRun) -> Commands:
    assert run.returncode == 0, run.stderr
    assert len(run.calls) == 1
    commands: Commands = []
    for arg in run.calls[0]:
        if arg in FLAGS:
            commands.append((arg, []))
        else:
            assert commands, f"argument {arg!r} before any flag"
            commands[-1][1].append(arg)
    return commands


def _properties(words: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for word in words:
        key, separator, value = word.partition("=")
        assert separator == "=", word
        result[key] = value
    return result


def _declared(commands: Commands) -> list[tuple[str, str]]:
    return [
        (words[1], words[2]) for flag, words in commands if flag == "--add" and words[0] == "item"
    ]


def _set_properties(commands: Commands) -> dict[str, dict[str, str]]:
    return {words[0]: _properties(words[1:]) for flag, words in commands if flag == "--set"}


def _flag_properties(commands: Commands, flag: str) -> dict[str, str]:
    return _properties(next(words for name, words in commands if name == flag))


class TestRcTemplate:
    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_it_is_a_lua_script_run_by_the_homebrew_interpreter(self, profile: str) -> None:
        assert _render(RC_TEMPLATE, profile).startswith("#!/usr/bin/env lua\n")

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_it_declares_every_item_in_one_sketchybar_call(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        commands = _commands(_rendered_run(lua, tmp_path, profile))

        assert [name for name, _ in _declared(commands)] == ITEMS

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_workspaces_and_the_front_app_sit_left_and_the_readings_right(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        positions = dict(_declared(_commands(_rendered_run(lua, tmp_path, profile))))

        assert positions == {
            **dict.fromkeys([*WORKSPACES, "front_app"], "left"),
            **dict.fromkeys(RIGHT_ITEMS, "right"),
        }

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_the_right_side_is_added_rightmost_first(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        commands = _commands(_rendered_run(lua, tmp_path, profile))

        right = [name for name, position in _declared(commands) if position == "right"]

        assert right == RIGHT_ITEMS

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_every_item_is_added_once_before_it_is_set(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        added: set[str] = set()
        for flag, words in _commands(_rendered_run(lua, tmp_path, profile)):
            if flag == "--add":
                assert words[1] not in added
                added.add(words[1])
            if flag == "--set":
                assert words[0] in added, words[0]

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_the_bar_is_on_top_of_every_display_at_the_configured_height(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        bar = _flag_properties(_commands(_rendered_run(lua, tmp_path, profile)), "--bar")

        assert bar["position"] == "top"
        assert bar["display"] == "all"
        assert bar["sticky"] == "on"
        assert bar["height"] == str(_profile_vars(profile)["devbox_sketchybar_height"])

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_items_default_to_the_configured_font_without_icons(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        default = _flag_properties(_commands(_rendered_run(lua, tmp_path, profile)), "--default")

        assert default["label.font"] == _profile_vars(profile)["devbox_sketchybar_font"]
        assert default["icon.drawing"] == "off"

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_workspaces_start_hidden_labelled_with_their_number_and_inset_from_the_bar(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        settings = _set_properties(_commands(_rendered_run(lua, tmp_path, profile)))
        height = int(cast("int", _profile_vars(profile)["devbox_sketchybar_height"]))

        for number in range(1, 10):
            properties = settings[f"ws.{number}"]
            assert properties["drawing"] == "off"
            assert properties["label"] == str(number)
            assert int(properties["background.height"]) < height

    def test_the_height_and_font_variables_reach_the_bar_the_pills_and_the_default_font(
        self, lua: str, tmp_path: Path
    ) -> None:
        font = "Kirill's $HOME Mono:Bold:13.0"

        commands = _commands(
            _rendered_run(
                lua, tmp_path, "personal", devbox_sketchybar_height=40, devbox_sketchybar_font=font
            )
        )

        assert _flag_properties(commands, "--bar")["height"] == "40"
        assert _set_properties(commands)["ws.1"]["background.height"] == "32"
        assert _flag_properties(commands, "--default")["label.font"] == font

    def test_a_taller_bar_gives_taller_workspace_pills(self, lua: str, tmp_path: Path) -> None:
        pills = [
            int(
                _set_properties(
                    _commands(
                        _rendered_run(
                            lua, tmp_path / str(height), "personal", devbox_sketchybar_height=height
                        )
                    )
                )["ws.1"]["background.height"]
            )
            for height in (24, 48)
        ]

        assert pills[0] < pills[1]

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_no_item_runs_a_script_because_hammerspoon_pushes_every_value(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        run = _rendered_run(lua, tmp_path, profile)
        _commands(run)

        assert "--subscribe" not in run.calls[0]
        assert not [
            arg for arg in run.calls[0] if re.match(r"(?:\w+\.)?(?:script|update_freq)=", arg)
        ]

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_it_exits_zero_when_sketchybar_succeeds(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        run = _rendered_run(lua, tmp_path, profile)

        assert run.returncode == 0, run.stderr

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    @pytest.mark.parametrize("sketchybar_rc", [1, 2, 127])
    def test_it_exits_non_zero_when_sketchybar_fails(
        self, lua: str, tmp_path: Path, profile: str, sketchybar_rc: int
    ) -> None:
        run = _run_rc(lua, tmp_path, _render(RC_TEMPLATE, profile), sketchybar_rc=sketchybar_rc)

        assert len(run.calls) == 1
        assert run.returncode != 0

    def test_it_exits_non_zero_when_sketchybar_is_not_installed(
        self, lua: str, tmp_path: Path
    ) -> None:
        run = _run_rc(lua, tmp_path, _render(RC_TEMPLATE, "personal"), sketchybar_installed=False)

        assert run.calls == []
        assert run.returncode != 0


class TestEdgeItem:
    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_the_edge_item_sits_on_the_right_between_cpu_and_input(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        declared = _declared(_commands(_rendered_run(lua, tmp_path, profile)))

        right = [name for name, position in declared if position == "right"]

        assert right[right.index("cpu") + 1 : right.index("input")] == ["edge"]
        assert dict(declared)["edge"] == "right"

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_the_edge_item_alone_draws_an_icon_in_the_configured_font(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        font = str(_profile_vars(profile)["devbox_sketchybar_font"])

        settings = _set_properties(_commands(_rendered_run(lua, tmp_path, profile)))

        assert settings["edge"]["icon.drawing"] == "on"
        assert settings["edge"]["icon.font"] == font
        assert settings["edge"]["padding_left"] == "10"
        assert {name for name, props in settings.items() if "icon.drawing" in props} == {"edge"}

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_the_edge_item_is_declared_when_the_edge_is_enabled(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        packages = _edge_packages(profile, enabled=True)

        commands = _commands(_rendered_run(lua, tmp_path, profile, devbox_packages=packages))

        assert "edge" in [name for name, _ in _declared(commands)]

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_a_machine_without_the_edge_gets_no_edge_item(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        packages = _edge_packages(profile, enabled=False)

        commands = _commands(_rendered_run(lua, tmp_path, profile, devbox_packages=packages))

        declared = _declared(commands)
        assert "edge" not in [name for name, _ in declared]
        assert [name for name, position in declared if position == "right"] == (
            RIGHT_ITEMS_WITHOUT_EDGE
        )
        assert "edge" not in _set_properties(commands)

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_a_machine_without_the_edge_still_declares_every_other_item_and_no_icon(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        packages = _edge_packages(profile, enabled=False)

        commands = _commands(_rendered_run(lua, tmp_path, profile, devbox_packages=packages))

        assert [name for name, _ in _declared(commands)] == [
            *WORKSPACES,
            "front_app",
            *RIGHT_ITEMS_WITHOUT_EDGE,
        ]
        assert not [
            (item, key)
            for item, props in _set_properties(commands).items()
            for key in props
            if key.startswith("icon.")
        ]

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_a_missing_enabled_flag_counts_as_enabled(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        packages = _edge_packages(profile)
        edge = cast("Doc", packages["otelbox_edge"])
        del edge["enabled"]

        commands = _commands(_rendered_run(lua, tmp_path, profile, devbox_packages=packages))

        assert "edge" in [name for name, _ in _declared(commands)]


def _driven_items(run_lua: RunLua, workspace_names: list[str]) -> set[str]:
    script = """
local render = dofile(DATA.render)
local view = {}
for i, name in ipairs(DATA.names) do
  view[i] = { name = name, display_uuid = "D1", layout = "M", visible = true, occupied = true }
end
local args = render.workspace_args(view, { D1 = 1 })
local status = render.status_args({
  cpu = 1, ram = 2, clock = "c", input = "EN", app = "a",
  battery = { percent = 50, charging = false },
})
for _, arg in ipairs(status) do args[#args + 1] = arg end
local edge = render.edge_args({ state = "ok", percent = 12, level = "ok", markers = {} })
for _, arg in ipairs(edge) do args[#args + 1] = arg end
print(encode(args))
"""
    args = cast("list[str]", run_lua(script, {"render": str(RENDER_LUA), "names": workspace_names}))
    return {args[i + 1] for i, arg in enumerate(args) if arg == "--set"}


class TestAgreementWithTheRenderer:
    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_every_item_the_renderer_sets_is_declared_by_the_rc(
        self, lua: str, run_lua: RunLua, tmp_path: Path, profile: str
    ) -> None:
        declared = {n for n, _ in _declared(_commands(_rendered_run(lua, tmp_path, profile)))}

        driven = _driven_items(run_lua, _rift_workspace_names(profile))

        assert driven - declared == set()

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_every_item_the_rc_declares_is_driven_by_the_renderer(
        self, lua: str, run_lua: RunLua, tmp_path: Path, profile: str
    ) -> None:
        declared = {n for n, _ in _declared(_commands(_rendered_run(lua, tmp_path, profile)))}

        driven = _driven_items(run_lua, _rift_workspace_names(profile))

        assert declared - driven == set()

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_without_the_edge_the_renderer_drives_only_the_edge_item_beyond_the_rc(
        self, lua: str, run_lua: RunLua, tmp_path: Path, profile: str
    ) -> None:
        packages = _edge_packages(profile, enabled=False)
        commands = _commands(_rendered_run(lua, tmp_path, profile, devbox_packages=packages))
        declared = {n for n, _ in _declared(commands)}

        driven = _driven_items(run_lua, _rift_workspace_names(profile))

        assert driven - declared == {"edge"}
        assert declared - driven == set()

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_the_workspace_items_are_the_workspaces_rift_names(
        self, lua: str, tmp_path: Path, profile: str
    ) -> None:
        commands = _commands(_rendered_run(lua, tmp_path, profile))

        items = [name for name, _ in _declared(commands) if name.startswith("ws.")]

        assert items == [f"ws.{name}" for name in _rift_workspace_names(profile)]

    def test_the_rc_paints_with_the_renderers_background_and_foreground(
        self, lua: str, run_lua: RunLua, tmp_path: Path
    ) -> None:
        script = "local render = dofile(DATA.render)\nprint(encode(render.COLOURS))"
        colours = cast("dict[str, str]", run_lua(script, {"render": str(RENDER_LUA)}))
        commands = _commands(_rendered_run(lua, tmp_path, "personal"))

        assert _flag_properties(commands, "--bar")["color"] == colours["bg"]
        assert _flag_properties(commands, "--default")["label.color"] == colours["fg"]


class TestConfigureTasks:
    def test_the_config_directory_is_created_before_the_config_is_written(self) -> None:
        modules = [_module_of(task) for task in _task_list(TASKS_FILE)]
        args = _args_of(DIRECTORY)

        assert modules.index(DIRECTORY) < modules.index(TEMPLATE)
        assert args["state"] == "directory"
        assert args["path"] == "{{ devbox_paths.dotfiles_root_dir }}/.config/sketchybar"
        assert args["mode"] == "0755"

    def test_the_config_lands_executable_because_sketchybar_runs_it_directly(self) -> None:
        args = _args_of(TEMPLATE)

        assert args["mode"] == "0755"
        assert args["dest"] == (
            "{{ devbox_paths.dotfiles_root_dir }}/.config/sketchybar/sketchybarrc"
        )

    def test_the_template_source_exists_under_the_roles_templates(self) -> None:
        src = str(_args_of(TEMPLATE)["src"])

        assert src == "darwin/.config/sketchybar/sketchybarrc.j2"
        assert (ROLE / "templates" / src).is_file()

    @pytest.mark.parametrize("module", [DIRECTORY, TEMPLATE])
    def test_the_directory_and_config_are_written_in_dev_mode_too(self, module: str) -> None:
        task = _by_module(module)

        assert _holds(task, dev_mode=True)
        assert _holds(task, dev_mode=False)

    @pytest.mark.parametrize(
        ("dev_mode", "runs"),
        [
            (False, True),
            ("false", True),
            ("no", True),
            (True, False),
            ("true", False),
            ("True", False),
            ("yes", False),
        ],
    )
    def test_the_service_task_is_skipped_in_dev_mode_only(
        self, *, dev_mode: object, runs: bool
    ) -> None:
        assert _holds(_by_module(SERVICE), dev_mode=dev_mode) is runs

    def test_the_service_task_runs_when_dev_mode_is_not_defined(self) -> None:
        assert _holds(_by_module(SERVICE))

    def test_the_service_is_the_sketchybar_formula_started_with_brew_on_the_path(self) -> None:
        task = _by_module(SERVICE)
        environment = cast("dict[str, str]", task["environment"])

        assert _args_of(SERVICE)["name"] == "sketchybar"
        assert environment["PATH"].startswith("/opt/homebrew/bin:")

    @pytest.mark.parametrize(
        ("wm", "state"),
        [("rift", "present"), ("aerospace", "absent")],
    )
    def test_the_service_runs_under_rift_and_is_stopped_under_aerospace(
        self, wm: str, state: str
    ) -> None:
        expression = str(_args_of(SERVICE)["state"])

        rendered = _logic_env().from_string(expression).render(devbox_wm=wm)

        assert rendered == state

    @pytest.mark.parametrize("wm", ["rift", "aerospace"])
    def test_the_service_task_runs_under_either_window_manager_outside_dev_mode(
        self, wm: str
    ) -> None:
        assert _holds(_by_module(SERVICE), dev_mode=False, devbox_wm=wm)

    def test_the_reload_command_is_sketchybar_reload_by_absolute_path(self) -> None:
        assert _args_of(COMMAND)["argv"] == ["/opt/homebrew/bin/sketchybar", "--reload"]
        assert _by_module(COMMAND)["changed_when"] is True

    @pytest.mark.parametrize(
        ("dev_mode", "wm", "config_changed", "service_changed"),
        list(itertools.product([False, True], ["rift", "aerospace"], [False, True], [False, True])),
    )
    def test_the_reload_runs_only_under_rift_when_the_config_changed_and_the_service_did_not(
        self, *, dev_mode: bool, wm: str, config_changed: bool, service_changed: bool
    ) -> None:
        context = {
            "dev_mode": dev_mode,
            "devbox_wm": wm,
            str(_by_module(TEMPLATE)["register"]): {"changed": config_changed},
            str(_by_module(SERVICE)["register"]): {"changed": service_changed},
        }

        expected = not dev_mode and wm == "rift" and config_changed and not service_changed

        assert _holds(_by_module(COMMAND), **context) is expected

    def test_a_skipped_service_task_does_not_block_the_reload_outside_dev_mode(self) -> None:
        context = {
            "dev_mode": False,
            "devbox_wm": "rift",
            str(_by_module(TEMPLATE)["register"]): {"changed": True},
            str(_by_module(SERVICE)["register"]): {"changed": False, "skipped": True},
        }

        assert _holds(_by_module(COMMAND), **context)

    def test_the_reload_reads_the_results_the_two_earlier_tasks_register(self) -> None:
        conditions = " ".join(_conditions(_by_module(COMMAND)))
        config_name = str(_by_module(TEMPLATE)["register"])
        service_name = str(_by_module(SERVICE)["register"])

        assert config_name in conditions
        assert service_name in conditions

    def test_the_tasks_run_in_the_order_directory_config_service_reload(self) -> None:
        modules = [_module_of(task) for task in _task_list(TASKS_FILE)]

        assert modules == [DIRECTORY, TEMPLATE, SERVICE, COMMAND]

    def test_every_task_carries_the_sketchybar_tag(self) -> None:
        for task in _task_list(TASKS_FILE):
            assert "sketchybar" in cast("list[str]", task["tags"]), task["name"]


class TestInclude:
    def _tasks(self) -> list[Doc]:
        return _task_list(MAIN_DARWIN)

    def _include(self) -> Doc:
        matches = [
            task
            for task in self._tasks()
            if task.get("ansible.builtin.include_tasks") == INCLUDE_PATH
        ]
        assert len(matches) == 1
        return matches[0]

    def test_the_included_file_exists(self) -> None:
        assert (ROLE / "tasks" / INCLUDE_PATH).is_file()

    def test_the_include_follows_the_window_manager_include(self) -> None:
        paths = [task.get("ansible.builtin.include_tasks") for task in self._tasks()]

        assert paths.index(INCLUDE_PATH) > paths.index(WM_INCLUDE_PATH)

    def test_the_include_runs_in_dev_mode_because_the_tasks_gate_themselves(self) -> None:
        include = self._include()

        assert _holds(include, dev_mode=True)
        assert _holds(include, dev_mode=False)

    def test_the_include_is_selectable_by_the_sketchybar_tag(self) -> None:
        assert "sketchybar" in cast("list[str]", self._include()["tags"])


class TestPackages:
    def test_sketchybar_and_the_lua_that_runs_its_config_are_installed(self) -> None:
        secondary = cast("list[str]", _role_defaults()["devbox_brew_secondary"])

        assert "sketchybar" in secondary
        assert "lua" in secondary


class TestMenuBarDefaults:
    def _entries(self, key: str) -> list[Doc]:
        defaults = cast("list[Doc]", _role_defaults()["devbox_macos_defaults"])
        return [entry for entry in defaults if entry["key"] == key]

    @staticmethod
    def _rendered_value(entry: Doc, wm: str) -> object:
        env = NativeEnvironment(
            undefined=StrictUndefined, autoescape=select_autoescape(default_for_string=False)
        )
        raw = entry["value"]
        if not isinstance(raw, str):
            return raw
        return env.from_string(raw).render(devbox_wm=wm)

    @pytest.mark.parametrize(
        ("key", "wm", "value"),
        [
            ("_HIHideMenuBar", "rift", True),
            ("_HIHideMenuBar", "aerospace", False),
            ("AppleMenuBarVisibleInFullscreen", "rift", False),
            ("AppleMenuBarVisibleInFullscreen", "aerospace", False),
        ],
    )
    def test_the_key_is_a_global_boolean_with_the_value_the_window_manager_calls_for(
        self, key: str, wm: str, *, value: bool
    ) -> None:
        (entry,) = self._entries(key)

        assert entry["domain"] == "NSGlobalDomain"
        assert entry["type"] == "bool"
        assert self._rendered_value(entry, wm) is value

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_every_profile_hides_the_menu_bar_because_it_runs_rift(self, profile: str) -> None:
        wm = str(_profile_vars(profile)["devbox_wm"])
        hide, fullscreen = (
            self._rendered_value(self._entries(key)[0], wm)
            for key in ("_HIHideMenuBar", "AppleMenuBarVisibleInFullscreen")
        )

        assert (hide, fullscreen) == (True, False)

    @pytest.mark.parametrize(
        ("wm", "pair"),
        [
            pytest.param("rift", (True, False), id="rift-always-hide"),
            pytest.param("aerospace", (False, False), id="aerospace-macos-default"),
        ],
    )
    def test_the_pair_of_keys_is_always_for_rift_and_in_full_screen_only_for_aerospace(
        self, wm: str, pair: tuple[bool, bool]
    ) -> None:
        rendered = (
            self._rendered_value(self._entries("_HIHideMenuBar")[0], wm),
            self._rendered_value(self._entries("AppleMenuBarVisibleInFullscreen")[0], wm),
        )

        assert rendered == pair
        assert all(isinstance(value, bool) for value in rendered)

    def test_the_fullscreen_key_is_a_plain_boolean_not_a_template(self) -> None:
        (entry,) = self._entries("AppleMenuBarVisibleInFullscreen")

        assert entry["value"] is False

    @pytest.mark.parametrize("wm", ["rift", "aerospace"])
    @pytest.mark.parametrize("key", ["_HIHideMenuBar", "AppleMenuBarVisibleInFullscreen"])
    def test_the_verify_task_accepts_what_defaults_read_prints_for_the_rendered_value(
        self, key: str, wm: str
    ) -> None:
        entry = self._entries(key)[0]
        value = cast("bool", self._rendered_value(entry, wm))

        assert not self._verify_fails(entry, value, stdout="1\n" if value else "0\n")

    @pytest.mark.parametrize("wm", ["rift", "aerospace"])
    @pytest.mark.parametrize("key", ["_HIHideMenuBar", "AppleMenuBarVisibleInFullscreen"])
    def test_the_verify_task_rejects_the_opposite_value_and_a_failed_read(
        self, key: str, wm: str
    ) -> None:
        entry = self._entries(key)[0]
        value = cast("bool", self._rendered_value(entry, wm))

        assert self._verify_fails(entry, value, stdout="0\n" if value else "1\n")
        assert self._verify_fails(entry, value, stdout="", rc=1)

    @staticmethod
    def _verify_fails(entry: Doc, value: object, *, stdout: str, rc: int = 0) -> bool:
        tasks = _task_list(ROLE / "tasks/darwin/configure_macos_defaults.yml")
        task = next(t for t in tasks if "Verify macOS user defaults" in str(t["name"]))
        env = Environment(
            undefined=StrictUndefined, autoescape=select_autoescape(default_for_string=False)
        )
        context = {
            "item": {**entry, "value": value},
            "devbox_macos_defaults_check": {"rc": rc, "stdout": stdout},
        }
        return bool(env.compile_expression(" ".join(str(task["failed_when"]).split()))(**context))


def _hint_task() -> Doc:
    return next(task for task in _task_list(MAIN_TASKS) if task.get("name") == RELOGIN_HINT)


def _hint_shown(results: list[Doc], **others: object) -> bool:
    context = {
        "devbox_macos_defaults_result": {"results": results},
        "devbox_user_result": {},
        "devbox_sh_cmd_space_write": {},
        "devbox_sh_cmd_opt_space_write": {},
        **others,
    }
    env = Environment(undefined=Undefined, autoescape=select_autoescape(default_for_string=False))
    return all(bool(env.compile_expression(c)(**context)) for c in _conditions(_hint_task()))


def _result(key: str, *, changed: bool | None) -> Doc:
    result: Doc = {"item": {"key": key}}
    if changed is not None:
        result["changed"] = changed
    return result


class TestReloginHint:
    def test_the_message_names_the_menu_bar_among_the_reasons_to_log_in_again(self) -> None:
        message = cast("Doc", _hint_task()["ansible.builtin.debug"])["msg"]

        assert "menu-bar" in " ".join(str(message).split())

    @pytest.mark.parametrize(
        "key",
        ["_HIHideMenuBar", "AppleMenuBarVisibleInFullscreen", "KeyRepeat", "InitialKeyRepeat"],
    )
    def test_a_changed_login_cached_key_shows_the_hint(self, key: str) -> None:
        assert _hint_shown([_result("com.apple.other", changed=True), _result(key, changed=True)])

    @pytest.mark.parametrize("key", ["_HIHideMenuBar", "AppleMenuBarVisibleInFullscreen"])
    def test_an_unchanged_key_does_not(self, key: str) -> None:
        assert not _hint_shown([_result(key, changed=False)])

    def test_a_changed_key_that_needs_no_login_does_not(self) -> None:
        assert not _hint_shown([_result("autohide", changed=True)])

    def test_a_skipped_result_does_not(self) -> None:
        assert not _hint_shown([_result("_HIHideMenuBar", changed=None)])

    def test_no_results_do_not(self) -> None:
        assert not _hint_shown([])

    @pytest.mark.parametrize(
        "trigger",
        ["devbox_user_result", "devbox_sh_cmd_space_write", "devbox_sh_cmd_opt_space_write"],
    )
    def test_the_other_triggers_still_show_it(self, trigger: str) -> None:
        assert _hint_shown([], **{trigger: {"changed": True}})
