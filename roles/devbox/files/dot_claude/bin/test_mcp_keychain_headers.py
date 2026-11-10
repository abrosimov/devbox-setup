from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mcp_keychain_headers

if TYPE_CHECKING:
    from collections.abc import Sequence


def runner_returning(
    returncode: int, stdout: str, seen: list[Sequence[str]] | None = None
) -> mcp_keychain_headers.Runner:
    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        if seen is not None:
            seen.append(argv)
        return subprocess.CompletedProcess(list(argv), returncode, stdout=stdout, stderr="")

    return run


def test_main_prints_bearer_header_for_keychain_item(capsys: pytest.CaptureFixture[str]) -> None:
    seen: list[Sequence[str]] = []

    code = mcp_keychain_headers.main(
        ["--service", "devbox-clickstack", "--account", "api-key"],
        runner_returning(0, "s3cret\n", seen),
    )

    assert code == 0
    assert json.loads(capsys.readouterr().out) == {"Authorization": "Bearer s3cret"}
    assert seen == [
        (
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            "devbox-clickstack",
            "-a",
            "api-key",
            "-w",
        )
    ]


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [
        pytest.param(44, "", id="item-missing"),
        pytest.param(0, "\n", id="empty-secret"),
        pytest.param(0, "line-one\nline-two\n", id="multi-line-secret"),
    ],
)
def test_main_fails_without_stdout_when_secret_is_unusable(
    returncode: int, stdout: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code = mcp_keychain_headers.main(
        ["--service", "devbox-clickstack", "--account", "api-key"],
        runner_returning(returncode, stdout),
    )

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "devbox-clickstack/api-key" in captured.err


def test_main_reports_timeout_of_security_cli(capsys: pytest.CaptureFixture[str]) -> None:
    def hang(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(list(argv), mcp_keychain_headers.SECURITY_TIMEOUT_SECONDS)

    code = mcp_keychain_headers.main(["--service", "svc", "--account", "acc"], hang)

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "svc/acc" in captured.err
