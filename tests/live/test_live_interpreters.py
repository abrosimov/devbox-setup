"""Every hook command a generated configuration declares can actually be run.

No engine reports this. Codex answers `hooks/list` with a hook it calls
discovered, trusted and enabled without resolving its command at all; Claude
Code and agy dispatch the command and drop the ENOENT. So the rest of this suite
passes a configuration whose interpreter does not exist, and the machine it is
deployed to runs no hooks.

The interpreters are venvs the playbook materialises in a `uv sync` task that is
separate from the task deploying the configuration that names them, so proving
the two agree means running both: this generates the configuration the way
`tests/live/generation.py` does, then deploys the hook directory and runs the
same `uv sync --frozen --no-dev` the playbook runs, and resolves every declared
command against the result.

`tests/deploy/test_hook_interpreters.py` is the static counterpart, checking the
declarations against the playbook without needing uv. This is the half that
catches a uv whose `--frozen` sync stops producing `.venv/bin/python`.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
from engines import require_binary
from generation import REPO_ROOT, apply_engine, render_ansible_template
from throwaway import ThrowawayHome

pytestmark = pytest.mark.live

_SYNC_TIMEOUT_SECONDS: Final = 600.0
_IGNORED_IN_HOOK_DIRECTORY: Final = shutil.ignore_patterns(".venv", "__pycache__", ".DS_Store")
AGY_HOOKS_TEMPLATE: Final = REPO_ROOT / "roles/devbox/files/dot_agy/config/hooks.json.j2"


@dataclass(frozen=True, slots=True)
class Engine:
    name: str
    bin_directory: str
    repo_bin: Path


ENGINES: Final = (
    Engine("claude", ".claude/bin", REPO_ROOT / "roles/devbox/files/dot_claude/bin"),
    Engine("codex", ".codex/bin", REPO_ROOT / "roles/devbox/files/dot_codex/bin"),
    Engine(
        "agy",
        ".gemini/antigravity-cli/bin",
        REPO_ROOT / "roles/devbox/files/dot_agy/bin",
    ),
)


@dataclass(frozen=True, slots=True)
class Deployed:
    engine: Engine
    home: ThrowawayHome
    commands: tuple[str, ...]

    def declared(self, token: str) -> Path:
        """Where `token` lands in the throwaway home, without following symlinks.

        Not `ThrowawayHome.resolve`: a venv interpreter is a symlink to the
        system Python, so resolving it leaves the temporary root and the guard
        refuses it — correctly, for a path anything might write to. Containment
        is therefore checked lexically here, and nothing below writes.
        """
        relative = token.removeprefix("~/").removeprefix(f"{self.home.path}/")
        candidate = Path(os.path.normpath(self.home.path / relative))
        assert candidate.is_relative_to(self.home.path), token
        return candidate


def _hook_commands(node: object) -> list[str]:
    if isinstance(node, dict):
        mine = (
            [str(node["command"])]
            if node.get("type") == "command" and isinstance(node.get("command"), str)
            else []
        )
        return mine + [command for value in node.values() for command in _hook_commands(value)]
    if isinstance(node, list):
        return [command for value in node for command in _hook_commands(value)]
    return []


def _generated_hook_commands(engine: Engine, home: ThrowawayHome) -> tuple[str, ...]:
    if engine.name == "claude":
        settings = json.loads((home.path / ".claude/settings.json").read_text(encoding="utf-8"))
        return tuple(_hook_commands(settings["hooks"]))
    if engine.name == "codex":
        config = tomllib.loads((home.path / ".codex/config.toml").read_text(encoding="utf-8"))
        return tuple(_hook_commands(config["hooks"]))
    rendered = render_ansible_template(AGY_HOOKS_TEMPLATE, home)
    home.write(".gemini/config/hooks.json", rendered, mode=0o644)
    return tuple(_hook_commands(json.loads(rendered)))


def _deploy(engine: Engine, root: Path) -> Deployed:
    uv = require_binary("uv")
    home = ThrowawayHome.create(root)
    apply_engine(engine.name, home)
    shutil.copytree(
        engine.repo_bin,
        home.directory(engine.bin_directory),
        ignore=_IGNORED_IN_HOOK_DIRECTORY,
        dirs_exist_ok=True,
    )
    completed = subprocess.run(
        [uv, "sync", "--frozen", "--no-dev"],
        capture_output=True,
        text=True,
        timeout=_SYNC_TIMEOUT_SECONDS,
        cwd=home.resolve(engine.bin_directory),
        env=home.environment(),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return Deployed(
        engine=engine,
        home=home,
        commands=_generated_hook_commands(engine, home),
    )


@pytest.fixture(scope="module", params=ENGINES, ids=lambda engine: engine.name)
def deployed(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> Deployed:
    engine = request.param
    assert isinstance(engine, Engine)
    return _deploy(engine, tmp_path_factory.mktemp(f"{engine.name}-interpreters") / "home")


def test_the_generated_configuration_declares_hooks(deployed: Deployed) -> None:
    assert deployed.commands


def test_every_declared_command_resolves_to_an_executable_file(deployed: Deployed) -> None:
    for command in deployed.commands:
        executable = deployed.declared(shlex.split(command)[0])
        assert executable.is_file(), f"{command}: {executable} does not exist"
        assert os.access(executable, os.X_OK), f"{command}: {executable} is not executable"


def test_every_script_a_declared_command_hands_its_interpreter_exists(
    deployed: Deployed,
) -> None:
    for command in deployed.commands:
        _, *arguments = shlex.split(command)
        for argument in arguments:
            if f"/{deployed.engine.bin_directory}/" not in argument:
                continue
            assert deployed.declared(argument).is_file(), f"{command}: {argument} is missing"
