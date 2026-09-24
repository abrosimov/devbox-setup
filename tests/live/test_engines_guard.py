"""A declared engine can never skip.

Hermetic, like test_throwaway_guard.py, and collected with it: the engine tests
skip themselves whenever the binary or its observable is missing, which is right
on a workstation and a trap in CI, where a silently failed install would leave a
job reporting green over nothing exercised. This is what stops that.
"""

from __future__ import annotations

import pytest
from engines import REQUIRED_ENGINES_VARIABLE, require_binary, required_engines, unusable


def test_nothing_is_required_by_default() -> None:
    assert required_engines({}) == frozenset()


@pytest.mark.parametrize(
    ("declared", "expected"),
    [
        ("codex", {"codex"}),
        ("claude,codex", {"claude", "codex"}),
        (" claude , codex ", {"claude", "codex"}),
        ("claude,,", {"claude"}),
        ("", set()),
    ],
)
def test_the_declaration_is_a_comma_separated_engine_list(
    declared: str,
    expected: set[str],
) -> None:
    assert required_engines({REQUIRED_ENGINES_VARIABLE: declared}) == expected


def test_an_undeclared_engine_skips_with_its_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(REQUIRED_ENGINES_VARIABLE, raising=False)
    with pytest.raises(pytest.skip.Exception, match="no language-server log"):
        unusable("agy", "no language-server log was written")


def test_a_declared_engine_fails_instead_of_skipping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(REQUIRED_ENGINES_VARIABLE, "agy,codex")
    with pytest.raises(pytest.fail.Exception, match="no language-server log"):
        unusable("agy", "no language-server log was written")


def test_a_declared_engine_whose_binary_is_absent_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(REQUIRED_ENGINES_VARIABLE, "definitely-not-installed")
    with pytest.raises(pytest.fail.Exception, match="not on PATH"):
        require_binary("definitely-not-installed")


def test_an_undeclared_binary_that_is_absent_only_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(REQUIRED_ENGINES_VARIABLE, "claude")
    with pytest.raises(pytest.skip.Exception, match="not on PATH"):
        require_binary("definitely-not-installed")


def test_an_installed_binary_is_returned_by_path() -> None:
    assert require_binary("sh").endswith("/sh")
