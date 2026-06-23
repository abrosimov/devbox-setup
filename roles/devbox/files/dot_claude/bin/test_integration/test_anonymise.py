from __future__ import annotations

import getpass

import pytest
from hypothesis import given
from hypothesis import strategies as st

from test_integration.anonymise import (
    EMAIL_PLACEHOLDER,
    HOME_PLACEHOLDER,
    IP_PLACEHOLDER,
    SHA_PLACEHOLDER,
    TIMESTAMP_PLACEHOLDER,
    TMPDIR_PLACEHOLDER,
    anonymise,
    anonymise_text,
)


@pytest.mark.parametrize(
    "text",
    [
        "/Users/kirillabrosimov/Projects/devbox-setup",
        "/Users/john.doe/work/notes.md",
        "/home/alice/repo",
        "alice@example.com sent the email",
        "commit fa3b9d2e8a4f5c1b2d3e4f5a6b7c8d9e0f1a2b3c was applied",
        "2026-06-20T11:30:45Z is the timestamp",
        "192.168.1.10 was the IP",
        "Bearer abcdefghijklmnopqrstuvwxyz",
        "/private/tmp/foo/bar",
        "/var/folders/qq/abc123/T/tmpfile",
    ],
)
def test_anonymise_is_idempotent(text: str) -> None:
    once = anonymise_text(text)
    twice = anonymise_text(once)
    assert once == twice


def test_anonymise_strips_current_user_homedir() -> None:
    try:
        user = getpass.getuser()
    except (OSError, KeyError):  # pragma: no cover
        pytest.skip("no user available in environment")
    text = f"/Users/{user}/Projects/devbox-setup/foo"
    assert user not in anonymise_text(text)
    assert HOME_PLACEHOLDER in anonymise_text(text)


def test_anonymise_handles_dict_structures() -> None:
    raw = {
        "command": "ls /Users/someone/notes",
        "tool_input": {
            "file_path": "/Users/jane/code/foo.py",
            "content": "alice@example.com\n",
            "args": ["--commit", "fa3b9d2e8a4f5c1b2d3e4f5a6b7c8d9e0f1a2b3c"],
        },
    }
    out = anonymise(raw)
    flat = str(out)
    assert "someone" not in flat
    assert "jane" not in flat
    assert "alice@example.com" not in flat
    assert EMAIL_PLACEHOLDER in flat
    assert SHA_PLACEHOLDER in flat


def test_email_is_replaced() -> None:
    assert anonymise_text("alice@example.com") == EMAIL_PLACEHOLDER
    assert "bob@" not in anonymise_text("bob@something.org")


def test_full_sha_is_replaced() -> None:
    sha = "fa3b9d2e8a4f5c1b2d3e4f5a6b7c8d9e0f1a2b3c"
    out = anonymise_text(sha)
    assert sha not in out
    assert SHA_PLACEHOLDER in out


def test_iso_timestamp_is_replaced() -> None:
    out = anonymise_text("2026-06-20T11:30:45.123Z")
    assert "2026-06-20" not in out
    assert TIMESTAMP_PLACEHOLDER in out


def test_var_folders_tmpdir_is_replaced() -> None:
    out = anonymise_text("/var/folders/qq/abc/T/work/file.txt")
    assert "qq" not in out
    assert TMPDIR_PLACEHOLDER in out


def test_semver_quadruple_is_not_replaced_as_ip() -> None:
    text = "version 1.2.3.4"
    assert anonymise_text(text) == "version 1.2.3.4"
    assert IP_PLACEHOLDER not in anonymise_text(text)


def test_high_first_octet_is_masked_as_ip() -> None:
    assert IP_PLACEHOLDER in anonymise_text("connect to 192.168.1.10")


def test_bearer_token_is_replaced() -> None:
    text = "Authorization: Bearer abcdefghijklmnopqr-stuvwxyz123"
    out = anonymise_text(text)
    assert "abcdefghijklmnopqr-stuvwxyz123" not in out


def test_non_string_passthrough() -> None:
    assert anonymise(42) == 42
    assert anonymise(None) is None
    true_value = True
    assert anonymise(true_value) is true_value


@given(st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), max_size=200))
def test_anonymise_does_not_introduce_real_secret_patterns(text: str) -> None:
    out = anonymise_text(text)
    # The output must not contain a credit-card-shaped 16-digit run that
    # wasn't in the input (smoke check that we're not synthesising new PII).
    import re

    new_credit_card = re.search(r"\b\d{16}\b", out) and not re.search(r"\b\d{16}\b", text)
    assert not new_credit_card


@given(st.text(min_size=0, max_size=300))
def test_anonymise_is_idempotent_property(text: str) -> None:
    once = anonymise_text(text)
    twice = anonymise_text(once)
    assert once == twice


def test_fixture_has_no_real_username() -> None:
    """Defence-in-depth: the current username should NEVER appear in output."""
    try:
        user = getpass.getuser()
    except (OSError, KeyError):  # pragma: no cover
        pytest.skip("no user available")
    if not user:
        pytest.skip("empty user")
    text = f"hello {user} from /Users/{user}/code"
    out = anonymise_text(text)
    assert user not in out or len(user) < 3  # tiny usernames like 'go' are unsafe to assert
