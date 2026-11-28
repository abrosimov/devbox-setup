"""Static contract between the OpenBao unseal tasks, their LaunchAgent and the script.

Behavioural coverage of the script lives in tests/scripts/test_openbao_unseal.py.
"""

from __future__ import annotations

import plistlib
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = REPO_ROOT / "roles/devbox"
TASKS = ROLE / "tasks/darwin/configure_openbao_unseal.yml"
MAIN_DARWIN = ROLE / "tasks/main_darwin.yml"
PLAYBOOK = REPO_ROOT / "playbooks/openbao_unseal.yml"
PLIST_TEMPLATE = ROLE / "templates/darwin/Library/LaunchAgents/local.openbao-unseal.plist.j2"
SCRIPT = REPO_ROOT / "scripts/openbao-unseal.py"
PROFILES = REPO_ROOT / "profiles"

Mapping = dict[str, object]


def _mapping(value: object) -> Mapping:
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


def _mappings(value: object) -> list[Mapping]:
    assert isinstance(value, list)
    return [_mapping(item) for item in value]


def _strings(value: object) -> list[str]:
    assert isinstance(value, list)
    return [str(item) for item in value]


def _load(path: Path) -> list[Mapping]:
    return _mappings(yaml.safe_load(path.read_text(encoding="utf-8")))


def _all_tasks(tasks: list[Mapping]) -> list[Mapping]:
    flat: list[Mapping] = []
    for task in tasks:
        flat.append(task)
        flat.extend(_all_tasks(_mappings(task.get("block", []))))
    return flat


def _task(suffix: str) -> Mapping:
    return next(t for t in _all_tasks(_load(TASKS)) if str(t["name"]).endswith(suffix))


def _render_plist() -> Mapping:
    env = Environment(undefined=StrictUndefined, autoescape=True)
    rendered = env.from_string(PLIST_TEMPLATE.read_text(encoding="utf-8")).render(
        devbox_openbao_unseal_dir="/Users/u/.local/share/openbao-unseal",
        devbox_openbao_unseal_config="/Users/u/.config/openbao-unseal/config.json",
        devbox_openbao_unseal_identity="/Users/u/.ssh/openbao_unseal_ed25519",
        devbox_openbao_unseal_log="/Users/u/Library/Logs/openbao-unseal.log",
    )
    return _mapping(plistlib.loads(rendered.encode()))


def test_agent_runs_the_deployed_script_with_the_system_interpreter() -> None:
    plist = _render_plist()
    assert plist["Label"] == "local.openbao-unseal"
    assert plist["ProgramArguments"] == [
        "/usr/bin/python3",
        "/Users/u/.local/share/openbao-unseal/openbao-unseal.py",
        "--config",
        "/Users/u/.config/openbao-unseal/config.json",
        "--identity",
        "/Users/u/.ssh/openbao_unseal_ed25519",
        "--log",
        "/Users/u/Library/Logs/openbao-unseal.log",
    ]


def test_agent_runs_at_load_and_every_five_minutes() -> None:
    plist = _render_plist()
    assert plist["RunAtLoad"] is True
    assert plist["StartInterval"] == 300
    assert plist["StandardErrorPath"] == "/Users/u/Library/Logs/openbao-unseal.log"


def test_deployed_script_is_the_repository_script() -> None:
    copy = _mapping(_task("deploy the script")["ansible.builtin.copy"])
    assert str(copy["src"]).endswith("/scripts/openbao-unseal.py")
    assert str(copy["dest"]).endswith("/openbao-unseal.py")
    assert SCRIPT.read_text(encoding="utf-8").startswith("#!/usr/bin/python3\n")


def test_key_generation_never_overwrites_and_has_no_passphrase() -> None:
    command = _mapping(_task("generate the dedicated SSH key if absent")["ansible.builtin.command"])
    argv = _strings(command["argv"])
    assert command["creates"] == "{{ devbox_openbao_unseal_identity }}"
    assert argv[argv.index("-t") + 1] == "ed25519"
    assert argv[argv.index("-N") + 1] == ""
    assert argv[argv.index("-f") + 1] == "{{ devbox_openbao_unseal_identity }}"
    restrict = _mapping(_task("restrict the private key to its owner")["ansible.builtin.file"])
    assert restrict["mode"] == "0600"


def test_teardown_keeps_the_ssh_key() -> None:
    removed = _strings(_task("remove LaunchAgent plist and script")["loop"])
    assert all("ssh" not in path and "identity" not in path for path in removed)


def test_config_is_validated_by_the_interpreter_the_agent_uses() -> None:
    argv = _strings(_mapping(_task("validate the config")["ansible.builtin.command"])["argv"])
    assert argv[0] == "/usr/bin/python3"
    assert "--check-config" in argv


def _role_defaults() -> Mapping:
    merged: Mapping = {}
    for path in sorted((ROLE / "defaults/main").glob("*.yml")):
        merged.update(_mapping(yaml.safe_load(path.read_text(encoding="utf-8")) or {}))
    return merged


def _active(profile: str, *, config_exists: bool) -> bool:
    variables = _role_defaults()
    variables.update(_mapping(yaml.safe_load((PROFILES / f"{profile}.yml").read_text()) or {}))
    expression = str(
        _mapping(_task("decide whether this machine unseals")["ansible.builtin.set_fact"])[
            "devbox_openbao_unseal_active"
        ]
    )
    env = Environment(undefined=StrictUndefined, autoescape=True)
    env.filters["bool"] = lambda value: value is True or str(value).lower() in {"true", "yes", "1"}
    rendered = env.from_string(expression).render(
        **variables,
        devbox_openbao_unseal_config_stat={"stat": {"exists": config_exists}},
    )
    return rendered.strip() == "True"


def test_only_the_personal_profile_unseals() -> None:
    assert _active("personal", config_exists=True) is True
    assert _active("work", config_exists=True) is False
    assert _active("personal", config_exists=False) is False


def _extra_brew(profile: str) -> list[str]:
    values = _mapping(yaml.safe_load((PROFILES / f"{profile}.yml").read_text(encoding="utf-8")))
    return _strings(values.get("devbox_extra_brew", []))


def test_only_the_personal_profile_installs_the_openbao_cli() -> None:
    install = next(
        t
        for t in _load(ROLE / "tasks/darwin/install_from_brew_secondary.yml")
        if t["name"] == "Install Homebrew apps"
    )

    assert "devbox_extra_brew" in str(_mapping(install["community.general.homebrew"])["name"])
    assert "openbao" in _extra_brew("personal")
    assert "openbao" not in _extra_brew("work")


def test_install_block_and_teardown_follow_the_same_decision() -> None:
    install = _task("install and schedule")
    teardown = _task("tear down (profile off or no local config)")
    assert install["when"] == "devbox_openbao_unseal_active | bool"
    assert teardown["when"] == "not (devbox_openbao_unseal_active | bool)"
    install_names = {str(t["name"]) for t in _mappings(install["block"])}
    assert any("generate the dedicated SSH key" in name for name in install_names)
    assert any("bootstrap LaunchAgent" in name for name in install_names)
    teardown_names = {str(t["name"]) for t in _mappings(teardown["block"])}
    assert any("bootout LaunchAgent" in name for name in teardown_names)


def test_every_task_is_tagged() -> None:
    for task in _load(TASKS):
        assert "openbao-unseal" in _strings(task["tags"]), task["name"]


def test_wired_into_darwin_flow_outside_dev_mode() -> None:
    entry = next(
        t
        for t in _load(MAIN_DARWIN)
        if t.get("ansible.builtin.include_tasks") == "darwin/configure_openbao_unseal.yml"
    )
    assert "dev_mode" in str(entry["when"])


def test_fast_path_playbook_deploys_the_overlay_first() -> None:
    (play,) = _load(PLAYBOOK)
    imports = [task["ansible.builtin.import_tasks"] for task in _mappings(play["tasks"])]
    assert imports == [
        "../roles/devbox/tasks/install_configs.yml",
        "../roles/devbox/tasks/darwin/configure_openbao_unseal.yml",
        "../roles/devbox/tasks/darwin/configure_openbao_age_identity.yml",
    ]
