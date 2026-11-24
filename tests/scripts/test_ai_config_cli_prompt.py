"""Interactive decision collection: per-field answers and the bulk '!' form.

`collect_decisions` takes its input and output as callables, so the loop is
driven here with scripted answers instead of a terminal.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest
from ai_config.cli import collect_decisions
from ai_config.core import Change, ChangeKind, MissingValue
from ai_config.decisions import DecisionSet, DecisionSource
from ai_config.model import SemanticSnapshot

if TYPE_CHECKING:
    from ai_config.core import FieldValue
    from ai_config.model import FieldPath

INIT = ChangeKind.INITIALISATION_REQUIRED
CONFLICT = ChangeKind.CONFLICT
MERGE = ChangeKind.MERGE


def _change(path: FieldPath, kind: ChangeKind) -> Change:
    return Change(
        path=path,
        kind=kind,
        scope=None,
        base=MissingValue.MISSING,
        repo=MissingValue.MISSING,
        live=MissingValue.MISSING,
        sensitive=False,
    )


def _semantic(value: object) -> FieldValue:
    return SemanticSnapshot.from_value({"value": value}).semantic_fields()[0].value


def _valued_change(
    path: FieldPath,
    kind: ChangeKind,
    *,
    repo: object,
    live: object,
    base: object = MissingValue.MISSING,
    merged: object = None,
    sensitive: bool = False,
    templated: bool = False,
) -> Change:
    return Change(
        path=path,
        kind=kind,
        scope=None,
        base=base if base is MissingValue.MISSING else _semantic(base),
        repo=_semantic(repo),
        live=_semantic(live),
        sensitive=sensitive,
        merged=None if merged is None else _semantic(merged),
        templated=templated,
    )


class Session:
    """A scripted operator: hands back queued answers, records what was asked."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []
        self.notes: list[str] = []
        self.events: list[tuple[str, str]] = []

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        self.events.append(("ask", prompt))
        return self.answers.pop(0)

    def notify(self, message: str) -> None:
        self.notes.append(message)
        self.events.append(("note", message))

    def run(self, *changes: Change) -> DecisionSet:
        return collect_decisions(
            tuple(change.path for change in changes),
            {change.path: change for change in changes},
            self.ask,
            self.notify,
        )


def test_each_field_is_answered_individually() -> None:
    session = Session(["repo", "live"])

    result = session.run(_change(("hooks", "Stop"), INIT), _change(("hooks", "Setup"), INIT))

    assert len(session.prompts) == 2
    assert [decision.source for decision in result.decisions] == [
        DecisionSource.REPO,
        DecisionSource.LIVE,
    ]


def test_bulk_answer_settles_the_remaining_changes_of_that_kind() -> None:
    session = Session(["repo!"])

    result = session.run(
        _change(("hooks", "Stop"), INIT),
        _change(("hooks", "Setup"), INIT),
        _change(("hooks", "PreToolUse"), INIT),
    )

    assert len(session.prompts) == 1, "the bulk answer must not prompt again"
    assert len(result.decisions) == 3
    assert all(decision.source is DecisionSource.REPO for decision in result.decisions)


def test_bulk_answer_reports_how_many_it_swept() -> None:
    session = Session(["live!"])

    session.run(
        _change(("hooks", "Stop"), INIT),
        _change(("hooks", "Setup"), INIT),
        _change(("hooks", "PreToolUse"), INIT),
    )

    assert any("2 further" in note for note in session.notes)


def test_bulk_answer_does_not_decide_a_different_kind() -> None:
    session = Session(["repo!", "live"])

    result = session.run(
        _change(("hooks", "Stop"), INIT),
        _change(("hooks", "Setup"), INIT),
        _change(("permissions", "allow"), CONFLICT),
    )

    assert len(session.prompts) == 2, "the conflict still needs its own answer"
    sources = {decision.path: decision.source for decision in result.decisions}
    assert sources[("hooks", "Setup")] is DecisionSource.REPO
    assert sources[("permissions", "allow")] is DecisionSource.LIVE


def test_bulk_answer_also_decides_the_field_it_was_given_on() -> None:
    session = Session(["live!"])

    result = session.run(_change(("hooks", "Stop"), INIT), _change(("hooks", "Setup"), INIT))

    assert [decision.path for decision in result.decisions] == [
        ("hooks", "Stop"),
        ("hooks", "Setup"),
    ]
    assert all(decision.source is DecisionSource.LIVE for decision in result.decisions)


@pytest.mark.parametrize("rejected", ["", "yes", "!", "repo!!", "repository"])
def test_an_unusable_answer_is_rejected_and_reasked(rejected: str) -> None:
    session = Session([rejected, "repo"])

    result = session.run(_change(("hooks", "Stop"), INIT))

    assert len(session.prompts) == 2
    assert session.notes, "the operator is told what a valid answer looks like"
    assert result.decisions[0].source is DecisionSource.REPO


def test_the_values_are_shown_before_the_question_is_asked() -> None:
    session = Session(["repo"])

    session.run(_valued_change(("model",), INIT, repo="opus", live="sonnet"))

    assert session.events == [
        ("note", "initialisation-required\tmodel"),
        ("note", '  - repo: "opus"'),
        ("note", '  + live: "sonnet"'),
        ("ask", "model (initialisation-required) [repo/live]: "),
    ]


def test_a_templated_path_is_flagged_in_the_header_note() -> None:
    session = Session(["repo"])

    session.run(_valued_change(("model",), INIT, repo="opus", live="sonnet", templated=True))

    assert session.notes[0] == "initialisation-required\tmodel\ttemplated"


def test_a_conflict_shows_the_base_first() -> None:
    session = Session(["live"])

    session.run(_valued_change(("model",), CONFLICT, base="old", repo="opus", live="sonnet"))

    assert session.notes[:4] == [
        "conflict\tmodel",
        '    base: "old"',
        '  - repo: "opus"',
        '  + live: "sonnet"',
    ]


def test_a_merge_shows_the_merged_value_last() -> None:
    session = Session(["repo"])

    session.run(
        _valued_change(
            ("allow",),
            MERGE,
            base=["a"],
            repo=["a", "r"],
            live=["a", "l"],
            merged=["a", "r", "l"],
        )
    )

    assert session.notes[:4] == [
        "merge\tallow",
        '  - repo: ["a","r"]',
        '  + live: ["a","l"]',
        '    merged: ["a","r","l"]',
    ]


def test_a_missing_side_is_marked_missing() -> None:
    session = Session(["repo"])

    session.run(_change(("hooks", "Stop"), INIT))

    assert session.notes[:3] == [
        "initialisation-required\thooks.Stop",
        "  - repo: <missing>",
        "  + live: <missing>",
    ]


def test_every_individually_answered_change_gets_its_own_block_in_order() -> None:
    session = Session(["repo", "live"])

    session.run(
        _valued_change(("first",), INIT, repo=1, live=2),
        _valued_change(("second",), INIT, repo=3, live=4),
    )

    assert [text for kind, text in session.events if kind == "note"] == [
        "initialisation-required\tfirst",
        "  - repo: 1",
        "  + live: 2",
        "initialisation-required\tsecond",
        "  - repo: 3",
        "  + live: 4",
    ]


def test_changes_swept_by_a_bulk_answer_add_no_notes_of_their_own() -> None:
    session = Session(["repo!"])

    session.run(
        _valued_change(("hooks", "Stop"), INIT, repo="stop-repo", live="stop-live"),
        _valued_change(("hooks", "Setup"), INIT, repo="setup-repo", live="setup-live"),
        _valued_change(("hooks", "PreToolUse"), INIT, repo="pre-repo", live="pre-live"),
    )

    assert session.notes == [
        "initialisation-required\thooks.Stop",
        '  - repo: "stop-repo"',
        '  + live: "stop-live"',
        "  repo applied to 2 further initialisation-required change(s)",
    ]


def test_a_change_of_another_kind_after_a_bulk_answer_still_shows_its_block() -> None:
    session = Session(["repo!", "live"])

    session.run(
        _valued_change(("hooks", "Stop"), INIT, repo=1, live=2),
        _valued_change(("hooks", "Setup"), INIT, repo=3, live=4),
        _valued_change(("permissions",), CONFLICT, base=5, repo=6, live=7),
    )

    assert session.notes[-4:] == [
        "conflict\tpermissions",
        "    base: 5",
        "  - repo: 6",
        "  + live: 7",
    ]
    assert not any("hooks.Setup" in note for note in session.notes)


@pytest.mark.parametrize("rejected", ["", "yes", "!", "repo!!"])
def test_reasking_after_an_unusable_answer_does_not_repeat_the_block(rejected: str) -> None:
    session = Session([rejected, "repo"])

    session.run(_valued_change(("model",), INIT, repo="opus", live="sonnet"))

    assert session.events == [
        ("note", "initialisation-required\tmodel"),
        ("note", '  - repo: "opus"'),
        ("note", '  + live: "sonnet"'),
        ("ask", "model (initialisation-required) [repo/live]: "),
        ("note", "Enter 'repo' or 'live', optionally suffixed with '!'."),
        ("ask", "model (initialisation-required) [repo/live]: "),
    ]


def test_a_long_value_is_capped_in_the_note() -> None:
    session = Session(["repo"])

    session.run(_valued_change(("model",), INIT, repo="z" * 250, live="short"))

    shown = session.notes[1].removeprefix("  - repo: ")
    assert shown == '"' + "z" * 98 + "…"


def test_sensitive_values_are_never_notified() -> None:
    session = Session(["repo!"])

    session.run(
        _valued_change(
            ("token",),
            CONFLICT,
            base="base-secret",
            repo="repo-secret",
            live="live-secret",
            sensitive=True,
        ),
        _valued_change(
            ("other",),
            CONFLICT,
            base="other-base-secret",
            repo="other-repo-secret",
            live="other-live-secret",
            sensitive=True,
        ),
    )

    assert session.notes[:4] == [
        "conflict\ttoken",
        "    base: <redacted>",
        "  - repo: <redacted>",
        "  + live: <redacted>",
    ]
    assert "secret" not in "".join(session.notes) + "".join(session.prompts)


def test_a_sensitive_merge_redacts_the_merged_value_too() -> None:
    session = Session(["live"])

    session.run(
        _valued_change(
            ("token",),
            MERGE,
            base=["b-secret"],
            repo=["r-secret"],
            live=["l-secret"],
            merged=["m-secret"],
            sensitive=True,
        )
    )

    assert session.notes[:4] == [
        "merge\ttoken",
        "  - repo: <redacted>",
        "  + live: <redacted>",
        "    merged: <redacted>",
    ]
    assert "secret" not in "".join(session.notes)


def test_a_sensitive_missing_side_is_redacted_not_reported_missing() -> None:
    session = Session(["repo"])

    session.run(dataclasses.replace(_change(("gone",), INIT), sensitive=True))

    assert session.notes[:3] == [
        "initialisation-required\tgone",
        "  - repo: <redacted>",
        "  + live: <redacted>",
    ]
