"""Every hook command this repository declares names an executable deployment creates.

No engine checks this. Codex `hooks/list` reports a hook as discovered, trusted
and enabled without ever resolving its command; Claude Code and agy dispatch the
command and discard the resulting ENOENT. So a hook whose interpreter does not
exist is invisible to every other suite here and dead on the machine.

The interpreters are venvs — `~/.claude/bin/.venv/bin/python` and its Codex and
agy counterparts — materialised by a `uv sync` task that is separate from the
task deploying the configuration naming them. This module is the static half of
the check: the declared executable must be the venv that a `uv sync` task in
this repository actually builds, or a file the same directory ships. The live
half (`tests/live/test_live_interpreters.py`) runs that `uv sync` and confirms
the path it produces is the path declared here.
"""

from __future__ import annotations

import json
import shlex
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
import yaml
from jinja2 import Environment, StrictUndefined

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
CLAUDE_SETTINGS: Final = REPO_ROOT / "roles/devbox/files/dot_claude/settings.json.j2"
CODEX_CONFIG: Final = REPO_ROOT / "roles/devbox/files/dot_codex/config.toml.j2"
AGY_HOOKS: Final = REPO_ROOT / "roles/devbox/files/dot_agy/config/hooks.json.j2"
TASK_FILES: Final = (
    REPO_ROOT / "roles/devbox/tasks/install_configs.yml",
    REPO_ROOT / "roles/devbox/tasks/install_codex_configs.yml",
)

# The marker each config spells the deploy root as, normalised to one token so a
# declared command and a playbook `chdir` can be compared.
HOME: Final = "<home>"
_VENV_INTERPRETER: Final = ".venv/bin/python"
_UV_SYNC: Final = "sync --frozen --no-dev"
# Ansible expressions that resolve to the deploy root, longest first so the
# Codex one is not half-replaced by the shorter dotfiles-root match.
_ROOT_EXPRESSIONS: Final = (
    ("{{ devbox_codex_home }}", f"{HOME}/.codex"),
    ("{{ devbox_paths.dotfiles_root_dir }}", HOME),
)


@dataclass(frozen=True, slots=True)
class Engine:
    name: str
    bin_directory: str
    repo_bin: Path
    commands: tuple[str, ...]

    @property
    def interpreter(self) -> str:
        return f"{HOME}/{self.bin_directory}/{_VENV_INTERPRETER}"


def _hook_commands(node: object) -> list[str]:
    """Every `{"type": "command", "command": ...}` handler anywhere in the document.

    All three engines nest hook handlers differently; none nests anything else
    that carries this shape.
    """
    if isinstance(node, dict):
        found = [
            str(node["command"])
            if node.get("type") == "command" and isinstance(node.get("command"), str)
            else ""
        ]
        return [command for command in found if command] + [
            command for value in node.values() for command in _hook_commands(value)
        ]
    if isinstance(node, list):
        return [command for value in node for command in _hook_commands(value)]
    return []


def _render_agy_hooks() -> object:
    jinja = Environment(undefined=StrictUndefined, autoescape=False)  # noqa: S701
    rendered = jinja.from_string(AGY_HOOKS.read_text(encoding="utf-8")).render(
        lookup=lambda _plugin, _name: HOME
    )
    return json.loads(rendered)


def _engines() -> tuple[Engine, ...]:
    # Read unrendered: the `hooks` blocks carry no Jinja, and the expressions the
    # rest of each template does carry sit inside quoted scalars, so both parsers
    # accept the source. agy is the exception — its commands embed the home lookup.
    claude = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    codex = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    return (
        Engine(
            name="claude",
            bin_directory=".claude/bin",
            repo_bin=REPO_ROOT / "roles/devbox/files/dot_claude/bin",
            commands=tuple(
                command.replace("~/", f"{HOME}/") for command in _hook_commands(claude["hooks"])
            ),
        ),
        Engine(
            name="codex",
            bin_directory=".codex/bin",
            repo_bin=REPO_ROOT / "roles/devbox/files/dot_codex/bin",
            commands=tuple(
                command.replace("~/", f"{HOME}/") for command in _hook_commands(codex["hooks"])
            ),
        ),
        Engine(
            name="agy",
            bin_directory=".gemini/antigravity-cli/bin",
            repo_bin=REPO_ROOT / "roles/devbox/files/dot_agy/bin",
            commands=tuple(_hook_commands(_render_agy_hooks())),
        ),
    )


def _uv_sync_directories() -> set[str]:
    directories: set[str] = set()
    for path in TASK_FILES:
        loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(loaded, list)
        for task in loaded:
            command = task.get("ansible.builtin.command") if isinstance(task, dict) else None
            if not isinstance(command, dict) or _UV_SYNC not in str(command.get("cmd", "")):
                continue
            directory = str(command["chdir"])
            for expression, replacement in _ROOT_EXPRESSIONS:
                directory = directory.replace(expression, replacement)
            directories.add(directory)
    return directories


ENGINES: Final = _engines()


@pytest.fixture(params=ENGINES, ids=lambda engine: engine.name)
def engine(request: pytest.FixtureRequest) -> Engine:
    assert isinstance(request.param, Engine)
    return request.param


def test_the_repository_declares_hooks_for_every_engine(engine: Engine) -> None:
    assert engine.commands


def test_every_declared_command_runs_out_of_the_engines_deployed_bin(engine: Engine) -> None:
    prefix = f"{HOME}/{engine.bin_directory}/"
    for command in engine.commands:
        assert shlex.split(command)[0].startswith(prefix), command


def test_every_declared_interpreter_is_a_venv_the_playbook_builds(engine: Engine) -> None:
    interpreters = {
        executable
        for command in engine.commands
        if (executable := shlex.split(command)[0]).endswith(_VENV_INTERPRETER)
    }
    assert interpreters == {engine.interpreter}
    assert f"{HOME}/{engine.bin_directory}" in _uv_sync_directories()


def test_that_venv_has_a_frozen_uv_project_to_be_built_from(engine: Engine) -> None:
    assert (engine.repo_bin / "pyproject.toml").is_file()
    assert (engine.repo_bin / "uv.lock").is_file()


def test_every_declared_command_that_is_not_the_interpreter_is_a_shipped_executable(
    engine: Engine,
) -> None:
    for command in engine.commands:
        executable = shlex.split(command)[0]
        if executable == engine.interpreter:
            continue
        shipped = engine.repo_bin / executable.removeprefix(f"{HOME}/{engine.bin_directory}/")
        assert shipped.is_file(), executable
        assert shipped.stat().st_mode & 0o111, f"{executable} is not executable in the repository"


def test_every_script_the_interpreter_is_handed_is_shipped_beside_it(engine: Engine) -> None:
    prefix = f"{HOME}/{engine.bin_directory}/"
    for command in engine.commands:
        executable, *arguments = shlex.split(command)
        if executable != engine.interpreter:
            continue
        script = next(argument for argument in arguments if argument.startswith(prefix))
        assert (engine.repo_bin / script.removeprefix(prefix)).is_file(), command
