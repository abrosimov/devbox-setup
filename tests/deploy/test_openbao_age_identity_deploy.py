"""Static contract of the OpenBao break-glass age identity tasks, profiles and Makefile target.

The identity task file is evaluated the way test_openbao_unseal_deploy.py evaluates the unseal
tasks: the activation expression is rendered against the role defaults overlaid by a profile,
and the remaining guarantees are read off the task structure. The Makefile target is run against
a stub `age-keygen`, so what it passes to the tool and what it writes to disk is observed.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = REPO_ROOT / "roles/devbox"
TASKS = ROLE / "tasks/darwin/configure_openbao_age_identity.yml"
MAIN_DARWIN = ROLE / "tasks/main_darwin.yml"
PLAYBOOK = REPO_ROOT / "playbooks/openbao_unseal.yml"
PROFILES = REPO_ROOT / "profiles"
MAKEFILE = REPO_ROOT / "Makefile"

TARGET = "openbao-offline-age-key"
TAG = "openbao-unseal"
AGE_KEYGEN = "/opt/homebrew/bin/age-keygen"
IDENTITY = "{{ devbox_openbao_age_identity }}"
STUB_SECRET = "AGE-SECRET-KEY-1" + "STUBSTUBSTUBSTUB"
GUIDANCE = "Passwords (iCloud Keychain)"

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


def _task(fragment: str) -> Mapping:
    return next(t for t in _all_tasks(_load(TASKS)) if fragment in str(t["name"]))


def _block() -> Mapping:
    return next(t for t in _load(TASKS) if "block" in t)


def _block_names() -> list[str]:
    return [str(t["name"]) for t in _mappings(_block()["block"])]


def _role_defaults() -> Mapping:
    merged: Mapping = {}
    for path in sorted((ROLE / "defaults/main").glob("*.yml")):
        merged.update(_mapping(yaml.safe_load(path.read_text(encoding="utf-8")) or {}))
    return merged


def _profile(name: str) -> Mapping:
    return _mapping(yaml.safe_load((PROFILES / f"{name}.yml").read_text(encoding="utf-8")) or {})


def _env() -> Environment:
    env = Environment(undefined=StrictUndefined, autoescape=True)
    env.filters["bool"] = lambda value: value is True or str(value).lower() in {"true", "yes", "1"}
    return env


def _set_fact(key: str) -> str:
    facts = _mapping(_task("resolve paths")["ansible.builtin.set_fact"])
    return str(facts[key])


def _active(variables: Mapping) -> bool:
    rendered = _env().from_string(_set_fact("devbox_openbao_age_active")).render(**variables)
    assert rendered.strip() in {"True", "False"}
    return rendered.strip() == "True"


def _profile_variables(name: str) -> Mapping:
    variables = _role_defaults()
    variables.update(_profile(name))
    return variables


def _resolved(key: str, home: str = "/Users/u") -> str:
    return _env().from_string(_set_fact(key)).render(ansible_facts={"env": {"HOME": home}})


@pytest.mark.parametrize(
    ("unseal", "identity", "expected"),
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
    ids=["both-on", "identity-off", "unseal-off", "both-off"],
)
def test_identity_is_active_only_when_both_switches_are_on(
    *, unseal: bool, identity: bool, expected: bool
) -> None:
    variables: Mapping = {
        "devbox_openbao_unseal_enabled": unseal,
        "devbox_openbao_age_identity_enabled": identity,
    }
    assert _active(variables) is expected


def test_identity_is_inactive_when_the_switches_are_undefined() -> None:
    assert _active({}) is False


def test_role_defaults_leave_the_identity_off() -> None:
    assert _role_defaults()["devbox_openbao_age_identity_enabled"] is False
    assert _active(_role_defaults()) is False


def test_personal_profile_creates_and_work_profile_removes() -> None:
    assert _profile("personal")["devbox_openbao_age_identity_enabled"] is True
    assert _active(_profile_variables("personal")) is True
    assert _active(_profile_variables("work")) is False


def test_work_profile_does_not_switch_the_identity_on() -> None:
    assert "devbox_openbao_age_identity_enabled" not in _profile("work")


def test_a_retired_identity_switch_deactivates_the_personal_profile() -> None:
    variables = _profile_variables("personal")
    variables["devbox_openbao_age_identity_enabled"] = False
    assert _active(variables) is False


def test_identity_lives_under_the_age_directory_in_the_home() -> None:
    assert _resolved("devbox_openbao_age_dir") == "/Users/u/.config/age"
    assert _resolved("devbox_openbao_age_identity") == "/Users/u/.config/age/openbao-unseal.key"


def test_removal_runs_exactly_when_inactive_and_creation_exactly_when_active() -> None:
    removal = _task("remove the retired identity")
    assert removal["when"] == "not (devbox_openbao_age_active | bool)"
    assert _block()["when"] == "devbox_openbao_age_active | bool"


def test_removal_deletes_only_the_identity_file() -> None:
    removal = _mapping(_task("remove the retired identity")["ansible.builtin.file"])
    assert removal == {"path": IDENTITY, "state": "absent"}


def test_removal_does_not_depend_on_age_keygen_being_installed() -> None:
    top_level = [str(t["name"]) for t in _load(TASKS)]
    assert any("remove the retired identity" in name for name in top_level)
    nested = _block_names()
    assert not any("remove the retired identity" in name for name in nested)
    assert any("require age-keygen" in name for name in nested)


def test_age_keygen_presence_is_asserted_before_anything_is_generated() -> None:
    names = _block_names()

    def index(fragment: str) -> int:
        return next(i for i, name in enumerate(names) if fragment in name)

    assert index("look for age-keygen") < index("require age-keygen")
    assert index("require age-keygen") < index("ensure the directory exists")
    assert index("require age-keygen") < index("generate the identity if absent")
    assert index("require age-keygen") < index("read the recipient")


def test_presence_assertion_checks_the_binary_that_is_later_run() -> None:
    probed = _mapping(_task("look for age-keygen")["ansible.builtin.stat"])
    assert probed["path"] == AGE_KEYGEN
    assert _task("look for age-keygen")["register"] == "devbox_openbao_age_keygen"
    check = _mapping(_task("require age-keygen")["ansible.builtin.assert"])
    assert _strings(check["that"]) == ["devbox_openbao_age_keygen.stat.exists"]
    assert AGE_KEYGEN in str(check["fail_msg"])
    assert "brew install age" in " ".join(str(check["fail_msg"]).split())
    for name in ("generate the identity if absent", "read the recipient"):
        argv = _strings(_mapping(_task(name)["ansible.builtin.command"])["argv"])
        assert argv[0] == AGE_KEYGEN


def test_generation_never_overwrites_an_existing_identity() -> None:
    command = _mapping(_task("generate the identity if absent")["ansible.builtin.command"])
    assert command["creates"] == IDENTITY
    assert _strings(command["argv"]) == [AGE_KEYGEN, "-o", IDENTITY]
    assert "removes" not in command
    assert "cmd" not in command


def test_generation_is_not_a_shell_command() -> None:
    task = _task("generate the identity if absent")
    assert "ansible.builtin.shell" not in task
    assert "ansible.builtin.command" in task


def test_directory_is_private_and_identity_is_owner_only() -> None:
    directory = _mapping(_task("ensure the directory exists")["ansible.builtin.file"])
    assert directory["path"] == "{{ devbox_openbao_age_dir }}"
    assert directory["state"] == "directory"
    assert directory["mode"] == "0700"
    restrict = _mapping(_task("restrict the identity to its owner")["ansible.builtin.file"])
    assert restrict["path"] == IDENTITY
    assert restrict["mode"] == "0600"
    assert "state" not in restrict


def test_identity_mode_is_restricted_after_generation() -> None:
    names = _block_names()
    generated = next(i for i, n in enumerate(names) if "generate the identity" in n)
    restricted = next(i for i, n in enumerate(names) if "restrict the identity" in n)
    directory = next(i for i, n in enumerate(names) if "ensure the directory" in n)
    assert directory < generated < restricted


def test_recipient_is_derived_with_the_public_flag_and_never_changes_state() -> None:
    task = _task("read the recipient")
    argv = _strings(_mapping(task["ansible.builtin.command"])["argv"])
    assert argv == [AGE_KEYGEN, "-y", IDENTITY]
    assert task["changed_when"] is False
    assert task["register"] == "devbox_openbao_age_recipient"


def test_only_the_recipient_is_printed_never_the_identity_contents() -> None:
    message = str(_mapping(_task("show the recipient")["ansible.builtin.debug"])["msg"])
    assert "devbox_openbao_age_recipient.stdout" in message
    assert "devbox_openbao_age_identity }}" in message
    for task in _all_tasks(_load(TASKS)):
        assert "ansible.builtin.slurp" not in task
        assert "ansible.builtin.shell" not in task
        assert "ansible.builtin.fetch" not in task
        assert "AGE-SECRET-KEY" not in str(task)


@pytest.mark.parametrize(
    "fragment",
    ["restrict the identity to its owner", "read the recipient", "show the recipient"],
)
def test_tasks_that_need_the_generated_file_are_skipped_in_check_mode(fragment: str) -> None:
    assert _task(fragment)["when"] == "not ansible_check_mode"


def test_directory_and_generation_are_not_skipped_in_check_mode() -> None:
    for fragment in ("ensure the directory exists", "generate the identity if absent"):
        assert "when" not in _task(fragment)


def test_every_task_carries_the_fast_path_tag() -> None:
    tasks = _load(TASKS)
    assert len(tasks) == 3
    for task in tasks:
        assert _strings(task["tags"]) == [TAG], task["name"]


def test_fast_path_target_runs_the_tag_the_tasks_carry() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    recipe = re.search(r"^openbao-unseal-push:.*\n(?:\t.*\n)+", text, re.MULTILINE)
    assert recipe is not None
    tags = re.search(r"--tags (\S+)", recipe.group(0))
    assert tags is not None
    assert TAG in tags.group(1).split(",")


def test_identity_is_included_in_the_darwin_flow_outside_dev_mode() -> None:
    entries = _load(MAIN_DARWIN)
    wanted = "darwin/configure_openbao_age_identity.yml"
    matching = [t for t in entries if t.get("ansible.builtin.include_tasks") == wanted]
    assert len(matching) == 1
    assert matching[0]["when"] == "not (dev_mode | default(false) | bool)"
    unseal = next(
        t
        for t in entries
        if t.get("ansible.builtin.include_tasks") == "darwin/configure_openbao_unseal.yml"
    )
    assert matching[0]["when"] == unseal["when"]


def test_identity_is_generated_after_age_is_installed() -> None:
    includes = [str(t.get("ansible.builtin.include_tasks")) for t in _all_tasks(_load(MAIN_DARWIN))]
    brew = includes.index("darwin/install_from_brew_secondary.yml")
    identity = includes.index("darwin/configure_openbao_age_identity.yml")
    assert brew < identity


def test_fast_path_playbook_imports_the_identity_once_after_the_unseal_tasks() -> None:
    (play,) = _load(PLAYBOOK)
    imports = [str(t["ansible.builtin.import_tasks"]) for t in _mappings(play["tasks"])]
    identity = "../roles/devbox/tasks/darwin/configure_openbao_age_identity.yml"
    unseal = "../roles/devbox/tasks/darwin/configure_openbao_unseal.yml"
    assert imports.count(identity) == 1
    assert imports.index(identity) > imports.index(unseal)


def test_fast_path_playbook_loads_the_default_that_the_tasks_read() -> None:
    (play,) = _load(PLAYBOOK)
    core = ROLE / "defaults/main/core.yml"
    loaded = [(PLAYBOOK.parent / p).resolve() for p in _strings(play["vars_files"])]
    assert core in loaded
    defaults = _mapping(yaml.safe_load(core.read_text(encoding="utf-8")))
    assert "devbox_openbao_age_identity_enabled" in defaults


def _extra_brew(profile: str) -> list[str]:
    return _strings(_profile(profile).get("devbox_extra_brew", []))


def test_age_is_installed_in_every_full_run_through_the_secondary_formulae() -> None:
    secondary = _strings(_role_defaults()["devbox_brew_secondary"])
    assert "age" in secondary
    install = next(
        t
        for t in _load(ROLE / "tasks/darwin/install_from_brew_secondary.yml")
        if t["name"] == "Install Homebrew apps"
    )
    names = str(_mapping(install["community.general.homebrew"])["name"])
    assert "devbox_brew_secondary" in names


def test_age_is_not_duplicated_in_any_profile_extra_formulae() -> None:
    profiles = sorted(PROFILES.glob("*.yml"))
    assert {p.stem for p in profiles} >= {"personal", "work"}
    for path in profiles:
        assert "age" not in _extra_brew(path.stem), path.name


def test_personal_profile_keeps_the_openbao_cli_in_its_extra_formulae() -> None:
    assert "openbao" in _extra_brew("personal")


def _phony_targets() -> set[str]:
    logical = MAKEFILE.read_text(encoding="utf-8").replace("\\\n", " ").splitlines()
    for line in logical:
        if line.startswith(".PHONY:"):
            return set(line.removeprefix(".PHONY:").split())
    msg = "no .PHONY line in the Makefile"
    raise AssertionError(msg)


def _make() -> str:
    found = shutil.which("make")
    assert found is not None, "make is required to run the Makefile tests"
    return found


def _basic_tools(sandbox: Path) -> Path:
    tools = sandbox / "tools"
    tools.mkdir(exist_ok=True)
    for name in ("echo", "head"):
        source = shutil.which(name)
        if source is not None and not (tools / name).exists():
            (tools / name).symlink_to(source)
    return tools


def _run_make(
    args: list[str], sandbox: Path, path_dirs: list[Path]
) -> subprocess.CompletedProcess[str]:
    directories = {name: sandbox / name for name in ("cwd", "home", "scratch")}
    for directory in directories.values():
        directory.mkdir(exist_ok=True)
    env = {
        "PATH": os.pathsep.join(str(p) for p in [*path_dirs, _basic_tools(sandbox)]),
        "HOME": str(directories["home"]),
        "TMPDIR": str(directories["scratch"]),
        "AGE_RECORD": str(sandbox / "record" / "argv.txt"),
    }
    return subprocess.run(
        [_make(), "-f", str(MAKEFILE), *args],
        cwd=directories["cwd"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _install_stub(sandbox: Path, *, exit_code: int = 0) -> Path:
    bin_dir = sandbox / "bin"
    bin_dir.mkdir()
    (sandbox / "record").mkdir()
    stub = bin_dir / "age-keygen"
    stub.write_text(
        "#!/bin/sh\n"
        'echo "argc=$#" > "$AGE_RECORD"\n'
        'for arg in "$@"; do echo "arg=$arg" >> "$AGE_RECORD"; done\n'
        'echo "# created: stub"\n'
        'echo "# public key: age1stubrecipient"\n'
        f'echo "{STUB_SECRET}"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    return bin_dir


def _files_under(*roots: Path) -> list[Path]:
    return [p for root in roots for p in root.rglob("*") if p.is_file()]


def test_offline_key_target_is_declared_phony() -> None:
    assert TARGET in _phony_targets()


def test_offline_key_target_is_listed_in_help(tmp_path: Path) -> None:
    result = _run_make(["help"], tmp_path, [tmp_path])
    assert result.returncode == 0, result.stderr
    assert f"make {TARGET} " in result.stdout


def test_offline_key_recipe_has_no_output_file_or_file_redirect(tmp_path: Path) -> None:
    result = _run_make(["-n", TARGET], tmp_path, [tmp_path])

    assert result.returncode == 0, result.stderr
    recipe = result.stdout
    keygen_calls = [
        line.strip()
        for line in recipe.splitlines()
        if re.search(r"(^|[;&|{]\s*)age-keygen\b", line.strip())
    ]
    assert keygen_calls == ["age-keygen"]
    redirects = [r.replace(" ", "") for r in re.findall(r">+\s*[^\s;]+", recipe)]
    assert all(r in {">/dev/null", ">&2"} for r in redirects), redirects
    assert "tee" not in recipe.split()
    assert not re.search(r"(^|\s)(-o|--output)\b", recipe)


def test_offline_key_prints_the_identity_to_the_screen_and_writes_nothing(tmp_path: Path) -> None:
    bin_dir = _install_stub(tmp_path)

    result = _run_make([TARGET], tmp_path, [bin_dir])

    assert result.returncode == 0, result.stderr
    assert STUB_SECRET in result.stdout
    assert "age1stubrecipient" in result.stdout
    record = (tmp_path / "record" / "argv.txt").read_text(encoding="utf-8").splitlines()
    assert record == ["argc=0"]
    assert _files_under(tmp_path / "cwd", tmp_path / "home", tmp_path / "scratch") == []
    for path in _files_under(tmp_path / "record"):
        assert STUB_SECRET not in path.read_text(encoding="utf-8")


def test_offline_key_guidance_follows_the_identity(tmp_path: Path) -> None:
    bin_dir = _install_stub(tmp_path)

    result = _run_make([TARGET], tmp_path, [bin_dir])

    out = result.stdout
    assert out.index(STUB_SECRET) < out.index(GUIDANCE)
    assert "vault_openbao_unseal_age_recipients" in out
    assert STUB_SECRET not in result.stderr


def test_offline_key_fails_with_a_hint_when_age_keygen_is_missing(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    result = _run_make([TARGET], tmp_path, [empty])

    assert result.returncode != 0
    assert "age-keygen not found" in result.stderr
    assert "brew install age" in result.stderr
    assert GUIDANCE not in result.stdout
    assert _files_under(tmp_path / "cwd", tmp_path / "home") == []


def test_offline_key_gives_no_guidance_when_age_keygen_fails(tmp_path: Path) -> None:
    bin_dir = _install_stub(tmp_path, exit_code=3)

    result = _run_make([TARGET], tmp_path, [bin_dir])

    assert result.returncode != 0
    assert GUIDANCE not in result.stdout
