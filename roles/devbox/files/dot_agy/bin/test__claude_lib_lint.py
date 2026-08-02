from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import lint


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("main.go", ["golangci-lint", "run"]),
        ("util.py", ["ruff", "check"]),
        ("App.tsx", ["npx", "eslint"]),
        ("util.ts", ["npx", "eslint"]),
        ("index.js", ["npx", "eslint"]),
        ("App.jsx", ["npx", "eslint"]),
        ("Dockerfile", ["hadolint"]),
        ("docker-compose.yml", ["dclint"]),
        ("docker-compose.yaml", ["dclint"]),
        ("compose.yml", ["dclint"]),
        ("compose.yaml", ["dclint"]),
    ],
)
def test_linter_for_file_known_types(filename: str, expected: list[str]) -> None:
    assert lint.linter_for_file(Path(filename)) == expected


@pytest.mark.parametrize(
    "filename",
    [
        "README.md",
        "config.yaml",
        "Makefile",
        "data.csv",
        "noext",
    ],
)
def test_linter_for_file_unknown_returns_none(filename: str) -> None:
    assert lint.linter_for_file(Path(filename)) is None


def test_linter_for_file_dockerfile_variant() -> None:
    # Plain Dockerfile is the canonical case; variants like Dockerfile.dev
    # are intentionally not routed (they're often build-stage forks and may
    # break hadolint without --ignore).
    assert lint.linter_for_file(Path("Dockerfile")) == ["hadolint"]


def test_linter_for_file_is_case_insensitive_on_suffix() -> None:
    # .PY is rare in practice but the dispatch must not regress.
    assert lint.linter_for_file(Path("script.PY")) == ["ruff", "check"]


def test_linter_for_file_returns_fresh_list() -> None:
    a = lint.linter_for_file(Path("a.go"))
    b = lint.linter_for_file(Path("b.go"))
    assert a is not None
    assert b is not None
    a.append("--mutated")
    assert b == ["golangci-lint", "run"]
