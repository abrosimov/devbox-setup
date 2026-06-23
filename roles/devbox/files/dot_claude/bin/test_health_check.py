from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

import health_check

if TYPE_CHECKING:
    import pytest


def test_check_tools_partitions_found_and_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    tools = (
        health_check.Tool("alpha", "critical", "brew install alpha"),
        health_check.Tool("beta", "important", "brew install beta"),
        health_check.Tool("gamma", "optional", "brew install gamma"),
    )
    monkeypatch.setattr(
        health_check,
        "locate",
        lambda name: "/usr/local/bin/alpha" if name == "alpha" else None,
    )

    found, missing = health_check.check_tools(tools)
    assert [r.tool.name for r in found] == ["alpha"]
    assert [r.tool.name for r in missing] == ["beta", "gamma"]
    assert found[0].location == "/usr/local/bin/alpha"


def test_render_report_all_found_omits_missing_section() -> None:
    found = [
        health_check.CheckResult(
            tool=health_check.Tool("git", "critical", ""),
            location="/usr/bin/git",
        ),
    ]
    report = health_check.render_report(found, missing=[], total=1)
    assert "1 tools found" in report
    assert "All 1 tools available" in report
    assert "missing" not in report.lower() or "0 missing" in report.lower()


def test_render_report_critical_missing_marks_failure() -> None:
    missing = [
        health_check.CheckResult(
            tool=health_check.Tool("git", "critical", "brew install git"),
            location=None,
        ),
    ]
    report = health_check.render_report(found=[], missing=missing, total=1)
    assert "[CRITICAL]" in report
    assert "Install: brew install git" in report
    assert "Critical tools missing" in report


def test_render_report_only_optional_missing_no_critical_warning() -> None:
    missing = [
        health_check.CheckResult(
            tool=health_check.Tool("bat", "optional", "brew install bat"),
            location=None,
        ),
    ]
    report = health_check.render_report(found=[], missing=missing, total=1)
    assert "[OPTIONAL]" in report
    assert "Critical tools missing" not in report


def test_main_returns_zero_when_no_critical_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        health_check,
        "TOOLS",
        (
            health_check.Tool("present", "critical", ""),
            health_check.Tool("absent", "optional", ""),
        ),
    )
    monkeypatch.setattr(
        health_check,
        "locate",
        lambda name: "/usr/bin/present" if name == "present" else None,
    )
    assert health_check.main() == 0


def test_main_returns_one_when_critical_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        health_check, "TOOLS", (health_check.Tool("missing-critical", "critical", "install me"),)
    )
    monkeypatch.setattr(health_check, "locate", lambda _name: None)
    assert health_check.main() == 1
