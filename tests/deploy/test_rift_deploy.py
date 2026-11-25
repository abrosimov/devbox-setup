"""Static contract of the Rift window manager deployment.

Four artefacts have to agree: the pinned release in devbox_packages.rift, the Rift
config template, the local.rift LaunchAgent, and tasks/darwin/configure_window_manager.yml
together with the AeroSpace tasks that devbox_wm now gates. Nothing here starts a
process: templates are rendered under StrictUndefined with Ansible's trim_blocks, task
files are loaded as YAML, and their `when` conditions are evaluated against modelled
machine states, so a gate that is spelled differently but behaves the same still passes.
"""

from __future__ import annotations

import base64
import json
import plistlib
import posixpath
import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

import pytest
import yaml
from jinja2 import Environment, StrictUndefined, select_autoescape

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = REPO_ROOT / "roles/devbox"
DEFAULTS_DIR = ROLE / "defaults/main"
PROFILES_DIR = REPO_ROOT / "profiles"
WM_TASKS = ROLE / "tasks/darwin/configure_window_manager.yml"
CONFIG_TEMPLATE = ROLE / "templates/darwin/.config/rift/config.toml.j2"
PLIST_TEMPLATE = ROLE / "templates/darwin/Library/LaunchAgents/local.rift.plist.j2"
HANDLERS = ROLE / "handlers/main.yml"
INSTALL_CONFIGS = ROLE / "tasks/install_configs.yml"
APPLY_CONFIGS = ROLE / "tasks/apply_configs.yml"
MAIN_DARWIN = ROLE / "tasks/main_darwin.yml"
AEROSPACE_TOML = ROLE / "files/.config/aerospace/aerospace.toml"

PROFILE_NAMES: Final = ("personal", "work")
HOME: Final = "/Users/tester"
USER_UID: Final = 501
SERVICE_LABEL: Final = "local.rift"
INSTALL_BLOCK: Final = "download, verify and install the pinned Rift"
ROLLBACK_BLOCK: Final = "roll back a config Rift rejected"
STOP_AEROSPACE_BLOCK: Final = "stop AeroSpace and remove its login item"
LITERAL_MODIFIERS: Final = frozenset({"meta", "alt", "cmd", "command", "option", "opt"})

Doc = dict


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


_DEFAULTS: Final = _role_defaults()
_PIN: Final = _DEFAULTS["devbox_packages"]["rift"]
_WM_TASKS: Final = _task_list(WM_TASKS)


def _to_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "on"}
    return bool(value)


def _render_env() -> Environment:
    """Ansible's template module: trim_blocks on, trailing newline kept."""
    env = Environment(
        undefined=StrictUndefined,
        trim_blocks=True,
        keep_trailing_newline=True,
        autoescape=select_autoescape(default_for_string=False),
    )
    filters = cast("dict[str, Callable[..., object]]", env.filters)
    filters["dirname"] = posixpath.dirname
    return env


def _match_test(value: object, pattern: str) -> bool:
    return re.match(pattern, str(value)) is not None


def _skipped_test(result: Doc) -> bool:
    return bool(result.get("skipped"))


def _b64decode_filter(value: str) -> str:
    return base64.b64decode(value).decode("utf-8")


def _logic_env() -> Environment:
    env = _render_env()
    tests = cast("dict[str, Callable[..., object]]", env.tests)
    filters = cast("dict[str, Callable[..., object]]", env.filters)
    tests["match"] = _match_test
    tests["skipped"] = _skipped_test
    filters["bool"] = _to_bool
    filters["b64decode"] = _b64decode_filter
    return env


def _render_config(profile: str = "personal", **overrides: object) -> str:
    template = _render_env().from_string(CONFIG_TEMPLATE.read_text(encoding="utf-8"))
    return template.render(**{**_profile_vars(profile), **overrides})


def _config(profile: str = "personal", **overrides: object) -> Doc:
    return tomllib.loads(_render_config(profile, **overrides))


def _binding_tables(config: Doc) -> dict[str, Doc]:
    modes = {f"binding_modes.{mode}": table for mode, table in config["binding_modes"].items()}
    return {"keys": config["keys"], **modes}


def _modifiers(binding: str) -> list[str]:
    return [part.strip() for part in binding.split(" + ")][:-1]


def _canonical(binding: str) -> tuple[tuple[str, ...], str]:
    parts = [part.strip().lower() for part in binding.split(" + ")]
    return tuple(sorted(parts[:-1])), parts[-1]


def _action_targets(action: object) -> Iterator[str]:
    if isinstance(action, dict):
        if "binding_mode" in action:
            yield action["binding_mode"]
        for value in action.values():
            yield from _action_targets(value)
    elif isinstance(action, list):
        for item in action:
            yield from _action_targets(item)


class TestConfigTemplate:
    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_renders_and_parses_for_every_profile(self, profile: str) -> None:
        config = _config(profile)

        assert {
            "settings",
            "virtual_workspaces",
            "modifier_combinations",
            "keys",
            "binding_modes",
        } <= set(config)

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_hot_reload_is_off_so_the_playbook_owns_reloading(self, profile: str) -> None:
        assert _config(profile)["settings"]["hot_reload"] is False

    def test_global_workspace_mode_with_nine_workspaces(self) -> None:
        workspaces = _config()["virtual_workspaces"]

        assert workspaces["mode"] == "global"
        assert workspaces["enabled"] is True
        assert workspaces["default_workspace_count"] == 9

    def test_workspace_names_are_one_to_nine(self) -> None:
        names = _config()["virtual_workspaces"]["workspace_names"]

        assert names == [str(n) for n in range(1, 10)]

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_every_workspace_has_exactly_one_master_stack_rule(self, profile: str) -> None:
        rules = _config(profile)["virtual_workspaces"]["workspace_rules"]

        assert [rule["workspace"] for rule in rules] == list(range(9))
        assert {rule["layout"] for rule in rules} == {"master_stack"}
        assert all(set(rule) == {"workspace", "layout", "display"} for rule in rules)

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_rule_display_lists_follow_the_main_and_side_variables(self, profile: str) -> None:
        variables = _profile_vars(profile)
        rules = _config(profile)["virtual_workspaces"]["workspace_rules"]

        assert [rule["display"] for rule in rules[:5]] == [
            variables["devbox_rift_display_main"]
        ] * 5
        assert [rule["display"] for rule in rules[5:]] == [
            variables["devbox_rift_display_side"]
        ] * 4

    def test_display_variables_are_not_swapped_or_shifted_at_the_boundary(self) -> None:
        rules = _config(
            devbox_rift_display_main=["MAIN-A", "MAIN-B"],
            devbox_rift_display_side=["SIDE-A"],
        )["virtual_workspaces"]["workspace_rules"]

        assert [rule["display"] for rule in rules] == [["MAIN-A", "MAIN-B"]] * 5 + [["SIDE-A"]] * 4

    def test_display_names_with_spaces_apostrophes_and_accents_survive(self) -> None:
        names = ["Kirill's Studio Display", "LG UltraFine 5K", "Écran"]
        rules = _config(devbox_rift_display_main=names)["virtual_workspaces"]["workspace_rules"]

        assert rules[0]["display"] == names

    def test_auto_focus_blacklist_is_the_two_desktop_assistants(self) -> None:
        blacklist = _config()["settings"]["auto_focus_blacklist"]

        assert blacklist == ["com.anthropic.claudefordesktop", "com.openai.codex"]
        assert blacklist == _DEFAULTS["devbox_rift_auto_focus_blacklist"]

    @pytest.mark.parametrize("blacklist", [[], ["com.example.only"], ["a.b", "c.d", "e.f"]])
    def test_auto_focus_blacklist_follows_the_variable(self, blacklist: list[str]) -> None:
        rendered = _config(devbox_rift_auto_focus_blacklist=blacklist)

        assert rendered["settings"]["auto_focus_blacklist"] == blacklist

    def test_default_super_is_meta_alt(self) -> None:
        assert _DEFAULTS["devbox_rift_super"] == "Meta + Alt"
        assert _config()["modifier_combinations"] == {"super": "Meta + Alt"}

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_every_keys_binding_starts_with_super(self, profile: str) -> None:
        offenders = [
            binding for binding in _config(profile)["keys"] if _modifiers(binding)[:1] != ["super"]
        ]

        assert offenders == []

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_every_binding_mode_is_entered_from_keys_and_exits_to_default(
        self, profile: str
    ) -> None:
        config = _config(profile)
        entered = {t for action in config["keys"].values() for t in _action_targets(action)}

        assert config["binding_modes"]
        for mode, bindings in config["binding_modes"].items():
            exits = [
                b for b, action in bindings.items() if "default" in set(_action_targets(action))
            ]

            assert mode in entered, mode
            assert exits, mode

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_no_binding_uses_a_literal_meta_or_alt(self, profile: str) -> None:
        tables = _binding_tables(_config(profile))

        offenders = [
            f"[{table}] {binding}"
            for table, bindings in tables.items()
            for binding in bindings
            if LITERAL_MODIFIERS & {m.lower() for m in _modifiers(binding)}
        ]

        assert offenders == []

    def test_super_is_defined_once_and_nowhere_else_in_the_file(self) -> None:
        text = _render_config()

        assert text.count(_DEFAULTS["devbox_rift_super"]) == 1
        assert len(re.findall(r"^super\s*=", text, flags=re.MULTILINE)) == 1

    def test_a_changed_super_changes_only_the_modifier_definition(self) -> None:
        baseline = _config()
        changed = _config(devbox_rift_super="Ctrl + Alt + Shift")

        assert changed["modifier_combinations"] == {"super": "Ctrl + Alt + Shift"}
        assert {k: v for k, v in changed.items() if k != "modifier_combinations"} == {
            k: v for k, v in baseline.items() if k != "modifier_combinations"
        }
        assert (
            _render_config(devbox_rift_super="Ctrl + Alt + Shift").count("Ctrl + Alt + Shift") == 1
        )

    def test_digits_one_to_nine_switch_to_workspaces_zero_to_eight(self) -> None:
        keys = _config()["keys"]

        for n in range(1, 10):
            assert keys[f"super + {n}"] == {"switch_to_workspace": n - 1}

    def test_shift_digits_move_the_window_to_workspaces_zero_to_eight(self) -> None:
        keys = _config()["keys"]

        for n in range(1, 10):
            assert keys[f"super + Shift + {n}"] == {"move_window_to_workspace": n - 1}

    def test_no_other_key_switches_or_moves_to_a_workspace(self) -> None:
        keys = _config()["keys"]
        actions = [action for action in keys.values() if isinstance(action, dict)]

        switches = [a["switch_to_workspace"] for a in actions if "switch_to_workspace" in a]
        moves = [a["move_window_to_workspace"] for a in actions if "move_window_to_workspace" in a]

        assert sorted(switches) == list(range(9))
        assert sorted(moves) == list(range(9))
        assert not isinstance(keys["super + 0"], dict)

    def test_every_workspace_a_binding_targets_has_a_rule(self) -> None:
        config = _config()
        ruled = {rule["workspace"] for rule in config["virtual_workspaces"]["workspace_rules"]}
        targeted = {
            action[verb]
            for action in config["keys"].values()
            if isinstance(action, dict)
            for verb in ("switch_to_workspace", "move_window_to_workspace")
            if verb in action
        }

        assert targeted <= ruled

    def test_binding_modes_come_after_every_keys_entry(self) -> None:
        text = _render_config()
        header = text.index("[binding_modes.")
        key_lines = [m.start() for m in re.finditer(r'^"super \+ ', text, flags=re.MULTILINE)]

        assert key_lines
        assert max(key_lines) < header

    def test_binding_mode_entries_do_not_leak_into_keys(self) -> None:
        config = _config()
        mode_bindings = {b for table in config["binding_modes"].values() for b in table}

        assert mode_bindings.isdisjoint(config["keys"])
        assert "super + Tab" in config["keys"]
        assert "super + Shift + 9" in config["keys"]
        assert "super + Shift + Semicolon" in config["keys"]

    def test_every_binding_mode_a_key_enters_exists(self) -> None:
        config = _config()
        known = {*config["binding_modes"], "default"}
        targets = {
            target
            for table in _binding_tables(config).values()
            for action in table.values()
            for target in _action_targets(action)
        }

        assert "service" in targets
        assert targets <= known

    @pytest.mark.parametrize("profile", PROFILE_NAMES)
    def test_no_two_bindings_in_a_table_are_the_same_chord(self, profile: str) -> None:
        for table, bindings in _binding_tables(_config(profile)).items():
            canonical = [_canonical(b) for b in bindings]

            assert len(canonical) == len(set(canonical)), table

    def test_modifier_combinations_only_defines_super(self) -> None:
        assert set(_config()["modifier_combinations"]) == {"super"}


@dataclass(frozen=True)
class Machine:
    """What the playbook finds on the host, and the devbox_wm it was asked for."""

    wm: str = "rift"
    current: bool = True
    rift_running: bool = False
    agent_loaded: bool = False
    config_changed: bool = False
    plist_changed: bool = False
    aerospace_running: bool = False
    aerospace_login_item_on: bool = False
    aerospace_exits: bool = True
    app_installed: bool = True
    bootstrap_starts_rift: bool = False
    reload_rc: int = 0
    check_mode: bool = False


@dataclass(frozen=True)
class Step:
    task: Doc
    ran: bool
    ancestors: tuple[str, ...]
    section: str


def _conditions(task: Doc) -> tuple[str, ...]:
    when = task.get("when")
    if when is None:
        return ()
    if isinstance(when, list):
        return tuple(str(item) for item in when)
    return (str(when),)


def _leaves(
    tasks: list[Doc],
    inherited: tuple[str, ...] = (),
    ancestors: tuple[str, ...] = (),
    section: str = "block",
) -> Iterator[tuple[Doc, tuple[str, ...], tuple[str, ...], str]]:
    for task in tasks:
        own = inherited + _conditions(task)
        children = [name for name in ("block", "rescue", "always") if name in task]
        if not children:
            yield task, own, ancestors, section
            continue
        for name in children:
            yield from _leaves(task[name], own, (*ancestors, task["name"]), name)


def _holds(conditions: tuple[str, ...], context: Doc) -> bool:
    env = _logic_env()
    return all(
        bool(env.compile_expression(c, undefined_to_none=False)(**context)) for c in conditions
    )


def _probe(*, found: bool) -> Doc:
    return {"rc": 0 if found else 1, "changed": False}


def _outcome(machine: Machine, register: str, context: Doc) -> Doc:
    replaced = bool(context.get("devbox_rift_replaced"))
    stray_stopped = not context.get("devbox_rift_stray_stop", {"skipped": True}).get("skipped")
    survives = (
        not replaced and not stray_stopped and not (machine.plist_changed and machine.agent_loaded)
    )
    autostarted = machine.bootstrap_starts_rift and not context.get(
        "devbox_rift_bootstrapped", {"skipped": True}
    ).get("skipped")
    backup = (
        {"backup_file": f"{HOME}/.config/rift/config.toml.1~"} if machine.config_changed else {}
    )
    outcomes: dict[str, Doc] = {
        "devbox_rift_brew": {"rc": 1, "stdout": ""},
        "devbox_rift_running": _probe(found=machine.rift_running),
        "devbox_rift_running_now": _probe(found=(machine.rift_running and survives) or autostarted),
        "devbox_rift_agent": _probe(found=machine.agent_loaded),
        "devbox_rift_config": {"changed": machine.config_changed, **backup},
        "devbox_rift_plist": {"changed": machine.plist_changed},
        "devbox_rift_reload": {
            "rc": machine.reload_rc,
            "changed": True,
            "stderr": "invalid config",
            "stdout": "",
        },
        "devbox_rift_app_before": {"stat": {"exists": machine.app_installed}},
        "devbox_aerospace_toml": {"stat": {"exists": True}},
        "devbox_aerospace_login_off": {"changed": machine.aerospace_login_item_on},
        "devbox_aerospace_running_wm": _probe(found=machine.aerospace_running),
        "devbox_aerospace_exit_wait": _probe(found=not machine.aerospace_exits),
    }
    return outcomes.get(register, {"rc": 0, "changed": False})


def _base_context(machine: Machine) -> Doc:
    return {
        "devbox_wm": machine.wm,
        "ansible_check_mode": machine.check_mode,
        "dev_mode": False,
        "item": "any-item",
        "ansible_facts": {
            "os_family": "Darwin",
            "user_uid": USER_UID,
            "env": {"HOME": HOME, "PATH": "/usr/bin"},
        },
        "devbox_paths": {"dotfiles_root_dir": HOME},
        "devbox_packages": {"rift": _PIN},
    }


def _simulate(tasks: list[Doc], machine: Machine) -> list[Step]:
    context = _base_context(machine)
    steps: list[Step] = []
    for task, conditions, ancestors, section in _leaves(tasks):
        ran = section != "rescue" and _holds(conditions, context)
        steps.append(Step(task, ran, ancestors, section))
        if "register" in task:
            skipped: Doc = {"changed": False, "skipped": True}
            context[task["register"]] = (
                _outcome(machine, task["register"], context) if ran else skipped
            )
        facts = task.get("ansible.builtin.set_fact")
        if ran and facts:
            for key, value in facts.items():
                if key == "devbox_rift_is_current":
                    context[key] = "True" if machine.current else "False"
                elif not isinstance(value, str) or "{{" not in value:
                    context[key] = value
    return steps


def _argv(task: Doc) -> list[str]:
    command = task.get("ansible.builtin.command")
    if isinstance(command, dict):
        return [str(arg) for arg in command.get("argv", [])]
    if isinstance(command, str):
        return command.split()
    return []


def _launchctl(verb: str) -> Callable[[Doc], bool]:
    return lambda task: (
        len(_argv(task)) > 1 and _argv(task)[0].endswith("launchctl") and _argv(task)[1] == verb
    )


def _rift_cli(*words: str) -> Callable[[Doc], bool]:
    return lambda task: (
        bool(_argv(task))
        and _argv(task)[0] == "{{ devbox_rift_cli }}"
        and _argv(task)[1:] == list(words)
    )


def _mentions_aerospace(task: Doc) -> bool:
    ignored = {
        "name",
        "when",
        "tags",
        "register",
        "notify",
        "ansible.builtin.assert",
        "ansible.builtin.fail",
        "community.general.osx_defaults",
    }
    body = {key: value for key, value in task.items() if key not in ignored}
    return "aerospace" in json.dumps(body).lower()


def _in_block(step: Step, name: str) -> bool:
    return any(name in ancestor for ancestor in step.ancestors)


def _ran(
    steps: list[Step], predicate: Callable[[Doc], bool], *, outside_install: bool = False
) -> list[bool]:
    return [
        step.ran
        for step in steps
        if predicate(step.task) and not (outside_install and _in_block(step, INSTALL_BLOCK))
    ]


def _index(steps: list[Step], predicate: Callable[[Doc], bool]) -> int:
    return next(i for i, step in enumerate(steps) if predicate(step.task))


_BOOTSTRAP: Final = _launchctl("bootstrap")
_KICKSTART: Final = _launchctl("kickstart")
_BOOTOUT: Final = _launchctl("bootout")
_SAVE_AND_EXIT: Final = _rift_cli("execute", "save-and-exit")


def _named(fragment: str) -> Callable[[Doc], bool]:
    return lambda task: fragment in task["name"]


_STRAY_STOP: Final = _named("outside the LaunchAgent")
_STRAY_WAIT: Final = _named("stray Rift to exit")
_RELOAD: Final = _rift_cli("execute", "config", "reload")
_QUERY: Final = _rift_cli("query", "workspaces")


def _starts_rift(task: Doc) -> bool:
    return any(probe(task) for probe in (_BOOTSTRAP, _KICKSTART, _RELOAD, _QUERY))


def _aerospace_reload(task: Doc) -> bool:
    return bool(_argv(task)) and _argv(task)[0].endswith("/aerospace")


_BUSY_MACHINE: Final = Machine(
    current=False,
    rift_running=True,
    agent_loaded=True,
    config_changed=True,
    plist_changed=True,
    aerospace_running=True,
    aerospace_login_item_on=True,
)


class TestWindowManagerGating:
    def test_the_probes_find_the_tasks_they_name(self) -> None:
        steps = _simulate(_WM_TASKS, Machine())

        assert len(_ran(steps, _BOOTSTRAP)) == 1
        assert len(_ran(steps, _KICKSTART)) == 1
        assert len(_ran(steps, _BOOTOUT)) == 2
        assert len(_ran(steps, _RELOAD)) == 2
        assert len(_ran(steps, _SAVE_AND_EXIT)) == 3
        assert len([s for s in steps if _STRAY_STOP(s.task)]) == 1
        assert len([s for s in steps if _STRAY_WAIT(s.task)]) == 1
        assert len([s for s in steps if _mentions_aerospace(s.task)]) >= 8

    def test_default_window_manager_is_rift_and_the_allowed_values_are_the_two(self) -> None:
        guard = _WM_TASKS[0]["ansible.builtin.assert"]["that"]
        env = _logic_env()

        assert _DEFAULTS["devbox_wm"] == "rift"
        assert all(env.compile_expression(expr)(devbox_wm="rift") for expr in guard)
        assert all(env.compile_expression(expr)(devbox_wm="aerospace") for expr in guard)

    @pytest.mark.parametrize("wm", ["sway", "Rift", "", "rift ", None, "yabai"])
    def test_an_unknown_window_manager_is_refused(self, wm: str | None) -> None:
        guard = _WM_TASKS[0]["ansible.builtin.assert"]["that"]
        env = _logic_env()

        assert not all(env.compile_expression(expr)(devbox_wm=wm) for expr in guard)

    @pytest.mark.parametrize(
        "machine",
        [
            _BUSY_MACHINE,
            replace(_BUSY_MACHINE, current=True),
            replace(_BUSY_MACHINE, rift_running=False, agent_loaded=False),
            replace(_BUSY_MACHINE, aerospace_running=False),
        ],
        ids=["busy", "busy-and-current", "rift-idle", "aerospace-idle"],
    )
    def test_with_aerospace_chosen_nothing_starts_rift_or_touches_aerospace(
        self, machine: Machine
    ) -> None:
        steps = _simulate(_WM_TASKS, replace(machine, wm="aerospace"))

        started = [s.task["name"] for s in steps if s.ran and _starts_rift(s.task)]
        aerospace = [s.task["name"] for s in steps if s.ran and _mentions_aerospace(s.task)]

        assert started == []
        assert aerospace == []

    def test_with_aerospace_chosen_a_running_rift_is_saved_and_its_agent_booted_out(self) -> None:
        steps = _simulate(_WM_TASKS, replace(_BUSY_MACHINE, wm="aerospace", current=True))

        assert _ran(steps, _SAVE_AND_EXIT, outside_install=True) == [False, True]
        assert _ran(steps, _BOOTOUT) == [False, True]

    def test_with_aerospace_chosen_an_idle_rift_is_left_alone(self) -> None:
        steps = _simulate(
            _WM_TASKS, Machine(wm="aerospace", rift_running=False, agent_loaded=False)
        )

        assert _ran(steps, _SAVE_AND_EXIT, outside_install=True) == [False, False]
        assert _ran(steps, _BOOTOUT) == [False, False]

    def test_rift_is_installed_in_both_modes(self) -> None:
        steps = _simulate(_WM_TASKS, Machine(wm="aerospace", current=False))
        download = next(s for s in steps if "ansible.builtin.get_url" in s.task)

        assert download.ran

    def test_with_rift_chosen_a_stale_agent_is_booted_out_before_it_is_bootstrapped(self) -> None:
        steps = _simulate(_WM_TASKS, Machine(agent_loaded=True, plist_changed=True))
        bootout_on_change = [
            s
            for s in steps
            if _BOOTOUT(s.task) and "devbox_rift_plist.changed" in " ".join(_conditions(s.task))
        ]

        assert [s.ran for s in bootout_on_change] == [True]
        assert _index(steps, _BOOTOUT) < _index(steps, _BOOTSTRAP)
        assert _ran(steps, _BOOTSTRAP) == [True]

    def test_with_rift_chosen_a_fresh_machine_bootstraps_and_starts_rift(self) -> None:
        steps = _simulate(
            _WM_TASKS, Machine(current=False, plist_changed=True, config_changed=True)
        )

        assert _ran(steps, _BOOTSTRAP) == [True]
        assert _ran(steps, _KICKSTART) == [True]
        assert _ran(steps, _BOOTOUT) == [False, False]
        assert _ran(steps, _SAVE_AND_EXIT, outside_install=True) == [False, False]

    def test_with_rift_chosen_a_healthy_running_rift_is_not_disturbed(self) -> None:
        steps = _simulate(_WM_TASKS, Machine(rift_running=True, agent_loaded=True))

        assert not any(s.ran for s in steps if _starts_rift(s.task))
        assert _ran(steps, _BOOTOUT) == [False, False]
        assert _ran(steps, _SAVE_AND_EXIT) == [False, False, False]
        assert not any(s.ran for s in steps if _STRAY_STOP(s.task) or _STRAY_WAIT(s.task))

    def test_with_rift_chosen_a_hand_started_rift_is_stopped_before_the_agent_is_bootstrapped(
        self,
    ) -> None:
        steps = _simulate(_WM_TASKS, Machine(rift_running=True, agent_loaded=False))

        assert [s.ran for s in steps if _STRAY_STOP(s.task)] == [True]
        assert [s.ran for s in steps if _STRAY_WAIT(s.task)] == [True]
        assert _ran(steps, _BOOTSTRAP) == [True]
        stop = _index(steps, _STRAY_STOP)
        assert stop < _index(steps, _STRAY_WAIT) < _index(steps, _BOOTSTRAP)

    def test_the_stray_stop_saves_the_layout_with_the_cli(self) -> None:
        stop = next(s.task for s in _simulate(_WM_TASKS, Machine()) if _STRAY_STOP(s.task))

        assert _SAVE_AND_EXIT(stop)
        assert stop["register"] == "devbox_rift_stray_stop"

    @pytest.mark.parametrize(
        "machine",
        [
            Machine(rift_running=True, agent_loaded=True),
            Machine(rift_running=False, agent_loaded=False),
            Machine(wm="aerospace", rift_running=True, agent_loaded=False),
            Machine(rift_running=True, agent_loaded=False, check_mode=True),
            Machine(current=False, rift_running=True, agent_loaded=False),
        ],
        ids=["agent-loaded", "not-running", "aerospace", "check-mode", "replaced-this-run"],
    )
    def test_no_stray_stop_unless_rift_is_chosen_hand_started_and_not_just_replaced(
        self, machine: Machine
    ) -> None:
        steps = _simulate(_WM_TASKS, machine)

        assert [s.ran for s in steps if _STRAY_STOP(s.task)] == [False]
        assert [s.ran for s in steps if _STRAY_WAIT(s.task)] == [False]

    def test_a_fresh_machine_confirms_that_rift_answers(self) -> None:
        steps = _simulate(
            _WM_TASKS, Machine(current=False, plist_changed=True, config_changed=True)
        )

        assert _ran(steps, _BOOTSTRAP) == [True]
        assert _ran(steps, _QUERY) == [True]

    def test_a_rift_started_only_by_the_bootstrap_is_still_confirmed(self) -> None:
        machine = Machine(plist_changed=True, bootstrap_starts_rift=True)
        steps = _simulate(_WM_TASKS, machine)

        assert _ran(steps, _BOOTSTRAP) == [True]
        assert _ran(steps, _KICKSTART) == [False]
        assert _ran(steps, _QUERY) == [True]

    def test_a_kickstart_without_a_bootstrap_is_still_confirmed(self) -> None:
        steps = _simulate(_WM_TASKS, Machine(rift_running=False, agent_loaded=True))

        assert _ran(steps, _BOOTSTRAP) == [False]
        assert _ran(steps, _KICKSTART) == [True]
        assert _ran(steps, _QUERY) == [True]

    def test_a_healthy_running_rift_with_a_loaded_agent_is_not_queried(self) -> None:
        steps = _simulate(_WM_TASKS, Machine(rift_running=True, agent_loaded=True))

        assert _ran(steps, _QUERY) == [False]

    @pytest.mark.parametrize(
        "machine",
        [
            Machine(wm="aerospace", current=False, plist_changed=True),
            Machine(current=False, plist_changed=True, check_mode=True),
        ],
        ids=["aerospace", "check-mode"],
    )
    def test_no_liveness_check_with_aerospace_chosen_or_in_check_mode(
        self, machine: Machine
    ) -> None:
        assert _ran(_simulate(_WM_TASKS, machine), _QUERY) == [False]

    def test_with_rift_chosen_a_rift_that_exited_cleanly_is_started_again(self) -> None:
        steps = _simulate(_WM_TASKS, Machine(rift_running=False, agent_loaded=True))

        assert _ran(steps, _BOOTSTRAP) == [False]
        assert _ran(steps, _KICKSTART) == [True]

    def test_kickstart_never_kills_a_running_rift(self) -> None:
        kickstart = next(s.task for s in _simulate(_WM_TASKS, Machine()) if _KICKSTART(s.task))

        assert "-k" not in _argv(kickstart)

    def test_a_changed_config_is_reloaded_only_in_a_running_rift(self) -> None:
        running = _simulate(
            _WM_TASKS, Machine(rift_running=True, agent_loaded=True, config_changed=True)
        )
        stopped = _simulate(_WM_TASKS, Machine(rift_running=False, config_changed=True))
        unchanged = _simulate(_WM_TASKS, Machine(rift_running=True, agent_loaded=True))

        assert _ran(running, _RELOAD)[0] is True
        assert _ran(stopped, _RELOAD)[0] is False
        assert _ran(unchanged, _RELOAD)[0] is False

    def test_a_config_changed_while_rift_was_replaced_is_not_reloaded_into_the_new_instance(
        self,
    ) -> None:
        steps = _simulate(
            _WM_TASKS,
            Machine(current=False, rift_running=True, agent_loaded=True, config_changed=True),
        )

        assert _ran(steps, _RELOAD)[0] is False
        assert _ran(steps, _KICKSTART) == [True]

    def test_the_reload_is_skipped_in_check_mode(self) -> None:
        machine = Machine(
            rift_running=True, agent_loaded=True, config_changed=True, check_mode=True
        )

        assert _ran(_simulate(_WM_TASKS, machine), _RELOAD)[0] is False

    def test_a_rejected_config_is_rolled_back_reloaded_and_fails_the_run(self) -> None:
        machine = Machine(rift_running=True, agent_loaded=True, config_changed=True, reload_rc=1)
        steps = _simulate(_WM_TASKS, machine)
        rollback = [s for s in steps if _in_block(s, ROLLBACK_BLOCK)]

        assert [s.ran for s in rollback] == [True, True, True]
        copy = rollback[0].task["ansible.builtin.copy"]
        assert copy["src"] == "{{ devbox_rift_config.backup_file }}"
        assert copy["dest"] == "{{ devbox_rift_conf_dir }}/config.toml"
        assert _RELOAD(rollback[1].task)
        assert "ansible.builtin.fail" in rollback[2].task

    def test_an_accepted_config_does_not_trigger_the_rollback(self) -> None:
        machine = Machine(rift_running=True, agent_loaded=True, config_changed=True, reload_rc=0)
        steps = _simulate(_WM_TASKS, machine)

        assert not any(s.ran for s in steps if _in_block(s, ROLLBACK_BLOCK))

    def test_no_rollback_when_no_reload_ran(self) -> None:
        steps = _simulate(_WM_TASKS, Machine(rift_running=False, config_changed=True, reload_rc=1))

        assert not any(s.ran for s in steps if _in_block(s, ROLLBACK_BLOCK))

    def test_config_template_keeps_a_backup_for_the_rollback(self) -> None:
        task = next(
            t
            for t, *_ in _leaves(_WM_TASKS)
            if "ansible.builtin.template" in t and "config.toml" in str(t)
        )

        assert task["ansible.builtin.template"]["backup"] is True
        assert task["register"] == "devbox_rift_config"

    @pytest.mark.parametrize("wm", ["rift", "aerospace"])
    def test_config_and_agent_templates_deploy_in_both_modes(self, wm: str) -> None:
        steps = _simulate(_WM_TASKS, Machine(wm=wm))

        deployed = [
            s.task["register"] for s in steps if s.ran and "ansible.builtin.template" in s.task
        ]

        assert deployed == ["devbox_rift_config", "devbox_rift_plist"]

    def test_check_mode_installs_starts_and_stops_nothing(self) -> None:
        steps = _simulate(_WM_TASKS, replace(_BUSY_MACHINE, check_mode=True))

        assert not any(s.ran for s in steps if _in_block(s, INSTALL_BLOCK) and s.section == "block")
        assert not any(s.ran for s in steps if _in_block(s, STOP_AEROSPACE_BLOCK))
        assert not any(s.ran for s in steps if _KICKSTART(s.task) or _RELOAD(s.task))

    def test_the_aerospace_stop_block_runs_when_aerospace_runs_or_would_log_in(self) -> None:
        def block(machine: Machine) -> list[bool]:
            return [
                s.ran for s in _simulate(_WM_TASKS, machine) if _in_block(s, STOP_AEROSPACE_BLOCK)
            ]

        assert block(Machine(aerospace_running=True)) == [False, True, True, True, False]
        assert block(Machine(aerospace_running=True, aerospace_exits=False)) == [
            False,
            True,
            True,
            True,
            True,
        ]
        assert block(Machine(aerospace_running=False, aerospace_login_item_on=True)) == [
            True,
            True,
            True,
            True,
            False,
        ]
        assert block(Machine(aerospace_running=False, aerospace_login_item_on=False)) == [False] * 5

    def test_aerospace_is_stopped_before_rift_starts(self) -> None:
        steps = _simulate(_WM_TASKS, Machine(aerospace_running=True))
        pkill = _index(steps, lambda t: "pkill" in _argv(t))
        osascript = _index(steps, lambda t: any("osascript" in a for a in _argv(t)))
        reload_config = _index(steps, _aerospace_reload)

        assert reload_config < osascript < pkill
        assert pkill < _index(steps, _BOOTSTRAP)
        assert pkill < _index(steps, _KICKSTART)

    def test_the_login_item_is_switched_off_before_aerospace_is_asked_to_reload(self) -> None:
        steps = _simulate(_WM_TASKS, Machine())

        assert _index(steps, lambda t: "ansible.builtin.replace" in t) < _index(
            steps, _aerospace_reload
        )

    def test_the_login_item_edit_only_flips_start_at_login_in_the_real_aerospace_config(
        self,
    ) -> None:
        edit = next(t for t, *_ in _leaves(_WM_TASKS) if "ansible.builtin.replace" in t)[
            "ansible.builtin.replace"
        ]
        source = AEROSPACE_TOML.read_text(encoding="utf-8")

        result = re.sub(edit["regexp"], edit["replace"], source, flags=re.MULTILINE)
        changed = [
            after
            for before, after in zip(source.splitlines(), result.splitlines(), strict=True)
            if before != after
        ]

        assert len(re.findall(edit["regexp"], source, flags=re.MULTILINE)) == 1
        assert changed == ["start-at-login = false"]
        assert edit["path"].endswith("/.config/aerospace/aerospace.toml")

    @pytest.mark.parametrize(
        "line", ["start-at-login = false", "# start-at-login = true", "other-key = true"]
    )
    def test_the_login_item_edit_leaves_other_lines_alone(self, line: str) -> None:
        edit = next(t for t, *_ in _leaves(_WM_TASKS) if "ansible.builtin.replace" in t)[
            "ansible.builtin.replace"
        ]

        assert re.sub(edit["regexp"], edit["replace"], line, flags=re.MULTILINE) == line

    def test_the_include_runs_after_apply_configs_and_never_in_dev_mode(self) -> None:
        tasks = _task_list(MAIN_DARWIN)
        names = [t.get("name") for t in tasks]
        include = next(
            t
            for t in tasks
            if t.get("ansible.builtin.include_tasks") == "darwin/configure_window_manager.yml"
        )
        env = _logic_env()
        conditions = _conditions(include)

        assert names.index(include["name"]) == names.index("Apply configs") + 1
        assert not all(env.compile_expression(c)(dev_mode=True) for c in conditions)
        assert all(env.compile_expression(c)(dev_mode=False) for c in conditions)
        assert {"wm", "rift"} <= set(include["tags"])


def _aerospace_tasks(path: Path) -> list[tuple[Doc, tuple[str, ...]]]:
    return [
        (task, conditions)
        for task, conditions, *_ in _leaves(_task_list(path))
        if _mentions_aerospace(task)
    ]


class TestAerospaceTasksFollowTheWindowManager:
    @pytest.mark.parametrize(("path", "expected"), [(INSTALL_CONFIGS, 3), (APPLY_CONFIGS, 2)])
    def test_the_aerospace_tasks_exist(self, path: Path, expected: int) -> None:
        assert len(_aerospace_tasks(path)) == expected

    @pytest.mark.parametrize("path", [INSTALL_CONFIGS, APPLY_CONFIGS])
    def test_none_runs_while_rift_is_the_window_manager(self, path: Path) -> None:
        context = {**_base_context(Machine(wm="rift")), "devbox_aerospace_running": {"rc": 1}}

        ran = [
            task["name"]
            for task, conditions in _aerospace_tasks(path)
            if _holds(conditions, context)
        ]

        assert ran == []

    @pytest.mark.parametrize("path", [INSTALL_CONFIGS, APPLY_CONFIGS])
    def test_all_run_while_aerospace_is_the_window_manager(self, path: Path) -> None:
        context = {**_base_context(Machine(wm="aerospace")), "devbox_aerospace_running": {"rc": 1}}

        skipped = [
            task["name"]
            for task, conditions in _aerospace_tasks(path)
            if not _holds(conditions, context)
        ]

        assert skipped == []

    def test_the_layouts_venv_bootstrap_still_skips_check_mode(self) -> None:
        context = {
            **_base_context(Machine(wm="aerospace", check_mode=True)),
            "devbox_aerospace_running": {"rc": 1},
        }
        bootstrap = next(c for t, c in _aerospace_tasks(INSTALL_CONFIGS) if "uv sync" in str(t))

        assert not _holds(bootstrap, context)

    def test_launching_aerospace_still_skips_dev_mode_and_a_running_aerospace(self) -> None:
        launch = next(
            c
            for t, c in _aerospace_tasks(APPLY_CONFIGS)
            if t["ansible.builtin.command"].startswith("open")
        )
        context = {**_base_context(Machine(wm="aerospace")), "devbox_aerospace_running": {"rc": 1}}

        assert _holds(launch, context)
        assert not _holds(launch, {**context, "dev_mode": True})
        assert not _holds(launch, {**context, "devbox_aerospace_running": {"rc": 0}})


_FACT_TASKS: Final = [
    t for t in _WM_TASKS if "ansible.builtin.set_fact" in t and "resolve" in t["name"]
]


def _facts(home: str = HOME) -> dict[str, str]:
    env = _render_env()
    context: Doc = {
        "ansible_facts": {"env": {"HOME": home, "PATH": "/usr/bin"}, "user_uid": USER_UID},
        "devbox_packages": {"rift": _PIN},
    }
    facts: dict[str, str] = {}
    for task in _FACT_TASKS:
        for key, expression in task["ansible.builtin.set_fact"].items():
            facts[key] = env.from_string(expression).render(**context, **facts)
    return facts


def _render_plist(**overrides: object) -> Doc:
    context: Doc = {
        "ansible_facts": {"env": {"HOME": HOME}},
        "devbox_rift_app": _facts()["devbox_rift_app"],
        **overrides,
    }
    text = _render_env().from_string(PLIST_TEMPLATE.read_text(encoding="utf-8")).render(**context)
    return plistlib.loads(text.encode("utf-8"))


class TestLaunchAgent:
    def test_the_label_is_the_service_the_tasks_address(self) -> None:
        facts = _facts()

        assert _render_plist()["Label"] == SERVICE_LABEL
        assert facts["devbox_rift_service"] == f"gui/{USER_UID}/{SERVICE_LABEL}"
        assert (
            facts["devbox_rift_plist_path"] == f"{HOME}/Library/LaunchAgents/{SERVICE_LABEL}.plist"
        )

    def test_it_runs_the_installed_bundle_with_restore_and_nothing_else(self) -> None:
        assert _render_plist()["ProgramArguments"] == [
            f"{HOME}/Applications/Rift.app/Contents/MacOS/rift",
            "--restore",
        ]

    def test_the_program_path_is_the_one_the_installer_checks_for(self) -> None:
        inspect = next(t for t in _WM_TASKS if "inspect the installed Rift" in t["name"])
        rendered = [_render_env().from_string(item).render(**_facts()) for item in inspect["loop"]]

        assert _render_plist()["ProgramArguments"][0] in rendered

    def test_a_crash_is_restarted_and_a_clean_exit_is_not(self) -> None:
        plist = _render_plist()

        assert plist["RunAtLoad"] is True
        assert plist["KeepAlive"] == {"SuccessfulExit": False, "Crashed": True}

    def test_both_streams_go_to_the_log_the_playbook_names(self) -> None:
        plist = _render_plist()
        log = f"{HOME}/Library/Logs/rift.log"

        assert plist["StandardOutPath"] == log
        assert plist["StandardErrorPath"] == log

    def test_the_path_lets_exec_bindings_find_user_and_homebrew_tools(self) -> None:
        path = _render_plist()["EnvironmentVariables"]["PATH"].split(":")

        assert path[0] == f"{HOME}/.local/bin"
        assert "/opt/homebrew/bin" in path

    def test_it_loads_only_in_a_gui_session(self) -> None:
        assert _render_plist()["LimitLoadToSessionType"] == "Aqua"

    def test_a_home_with_a_space_stays_one_program_path(self) -> None:
        app = "/Users/Test User/Applications/Rift.app"
        plist = _render_plist(
            devbox_rift_app=app, ansible_facts={"env": {"HOME": "/Users/Test User"}}
        )

        assert plist["ProgramArguments"] == [f"{app}/Contents/MacOS/rift", "--restore"]
        assert plist["StandardOutPath"] == "/Users/Test User/Library/Logs/rift.log"

    def test_every_directory_the_deployment_writes_into_is_created_first(self) -> None:
        facts = _facts()
        env = _render_env()
        directories = {
            env.from_string(item).render(**facts)
            for task, *_ in _leaves(_WM_TASKS)
            if task.get("ansible.builtin.file", {}).get("state") == "directory"
            for item in task["loop"]
        }
        written = [
            Path(facts["devbox_rift_app"]).parent,
            Path(facts["devbox_rift_cli"]).parent,
            Path(facts["devbox_rift_marker"]).parent,
            Path(facts["devbox_rift_conf_dir"]),
            Path(facts["devbox_rift_plist_path"]).parent,
            Path(_render_plist()["StandardOutPath"]).parent,
        ]

        assert {str(p) for p in written} <= directories


class TestPinAndInstaller:
    def test_the_pin_has_exactly_the_documented_fields(self) -> None:
        assert set(_PIN) == {"repository", "version", "asset", "sha256"}

    def test_sha256_is_64_lowercase_hex(self) -> None:
        assert re.fullmatch(r"[0-9a-f]{64}", _PIN["sha256"])

    def test_repository_is_owner_slash_name_and_version_is_a_release_number(self) -> None:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+", _PIN["repository"])
        assert re.fullmatch(r"\d+\.\d+\.\d+", _PIN["version"])

    def test_asset_template_carries_the_version_placeholder_once(self) -> None:
        assert _PIN["asset"].count("{version}") == 1

    def test_the_resolved_asset_is_a_plain_file_name(self) -> None:
        name = _facts()["devbox_rift_asset_name"]

        assert name == _PIN["asset"].replace("{version}", _PIN["version"])
        assert re.fullmatch(r"[A-Za-z0-9._-]+", name)
        assert "{" not in name
        assert _PIN["version"] in name

    def test_the_download_url_is_the_pinned_release_asset_over_https(self) -> None:
        facts = _facts()

        assert facts["devbox_rift_url"] == (
            f"https://github.com/{_PIN['repository']}/releases/download/v{_PIN['version']}/"
            f"{facts['devbox_rift_asset_name']}"
        )

    def test_the_paths_resolve_under_home(self) -> None:
        facts = _facts()

        assert facts["devbox_rift_app"] == f"{HOME}/Applications/Rift.app"
        assert facts["devbox_rift_cli"] == f"{HOME}/.local/bin/rift-cli"
        assert facts["devbox_rift_conf_dir"] == f"{HOME}/.config/rift"
        assert facts["devbox_rift_marker"] == f"{HOME}/.local/share/rift/.release-digest"

    @staticmethod
    def _pin_guard() -> list[str]:
        task = next(t for t in _WM_TASKS if "malformed Rift pin" in t["name"])
        return task["ansible.builtin.assert"]["that"]

    @staticmethod
    def _install_block() -> Doc:
        return next(t for t in _WM_TASKS if INSTALL_BLOCK in t["name"])

    def test_a_well_formed_pin_passes_the_pin_assertion(self) -> None:
        env = _logic_env()
        context: Doc = {
            "devbox_packages": {"rift": _PIN},
            "devbox_rift_asset_name": _facts()["devbox_rift_asset_name"],
        }

        assert all(env.compile_expression(expr)(**context) for expr in self._pin_guard())

    @pytest.mark.parametrize(
        "sha256",
        [
            "",
            "a" * 63,
            "a" * 65,
            "A" * 64,
            "g" * 64,
            "0x" + "a" * 62,
            "sha256:" + "a" * 64,
            "a" * 64 + "\n",
        ],
        ids=[
            "empty",
            "short",
            "long",
            "uppercase",
            "non-hex",
            "prefixed-0x",
            "prefixed-sha256",
            "trailing-newline",
        ],
    )
    def test_a_malformed_sha256_is_refused(self, sha256: str) -> None:
        env = _logic_env()
        context: Doc = {
            "devbox_packages": {"rift": {**_PIN, "sha256": sha256}},
            "devbox_rift_asset_name": "rift.tar.gz",
        }

        assert not all(env.compile_expression(expr)(**context) for expr in self._pin_guard())

    @pytest.mark.parametrize(
        "asset",
        [
            "",
            "../rift.tar.gz",
            "dir/rift.tar.gz",
            "rift tar.gz",
            "rift.tar.gz;rm",
            "https://x/rift.tar.gz",
            "rift.tar.gz\n",
        ],
        ids=[
            "empty",
            "parent",
            "subdirectory",
            "space",
            "shell-metachar",
            "url",
            "trailing-newline",
        ],
    )
    def test_an_asset_that_is_not_a_plain_file_name_is_refused(self, asset: str) -> None:
        env = _logic_env()
        context: Doc = {"devbox_packages": {"rift": _PIN}, "devbox_rift_asset_name": asset}

        assert not all(env.compile_expression(expr)(**context) for expr in self._pin_guard())

    def test_the_download_checks_the_pinned_sha256(self) -> None:
        download = next(
            t for t in self._install_block()["block"] if "ansible.builtin.get_url" in t
        )["ansible.builtin.get_url"]
        context: Doc = {"devbox_packages": {"rift": _PIN}, **_facts()}
        env = _render_env()

        assert env.from_string(download["checksum"]).render(**context) == f"sha256:{_PIN['sha256']}"
        assert env.from_string(download["url"]).render(**context) == _facts()["devbox_rift_url"]
        assert download.get("validate_certs", True) is True
        assert download["dest"].startswith("{{ devbox_rift_staging.path }}/")

    def test_the_download_happens_before_anything_is_unpacked_or_replaced(self) -> None:
        block = self._install_block()["block"]
        modules = [
            next(key for key in task if key.startswith("ansible.builtin.")) for task in block
        ]
        unpack = next(
            i for i, task in enumerate(block) if _argv(task)[:2] == ["/usr/bin/tar", "-xzf"]
        )
        first_replace = next(
            i
            for i, task in enumerate(block)
            if _argv(task)[:1] in (["/usr/bin/ditto"], ["/bin/mv"])
        )

        assert modules.index("ansible.builtin.get_url") < unpack < first_replace

    @pytest.mark.parametrize(("app_installed", "aside_ran"), [(True, True), (False, False)])
    def test_a_first_install_has_no_bundle_to_move_aside_but_still_places_the_new_one(
        self, *, app_installed: bool, aside_ran: bool
    ) -> None:
        steps = _simulate(_WM_TASKS, Machine(current=False, app_installed=app_installed))
        aside = [s.ran for s in steps if _argv(s.task)[-1:] == ["{{ devbox_rift_app }}.old"]]
        place = [
            s.ran for s in steps if _argv(s.task)[:2] == ["/bin/mv", "{{ devbox_rift_app }}.new"]
        ]

        assert aside == [aside_ran]
        assert place == [True]

    def test_the_archive_is_unpacked_with_the_system_tar_from_staging_into_staging(self) -> None:
        block = self._install_block()["block"]
        argv = next(_argv(t) for t in block if _argv(t)[:2] == ["/usr/bin/tar", "-xzf"])
        download = next(t for t in block if "ansible.builtin.get_url" in t)[
            "ansible.builtin.get_url"
        ]

        assert argv[2] == download["dest"]
        assert argv[3:] == ["-C", "{{ devbox_rift_staging.path }}"]
        assert not any("ansible.builtin.unarchive" in t for t in block)

    def test_the_installed_bundle_is_inspected_before_it_is_moved_aside_and_only_then_moved(
        self,
    ) -> None:
        block = self._install_block()["block"]
        inspect = next(
            i for i, t in enumerate(block) if t.get("register") == "devbox_rift_app_before"
        )
        aside = next(
            i
            for i, t in enumerate(block)
            if _argv(t)[:3] == ["/bin/mv", "{{ devbox_rift_app }}", "{{ devbox_rift_app }}.old"]
        )
        conditions = _conditions(block[aside])

        assert inspect < aside
        assert block[inspect]["ansible.builtin.stat"]["path"] == "{{ devbox_rift_app }}"
        assert _holds(conditions, {"devbox_rift_app_before": {"stat": {"exists": True}}})
        assert not _holds(conditions, {"devbox_rift_app_before": {"stat": {"exists": False}}})

    def test_a_running_rift_is_saved_and_has_exited_before_the_bundle_moves(self) -> None:
        block = self._install_block()["block"]
        first_move = next(i for i, t in enumerate(block) if _argv(t)[:1] == ["/bin/mv"])
        save = next(i for i, t in enumerate(block) if _SAVE_AND_EXIT(t))
        wait = next(i for i, t in enumerate(block) if _argv(t)[:2] == ["pgrep", "-x"])

        assert save < wait < first_move

    def test_the_release_digest_is_recorded_last_so_a_failed_install_is_retried(self) -> None:
        block = self._install_block()["block"]
        marker = next(
            i
            for i, t in enumerate(block)
            if t.get("ansible.builtin.copy", {}).get("dest") == "{{ devbox_rift_marker }}"
        )
        cli = next(
            i
            for i, t in enumerate(block)
            if t.get("ansible.builtin.copy", {}).get("dest") == "{{ devbox_rift_cli }}"
        )
        in_place = next(
            i
            for i, t in enumerate(block)
            if _argv(t)[:2] == ["/bin/mv", "{{ devbox_rift_app }}.new"]
        )

        assert in_place < cli < marker
        assert not any("ansible.builtin.copy" in t for t in block[marker + 1 :])

    def test_the_marker_holds_the_pinned_digest(self) -> None:
        block = self._install_block()["block"]
        marker = next(
            t
            for t in block
            if t.get("ansible.builtin.copy", {}).get("dest") == "{{ devbox_rift_marker }}"
        )

        content = (
            _render_env()
            .from_string(marker["ansible.builtin.copy"]["content"])
            .render(devbox_packages={"rift": _PIN})
        )

        assert content == f"{_PIN['sha256']}\n"

    def test_a_failed_install_puts_the_previous_bundle_back_and_fails_the_run(self) -> None:
        rescue = self._install_block()["rescue"]
        inspect = next(t for t in rescue if t.get("register") == "devbox_rift_rescue_bundles")
        restore = next(t for t in rescue if _argv(t)[:1] == ["/bin/mv"])
        paths = [
            _render_env().from_string(item).render(devbox_rift_app="/a/Rift.app")
            for item in inspect["loop"]
        ]

        assert paths == ["/a/Rift.app.old", "/a/Rift.app"]
        assert rescue.index(inspect) < rescue.index(restore)
        assert _argv(restore) == ["/bin/mv", "{{ devbox_rift_app }}.old", "{{ devbox_rift_app }}"]
        assert "ansible.builtin.fail" in rescue[-1]

    @pytest.mark.parametrize(
        ("old_exists", "app_exists", "restores"),
        [(True, False, True), (True, True, False), (False, False, False), (False, True, False)],
        ids=["old-only", "both", "neither", "app-only"],
    )
    def test_the_previous_bundle_is_restored_only_when_it_exists_and_the_app_is_missing(
        self, *, old_exists: bool, app_exists: bool, restores: bool
    ) -> None:
        rescue = self._install_block()["rescue"]
        restore = next(t for t in rescue if _argv(t)[:1] == ["/bin/mv"])
        context: Doc = {
            "devbox_rift_rescue_bundles": {
                "results": [{"stat": {"exists": old_exists}}, {"stat": {"exists": app_exists}}]
            }
        }

        assert _holds(_conditions(restore), context) is restores

    def test_staging_and_the_half_copied_bundle_are_removed_on_every_path(self) -> None:
        removal = self._install_block()["always"][0]

        assert removal["ansible.builtin.file"] == {"path": "{{ item }}", "state": "absent"}
        assert any("devbox_rift_staging.path" in item for item in removal["loop"])
        assert "{{ devbox_rift_app }}.new" in removal["loop"]
        assert removal["when"] == "item | length > 0"

    def test_the_staging_removal_survives_a_staging_directory_that_was_never_made(self) -> None:
        loop = self._install_block()["always"][0]["loop"]

        rendered = [
            _logic_env()
            .from_string(item)
            .render(devbox_rift_staging={}, devbox_rift_app="/a/Rift.app")
            for item in loop
        ]

        assert sorted(rendered) == ["", "/a/Rift.app.new"]

    @pytest.mark.parametrize(
        ("installed", "marker", "expected"),
        [
            ((True, True), _PIN["sha256"] + "\n", "True"),
            ((True, True), _PIN["sha256"], "True"),
            ((True, True), "0" * 64 + "\n", "False"),
            ((True, True), _PIN["sha256"].upper() + "\n", "False"),
            ((True, True), _PIN["sha256"][:-1] + "\n", "False"),
            ((True, True), "", "False"),
            ((True, False), _PIN["sha256"] + "\n", "False"),
            ((False, True), _PIN["sha256"] + "\n", "False"),
            ((False, False), _PIN["sha256"] + "\n", "False"),
        ],
        ids=[
            "current",
            "no-newline",
            "other-digest",
            "uppercase",
            "truncated",
            "empty-marker",
            "cli-missing",
            "app-missing",
            "both-missing",
        ],
    )
    def test_the_pinned_rift_counts_as_installed_only_with_both_files_and_the_digest(
        self, installed: tuple[bool, bool], marker: str, expected: str
    ) -> None:
        decide = next(t for t in _WM_TASKS if "decide whether" in t["name"])
        expression = decide["ansible.builtin.set_fact"]["devbox_rift_is_current"]
        context: Doc = {
            "devbox_packages": {"rift": _PIN},
            "devbox_rift_installed_files": {
                "results": [{"stat": {"exists": flag}} for flag in installed]
            },
            "devbox_rift_marker_content": {"content": base64.b64encode(marker.encode()).decode()},
        }

        assert _logic_env().from_string(expression).render(**context) == expected

    def test_a_missing_marker_file_counts_as_not_installed(self) -> None:
        decide = next(t for t in _WM_TASKS if "decide whether" in t["name"])
        expression = decide["ansible.builtin.set_fact"]["devbox_rift_is_current"]
        context: Doc = {
            "devbox_packages": {"rift": _PIN},
            "devbox_rift_installed_files": {"results": [{"stat": {"exists": True}}] * 2},
            "devbox_rift_marker_content": {"failed": True, "msg": "file not found"},
        }

        assert _logic_env().from_string(expression).render(**context) == "False"

    def test_the_install_block_is_skipped_for_a_current_install_and_in_check_mode(self) -> None:
        def block_ran(machine: Machine) -> bool:
            steps = _simulate(_WM_TASKS, machine)
            return any(s.ran for s in steps if _in_block(s, INSTALL_BLOCK) and s.section == "block")

        assert block_ran(Machine(current=False)) is True
        assert block_ran(Machine(current=True)) is False
        assert block_ran(Machine(current=False, check_mode=True)) is False

    def test_a_homebrew_rift_stops_the_run(self) -> None:
        refuse = next(t for t in _WM_TASKS if "alongside a Homebrew Rift" in t["name"])

        assert "ansible.builtin.fail" in refuse
        assert _holds(_conditions(refuse), {"devbox_rift_brew": {"rc": 0}})
        assert not _holds(_conditions(refuse), {"devbox_rift_brew": {"rc": 1}})


class TestSpacesSetting:
    @staticmethod
    def _task() -> Doc:
        return next(t for t in _WM_TASKS if "community.general.osx_defaults" in t)

    @pytest.mark.parametrize(("wm", "spans"), [("rift", "False"), ("aerospace", "True")])
    def test_rift_wants_separate_spaces_and_aerospace_wants_one_shared_space(
        self, wm: str, spans: str
    ) -> None:
        value = self._task()["community.general.osx_defaults"]["value"]

        assert _logic_env().from_string(value).render(devbox_wm=wm) == spans

    def test_the_setting_is_the_spaces_domain_key(self) -> None:
        defaults = self._task()["community.general.osx_defaults"]

        assert (defaults["domain"], defaults["key"], defaults["type"]) == (
            "com.apple.spaces",
            "spans-displays",
            "bool",
        )

    def test_a_change_notifies_a_handler_that_exists_and_names_the_window_manager(self) -> None:
        handler = next(h for h in _task_list(HANDLERS) if h["name"] == self._task()["notify"])

        message = (
            _logic_env()
            .from_string(handler["ansible.builtin.debug"]["msg"])
            .render(devbox_wm="rift")
        )

        assert "devbox_wm=rift" in message
