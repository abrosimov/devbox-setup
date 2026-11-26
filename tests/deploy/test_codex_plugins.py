from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import cast

import pytest
import yaml
from ai_config import (
    ConfigurationFormat,
    build_repository_document,
    load_template_variables,
    snapshot_mapping,
)
from ansible.plugins.filter.core import FilterModule as CoreFilters
from jinja2 import StrictUndefined
from jinja2.nativetypes import NativeEnvironment

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = REPO_ROOT / "roles/devbox"
CODEX_DEFAULTS = ROLE / "defaults/main/codex.yml"
CODEX_CONFIG = ROLE / "files/dot_codex/config.toml.j2"
CODEX_MANIFEST = ROLE / "files/dot_codex/config.ai-config.json"
CODEX_TASKS = ROLE / "tasks/install_codex_configs.yml"
PROFILES = ("personal", "work")

CLI = "/opt/codex/bin/codex"
FIRST_PLUGIN_TASK = "Inspect installed Codex plugins for the retired Langfuse tracing plugin"
LAST_PLUGIN_TASK = "Assert repository-declared Codex plugins are installed and enabled"
ADD_MARKETPLACES = "Add Codex plugin marketplaces"
REFRESH_MARKETPLACE = "Refresh the marketplace of each Codex plugin not installed yet"
INSTALL_PLUGINS = "Install Codex plugins"
INSPECT_AFTER = "Inspect Codex plugins after installation"
ASSERT_INSTALLED = LAST_PLUGIN_TASK

type Task = dict[str, object]
type Declared = dict[str, str]

TEMPORAL = {"name": "temporal", "marketplace": "temporal-marketplace"}
TEMPORAL_ID = "temporal@temporal-marketplace"
TEMPORAL_SOURCE = "temporalio/codex-temporal-plugin"


def _load_tasks() -> list[Task]:
    loaded: object = yaml.safe_load(CODEX_TASKS.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    return cast("list[Task]", loaded)


def _task(name: str) -> Task:
    return next(task for task in _load_tasks() if task.get("name") == name)


def _defaults() -> dict[str, object]:
    loaded: object = yaml.safe_load(CODEX_DEFAULTS.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return cast("dict[str, object]", loaded)


def _declared(key: str) -> list[Declared]:
    return cast("list[Declared]", _defaults()[key])


def _environment() -> NativeEnvironment:
    environment = NativeEnvironment(undefined=StrictUndefined, autoescape=False)
    for name, function in CoreFilters().filters().items():
        environment.filters.setdefault(name, function)
    return environment


def _render(template: str, **context: object) -> object:
    return _environment().from_string(template).render(**context)


def _conditions(task: Task) -> list[str]:
    when = task["when"]
    assert isinstance(when, list)
    return cast("list[str]", when)


def _runs(
    name: str,
    item: Declared,
    *,
    check_mode: bool = False,
    cli_rc: int = 0,
    plugins: dict[str, object] | None = None,
    marketplaces: dict[str, object] | None = None,
) -> bool:
    context: dict[str, object] = {
        "item": item,
        "ansible_check_mode": check_mode,
        "devbox_codex_cli_path": {"rc": cli_rc, "stdout": CLI},
    }
    if plugins is not None:
        context["devbox_codex_plugins_before"] = {"stdout": json.dumps(plugins)}
    if marketplaces is not None:
        context["devbox_codex_marketplaces_before"] = {"stdout": json.dumps(marketplaces)}
    # Ansible evaluates a `when` list left to right and stops at the first false entry,
    # so a registered variable a guard protects is never touched when it is false.
    return all(
        _render("{{ " + condition + " }}", **context) is True
        for condition in _conditions(_task(name))
    )


def _plugin_listing(*entries: tuple[str, bool]) -> dict[str, object]:
    return {
        "installed": [
            {"pluginId": plugin_id, "enabled": enabled} for plugin_id, enabled in entries
        ],
        "available": [],
    }


def _marketplace_listing(*names: str) -> dict[str, object]:
    return {"marketplaces": [{"name": name} for name in names]}


def _argv(name: str, item: Declared) -> list[object]:
    command = cast("dict[str, list[str]]", _task(name)["ansible.builtin.command"])
    return [
        _render(token, item=item, devbox_codex_cli_path={"stdout": CLI})
        for token in command["argv"]
    ]


class TestDeclaredCodexPlugins:
    def test_every_plugin_comes_from_a_declared_marketplace(self) -> None:
        marketplaces = {entry["name"] for entry in _declared("devbox_codex_plugin_marketplaces")}

        assert marketplaces
        assert {
            plugin["marketplace"] for plugin in _declared("devbox_codex_plugins")
        } <= marketplaces

    def test_marketplaces_have_a_unique_name_and_a_source(self) -> None:
        entries = _declared("devbox_codex_plugin_marketplaces")
        names = [entry["name"] for entry in entries]

        assert len(names) == len(set(names))
        assert all(set(entry) == {"name", "source"} for entry in entries)
        assert all(entry["name"].strip() and entry["source"].strip() for entry in entries)

    def test_plugins_are_unique_and_name_their_marketplace(self) -> None:
        plugins = _declared("devbox_codex_plugins")
        identifiers = [f"{plugin['name']}@{plugin['marketplace']}" for plugin in plugins]

        assert len(identifiers) == len(set(identifiers))
        assert all(set(plugin) == {"name", "marketplace"} for plugin in plugins)
        assert all("@" not in plugin["name"] and plugin["name"].strip() for plugin in plugins)

    def test_temporal_is_installed_from_its_git_marketplace(self) -> None:
        assert {"name": "temporal-marketplace", "source": TEMPORAL_SOURCE} in _declared(
            "devbox_codex_plugin_marketplaces"
        )
        assert TEMPORAL in _declared("devbox_codex_plugins")


@pytest.mark.parametrize("profile", PROFILES)
class TestRenderedCodexConfig:
    @staticmethod
    def _rendered_plugins(profile: str) -> dict[str, object]:
        variables = load_template_variables(REPO_ROOT, profile)
        document = build_repository_document(
            CODEX_CONFIG.read_bytes(), ConfigurationFormat.TOML, variables
        )
        plugins = snapshot_mapping(document.rendered)["plugins"]
        assert isinstance(plugins, dict)
        return cast("dict[str, object]", plugins)

    @staticmethod
    def _declared_for(profile: str) -> list[Declared]:
        variables = load_template_variables(REPO_ROOT, profile)
        return cast("list[Declared]", variables["devbox_codex_plugins"])

    def test_every_declared_plugin_is_enabled(self, profile: str) -> None:
        plugins = self._rendered_plugins(profile)
        declared = self._declared_for(profile)

        assert declared
        for plugin in declared:
            identifier = f"{plugin['name']}@{plugin['marketplace']}"
            assert identifier in plugins
            assert cast("dict[str, object]", plugins[identifier])["enabled"] is True

    def test_no_plugin_of_a_declared_marketplace_is_left_to_install_by_hand(
        self, profile: str
    ) -> None:
        variables = load_template_variables(REPO_ROOT, profile)
        marketplaces = {
            entry["name"]
            for entry in cast("list[Declared]", variables["devbox_codex_plugin_marketplaces"])
        }
        declared = {
            f"{plugin['name']}@{plugin['marketplace']}" for plugin in self._declared_for(profile)
        }
        from_declared_marketplaces = {
            identifier
            for identifier in self._rendered_plugins(profile)
            if identifier.rpartition("@")[2] in marketplaces
        }

        assert from_declared_marketplaces == declared


def test_codex_reconcile_owns_the_plugins_table_that_plugin_add_writes() -> None:
    manifest = json.loads(CODEX_MANIFEST.read_text(encoding="utf-8"))
    rendered = tomllib.loads(
        CODEX_CONFIG.read_text(encoding="utf-8").replace("{{", "").replace("}}", "")
    )

    assert {"path": "plugins", "scope": "shared"} in manifest["fields"]
    assert rendered["plugins"][TEMPORAL_ID] == {"enabled": True}


class TestCodexPluginTasks:
    def test_the_installation_follows_the_retired_plugin_removal(self) -> None:
        names = [str(task["name"]) for task in _load_tasks()]
        sequence = [
            "Remove the retired Langfuse tracing plugin",
            "Remove the retired Langfuse tracing marketplace",
            ADD_MARKETPLACES,
            REFRESH_MARKETPLACE,
            INSTALL_PLUGINS,
            INSPECT_AFTER,
            ASSERT_INSTALLED,
            "Grant Codex hook trust for repository-declared hooks",
        ]
        positions = [names.index(name) for name in sequence]

        assert positions == sorted(positions)
        assert names.index("Find Codex CLI path") < names.index(FIRST_PLUGIN_TASK)

    @pytest.mark.parametrize("name", [ADD_MARKETPLACES, REFRESH_MARKETPLACE, INSTALL_PLUGINS])
    def test_a_mutating_step_reports_changed_fails_closed_and_targets_the_codex_home(
        self, name: str
    ) -> None:
        task = _task(name)

        assert task["changed_when"] is True
        assert "failed_when" not in task
        assert "ignore_errors" not in task
        assert task["environment"] == {"CODEX_HOME": "{{ devbox_codex_home }}"}
        assert set(cast("list[str]", task["tags"])) == {"configs", "ai", "codex"}

    def test_the_inspection_after_installation_runs_in_check_mode_and_changes_nothing(
        self,
    ) -> None:
        task = _task(INSPECT_AFTER)

        assert task["check_mode"] is False
        assert task["changed_when"] is False
        assert task["when"] == "devbox_codex_cli_path.rc == 0"
        assert task["register"] == "devbox_codex_plugins_after"
        assert task["environment"] == {"CODEX_HOME": "{{ devbox_codex_home }}"}
        assert _argv(INSPECT_AFTER, TEMPORAL) == [CLI, "plugin", "list", "--json"]

    def test_the_loops_iterate_the_declared_lists(self) -> None:
        marketplaces = _declared("devbox_codex_plugin_marketplaces")
        plugins = _declared("devbox_codex_plugins")
        context = {
            "devbox_codex_plugin_marketplaces": marketplaces,
            "devbox_codex_plugins": plugins,
        }

        assert _render(str(_task(ADD_MARKETPLACES)["loop"]), **context) == marketplaces
        assert _render(str(_task(REFRESH_MARKETPLACE)["loop"]), **context) == plugins
        assert _render(str(_task(INSTALL_PLUGINS)["loop"]), **context) == plugins
        assert _render(str(_task(ASSERT_INSTALLED)["loop"]), **context) == plugins

    def test_the_commands_carry_the_declared_names_and_sources(self) -> None:
        marketplace = {"name": "temporal-marketplace", "source": TEMPORAL_SOURCE}

        assert _argv(ADD_MARKETPLACES, marketplace) == [
            CLI,
            "plugin",
            "marketplace",
            "add",
            TEMPORAL_SOURCE,
            "--json",
        ]
        assert _argv(REFRESH_MARKETPLACE, TEMPORAL) == [
            CLI,
            "plugin",
            "marketplace",
            "upgrade",
            "temporal-marketplace",
        ]
        assert _argv(INSTALL_PLUGINS, TEMPORAL) == [CLI, "plugin", "add", TEMPORAL_ID, "--json"]

    @pytest.mark.parametrize(
        ("listing", "expected"),
        [
            pytest.param(_marketplace_listing(), True, id="no-marketplace-at-all"),
            pytest.param(_marketplace_listing("temporal-marketplace"), False, id="present"),
            pytest.param(
                _marketplace_listing("openai-curated", "temporal-marketplace"),
                False,
                id="present-among-others",
            ),
            pytest.param(
                _marketplace_listing("temporal-marketplace-old"),
                True,
                id="only-a-longer-name-is-present",
            ),
            pytest.param(_marketplace_listing("Temporal-Marketplace"), True, id="name-is-exact"),
            pytest.param(_marketplace_listing("temporal"), True, id="a-prefix-is-not-the-name"),
        ],
    )
    def test_a_marketplace_is_added_exactly_when_its_name_is_not_listed(
        self, listing: dict[str, object], *, expected: bool
    ) -> None:
        marketplace = {"name": "temporal-marketplace", "source": TEMPORAL_SOURCE}

        assert _runs(ADD_MARKETPLACES, marketplace, marketplaces=listing) is expected

    @pytest.mark.parametrize("name", [REFRESH_MARKETPLACE, INSTALL_PLUGINS])
    @pytest.mark.parametrize(
        ("listing", "expected"),
        [
            pytest.param(_plugin_listing(), True, id="nothing-installed"),
            pytest.param(_plugin_listing((TEMPORAL_ID, True)), False, id="installed"),
            pytest.param(
                _plugin_listing((TEMPORAL_ID, False)),
                False,
                id="installed-but-disabled-is-left-to-the-reconcile",
            ),
            pytest.param(
                _plugin_listing(("browser@openai-bundled", True)), True, id="only-others-installed"
            ),
            pytest.param(
                _plugin_listing(("temporal@some-other-marketplace", True)),
                True,
                id="same-name-from-another-marketplace",
            ),
            pytest.param(
                _plugin_listing(("other@temporal-marketplace", True)),
                True,
                id="another-plugin-of-the-same-marketplace",
            ),
            pytest.param(
                _plugin_listing(("temporal@temporal-marketplace-old", True)),
                True,
                id="marketplace-has-a-longer-name",
            ),
        ],
    )
    def test_a_plugin_is_installed_exactly_when_its_id_is_not_listed(
        self, name: str, listing: dict[str, object], *, expected: bool
    ) -> None:
        assert _runs(name, TEMPORAL, plugins=listing) is expected

    def test_each_listed_plugin_is_judged_on_its_own(self) -> None:
        present = {"name": "alpha", "marketplace": "m"}
        missing = {"name": "beta", "marketplace": "m"}
        listing = _plugin_listing(("alpha@m", True))

        assert _runs(INSTALL_PLUGINS, present, plugins=listing) is False
        assert _runs(INSTALL_PLUGINS, missing, plugins=listing) is True
        assert _runs(REFRESH_MARKETPLACE, present, plugins=listing) is False
        assert _runs(REFRESH_MARKETPLACE, missing, plugins=listing) is True

    @pytest.mark.parametrize("name", [ADD_MARKETPLACES, REFRESH_MARKETPLACE, INSTALL_PLUGINS])
    def test_nothing_is_changed_in_check_mode(self, name: str) -> None:
        item = (
            {"name": "temporal-marketplace", "source": TEMPORAL_SOURCE}
            if name == ADD_MARKETPLACES
            else TEMPORAL
        )
        missing = {
            "plugins": _plugin_listing(),
            "marketplaces": _marketplace_listing(),
        }

        assert _runs(name, item, **missing) is True
        assert _runs(name, item, check_mode=True, **missing) is False

    @pytest.mark.parametrize(
        "name", [ADD_MARKETPLACES, REFRESH_MARKETPLACE, INSTALL_PLUGINS, ASSERT_INSTALLED]
    )
    def test_nothing_runs_without_a_codex_cli(self, name: str) -> None:
        item = (
            {"name": "temporal-marketplace", "source": TEMPORAL_SOURCE}
            if name == ADD_MARKETPLACES
            else TEMPORAL
        )

        assert _runs(name, item, cli_rc=1) is False

    def test_the_inspection_after_installation_needs_a_codex_cli(self) -> None:
        condition = str(_task(INSPECT_AFTER)["when"])

        assert _render("{{ " + condition + " }}", devbox_codex_cli_path={"rc": 0}) is True
        assert _render("{{ " + condition + " }}", devbox_codex_cli_path={"rc": 127}) is False


class TestCodexPluginAssertion:
    @staticmethod
    def _holds(plugin: Declared, listing: dict[str, object]) -> bool:
        task = _task(ASSERT_INSTALLED)
        variables = cast("dict[str, str]", task["vars"])
        enabled = _render(
            variables["devbox_codex_enabled_plugin_ids"],
            devbox_codex_plugins_after={"stdout": json.dumps(listing)},
        )
        conditions = cast("dict[str, list[str]]", task["ansible.builtin.assert"])["that"]
        return all(
            _render("{{ " + condition + " }}", item=plugin, devbox_codex_enabled_plugin_ids=enabled)
            is True
            for condition in conditions
        )

    def test_passes_when_the_plugin_is_installed_and_enabled(self) -> None:
        assert self._holds(TEMPORAL, _plugin_listing((TEMPORAL_ID, True)))

    def test_passes_among_other_plugins(self) -> None:
        listing = _plugin_listing(
            ("browser@openai-bundled", True), (TEMPORAL_ID, True), ("pdf@openai", False)
        )

        assert self._holds(TEMPORAL, listing)

    @pytest.mark.parametrize(
        "listing",
        [
            pytest.param(_plugin_listing(), id="absent-from-an-empty-listing"),
            pytest.param(_plugin_listing(("browser@openai-bundled", True)), id="absent"),
            pytest.param(_plugin_listing((TEMPORAL_ID, False)), id="installed-but-disabled"),
            pytest.param(
                _plugin_listing(("temporal@some-other-marketplace", True)), id="other-marketplace"
            ),
            pytest.param(_plugin_listing(("other@temporal-marketplace", True)), id="other-plugin"),
            pytest.param(
                _plugin_listing((TEMPORAL_ID, False), ("browser@openai-bundled", True)),
                id="disabled-next-to-an-enabled-plugin",
            ),
            pytest.param(
                {"installed": [], "available": [{"pluginId": TEMPORAL_ID}]}, id="only-available"
            ),
        ],
    )
    def test_fails_when_the_plugin_is_not_installed_and_enabled(
        self, listing: dict[str, object]
    ) -> None:
        assert not self._holds(TEMPORAL, listing)

    def test_the_failure_names_the_plugin(self) -> None:
        task = _task(ASSERT_INSTALLED)
        message = cast("dict[str, str]", task["ansible.builtin.assert"])["fail_msg"]

        assert _render(message, item=TEMPORAL) == (
            f"Codex plugin {TEMPORAL_ID} is not installed and enabled"
        )

    def test_reads_the_listing_taken_after_the_installation(self) -> None:
        task = _task(ASSERT_INSTALLED)
        variables = cast("dict[str, str]", task["vars"])

        assert "devbox_codex_plugins_after.stdout" in variables["devbox_codex_enabled_plugin_ids"]
        assert "devbox_codex_plugins_before" not in json.dumps(task)
        assert _task(INSPECT_AFTER)["register"] == "devbox_codex_plugins_after"


FAKE_CODEX = """#!{python}
import json
import os
import sys

SOURCES = {sources}
home = os.environ["CODEX_HOME"]
args = sys.argv[1:]

with open(os.path.join(home, "calls.log"), "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\\n")

state_path = os.path.join(home, "state.json")
with open(state_path, encoding="utf-8") as handle:
    state = json.load(handle)


def save():
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


if args[:2] == ["plugin", "list"]:
    print(json.dumps({{"installed": state["installed"], "available": []}}))
elif args == ["plugin", "marketplace", "list", "--json"]:
    print(json.dumps({{"marketplaces": [{{"name": name}} for name in state["marketplaces"]]}}))
elif args[:3] == ["plugin", "marketplace", "add"]:
    if os.environ.get("FAKE_CODEX_REFUSE_MARKETPLACE"):
        sys.exit("marketplace add refused")
    name = SOURCES[args[3]]
    if name not in state["marketplaces"]:
        state["marketplaces"].append(name)
    save()
    print(json.dumps({{"name": name}}))
elif args[:3] == ["plugin", "marketplace", "upgrade"]:
    if args[3] not in state["marketplaces"]:
        sys.exit("unknown marketplace " + args[3])
elif args[:2] == ["plugin", "add"]:
    if args[2].rpartition("@")[2] not in state["marketplaces"]:
        sys.exit("unknown marketplace for " + args[2])
    enabled = os.environ.get("FAKE_CODEX_ENABLE", "1") == "1"
    state["installed"].append({{"pluginId": args[2], "enabled": enabled}})
    save()
    print(json.dumps({{"pluginId": args[2]}}))
elif args[:2] == ["plugin", "remove"] or args[:3] == ["plugin", "marketplace", "remove"]:
    pass
else:
    sys.exit("unexpected arguments: " + " ".join(args))
"""

READ_ONLY_CALLS = ("plugin list", "plugin marketplace list")


class CodexRun:
    def __init__(self, root: Path) -> None:
        self.home = root / "codex"
        self.bin = root / "bin"
        self.root = root
        self.home.mkdir()
        self.bin.mkdir()
        sources = {
            entry["source"]: entry["name"]
            for entry in _declared("devbox_codex_plugin_marketplaces")
        }
        cli = self.bin / "codex"
        cli.write_text(
            FAKE_CODEX.format(python=sys.executable, sources=json.dumps(sources)), encoding="utf-8"
        )
        cli.chmod(0o755)
        self.seed(marketplaces=[], installed=[])

    def seed(self, *, marketplaces: list[str], installed: list[dict[str, object]]) -> None:
        (self.home / "state.json").write_text(
            json.dumps({"marketplaces": marketplaces, "installed": installed}), encoding="utf-8"
        )

    @property
    def mutations(self) -> list[str]:
        log = self.home / "calls.log"
        if not log.exists():
            return []
        return [
            line
            for line in log.read_text(encoding="utf-8").splitlines()
            if not line.startswith(READ_ONLY_CALLS)
        ]

    @property
    def installed(self) -> list[dict[str, object]]:
        state = json.loads((self.home / "state.json").read_text(encoding="utf-8"))
        return cast("list[dict[str, object]]", state["installed"])

    def play(
        self, *, check: bool = False, extra_env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        tasks = _load_tasks()
        names = [str(task["name"]) for task in tasks]
        selected = tasks[names.index(FIRST_PLUGIN_TASK) : names.index(LAST_PLUGIN_TASK) + 1]
        playbook = self.root / "playbook.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            "ansible_python_interpreter": sys.executable,
                            "devbox_codex_home": str(self.home),
                            "devbox_codex_plugin_marketplaces": _declared(
                                "devbox_codex_plugin_marketplaces"
                            ),
                            "devbox_codex_plugins": _declared("devbox_codex_plugins"),
                        },
                        "tasks": [
                            {
                                "name": "Locate the Codex CLI",
                                "ansible.builtin.set_fact": {
                                    "devbox_codex_cli_path": {
                                        "rc": 0,
                                        "stdout": str(self.bin / "codex"),
                                    }
                                },
                            },
                            *selected,
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment.update(
            {
                "ANSIBLE_LOCAL_TEMP": str(self.root / "ansible-local"),
                "ANSIBLE_REMOTE_TEMP": str(self.root / "ansible-remote"),
                "ANSIBLE_HOME": str(self.root / "ansible-home"),
                "ANSIBLE_NOCOLOR": "1",
                **(extra_env or {}),
            }
        )
        return subprocess.run(
            [
                str(Path(sys.executable).parent / "ansible-playbook"),
                "-i",
                "localhost,",
                *(["--check"] if check else []),
                str(playbook),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            env=environment,
            cwd=self.root,
            check=False,
        )


@pytest.mark.integration
class TestCodexPluginsUnderAnsible:
    @pytest.fixture
    def run(self, tmp_path: Path) -> CodexRun:
        return CodexRun(tmp_path)

    def test_a_fresh_machine_gets_the_marketplace_then_the_plugin(self, run: CodexRun) -> None:
        result = run.play()

        assert result.returncode == 0, result.stdout + result.stderr
        assert run.mutations == [
            f"plugin marketplace add {TEMPORAL_SOURCE} --json",
            "plugin marketplace upgrade temporal-marketplace",
            f"plugin add {TEMPORAL_ID} --json",
        ]
        assert run.installed == [{"pluginId": TEMPORAL_ID, "enabled": True}]

    def test_a_second_run_changes_nothing(self, run: CodexRun) -> None:
        assert run.play().returncode == 0
        calls_after_first = run.mutations

        second = run.play()

        assert second.returncode == 0, second.stdout + second.stderr
        assert run.mutations == calls_after_first
        assert "changed=0" in second.stdout

    def test_an_added_marketplace_without_the_plugin_installs_only_the_plugin(
        self, run: CodexRun
    ) -> None:
        run.seed(marketplaces=["temporal-marketplace"], installed=[])

        result = run.play()

        assert result.returncode == 0, result.stdout + result.stderr
        assert run.mutations == [
            "plugin marketplace upgrade temporal-marketplace",
            f"plugin add {TEMPORAL_ID} --json",
        ]

    def test_an_installed_plugin_is_left_alone(self, run: CodexRun) -> None:
        run.seed(
            marketplaces=["temporal-marketplace"],
            installed=[{"pluginId": TEMPORAL_ID, "enabled": True}],
        )

        result = run.play()

        assert result.returncode == 0, result.stdout + result.stderr
        assert run.mutations == []

    def test_a_check_run_neither_adds_nor_installs_nor_asserts(self, run: CodexRun) -> None:
        result = run.play(check=True)

        assert result.returncode == 0, result.stdout + result.stderr
        assert run.mutations == []
        assert run.installed == []

    def test_a_plugin_that_installs_disabled_fails_the_run(self, run: CodexRun) -> None:
        result = run.play(extra_env={"FAKE_CODEX_ENABLE": "0"})

        assert result.returncode != 0
        assert f"Codex plugin {TEMPORAL_ID} is not installed and enabled" in (
            result.stdout + result.stderr
        )

    def test_a_marketplace_the_cli_refuses_fails_the_run_before_any_install(
        self, run: CodexRun
    ) -> None:
        result = run.play(extra_env={"FAKE_CODEX_REFUSE_MARKETPLACE": "1"})

        assert result.returncode != 0
        assert run.installed == []
