from __future__ import annotations

import json
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

import pytest
from langfuse_config import cli

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_MANIFEST = REPO_ROOT / "roles/devbox/files/dot_claude/settings.ai-config.json"
OPERATOR_PK = "pk-lf-0a1b2c3d-4e5f-6789-abcd-ef0123456789"
OPERATOR_SK = "sk-lf-9f8e7d6c-5b4a-3210-fedc-ba9876543210"
HOME = "/Users/someone"


@dataclass
class FakeTerminal:
    answers: list[str | EOFError]
    tty: bool = True
    prompts: list[tuple[str, bool]] = field(default_factory=list)

    def is_tty(self) -> bool:
        return self.tty

    def read(self, prompt: str, *, hidden: bool) -> str:
        self.prompts.append((prompt, hidden))
        answer = self.answers.pop(0)
        if isinstance(answer, EOFError):
            raise answer
        return answer


@dataclass
class FakeSecurity:
    status: int = 0
    calls: list[tuple[tuple[str, ...], str]] = field(default_factory=list)

    def __call__(self, arguments: tuple[str, ...], stdin: str, /) -> int:
        self.calls.append((arguments, stdin))
        return self.status


@dataclass
class Run:
    status: int
    stderr: str


def seed(
    terminal: FakeTerminal,
    security: FakeSecurity,
    *,
    platform_name: str = "Darwin",
    home: str = HOME,
) -> Run:
    stderr = StringIO()
    status = cli.main(
        [],
        platform_name=platform_name,
        environment={"HOME": home},
        terminal=terminal,
        runner=security,
        stderr=stderr,
    )
    return Run(status=status, stderr=stderr.getvalue())


def test_both_keys_are_stored_through_stdin_never_on_the_command_line() -> None:
    security = FakeSecurity()

    run = seed(FakeTerminal([OPERATOR_PK, OPERATOR_SK]), security)

    assert run.status == 0
    assert [arguments for arguments, _ in security.calls] == [
        ("/usr/bin/security", "-i"),
        ("/usr/bin/security", "-i"),
    ]
    assert [stdin for _, stdin in security.calls] == [
        (
            "add-generic-password -U -s devbox-langfuse -a public-key -T /usr/bin/security "
            f"-w {OPERATOR_PK} {HOME}/Library/Keychains/login.keychain-db\n"
        ),
        (
            "add-generic-password -U -s devbox-langfuse -a secret-key -T /usr/bin/security "
            f"-w {OPERATOR_SK} {HOME}/Library/Keychains/login.keychain-db\n"
        ),
    ]
    assert OPERATOR_SK not in run.stderr


def test_only_the_secret_key_is_read_hidden() -> None:
    terminal = FakeTerminal([OPERATOR_PK, OPERATOR_SK])

    seed(terminal, FakeSecurity())

    assert [hidden for _, hidden in terminal.prompts] == [False, True]


def test_a_rerun_replaces_the_items_in_place() -> None:
    security = FakeSecurity()

    seed(FakeTerminal([OPERATOR_PK, OPERATOR_SK]), security)
    seed(FakeTerminal([OPERATOR_PK.replace("0a", "1b"), OPERATOR_SK.replace("9f", "8e")]), security)

    assert len(security.calls) == 4
    assert all(" -U " in stdin for _, stdin in security.calls)


@pytest.mark.parametrize(
    "answers",
    [
        [OPERATOR_SK, OPERATOR_SK, OPERATOR_SK],
        ["", "pk-lf-", "pk-lf-with space"],
    ],
)
def test_a_malformed_public_key_is_retried_then_abandoned_without_storing(
    answers: list[str | EOFError],
) -> None:
    security = FakeSecurity()

    run = seed(FakeTerminal(answers), security)

    assert run.status == 1
    assert security.calls == []
    assert "giving up on public-key after 3 attempts" in run.stderr


def test_a_swapped_secret_key_is_rejected_before_anything_is_stored() -> None:
    security = FakeSecurity()

    run = seed(FakeTerminal([OPERATOR_PK, OPERATOR_PK, OPERATOR_PK, OPERATOR_PK]), security)

    assert run.status == 1
    assert security.calls == []


def test_a_correct_key_after_a_typo_is_accepted() -> None:
    security = FakeSecurity()

    run = seed(FakeTerminal(["pk-typo", OPERATOR_PK, OPERATOR_SK]), security)

    assert run.status == 0
    assert len(security.calls) == 2


def test_a_keychain_failure_is_reported_without_echoing_the_key() -> None:
    run = seed(FakeTerminal([OPERATOR_PK, OPERATOR_SK]), FakeSecurity(status=1))

    assert run.status == 1
    assert "could not store devbox-langfuse/public-key" in run.stderr
    assert OPERATOR_PK not in run.stderr


def test_a_home_with_whitespace_is_refused_rather_than_split() -> None:
    security = FakeSecurity()

    run = seed(FakeTerminal([OPERATOR_PK, OPERATOR_SK]), security, home="/Users/some one")

    assert run.status == 1
    assert security.calls == []


def test_closed_input_stops_without_storing() -> None:
    security = FakeSecurity()

    run = seed(FakeTerminal([OPERATOR_PK, EOFError()]), security)

    assert run.status == 1
    assert security.calls == []


def test_a_non_tty_is_refused() -> None:
    security = FakeSecurity()

    run = seed(FakeTerminal([], tty=False), security)

    assert run.status == 1
    assert security.calls == []
    assert "make langfuse-config" in run.stderr


def test_other_platforms_exit_cleanly_without_prompting() -> None:
    terminal = FakeTerminal([])

    run = seed(terminal, FakeSecurity(), platform_name="Linux")

    assert run.status == 0
    assert terminal.prompts == []


def test_the_slots_are_the_ones_the_claude_manifest_binds() -> None:
    manifest = json.loads(CLAUDE_MANIFEST.read_text(encoding="utf-8"))
    bindings = {rule["binding"] for rule in manifest["fields"] if "binding" in rule}

    assert bindings == {f"keychain:{cli.KEYCHAIN_SERVICE}/{slot.account}" for slot in cli.SLOTS}
