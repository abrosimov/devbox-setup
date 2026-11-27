from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from jinja2 import StrictUndefined, Template

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS = REPO_ROOT / "roles/devbox/tasks/install_configs.yml"
LOCAL_PLAYBOOK = REPO_ROOT / "playbooks/local.yml"
KARABINER_DIR = REPO_ROOT / "roles/devbox/files/.config/karabiner"
KARABINER_SEED = KARABINER_DIR / "karabiner.json"
CAPS_LOCK_ASSET = KARABINER_DIR / "assets/complex_modifications/caps_lock_rift_super.json"
CORE_DEFAULTS = REPO_ROOT / "roles/devbox/defaults/main/core.yml"
CAPS_LOCK_RULE = "Caps Lock → Control+Option"
LAYOUT_RULE = "Tap Left/Right Command → English, Tap Left/Right Option → Russian"
_KARABINER_FAMILY = {"control": "ctrl", "option": "alt", "command": "meta", "shift": "shift"}
_RIFT_FAMILY = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "opt": "alt",
    "meta": "meta",
    "cmd": "meta",
    "command": "meta",
    "shift": "shift",
}
_RIFT_MODIFIER = re.compile(
    rf"(?:l|r|left|right)?({'|'.join(_RIFT_FAMILY)})(?:left|right)?",
)

_tasks = yaml.safe_load(TASKS.read_text())
_local_playbook = yaml.safe_load(LOCAL_PLAYBOOK.read_text())
_karabiner_seed = json.loads(KARABINER_SEED.read_text())
_core_defaults = yaml.safe_load(CORE_DEFAULTS.read_text())


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


def _seed_rules() -> list[dict]:
    return _karabiner_seed["profiles"][0]["complex_modifications"]["rules"]


def _rules_described(rules: list[dict], description: str) -> list[dict]:
    return [rule for rule in rules if rule["description"] == description]


def _karabiner_family(name: str) -> str:
    return _KARABINER_FAMILY.get(re.sub(r"^(?:left|right)_", "", name), name)


def _emitted_families(rule: dict) -> frozenset[str]:
    [manipulator] = rule["manipulators"]
    [event] = manipulator["to"]
    names = [event["key_code"], *event.get("modifiers", [])]
    return frozenset(_karabiner_family(name) for name in names)


def _rift_super_families(combination: str) -> frozenset[str]:
    matches = [_RIFT_MODIFIER.fullmatch(part.strip().lower()) for part in combination.split("+")]

    assert None not in matches, f"unrecognised modifier in super = {combination!r}"
    return frozenset(_RIFT_FAMILY[m.group(1)] for m in matches if m is not None)


def _caps_lock_rule() -> dict:
    [rule] = _rules_described(_seed_rules(), CAPS_LOCK_RULE)
    return rule


def test_karabiner_seed_first_profile_is_the_selected_one() -> None:
    assert _karabiner_seed["profiles"][0]["selected"] is True


def test_karabiner_seed_has_no_simple_modifications() -> None:
    assert [p["name"] for p in _karabiner_seed["profiles"] if "simple_modifications" in p] == []


def test_karabiner_seed_first_profile_holds_the_layout_rule_and_the_caps_lock_rule() -> None:
    descriptions = [rule["description"] for rule in _seed_rules()]

    assert sorted(descriptions) == sorted([LAYOUT_RULE, CAPS_LOCK_RULE])


def test_caps_lock_rule_sends_control_with_option_as_one_event() -> None:
    assert _caps_lock_rule()["manipulators"] == [
        {
            "type": "basic",
            "from": {"key_code": "caps_lock", "modifiers": {"optional": ["any"]}},
            "to": [{"key_code": "left_control", "modifiers": ["left_option"]}],
        }
    ]


def test_no_other_seed_rule_takes_caps_lock() -> None:
    grabbing = [
        rule["description"]
        for rule in _seed_rules()
        for manipulator in rule["manipulators"]
        if manipulator["from"].get("key_code") == "caps_lock"
    ]

    assert grabbing == [CAPS_LOCK_RULE]


def test_rift_super_is_the_modifier_set_the_caps_lock_rule_emits() -> None:
    super_value = _core_defaults["devbox_rift_super"]

    assert super_value == "Ctrl + Alt"
    assert _emitted_families(_caps_lock_rule()) == _rift_super_families(super_value)
    assert _emitted_families(_caps_lock_rule()) == {"ctrl", "alt"}


@pytest.mark.parametrize(
    "super_value",
    ["Ctrl", "Alt", "Ctrl + Alt + Shift", "Ctrl + Meta", "Meta + Shift", "CtrlRight"],
)
def test_a_rift_super_that_drifts_from_the_caps_lock_rule_is_detected(super_value: str) -> None:
    assert _emitted_families(_caps_lock_rule()) != _rift_super_families(super_value)


@pytest.mark.parametrize(
    ("key_code", "modifiers"),
    [
        ("left_control", []),
        ("left_option", []),
        ("left_control", ["left_option", "left_shift"]),
        ("left_control", ["left_command"]),
        ("left_shift", ["left_option"]),
        ("caps_lock", ["left_control", "left_option"]),
    ],
    ids=["control-only", "option-only", "extra-shift", "command-not-option", "shift", "key-kept"],
)
def test_a_caps_lock_rule_that_drifts_from_the_rift_super_is_detected(
    key_code: str, modifiers: list[str]
) -> None:
    rule = {"manipulators": [{"to": [{"key_code": key_code, "modifiers": modifiers}]}]}

    assert _emitted_families(rule) != _rift_super_families(_core_defaults["devbox_rift_super"])


@pytest.mark.parametrize(
    ("key_code", "modifiers"),
    [
        ("left_control", ["left_option"]),
        ("right_control", ["right_option"]),
        ("left_option", ["left_control"]),
        ("control", ["option"]),
    ],
)
def test_the_sync_ignores_which_side_or_order_the_two_modifiers_use(
    key_code: str, modifiers: list[str]
) -> None:
    rule = {"manipulators": [{"to": [{"key_code": key_code, "modifiers": modifiers}]}]}

    assert _emitted_families(rule) == _rift_super_families("Ctrl + Alt")


def test_caps_lock_asset_rules_equal_the_seed_rules_of_the_same_description() -> None:
    rules = json.loads(CAPS_LOCK_ASSET.read_text())["rules"]

    assert [rule["description"] for rule in rules] == [CAPS_LOCK_RULE]
    for rule in rules:
        assert _rules_described(_seed_rules(), rule["description"]) == [rule]


def test_git_hook_sync_uses_openrsync_compatible_permissions() -> None:
    task = _task(
        "Sync global git hooks (one-way, --delete purges non-managed hooks like stale git-lfs)"
    )

    assert task["ansible.posix.synchronize"]["rsync_opts"] == [
        "--exclude=.DS_Store",
        "--chmod=Du=rwx,Dgo=rx,Fu=rwx,Fgo=rx",
    ]


def test_local_overlay_fast_path_gathers_platform_and_user_facts() -> None:
    assert _local_playbook[0]["gather_facts"] is True


def _task(name: str) -> dict[str, object]:
    return next(task for task in _tasks if task["name"] == name)


@pytest.mark.parametrize(
    ("task_name", "exclusion"),
    [
        (
            "Copy local overlay files",
            "item.path != '.config/otelbox/edge/client/client.crt'",
        ),
        (
            "Copy local overlay files",
            "item.path != '.config/otelbox/edge/client/client.key'",
        ),
        (
            "Render local overlay templates",
            "item.path != '.config/otelbox/edge/client/client.crt.j2'",
        ),
        (
            "Render local overlay templates",
            "item.path != '.config/otelbox/edge/client/client.key.j2'",
        ),
    ],
)
def test_otelbox_client_key_bypasses_generic_diff_capable_tasks(
    task_name: str, exclusion: str
) -> None:
    task = _task(task_name)
    conditions = task["when"]
    assert isinstance(conditions, list)

    assert exclusion in conditions


def test_otelbox_client_key_copy_never_emits_a_diff() -> None:
    task = _task("Deploy private otelbox edge client key without diff")
    copy = task["ansible.builtin.copy"]
    conditions = task["when"]
    assert isinstance(copy, dict)
    assert isinstance(conditions, list)

    assert task["diff"] is False
    assert copy["mode"] == "0600"
    assert "item.path == '.config/otelbox/edge/client/client.key'" in conditions


def test_otelbox_client_overlay_is_validated_before_live_mutation() -> None:
    validation = _task("Validate the otelbox edge client certificate overlay before deployment")
    mutation_names = {
        "Deploy validated otelbox edge client certificate",
        "Deploy private otelbox edge client key without diff",
        "Reconcile absent otelbox edge client certificate files",
    }
    validation_index = _tasks.index(validation)
    mutation_indices = [
        index for index, task in enumerate(_tasks) if task["name"] in mutation_names
    ]
    command = validation["ansible.builtin.command"]

    assert validation["check_mode"] is False
    assert command["argv"][:2] == [
        "{{ ansible_playbook_python }}",
        "{{ role_path }}/../../scripts/otelbox-edge-cert-check.py",
    ]
    assert mutation_indices
    assert all(validation_index < index for index in mutation_indices)


@pytest.mark.parametrize(
    ("source_files", "expected"),
    [
        ((), "False"),
        (("client.crt",), "True"),
        (("client.key",), "True"),
        (("client.crt", "client.key"), "False"),
    ],
)
def test_incomplete_otelbox_client_overlay_fails_before_copy(
    source_files: tuple[str, ...], expected: str
) -> None:
    task = _task("Refuse an incomplete otelbox edge client certificate overlay")
    conditions = task["when"]
    assert isinstance(conditions, list)
    filetree = [
        {
            "path": f".config/otelbox/edge/client/{name}",
            "state": "file",
        }
        for name in source_files
    ]

    rendered = Template("{{ " + conditions[-1] + " }}", undefined=StrictUndefined).render(
        devbox_local_filetree_items=filetree
    )

    assert rendered == expected


@pytest.mark.parametrize(
    "task_name",
    [
        "Validate the otelbox edge client certificate overlay before deployment",
        "Deploy validated otelbox edge client certificate",
        "Deploy private otelbox edge client key without diff",
        "Reconcile absent otelbox edge client certificate files",
    ],
)
def test_otelbox_client_material_tasks_are_darwin_only(task_name: str) -> None:
    conditions = _task(task_name)["when"]

    assert isinstance(conditions, list)
    assert "ansible_facts['os_family'] == 'Darwin'" in conditions


@pytest.mark.parametrize(
    "task_name",
    [
        "Bootstrap Claude hooks venv via uv sync",
        "Bootstrap Antigravity hooks venv via uv sync",
        "Bootstrap AeroSpace layouts venv via uv sync",
    ],
)
def test_uv_sync_bootstrap_skips_under_check_mode(task_name: str) -> None:
    # ansible.builtin.command's chdir runs before the module consults
    # check_mode (os.chdir() happens unconditionally ahead of the check_mode
    # branch), so a dry run into a directory an earlier, merely-simulated
    # file/synchronize task never actually created aborts for real instead
    # of skipping. `creates:` cannot fix this, since it is evaluated after
    # the chdir has already failed. `not ansible_check_mode` is the
    # guard that keeps these three `--check` runs honest.
    conditions = _conditions(_task(task_name))

    assert "not ansible_check_mode" in conditions
    for wm in ("aerospace", "rift"):
        assert not _holds(conditions, devbox_wm=wm, ansible_check_mode=True)


def test_aerospace_layouts_venv_bootstrap_runs_only_for_aerospace_outside_check_mode() -> None:
    conditions = _conditions(_task("Bootstrap AeroSpace layouts venv via uv sync"))

    assert conditions == ["devbox_wm == 'aerospace'", "not ansible_check_mode"]
    assert _holds(conditions, devbox_wm="aerospace", ansible_check_mode=False)
    assert not _holds(conditions, devbox_wm="rift", ansible_check_mode=False)


def _conditions(task: dict[str, object]) -> list[str]:
    when = task["when"]
    return list(when) if isinstance(when, list) else [str(when)]


def _holds(conditions: list[str], **context: object) -> bool:
    return all(
        bool(
            Template("{{ " + condition + " }}", undefined=StrictUndefined).render(**context)
            == "True"
        )
        for condition in conditions
    )


def test_otelbox_client_reconciliation_requires_the_overlay() -> None:
    conditions = _task("Reconcile absent otelbox edge client certificate files")["when"]

    assert isinstance(conditions, list)
    assert "devbox_local_overlay_dir.stat.exists" in conditions


def test_client_material_change_restarts_a_loaded_collector_in_fast_paths() -> None:
    status = _task("Check otelbox edge status after client material changes")
    restart = _task("Restart otelbox edge after client material changes")

    assert status["check_mode"] is False
    assert status["failed_when"] is False
    assert status["ansible.builtin.command"]["argv"][-1].endswith("local.otelbox-edge")
    assert "devbox_otelbox_edge_client_material_changed | bool" in restart["when"]
    assert restart["when"][-1] == (
        "(devbox_otelbox_edge_client_material_agent.rc | default(1)) == 0"
    )


@pytest.mark.parametrize(
    ("source_files", "item", "expected"),
    [
        ((), "client.crt", "True"),
        ((), "client.key", "True"),
        (("client.crt",), "client.crt", "False"),
        (("client.crt",), "client.key", "True"),
        (("client.crt", "client.key"), "client.key", "False"),
    ],
)
def test_otelbox_client_pair_reconciles_files_absent_from_overlay(
    source_files: tuple[str, ...], item: str, expected: str
) -> None:
    task = _task("Reconcile absent otelbox edge client certificate files")
    conditions = task["when"]
    file_action = task["ansible.builtin.file"]
    assert isinstance(conditions, list)
    assert isinstance(file_action, dict)
    filetree = [
        {
            "path": f".config/otelbox/edge/client/{name}",
            "state": "file",
        }
        for name in source_files
    ]
    rendered = Template("{{ " + conditions[-1] + " }}", undefined=StrictUndefined).render(
        devbox_local_filetree_items=filetree, item=item
    )

    assert file_action["state"] == "absent"
    assert rendered == expected
