from pathlib import Path

import pytest
from main import TARGET_LINES, main, plan, verify


@pytest.mark.parametrize(
    ("current", "wanted", "expected"),
    [
        ("", ("a", "b"), ["a", "b"]),
        ("a\n", ("a", "b"), ["b"]),
        ("a\nb\n", ("a", "b"), []),
    ],
)
def test_plan_lists_only_missing_lines(
    current: str, wanted: tuple[str, ...], expected: list[str]
) -> None:
    assert [step.line for step in plan(current, wanted)] == expected


def test_verify_reports_missing_lines() -> None:
    assert verify("a\n", ("a", "b")) == ["b"]
    assert verify("a\nb\n", ("a", "b")) == []


def test_dry_run_changes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "config.txt"
    target.write_text("keep\n")

    assert main(["--file", str(target), "--dry-run"]) == 0
    assert target.read_text() == "keep\n"


def test_run_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "config.txt"
    target.write_text("keep")

    assert main(["--file", str(target)]) == 0
    after_first = target.read_text()
    assert main(["--file", str(target)]) == 0

    assert target.read_text() == after_first
    assert after_first.splitlines() == ["keep", *TARGET_LINES]
