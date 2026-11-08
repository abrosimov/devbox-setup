"""Static contract of upgrade mode: a provisioning run upgrades by default.

`devbox_upgrade_mode` defaults to true so `make personal` / `make work` keep
managed software current; `-e devbox_upgrade_mode=false` still gives an
install-only run. Casks upgrade through a dedicated `state: latest` task
because `brew upgrade` rejects the `--adopt` the install tasks pass.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "roles/devbox/defaults/main/core.yml"
TASKS_DIR = ROOT / "roles/devbox/tasks/darwin"
MAKEFILE = ROOT / "Makefile"
SWITCH = "devbox_upgrade_mode"
CASK = "community.general.homebrew_cask"
CASK_FILES = ("install_from_brew_primary.yml", "install_from_brew_secondary.yml")

Doc = dict


def _tasks(name: str) -> list[Doc]:
    loaded = yaml.safe_load((TASKS_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    return loaded


def _all_task_files() -> Iterator[Path]:
    yield from sorted(TASKS_DIR.glob("*.yml"))


def _when(task: Doc) -> str:
    when = task.get("when", "")
    return " ".join(when) if isinstance(when, list) else str(when)


def _options(task: Doc) -> list[str]:
    options = task[CASK].get("install_options", [])
    return [options] if isinstance(options, str) else list(options)


def test_upgrade_mode_defaults_to_true() -> None:
    core = yaml.safe_load(CORE.read_text(encoding="utf-8"))
    assert core[SWITCH] is True


def test_no_task_falls_back_to_install_only() -> None:
    for path in _all_task_files():
        text = path.read_text(encoding="utf-8")
        assert f"{SWITCH} | default(false)" not in text, path.name


def test_upgrade_targets_are_gone() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    assert re.search(r"^upgrade-(work|personal):", text, re.MULTILINE) is None
    assert "upgrade-work" not in text
    assert "upgrade-personal" not in text


def test_every_installed_cask_list_has_an_upgrade_task() -> None:
    for name in CASK_FILES:
        casks = [task for task in _tasks(name) if CASK in task and task[CASK]["state"] != "absent"]
        installs = {task[CASK]["name"] for task in casks if task[CASK]["state"] == "present"}
        upgrades = {task[CASK]["name"] for task in casks if task[CASK]["state"] == "latest"}
        assert installs == upgrades, name


def test_cask_upgrades_are_gated_not_greedy_and_never_adopt() -> None:
    for name in CASK_FILES:
        for task in _tasks(name):
            if CASK not in task or task[CASK]["state"] != "latest":
                continue
            assert SWITCH in _when(task), task["name"]
            assert not task[CASK].get("greedy", False), task["name"]
            assert "adopt" not in _options(task), task["name"]
            assert task.get("no_log") is True, task["name"]


def test_no_binaries_survives_the_upgrade() -> None:
    upgrades = [
        task
        for task in _tasks("install_from_brew_secondary.yml")
        if CASK in task and task[CASK]["state"] == "latest" and "no_binaries" in task[CASK]["name"]
    ]
    assert len(upgrades) == 1
    assert _options(upgrades[0]) == ["no-binaries"]


def test_uv_tools_are_installed_in_both_modes() -> None:
    install = next(task for task in _tasks("install_from_uv.yml") if "uv tool install" in str(task))
    assert "when" not in install
    upgrade = next(task for task in _tasks("install_from_uv.yml") if "uv tool upgrade" in str(task))
    assert SWITCH in _when(upgrade)


def _uv_install_command() -> Doc:
    install = next(task for task in _tasks("install_from_uv.yml") if "uv tool install" in str(task))
    return install["ansible.builtin.command"]


def test_uv_tool_install_takes_over_a_launcher_owned_by_another_installer() -> None:
    cmd = _uv_install_command()["cmd"]
    assert cmd.startswith("uv tool install ")
    assert "--force" in cmd.split()
    assert cmd.endswith("{{ item }}")


def test_uv_tool_presence_is_judged_by_uvs_own_tool_environment() -> None:
    creates = _uv_install_command()["creates"]
    assert creates.endswith("/.local/share/uv/tools/{{ item }}")
    assert "/.local/bin/" not in creates


def _command_task(name: str) -> Doc:
    tasks = [task for task in _tasks("install_from_brew_secondary.yml") if task["name"] == name]
    assert len(tasks) == 1, name
    return tasks[0]


TOOLCHAIN_UPGRADES = {
    # task name -> (path it must already exist at, text in changed_when)
    "Update Rust toolchains": (".cargo/bin/rustc", "(updated|installed) - "),
    "Update opam package repositories": (".opam/default", "synchronised from"),
    "Upgrade OCaml packages": (".opam/default", "The following actions "),
    "Upgrade SWI-Prolog LSP server": (".local/share/swi-prolog/pack/lsp_server", "upgraded"),
}


def test_toolchain_upgrades_are_gated_and_need_an_existing_install() -> None:
    for name, (path, _) in TOOLCHAIN_UPGRADES.items():
        task = _command_task(name)
        command = task["ansible.builtin.command"]
        assert SWITCH in _when(task), name
        assert command["removes"].endswith("/" + path), name
        assert "creates" not in command, name


def test_toolchain_upgrades_report_change_from_output() -> None:
    for name, (_, needle) in TOOLCHAIN_UPGRADES.items():
        task = _command_task(name)
        assert task["changed_when"] is not True, name
        assert needle in task["changed_when"], name
        assert task["register"] in task["changed_when"], name


def test_toolchain_upgrades_run_after_their_first_install() -> None:
    names = [task["name"] for task in _tasks("install_from_brew_secondary.yml")]
    order = [
        ("Init Rust toolchain", "Update Rust toolchains"),
        ("Install necessary OCaml packages", "Update opam package repositories"),
        ("Update opam package repositories", "Upgrade OCaml packages"),
        ("Install SWI-Prolog LSP server", "Upgrade SWI-Prolog LSP server"),
    ]
    for first, then in order:
        assert names.index(first) < names.index(then), (first, then)


def test_rustup_never_self_updates() -> None:
    argv = _command_task("Update Rust toolchains")["ansible.builtin.command"]["argv"]
    assert argv == ["rustup", "update", "--no-self-update"]


def test_opam_commands_answer_their_own_prompts() -> None:
    # A Homebrew upgrade of opam makes the next opam command ask to upgrade the
    # ~/.opam layout; unanswered, a non-interactive run says "n" and exits 10.
    for name in ("Update opam package repositories", "Upgrade OCaml packages"):
        argv = _command_task(name)["ansible.builtin.command"]["argv"]
        assert {"-y", "--yes"} & set(argv), name


def test_first_installs_are_unchanged() -> None:
    for name in ("Init Rust toolchain", "Install necessary OCaml packages"):
        task = _command_task(name)
        assert "creates" in task["ansible.builtin.command"], name
        assert "when" not in task, name


def test_app_store_follows_the_switch() -> None:
    (task,) = _tasks("install_from_appstore.yml")
    assert SWITCH in task["community.general.mas"]["state"]
