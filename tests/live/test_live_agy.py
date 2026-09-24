"""Antigravity honours the settings.json and hooks.json the repository generates.

agy exposes no headless command that reports its loaded configuration, and it
silently ignores a settings file it cannot parse. What it does do is echo the
loaded permission set and the discovered hook count into its language-server log
while starting up for an unauthenticated `agy agents`. That log is the only
observable here, so the assertions are deliberately narrow: they prove agy read
the generated files, not that it acted on them. Every agy hook event
(PreToolUse, PreInvocation, Stop) needs a model turn, so none is dispatched here.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pytest
from engines import binary_version, require_binary, unusable
from generation import REPO_ROOT, apply_engine, render_ansible_template
from throwaway import ThrowawayHome

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.live

HOOKS_TEMPLATE: Final = REPO_ROOT / "roles/devbox/files/dot_agy/config/hooks.json.j2"
_CLI_ROOT: Final = ".gemini/antigravity-cli"
_STARTUP_TIMEOUT_SECONDS: Final = 300.0
_PERMISSIONS: Final = re.compile(r"CLI settings initialized: permissions=(.*?), toolPermission=")
_NAMED_HOOKS: Final = re.compile(r"loaded (\d+) named hooks from (\d+) hooks\.json file\(s\)")
_MALFORMED_SETTINGS: Final = re.compile(r"failed to load cli settings, using defaults: (.+)")


@dataclass(frozen=True, slots=True)
class Startup:
    home: ThrowawayHome
    exit_code: int
    stdout: str
    stderr: str
    log: str


def _start(home: ThrowawayHome) -> Startup:
    binary = require_binary("agy")
    completed = subprocess.run(
        [binary, "agents"],
        capture_output=True,
        text=True,
        timeout=_STARTUP_TIMEOUT_SECONDS,
        cwd=home.path,
        env=home.environment(),
        check=False,
    )
    logs = sorted((home.path / _CLI_ROOT).glob("log/*.log"))
    if not logs:
        unusable(
            "agy",
            f"{binary_version(binary)} produced no language-server log in this environment; "
            "its loaded configuration cannot be observed",
        )
    return Startup(
        home=home,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        log="\n".join(path.read_text(errors="replace") for path in logs),
    )


def _prepare(root: Path, *, generate: bool) -> ThrowawayHome:
    home = ThrowawayHome.create(root)
    home.directory(_CLI_ROOT)
    home.directory(".gemini/config")
    if generate:
        apply_engine("agy", home)
        home.write(
            ".gemini/config/hooks.json",
            render_ansible_template(HOOKS_TEMPLATE, home),
            mode=0o644,
        )
    return home


def _search(pattern: re.Pattern[str], startup: Startup, subject: str) -> re.Match[str]:
    found = pattern.search(startup.log)
    if found is None:
        pytest.fail(
            f"{binary_version(require_binary('agy'))} logged no {subject} line matching "
            f"{pattern.pattern!r}; the log format this suite reads has changed"
        )
    return found


@pytest.fixture(scope="module")
def started(tmp_path_factory: pytest.TempPathFactory) -> Startup:
    return _start(_prepare(tmp_path_factory.mktemp("agy-live") / "home", generate=True))


@pytest.fixture
def bare(tmp_path: Path) -> Startup:
    return _start(_prepare(tmp_path / "home", generate=False))


@pytest.fixture
def unparseable(tmp_path: Path) -> Startup:
    home = _prepare(tmp_path / "home", generate=True)
    home.write(
        f"{_CLI_ROOT}/settings.json",
        '{"permissions": {"allow": ["Bash(ls:*)"],,,\n',
        mode=0o644,
    )
    return _start(home)


def test_the_unauthenticated_startup_completes(started: Startup) -> None:
    assert started.exit_code == 0


def test_every_permission_the_generated_settings_allow_is_loaded(started: Startup) -> None:
    reported = _search(_PERMISSIONS, started, "permission").group(1)
    settings = started.home.path / _CLI_ROOT / "settings.json"
    allowed = _allowed_commands(settings)
    assert allowed
    for command in allowed:
        assert command in reported


def test_every_named_hook_the_repository_declares_is_loaded(started: Startup) -> None:
    loaded, files = _search(_NAMED_HOOKS, started, "hook-manager").groups()
    declared = render_ansible_template(HOOKS_TEMPLATE, started.home)
    assert int(files) == 1
    assert int(loaded) == len(_names(declared))


def test_a_home_without_generated_configuration_loads_neither(bare: Startup) -> None:
    assert _search(_PERMISSIONS, bare, "permission").group(1) == "<nil>"
    assert _search(_NAMED_HOOKS, bare, "hook-manager").groups() == ("0", "0")


def test_an_unparseable_settings_file_silently_loses_every_permission(
    unparseable: Startup,
) -> None:
    """agy discards a settings.json it cannot parse and carries on with defaults.

    Observed, not assumed: exit 0, nothing on stdout or stderr, and the loaded
    permission set is the `<nil>` of a home with no configuration at all — the
    whole generated allow-list gone, with no foreground signal. The only record
    is a line in the language-server log, which is why this asserts on that line
    too: it is the single thread by which the failure is diagnosable, and an
    agy that stops writing it would leave the failure entirely undetectable.

    Pinned for two reasons. An agy that begins reporting this in the foreground
    is a change this repository wants to notice. And until then the generator
    must never emit an invalid settings.json, because the engine will not say so.

    hooks.json is a separate file with a separate loader, and the assertion that
    it still loads is the control: it shows the silence is scoped to the file
    that was broken rather than being a dead startup.
    """
    assert unparseable.exit_code == 0
    assert unparseable.stdout == ""
    assert unparseable.stderr == ""
    assert _search(_PERMISSIONS, unparseable, "permission").group(1) == "<nil>"
    assert _search(_MALFORMED_SETTINGS, unparseable, "malformed-settings")
    declared = render_ansible_template(HOOKS_TEMPLATE, unparseable.home)
    loaded, files = _search(_NAMED_HOOKS, unparseable, "hook-manager").groups()
    assert (int(loaded), int(files)) == (len(_names(declared)), 1)


def _allowed_commands(settings: Path) -> list[str]:
    loaded: object = json.loads(settings.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    permissions = loaded["permissions"]
    assert isinstance(permissions, dict)
    allow = permissions["allow"]
    assert isinstance(allow, list)
    return [str(entry) for entry in allow]


def _names(hooks: str) -> list[str]:
    loaded: object = json.loads(hooks)
    assert isinstance(loaded, dict)
    return list(loaded)
