"""Claude Code honours the settings.json that `ai-config apply claude` generated.

Claude Code offers no headless dump of the settings it loaded, so proof here is
by side-effect: the generated session-lifecycle hooks all invoke
`~/.claude/bin/.venv/bin/python <script>`, and the throwaway home supplies a stub
at exactly that path which records its arguments. What the stub recorded is what
the engine dispatched.

The session runs with `--input-format stream-json` and an immediately-closed
stdin: Claude Code starts the session, fires SessionStart and SessionEnd, and
exits 0 without ever reaching the model, so no account and no reachable API are
required. Only those two events are reachable this way — every tool-scoped hook
needs a model turn and stays unverified here.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pytest
from engines import require_binary
from generation import apply_engine
from throwaway import REAL_HOME, ThrowawayHome

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

pytestmark = pytest.mark.live

_SESSION_TIMEOUT_SECONDS: Final = 240.0
_INTERPRETER: Final = ".claude/bin/.venv/bin/python"
_INVOCATION_LOG: Final = "hook-invocations.log"
# The only lifecycle events a model-free print session reaches.
_REACHABLE_EVENTS: Final = ("SessionStart", "SessionEnd")
# A dead loopback port rather than an absent variable: an unset base URL would let
# a configured account reach the real API, turning a config test into a billed one.
_UNREACHABLE_API: Final = "http://127.0.0.1:1"
# A headless print session is a `startup` SessionStart, which the engine confirms
# by naming the dispatched hook `SessionStart:startup`. Matchers on this event
# filter on that word: omitted or `*` matches all, and a value of only word
# characters, spaces, commas and pipes is an exact `|`-separated list rather than
# a substring or a regex. `startup|resume` is the literal the repository ships.
_MATCHING: Final = {"": "no-matcher-at-all", "startup|resume": "repository-literal"}
_NOT_MATCHING: Final = {"compact": "wrong-source", "clear": "other-source"}


@dataclass(frozen=True, slots=True)
class Session:
    home: ThrowawayHome
    settings: Mapping[str, object]
    exit_code: int
    stderr: str
    events: tuple[Mapping[str, object], ...]
    invocations: tuple[str, ...]


def _stub_interpreter(home: ThrowawayHome) -> None:
    log = home.path / _INVOCATION_LOG
    home.write(
        _INTERPRETER,
        # Hook payloads arrive on stdin; draining them keeps the stub from
        # answering a dispatched hook with SIGPIPE instead of an exit code.
        f'#!/bin/sh\ncat >/dev/null\nprintf "%s\\n" "$*" >> "{log}"\nexit 0\n',
        mode=0o755,
    )


def _run(home: ThrowawayHome) -> Session:
    binary = require_binary("claude")
    workspace = home.directory("workspace")
    completed = subprocess.run(
        [
            binary,
            "--print",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--include-hook-events",
            "--verbose",
            "--setting-sources",
            "user",
            "--no-session-persistence",
        ],
        input="",
        capture_output=True,
        text=True,
        timeout=_SESSION_TIMEOUT_SECONDS,
        cwd=workspace,
        env=home.environment(
            ANTHROPIC_API_KEY="devbox-live-test-never-valid",
            ANTHROPIC_BASE_URL=_UNREACHABLE_API,
            CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
        ),
        check=False,
    )
    log = home.path / _INVOCATION_LOG
    return Session(
        home=home,
        settings=_settings_the_engine_was_handed(home),
        exit_code=completed.returncode,
        stderr=completed.stderr,
        events=tuple(
            json.loads(line) for line in completed.stdout.splitlines() if line.startswith("{")
        ),
        invocations=tuple(log.read_text(encoding="utf-8").splitlines()) if log.exists() else (),
    )


def _settings_the_engine_was_handed(home: ThrowawayHome) -> Mapping[str, object]:
    """Empty when the file does not parse — which is a state under test here."""
    try:
        loaded: object = json.loads((home.path / ".claude" / "settings.json").read_text("utf-8"))
    except json.JSONDecodeError:
        return {}
    assert isinstance(loaded, dict)
    return loaded


def declared_arguments(settings: Mapping[str, object], event: str) -> list[str]:
    """The part of each generated command for `event` that follows the interpreter."""
    hooks = settings.get("hooks")
    assert isinstance(hooks, dict)
    groups = hooks.get(event)
    assert isinstance(groups, list)
    arguments: list[str] = []
    for group in groups:
        assert isinstance(group, dict)
        entries = group.get("hooks")
        assert isinstance(entries, list)
        for entry in entries:
            assert isinstance(entry, dict)
            command = entry["command"]
            assert isinstance(command, str)
            interpreter, _, rest = command.partition(" ")
            assert interpreter == f"~/{_INTERPRETER}", command
            arguments.append(rest)
    return arguments


def _prepared(root: Path) -> ThrowawayHome:
    home = ThrowawayHome.create(root)
    apply_engine("claude", home)
    _stub_interpreter(home)
    return home


def _settings_of(home: ThrowawayHome) -> tuple[Path, dict[str, object]]:
    path = home.path / ".claude" / "settings.json"
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return path, loaded


@pytest.fixture(scope="module")
def session(tmp_path_factory: pytest.TempPathFactory) -> Session:
    return _run(_prepared(tmp_path_factory.mktemp("claude-live") / "home"))


@pytest.fixture
def blank_session(tmp_path: Path) -> Session:
    home = _prepared(tmp_path / "blank")
    path, settings = _settings_of(home)
    del settings["hooks"]
    path.write_text(json.dumps(settings), encoding="utf-8")
    return _run(home)


@pytest.fixture
def unparseable_session(tmp_path: Path) -> Session:
    home = _prepared(tmp_path / "unparseable")
    # Parsed and discarded: it asserts the generated file was valid, so the write
    # below is the only thing wrong with what the engine is handed.
    path, _ = _settings_of(home)
    path.write_text('{"permissions": {"allow": ["Bash(ls:*)"],,,\n', encoding="utf-8")
    return _run(home)


@pytest.fixture
def matcher_session(tmp_path: Path) -> Session:
    home = _prepared(tmp_path / "matcher")
    path, settings = _settings_of(home)
    hooks = settings["hooks"]
    assert isinstance(hooks, dict)
    hooks["SessionStart"] = [
        {
            **({"matcher": matcher} if matcher else {}),
            "hooks": [{"type": "command", "command": f"~/{_INTERPRETER} {marker}"}],
        }
        for matcher, marker in (*_MATCHING.items(), *_NOT_MATCHING.items())
    ]
    # The other reachable event would otherwise write its own generated hooks into
    # the same log, and the log is the whole observable.
    hooks["SessionEnd"] = []
    path.write_text(json.dumps(settings), encoding="utf-8")
    return _run(home)


def test_the_headless_session_completes_without_reaching_the_model(session: Session) -> None:
    assert session.exit_code == 0


def test_every_generated_session_lifecycle_hook_is_dispatched(session: Session) -> None:
    expanded = {
        argument.replace("~/", f"{session.home.path}/")
        for event in _REACHABLE_EVENTS
        for argument in declared_arguments(session.settings, event)
    }
    assert set(session.invocations) == expanded


def test_the_engine_reports_a_successful_response_for_each_dispatched_hook(
    session: Session,
) -> None:
    # SessionStart only: the SessionEnd hooks do run (the stub records them) but
    # the engine closes the output stream before reporting their responses.
    responses = _hook_responses(session.events, "SessionStart")
    assert len(responses) == len(declared_arguments(session.settings, "SessionStart"))
    assert {response["exit_code"] for response in responses} == {0}


def test_no_dispatched_hook_reaches_the_operator_configuration(session: Session) -> None:
    assert session.invocations
    for invocation in session.invocations:
        assert str(REAL_HOME) not in invocation


def test_settings_without_a_hooks_block_dispatch_nothing(blank_session: Session) -> None:
    assert blank_session.exit_code == 0
    assert blank_session.invocations == ()
    for event in _REACHABLE_EVENTS:
        assert _hook_responses(blank_session.events, event) == []


def test_a_matcher_that_names_another_session_source_does_not_fire(
    matcher_session: Session,
) -> None:
    """Matchers discriminate; an over-broad one would be invisible without this.

    The suite's other assertions are all satisfied by a hook that fires, so a
    matcher that matched everything — or one this repository mis-spelled into
    matching nothing — would pass them all. Two groups here name the source this
    session really has and two name sources it cannot have, so a matcher that
    stopped being evaluated fails on the second pair and one that stopped
    matching fails on the first.
    """
    assert matcher_session.exit_code == 0
    assert set(matcher_session.invocations) == set(_MATCHING.values())


def test_an_unparseable_settings_file_is_indistinguishable_from_having_no_hooks(
    unparseable_session: Session,
    blank_session: Session,
) -> None:
    """Claude Code drops a settings.json it cannot parse and says nothing.

    Observed, not assumed: exit 0, empty stderr, no hook dispatched, and no
    stream-json event — the same session a settings file with no `hooks` block
    produces. `--debug` adds nothing. Pinned for two reasons. A release that
    starts warning is an improvement this repository wants to notice, because
    today nothing else would. And until then the generator is the only thing
    standing between an operator and a silently unhooked session, so it must
    never emit an invalid file: the engine will not report one.
    """
    for observed in (unparseable_session, blank_session):
        assert observed.exit_code == 0
        assert observed.stderr == ""
        assert observed.invocations == ()
        assert [_hook_responses(observed.events, event) for event in _REACHABLE_EVENTS] == [[], []]


def _hook_responses(
    events: Sequence[Mapping[str, object]],
    event_name: str,
) -> list[Mapping[str, object]]:
    return [
        event
        for event in events
        if event.get("subtype") == "hook_response" and event.get("hook_event") == event_name
    ]
