"""Interactive decision collection: per-field answers and the bulk '!' form.

`collect_decisions` takes its input and output as callables, so the loop is
driven here with scripted answers instead of a terminal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from ai_config.cli import collect_decisions
from ai_config.core import Change, ChangeKind, MissingValue
from ai_config.decisions import DecisionSet, DecisionSource

if TYPE_CHECKING:
    from ai_config.model import FieldPath

INIT = ChangeKind.INITIALISATION_REQUIRED
CONFLICT = ChangeKind.CONFLICT


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


class Session:
    """A scripted operator: hands back queued answers, records what was asked."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []
        self.notes: list[str] = []

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answers.pop(0)

    def notify(self, message: str) -> None:
        self.notes.append(message)

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
