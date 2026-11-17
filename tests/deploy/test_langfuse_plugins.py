from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from ansible.plugins.filter.core import FilterModule as CoreFilters
from ansible.plugins.filter.mathstuff import FilterModule as MathFilters
from jinja2 import StrictUndefined, Template
from jinja2.nativetypes import NativeEnvironment

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_DEFAULTS = REPO_ROOT / "roles/devbox/defaults/main/claude.yml"
CLAUDE_SETTINGS = REPO_ROOT / "roles/devbox/files/dot_claude/settings.json.j2"
CLAUDE_HOOKS = CLAUDE_SETTINGS
CLAUDE_BIN = REPO_ROOT / "roles/devbox/files/dot_claude/bin"
VENDORED_HOOK = CLAUDE_BIN / "vendor/langfuse_hook.py"
CLAUDE_TASKS = REPO_ROOT / "roles/devbox/tasks/apply_configs.yml"
CODEX_DEFAULTS = REPO_ROOT / "roles/devbox/defaults/main/codex.yml"
CODEX_CONFIG = REPO_ROOT / "roles/devbox/files/dot_codex/config.toml.j2"
CODEX_LANGFUSE = REPO_ROOT / "roles/devbox/files/dot_codex/langfuse.json.j2"
CODEX_TASKS = REPO_ROOT / "roles/devbox/tasks/install_codex_configs.yml"
CODEX_VENDORED_HOOK = REPO_ROOT / "roles/devbox/files/dot_codex/bin/vendor/langfuse-codex/index.mjs"
PACKAGES = REPO_ROOT / "roles/devbox/defaults/main/packages.yml"
CODEX_NODE = "/opt/homebrew/opt/node@22/bin/node"
CODEX_LANGFUSE_HOOK = f"{CODEX_NODE} ~/.codex/bin/vendor/langfuse-codex/index.mjs"
RETIRED_CODEX_PLUGIN = "tracing@codex-observability-plugin"
RETIRED_CODEX_MARKETPLACE = "codex-observability-plugin"
AGY_BIN = REPO_ROOT / "roles/devbox/files/dot_agy/bin"
AGY_VENDORED_HOOK = AGY_BIN / "vendor/langfuse_hook.py"
AGY_HOOKS = REPO_ROOT / "roles/devbox/files/dot_agy/config/hooks.json.j2"
AGY_FISH = REPO_ROOT / "roles/devbox/files/.config/fish/functions/agy.fish"
ROLE = REPO_ROOT / "roles/devbox"
ROLE_MAIN = ROLE / "tasks/main.yml"
CORE_DEFAULTS = ROLE / "defaults/main/core.yml"
PROFILES = ("personal", "work")

LOOPBACK_URL = "http://127.0.0.1:14318"
CODEX_RENDER = "Install Codex Langfuse runtime configuration"
CODEX_READ_BACK = "Read back the Codex Langfuse runtime configuration"
CODEX_CHECK = "Check the Codex Langfuse runtime configuration traces as the profile user"
JSON_METACHARACTERS = ('a"b\\c', "R&D <tools>", "o'brien@example.com")


def _tasks_by_name(path: Path) -> dict[str, dict[str, object]]:
    tasks = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {task["name"]: task for task in tasks}


def _profile_user_id(profile: str) -> str:
    overlay = yaml.safe_load(
        (REPO_ROOT / "profiles" / f"{profile}.yml").read_text(encoding="utf-8")
    )
    return overlay["devbox_langfuse_user_id"]


def _ansible_environment() -> NativeEnvironment:
    environment = NativeEnvironment(undefined=StrictUndefined, autoescape=False)
    # Ansible's own `default` expects its templar's undefined marker, not Jinja's.
    for name, function in CoreFilters().filters().items():
        environment.filters.setdefault(name, function)
    return environment


def _render_native(template: str, **context: object) -> object:
    return _ansible_environment().from_string(template).render(**context)


def _evaluate(expression: str, **context: object) -> object:
    return _render_native("{{ " + expression + " }}", **context)


def _assert_passes(conditions: list[str], **context: object) -> bool:
    # Ansible's assert stops at the first false condition, so later ones never see
    # a value an earlier one already rejected.
    return all(_evaluate(condition, **context) is True for condition in conditions)


def _user_id_guard() -> dict[str, object]:
    return yaml.safe_load(ROLE_MAIN.read_text(encoding="utf-8"))[0]


def _user_id_guard_passes(**context: object) -> bool:
    return _assert_passes(_user_id_guard()["ansible.builtin.assert"]["that"], **context)


def _render_codex_langfuse(user_id: str, profile: str = "personal") -> str:
    return Template(CODEX_LANGFUSE.read_text(encoding="utf-8"), undefined=StrictUndefined).render(
        devbox_active_profile=profile, devbox_langfuse_user_id=user_id
    )


def _codex_check_passes(langfuse_json: str, user_id: str) -> bool:
    tasks = _tasks_by_name(CODEX_TASKS)
    check = tasks[CODEX_CHECK]
    slurped = {"content": base64.b64encode(langfuse_json.encode()).decode()}
    config = _render_native(
        check["vars"]["devbox_codex_langfuse_config"],
        **{tasks[CODEX_READ_BACK]["register"]: slurped},
    )
    return _assert_passes(
        check["ansible.builtin.assert"]["that"],
        devbox_codex_langfuse_config=config,
        devbox_langfuse_user_id=user_id,
    )


def test_claude_langfuse_hook_is_vendored_rather_than_installed_as_a_plugin() -> None:
    """Upstream ships the hook as `uv run --script` with PEP 723 inline metadata.

    That resolves dependencies at invocation time into an environment under
    UV_CACHE_DIR, which points into /tmp so uv stays writable inside the Bash
    sandbox — where macOS tmp_cleaner erodes it after three days. The hook is
    vendored instead; see roles/devbox/files/dot_claude/bin/vendor/README.md.
    """
    defaults = yaml.safe_load(CLAUDE_DEFAULTS.read_text(encoding="utf-8"))
    settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))

    assert VENDORED_HOOK.is_file()
    assert all(
        entry["name"] != "langfuse-observability"
        for entry in defaults["devbox_claude_plugin_marketplaces"]
    )
    assert all(
        entry["name"] != "langfuse-observability" for entry in defaults["devbox_claude_plugins"]
    )
    assert "langfuse-observability@langfuse-observability" not in settings["enabledPlugins"]
    assert "langfuse-observability" not in settings["extraKnownMarketplaces"]


def test_claude_langfuse_hook_runs_from_the_pinned_bin_venv() -> None:
    hooks = json.loads(CLAUDE_HOOKS.read_text(encoding="utf-8"))
    project = tomllib.loads((CLAUDE_BIN / "pyproject.toml").read_text(encoding="utf-8"))
    lock = (CLAUDE_BIN / "uv.lock").read_text(encoding="utf-8")

    assert any(dep.startswith("langfuse") for dep in project["project"]["dependencies"])
    assert 'name = "langfuse"' in lock

    expected = "~/.claude/bin/.venv/bin/python ~/.claude/bin/langfuse_trace_hook.py"
    for event in ("SessionStart", "Stop", "SessionEnd"):
        commands = [hook["command"] for group in hooks["hooks"][event] for hook in group["hooks"]]
        assert expected in commands


def test_claude_never_runs_the_vendored_hook_without_scrubbing_the_operator_keys() -> None:
    """The personal profile puts real Langfuse keys into Claude's env for the langfuse
    skill; the vendored hook would prefer them over the CC_LANGFUSE_* loopback edge."""
    hooks = json.loads(CLAUDE_HOOKS.read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for groups in hooks["hooks"].values()
        for group in groups
        for hook in group["hooks"]
    ]

    assert (CLAUDE_BIN / "langfuse_trace_hook.py").is_file()
    assert not [command for command in commands if "vendor/langfuse_hook.py" in command]


def test_claude_provisioning_is_idempotent_and_fail_closed() -> None:
    tasks = _tasks_by_name(CLAUDE_TASKS)
    add = tasks["Add Claude Code plugin marketplaces"]
    install = tasks["Install Claude Code plugins (user scope)"]
    verify = tasks["Assert required Claude Code plugins are installed and enabled"]

    assert add["changed_when"] is True
    assert install["changed_when"] is True
    assert "failed_when" not in add
    assert "failed_when" not in install
    assert "not ansible_check_mode" in add["when"]
    assert "not ansible_check_mode" in install["when"]
    assert "--scope" in add["ansible.builtin.command"]["argv"]
    assert "--scope" in install["ansible.builtin.command"]["argv"]
    assert "not ansible_check_mode" in verify["when"]


def test_claude_langfuse_runtime_is_loopback_only_and_media_free() -> None:
    settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    environment = settings["env"]

    assert environment["CC_LANGFUSE_BASE_URL"] == LOOPBACK_URL
    assert environment["CC_LANGFUSE_PUBLIC_KEY"] == "otelbox-local-public"
    assert environment["CC_LANGFUSE_SECRET_KEY"] == environment["CC_LANGFUSE_PUBLIC_KEY"].replace(
        "public", "secret"
    )
    assert environment["CC_LANGFUSE_CAPTURE_IMAGES"] == "false"
    assert environment["LANGFUSE_TRACING_ENVIRONMENT"] == "{{ devbox_active_profile }}"
    assert not environment["CC_LANGFUSE_PUBLIC_KEY"].startswith("pk-lf-")
    assert not environment["CC_LANGFUSE_SECRET_KEY"].startswith("sk-lf-")


def _codex_hooks(event: str) -> list[dict[str, object]]:
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    return [hook for group in config["hooks"][event] for hook in group["hooks"]]


def test_codex_langfuse_hook_is_vendored_rather_than_installed_as_a_plugin() -> None:
    """Upstream no longer commits its built `dist/`, and its hook runs a bare `node`
    from PATH; see roles/devbox/files/dot_codex/bin/vendor/README.md."""
    defaults = yaml.safe_load(CODEX_DEFAULTS.read_text(encoding="utf-8"))
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))

    assert CODEX_VENDORED_HOOK.is_file()
    assert "devbox_codex_plugin_marketplaces" not in defaults
    assert "devbox_codex_plugins" not in defaults
    assert RETIRED_CODEX_PLUGIN not in config["plugins"]
    assert config["features"]["hooks"] is True


def test_codex_langfuse_hook_runs_the_vendored_bundle_under_pinned_node() -> None:
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    packages = yaml.safe_load(PACKAGES.read_text(encoding="utf-8"))
    registered = {
        event: hook
        for event in config["hooks"]
        for hook in _codex_hooks(event)
        if "langfuse-codex" in str(hook["command"])
    }

    assert registered == {
        "Stop": {
            "command": CODEX_LANGFUSE_HOOK,
            "statusMessage": "Uploading Codex trace to Langfuse",
            "timeout": 30,
            "type": "command",
        }
    }
    assert "node@22" in packages["devbox_brew_secondary"]


def test_codex_native_trace_export_is_disabled_without_disabling_logs_or_metrics() -> None:
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    telemetry = config["otel"]

    assert telemetry["trace_exporter"] == "none"
    assert telemetry["exporter"]["otlp-grpc"]["endpoint"] == "http://127.0.0.1:4317"
    assert telemetry["metrics_exporter"]["otlp-grpc"]["endpoint"] == ("http://127.0.0.1:4317")
    assert telemetry["log_user_prompt"] is True


def test_codex_provisioning_installs_no_plugin() -> None:
    tasks = yaml.safe_load(CODEX_TASKS.read_text(encoding="utf-8"))
    runtime = _tasks_by_name(CODEX_TASKS)["Install Codex Langfuse runtime configuration"]
    commands = [task.get("ansible.builtin.command") for task in tasks]
    argvs = [
        command["argv"]
        for command in commands
        if isinstance(command, dict) and isinstance(command.get("argv"), list)
    ]

    assert runtime["ansible.builtin.template"]["mode"] == "0600"
    assert not [argv for argv in argvs if "plugin" in argv and "add" in argv]


@pytest.mark.parametrize(
    ("task_name", "selector", "inventory"),
    [
        (
            "Remove the retired Langfuse tracing plugin",
            RETIRED_CODEX_PLUGIN,
            "Inspect installed Codex plugins for the retired Langfuse tracing plugin",
        ),
        (
            "Remove the retired Langfuse tracing marketplace",
            RETIRED_CODEX_MARKETPLACE,
            "Inspect configured Codex plugin marketplaces for the retired Langfuse marketplace",
        ),
    ],
)
def test_codex_provisioning_removes_the_retired_plugin_after_listing_it(
    task_name: str, selector: str, inventory: str
) -> None:
    """Left installed, the retired plugin's own Stop hook uploads every turn a second time."""
    tasks = _tasks_by_name(CODEX_TASKS)
    names = list(tasks)
    remove = tasks[task_name]
    argv = remove["ansible.builtin.command"]["argv"]
    rendered = [_render_native(token, **remove["vars"]) for token in argv[1:]]

    assert rendered[-3:] == ["remove", selector, "--json"]
    assert "not ansible_check_mode" in remove["when"]
    assert any(f"{tasks[inventory]['register']}.stdout" in when for when in remove["when"])
    assert tasks[inventory]["check_mode"] is False
    assert names.index(inventory) < names.index(task_name)
    assert remove["changed_when"] is True
    assert "CODEX_HOME" in remove["environment"]


@pytest.mark.parametrize(
    ("task_name", "listing", "expected"),
    [
        (
            "Remove the retired Langfuse tracing plugin",
            {"installed": [{"pluginId": RETIRED_CODEX_PLUGIN}], "available": []},
            True,
        ),
        (
            "Remove the retired Langfuse tracing plugin",
            {"installed": [{"pluginId": "browser@openai-bundled"}], "available": []},
            False,
        ),
        (
            "Remove the retired Langfuse tracing marketplace",
            {"marketplaces": [{"name": RETIRED_CODEX_MARKETPLACE, "root": "/x"}]},
            True,
        ),
        ("Remove the retired Langfuse tracing marketplace", {"marketplaces": []}, False),
    ],
)
def test_codex_retired_plugin_removal_runs_exactly_when_the_listing_shows_it(
    task_name: str, listing: dict[str, object], *, expected: bool
) -> None:
    remove = _tasks_by_name(CODEX_TASKS)[task_name]
    (presence,) = [condition for condition in remove["when"] if "from_json" in condition]
    registered = next(
        task["register"]
        for task in _tasks_by_name(CODEX_TASKS).values()
        if "register" in task and f"{task['register']}.stdout" in presence
    )

    assert (
        _evaluate(presence, **remove["vars"], **{registered: {"stdout": json.dumps(listing)}})
        is expected
    )


def test_no_repo_path_bypasses_codex_hook_trust_verification() -> None:
    """Codex has a `--dangerously-bypass-hook-trust` escape hatch. Using it would
    run every discovered hook unverified, including any a third party injected."""
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.split("\0")
    this_file = str(Path(__file__).resolve().relative_to(REPO_ROOT))
    offenders = [
        name
        for name in tracked
        if name
        and name != this_file
        and (REPO_ROOT / name).is_file()
        and "dangerously-bypass-hook-trust"
        in (REPO_ROOT / name).read_bytes().decode(errors="replace")
    ]

    assert offenders == []


def test_codex_hook_trust_is_granted_from_an_explicit_allowlist() -> None:
    tasks = _tasks_by_name(CODEX_TASKS)
    trust = tasks["Grant Codex hook trust for repository-declared hooks"]
    command = trust["ansible.builtin.command"]["argv"]
    argv = trust["vars"]["devbox_codex_hook_trust_argv"]
    names = list(_tasks_by_name(CODEX_TASKS))

    assert "'uv', 'run', '--no-project', '--python', '>=3.12'" in argv
    assert ".venv" not in argv
    assert "scripts/codex-hook-trust.py" in argv
    assert "--plugin" not in argv
    assert "'--check'" in command
    assert "ansible_check_mode" in command
    assert trust["failed_when"] == "devbox_codex_hook_trust.rc != 0"
    assert "CODEX_HOME" in trust["environment"]
    # The reconcile and the plugin removal both change what `hooks/list` reports.
    assert names.index("Grant Codex hook trust for repository-declared hooks") > max(
        names.index("Apply repo-owned Codex settings through ai-config"),
        names.index("Remove the retired Langfuse tracing plugin"),
        names.index("Remove the retired Langfuse tracing marketplace"),
    )


def test_codex_hook_trust_argv_renders_to_the_config_allowlist_alone() -> None:
    """The argv is built by a Jinja expression whose only other failure mode is a
    mid-playbook template error, long after the packages are installed."""
    trust = _tasks_by_name(CODEX_TASKS)["Grant Codex hook trust for repository-declared hooks"]
    environment = NativeEnvironment(undefined=StrictUndefined, autoescape=False)
    environment.filters.update(MathFilters().filters())
    environment.filters.update(CoreFilters().filters())
    context = {
        "devbox_codex_repo_root": "/repo",
        "devbox_codex_home": "/home/user/.codex",
    }

    argv = environment.from_string(trust["vars"]["devbox_codex_hook_trust_argv"]).render(**context)

    assert argv == [
        "uv",
        "run",
        "--no-project",
        "--python",
        ">=3.12",
        "/repo/scripts/codex-hook-trust.py",
        "--repo-root",
        "/repo",
        "--codex-home",
        "/home/user/.codex",
        "--json",
    ]


def test_codex_langfuse_runtime_uses_only_dummy_loopback_credentials() -> None:
    rendered = Template(
        CODEX_LANGFUSE.read_text(encoding="utf-8"),
        undefined=StrictUndefined,
    ).render(devbox_active_profile="personal", devbox_langfuse_user_id="someone@example.com")
    config = json.loads(rendered)

    assert config["enabled"] is True
    assert config["public_key"] == "otelbox-local-public"
    assert config["secret_key"] == config["public_key"].replace("public", "secret")
    assert config["base_url"] == LOOPBACK_URL
    assert config["environment"] == "personal"
    assert config["debug"] is False
    assert config["fail_on_error"] is False
    assert not config["public_key"].startswith("pk-lf-")
    assert not config["secret_key"].startswith("sk-lf-")


def test_codex_langfuse_traces_are_attributed_to_the_profile_owner() -> None:
    """Without `user_id` the plugin falls back to the JWT in `auth.json`, which is
    absent for API-key auth — traces then land unattributed."""
    rendered = Template(
        CODEX_LANGFUSE.read_text(encoding="utf-8"),
        undefined=StrictUndefined,
    ).render(devbox_active_profile="work", devbox_langfuse_user_id="someone@example.com")
    config = json.loads(rendered)
    profiles = {
        name: yaml.safe_load((REPO_ROOT / "profiles" / f"{name}.yml").read_text(encoding="utf-8"))
        for name in ("personal", "work")
    }

    assert config["user_id"] == "someone@example.com"
    assert config["tags"] == ["codex"]
    assert all(profile["devbox_langfuse_user_id"] for profile in profiles.values())


@pytest.mark.parametrize("user_id", JSON_METACHARACTERS)
def test_codex_langfuse_user_survives_json_metacharacters(user_id: str) -> None:
    assert json.loads(_render_codex_langfuse(user_id))["user_id"] == user_id


def test_langfuse_user_guard_runs_first_on_every_tag() -> None:
    guard = _user_id_guard()

    assert "ansible.builtin.assert" in guard
    assert guard["tags"] == ["always"]


@pytest.mark.parametrize("user_id", ["", "   ", "unknown", "Unknown", " UNKNOWN\t"])
def test_langfuse_user_guard_rejects_a_meaningless_user(user_id: str) -> None:
    assert not _user_id_guard_passes(devbox_langfuse_user_id=user_id)


def test_langfuse_user_guard_rejects_an_undefined_user() -> None:
    assert not _user_id_guard_passes()


def test_langfuse_user_guard_rejects_the_role_default() -> None:
    core = yaml.safe_load(CORE_DEFAULTS.read_text(encoding="utf-8"))

    assert not _user_id_guard_passes(devbox_langfuse_user_id=core["devbox_langfuse_user_id"])


@pytest.mark.parametrize("profile", PROFILES)
def test_langfuse_user_guard_accepts_every_profile(profile: str) -> None:
    assert _user_id_guard_passes(devbox_langfuse_user_id=_profile_user_id(profile))


def test_codex_langfuse_configuration_is_read_back_right_after_rendering() -> None:
    tasks = yaml.safe_load(CODEX_TASKS.read_text(encoding="utf-8"))
    names = [task["name"] for task in tasks]
    render, read_back, check = tasks[names.index(CODEX_RENDER) :][:3]

    assert [read_back["name"], check["name"]] == [CODEX_READ_BACK, CODEX_CHECK]
    assert read_back["ansible.builtin.slurp"]["src"] == render["ansible.builtin.template"]["dest"]
    assert read_back["register"] in check["vars"]["devbox_codex_langfuse_config"]
    assert read_back["when"] == check["when"] == "not ansible_check_mode"
    assert render["tags"] == read_back["tags"] == check["tags"]


@pytest.mark.parametrize("profile", PROFILES)
def test_codex_langfuse_check_accepts_every_profile_render(profile: str) -> None:
    user_id = _profile_user_id(profile)

    assert _codex_check_passes(_render_codex_langfuse(user_id, profile), user_id)


@pytest.mark.parametrize("user_id", JSON_METACHARACTERS)
def test_codex_langfuse_check_accepts_json_metacharacters(user_id: str) -> None:
    assert _codex_check_passes(_render_codex_langfuse(user_id), user_id)


@pytest.mark.parametrize(
    "config",
    [
        {"enabled": False, "user_id": "someone@example.com"},
        {"enabled": "true", "user_id": "someone@example.com"},
        {"user_id": "someone@example.com"},
        {"enabled": True, "user_id": "unknown"},
        {"enabled": True},
    ],
)
def test_codex_langfuse_check_rejects_a_configuration_that_misattributes(
    config: dict[str, object],
) -> None:
    assert not _codex_check_passes(json.dumps(config), "someone@example.com")


@pytest.mark.integration
def test_codex_langfuse_render_and_check_pass_under_ansible(tmp_path: Path) -> None:
    tasks = _tasks_by_name(CODEX_TASKS)
    user_id = JSON_METACHARACTERS[0]
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
                        "devbox_codex_home": str(tmp_path / "codex"),
                        "devbox_codex_role_path": str(ROLE),
                        "devbox_active_profile": "personal",
                        "devbox_langfuse_user_id": user_id,
                    },
                    "tasks": [
                        {
                            "name": "Create the Codex home",
                            "ansible.builtin.file": {
                                "path": str(tmp_path / "codex"),
                                "state": "directory",
                            },
                        },
                        *(tasks[name] for name in (CODEX_RENDER, CODEX_READ_BACK, CODEX_CHECK)),
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "ANSIBLE_LOCAL_TEMP": str(tmp_path / "ansible-local"),
            "ANSIBLE_REMOTE_TEMP": str(tmp_path / "ansible-remote"),
            "ANSIBLE_HOME": str(tmp_path / "ansible-home"),
            "ANSIBLE_NOCOLOR": "1",
        }
    )

    result = subprocess.run(
        [str(Path(sys.executable).parent / "ansible-playbook"), "-i", "localhost,", str(playbook)],
        capture_output=True,
        text=True,
        timeout=180,
        env=environment,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    rendered = json.loads((tmp_path / "codex/langfuse.json").read_text(encoding="utf-8"))
    assert rendered["user_id"] == user_id


def test_repo_owned_langfuse_configuration_has_no_remote_ingestion_url() -> None:
    sources = (
        CLAUDE_SETTINGS.read_text(encoding="utf-8"),
        CODEX_LANGFUSE.read_text(encoding="utf-8"),
        AGY_FISH.read_text(encoding="utf-8"),
    )

    assert all("cloud.langfuse.com" not in source for source in sources)
    assert all("/api/public/otel" not in source for source in sources)


def test_all_engines_stamp_otelbox_telemetry_class_llm() -> None:
    """Every engine must tag its OTLP telemetry with otelbox.telemetry.class=llm
    so the gateway can route LLM traces to Langfuse."""
    claude_settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    assert claude_settings["env"]["OTEL_RESOURCE_ATTRIBUTES"] == "otelbox.telemetry.class=llm"

    agy_fish = AGY_FISH.read_text(encoding="utf-8")
    assert "OTEL_RESOURCE_ATTRIBUTES=otelbox.telemetry.class=llm" in agy_fish


def test_codex_hooks_run_from_a_pinned_interpreter_rather_than_an_ambient_one() -> None:
    """`/usr/bin/env python3` or a bare `node` hands the hook to whatever PATH resolves first."""
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    project = tomllib.loads(
        (REPO_ROOT / "roles/devbox/files/dot_codex/bin/pyproject.toml").read_text(encoding="utf-8")
    )

    assert project["project"]["requires-python"] == ">=3.11"
    assert (REPO_ROOT / "roles/devbox/files/dot_codex/bin/uv.lock").is_file()

    commands = [
        hook["command"]
        for groups in config["hooks"].values()
        for group in groups
        for hook in group["hooks"]
    ]
    assert commands
    assert all(
        command.startswith(("~/.codex/bin/.venv/bin/python ", f"{CODEX_NODE} "))
        for command in commands
    )


def test_codex_bin_sync_preserves_the_venv_it_bootstraps() -> None:
    tasks = _tasks_by_name(CODEX_TASKS)
    sync = tasks["Sync Codex bin directory"]
    bootstrap = tasks["Bootstrap Codex hooks venv via uv sync"]

    assert "--exclude=.venv" in sync["ansible.posix.synchronize"]["rsync_opts"]
    assert sync["ansible.posix.synchronize"]["delete"] is True
    assert "sync --frozen --no-dev" in bootstrap["ansible.builtin.command"]["cmd"]
    assert bootstrap["ansible.builtin.command"]["chdir"].endswith("/bin")


# ── Antigravity CLI (agy) ──────────────────────────────────────────────


def test_agy_langfuse_hook_is_a_symlink_to_the_claude_vendored_copy() -> None:
    """Agy reuses the Claude langfuse hook via a repo-internal symlink."""
    assert AGY_VENDORED_HOOK.is_symlink()
    assert AGY_VENDORED_HOOK.resolve() == VENDORED_HOOK.resolve()


def test_agy_langfuse_hook_has_the_durable_exporter_it_imports_beside_it() -> None:
    exporter = AGY_VENDORED_HOOK.parent / "durable_otel_exporter.py"
    assert exporter.is_symlink()
    assert exporter.resolve() == (VENDORED_HOOK.parent / "durable_otel_exporter.py").resolve()


def test_agy_langfuse_hook_runs_from_the_pinned_bin_venv() -> None:
    rendered = Template(
        AGY_HOOKS.read_text(encoding="utf-8"),
        undefined=StrictUndefined,
    ).render(lookup=lambda _plugin, _key: "/home/testuser")
    hooks = json.loads(rendered)

    project = tomllib.loads((AGY_BIN / "pyproject.toml").read_text(encoding="utf-8"))
    lock = (AGY_BIN / "uv.lock").read_text(encoding="utf-8")

    assert any(dep.startswith("langfuse") for dep in project["project"]["dependencies"])
    assert 'name = "langfuse"' in lock

    expected_suffix = "bin/.venv/bin/python"
    expected_script = "bin/vendor/langfuse_hook.py"
    hook_entry = hooks["langfuse_hook"]
    # `Stop` is a flat event: a list of handler objects, no matcher wrapper.
    (handler,) = hook_entry["Stop"]
    assert expected_suffix in handler["command"]
    assert expected_script in handler["command"]
    # Held off: agy's transcript is a log of typed steps with no chat rows, so the
    # Claude hook finds no turn in it (see dot_agy/bin/vendor/README.md).
    assert hook_entry["enabled"] is False


def test_agy_langfuse_env_vars_are_loopback_only() -> None:
    fish = AGY_FISH.read_text(encoding="utf-8")

    assert "CC_LANGFUSE_BASE_URL=http://127.0.0.1:14318" in fish
    assert "CC_LANGFUSE_PUBLIC_KEY=otelbox-local-public" in fish
    assert "CC_LANGFUSE_SECRET_KEY=otelbox-local-secret" in fish
    assert "CC_LANGFUSE_CAPTURE_IMAGES=false" in fish
    assert "CC_LANGFUSE_STATE_DIR=" in fish
    assert ".gemini/antigravity-cli/state" in fish
    assert "pk-lf-" not in fish
    assert "sk-lf-" not in fish


def test_agy_langfuse_state_dir_is_isolated_from_claude() -> None:
    """Agy must not share state with Claude's ~/.claude/state/."""
    fish = AGY_FISH.read_text(encoding="utf-8")
    assert "CC_LANGFUSE_STATE_DIR=" in fish
    assert ".claude/state" not in fish.split("CC_LANGFUSE_STATE_DIR=")[1].split()[0]
