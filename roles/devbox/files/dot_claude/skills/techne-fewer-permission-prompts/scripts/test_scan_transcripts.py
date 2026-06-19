"""Parser tests for scan_transcripts — covers extract_head and split_pipes only."""

from __future__ import annotations

import pytest
from scan_transcripts import extract_head, split_pipes


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("git status", ("git", "status")),
        # ``--stat`` and ``HEAD~1`` — first non-flag token after the command wins.
        ("git diff --stat HEAD~1", ("git", "diff")),
        ("ENV=val git diff", ("git", "diff")),
        ("FOO=1 BAR=2 make build", ("make", "build")),
        ("sudo apt install foo", ("apt", "install")),
        # sudo with a flag — the leader-stripping loop discards ``-E`` before
        # the real command head is read.
        ("sudo -E apt update", ("apt", "update")),
        # ``timeout 30 ...`` — both the leader and its numeric arg are stripped.
        ("timeout 30 curl https://x", ("curl", "https://x")),
        # ``/usr/bin/python3 -m pytest`` — basename of head becomes ``python3``;
        # ``-m`` is a flag and skipped; ``pytest`` is the first non-flag token.
        ("/usr/bin/python3 -m pytest", ("python3", "pytest")),
        ("cd /some/dir", ("cd", "/some/dir")),
    ],
)
def test_extract_head_returns_command_and_subcommand(
    cmd: str,
    expected: tuple[str, str],
) -> None:
    assert extract_head(cmd) == expected


@pytest.mark.parametrize("cmd", ["", "   "])
def test_extract_head_returns_none_for_empty(cmd: str) -> None:
    assert extract_head(cmd) is None


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("a | b", ["a", "b"]),
        ("a && b", ["a", "b"]),
        ("a; b; c", ["a", "b", "c"]),
        ("a || b", ["a", "b"]),
        # Pipe inside single quotes is literal — not a split point.
        ("echo 'x | y'", ["echo 'x | y'"]),
        # ``&&`` inside double quotes is literal — not a split point.
        ('echo "x && y"', ['echo "x && y"']),
        ("", []),
    ],
)
def test_split_pipes_respects_quotes_and_separators(
    cmd: str,
    expected: list[str],
) -> None:
    assert split_pipes(cmd) == expected
