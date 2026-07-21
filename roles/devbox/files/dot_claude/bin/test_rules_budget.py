"""Tests for rules_budget.py — heuristic behaviour on synthetic fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import rules_budget as rb


# ---------------------------------------------------------------------------
# scan_lines — heuristic branches
# ---------------------------------------------------------------------------


class TestScanLines:
    def test_hard_imperative_at_line_start(self) -> None:
        hits = rb.scan_lines(["MUST validate all input."])
        assert len(hits) == 1
        assert hits[0].strength == "hard"
        assert hits[0].kind == "imperative"

    def test_soft_imperative_at_line_start(self) -> None:
        hits = rb.scan_lines(["SHOULD prefer composition over inheritance."])
        assert len(hits) == 1
        assert hits[0].strength == "soft"

    def test_bullet_bold_keyword(self) -> None:
        hits = rb.scan_lines(["- **NEVER** commit secrets."])
        assert len(hits) == 1
        assert hits[0].strength == "hard"

    def test_numbered_bullet_keyword(self) -> None:
        hits = rb.scan_lines(["1. ALWAYS run tests before pushing."])
        assert len(hits) == 1
        assert hits[0].strength == "hard"

    def test_multi_word_keyword_wins_over_prefix(self) -> None:
        # MUST NOT (hard) must not be reduced to MUST (also hard) — kind stays imperative,
        # strength stays hard, but we want the whole keyword captured.
        hits = rb.scan_lines(["MUST NOT bypass hooks."])
        assert len(hits) == 1
        assert hits[0].strength == "hard"

    def test_prose_without_keyword_prefix_is_ignored(self) -> None:
        # Modal in the middle of prose — by design not counted (see doc-block).
        hits = rb.scan_lines(["The system should always prefer determinism."])
        assert hits == []

    def test_section_bullet_without_keyword(self) -> None:
        lines = [
            "## Rules",
            "",
            "- Determinism is required.",
            "- Functions stay small.",
        ]
        hits = rb.scan_lines(lines)
        assert len(hits) == 2
        assert all(h.kind == "section-bullet" for h in hits)

    def test_bullet_outside_rule_section_is_ignored(self) -> None:
        lines = [
            "## Overview",
            "",
            "- This paragraph describes the module.",
        ]
        hits = rb.scan_lines(lines)
        assert hits == []

    def test_dedup_between_branches(self) -> None:
        # A bullet under a Rules heading whose text also starts with an
        # imperative keyword must not be counted twice.
        lines = [
            "## Rules",
            "",
            "- MUST validate input.",
        ]
        hits = rb.scan_lines(lines)
        assert len(hits) == 1
        # The imperative branch runs first for that line.
        assert hits[0].kind == "imperative"

    def test_code_fence_is_excluded(self) -> None:
        lines = [
            "## Rules",
            "",
            "```",
            "- MUST NOT appear in output",
            "```",
            "- MUST appear in output",
        ]
        hits = rb.scan_lines(lines)
        assert len(hits) == 1
        assert "MUST appear" in hits[0].text

    def test_blockquote_is_excluded(self) -> None:
        hits = rb.scan_lines(["> MUST cite the source."])
        assert hits == []

    def test_table_row_is_excluded(self) -> None:
        hits = rb.scan_lines(["| MUST | column |"])
        assert hits == []

    def test_section_stack_pops_when_going_up(self) -> None:
        # Leaving a Rules H2 into a Notes H2 must stop counting bullets.
        lines = [
            "## Rules",
            "",
            "- Bullet A (counts).",
            "",
            "## Notes",
            "",
            "- Bullet B (does not count).",
        ]
        hits = rb.scan_lines(lines)
        assert len(hits) == 1
        assert "Bullet A" in hits[0].text

    def test_nested_rules_section_still_counts(self) -> None:
        lines = [
            "## Discipline",
            "",
            "### Sub-rule",
            "",
            "- Bullet counts because ancestor Discipline is rule-shaped.",
        ]
        hits = rb.scan_lines(lines)
        assert len(hits) == 1


class TestLineStrength:
    @pytest.mark.parametrize("line", ["- MUST X", "1. NEVER Y", "SHALL Z", "DO NOT touch"])
    def test_hard_lines(self, line: str) -> None:
        assert rb._line_strength_from_content(line) == "hard"

    @pytest.mark.parametrize("line", ["- SHOULD X", "PREFER Y", "AVOID Z"])
    def test_soft_lines(self, line: str) -> None:
        assert rb._line_strength_from_content(line) == "soft"

    def test_hard_word_in_prose_wins(self) -> None:
        # `SHOULD NEVER` — presence of NEVER upgrades the whole line to hard.
        assert rb._line_strength_from_content("- SHOULD NEVER swallow errors") == "hard"


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


class TestFrontmatter:
    def test_always_apply_true(self) -> None:
        lines = ["---", "name: x", "alwaysApply: true", "---", "body"]
        assert rb._read_frontmatter_alwaysapply(lines) is True

    def test_always_apply_false(self) -> None:
        lines = ["---", "name: x", "alwaysApply: false", "---", "body"]
        assert rb._read_frontmatter_alwaysapply(lines) is False

    def test_missing_always_apply(self) -> None:
        lines = ["---", "name: x", "---", "body"]
        assert rb._read_frontmatter_alwaysapply(lines) is False

    def test_no_frontmatter(self) -> None:
        lines = ["# Heading", "body"]
        assert rb._read_frontmatter_alwaysapply(lines) is False

    def test_frontmatter_end_index(self) -> None:
        lines = ["---", "k: v", "---", "body"]
        assert rb._frontmatter_end(lines) == 3

    def test_frontmatter_end_when_absent(self) -> None:
        assert rb._frontmatter_end(["# Heading"]) == 0


# ---------------------------------------------------------------------------
# End-to-end on a synthetic tree
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def synthetic_root(tmp_path: Path) -> Path:
    _write(
        tmp_path / "USER_AUTHORITY_PROTOCOL.md",
        "# UAP\n\n## Rules\n\n- MUST always confirm destructive actions.\n"
        "- SHOULD explain the diff.\n",
    )
    _write(
        tmp_path / "skills" / "always-on-skill" / "SKILL.md",
        "---\nname: always-on-skill\ndescription: x\nalwaysApply: true\n---\n\n"
        "# Skill\n\n## Protocol\n\n- MUST never do X.\n- Prefer Y.\n",
    )
    _write(
        tmp_path / "skills" / "trigger-skill" / "SKILL.md",
        "---\nname: trigger-skill\ndescription: y\n---\n\n"
        "# Skill\n\nALWAYS do the thing.\n",
    )
    _write(
        tmp_path / "agents" / "some_agent.md",
        "---\nname: some-agent\n---\n\n## Rules\n\n- MUST validate.\n",
    )
    _write(
        tmp_path / "commands" / "techne-thing.md",
        "---\ndescription: thing\n---\n\nNEVER skip approval.\n",
    )
    return tmp_path


class TestBudgetReport:
    def test_discover_finds_all_artefact_types(self, synthetic_root: Path) -> None:
        report = rb.build_report(synthetic_root)
        kinds = sorted({a.kind for a in report.artefacts})
        assert kinds == ["agent", "command", "skill", "uap"]
        assert len(report.artefacts) == 5

    def test_always_on_partitioning(self, synthetic_root: Path) -> None:
        report = rb.build_report(synthetic_root)
        always_on_paths = {a.rel_path for a in report.always_on}
        assert "USER_AUTHORITY_PROTOCOL.md" in always_on_paths
        assert "skills/always-on-skill/SKILL.md" in always_on_paths
        assert "skills/trigger-skill/SKILL.md" not in always_on_paths

    def test_aggregate_counts(self, synthetic_root: Path) -> None:
        report = rb.build_report(synthetic_root)
        # UAP: 2 bullets under Rules (1 hard imperative, 1 section-bullet soft).
        # always-on-skill: 2 bullets under Protocol (1 hard, 1 soft — Prefer is soft keyword).
        # Both always-on artefacts contribute 4 flat rules.
        assert report.always_on_flat == 4
        assert report.always_on_hard >= 2

    def test_scope_weighting(self, synthetic_root: Path) -> None:
        report = rb.build_report(synthetic_root)
        expected = (
            report.always_on_flat * rb.WEIGHT_ALWAYS_ON
            + sum(a.flat for a in report.triggered) * rb.WEIGHT_TRIGGER_LOADED
        )
        assert report.scope_aggregate == expected

    def test_hit_line_numbers_anchor_to_original_file(self, synthetic_root: Path) -> None:
        report = rb.build_report(synthetic_root)
        skill = next(
            a for a in report.artefacts if a.rel_path == "skills/always-on-skill/SKILL.md"
        )
        # Frontmatter is 4 lines (---, name, description, alwaysApply, ---) so
        # rules start at least on line 6.
        assert all(h.line_no >= 6 for h in skill.hits)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_stdout_markdown(self, synthetic_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = rb.main(["--root", str(synthetic_root)])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "# Rules-Budget Report" in out
        assert "Always-on" in out

    def test_json_output_parses(self, synthetic_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = rb.main(["--root", str(synthetic_root), "--json"])
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert "aggregate" in payload
        assert payload["aggregate"]["always_on_flat"] > 0
        assert payload["aggregate"]["verdict"] in {"under", "in-range", "over"}

    def test_baseline_writes_file(self, synthetic_root: Path, tmp_path: Path) -> None:
        out_path = tmp_path / "baseline.md"
        exit_code = rb.main(["--root", str(synthetic_root), "--baseline", str(out_path)])
        assert exit_code == 0
        assert out_path.exists()
        assert "Rules-Budget Report" in out_path.read_text(encoding="utf-8")

    def test_missing_root_returns_nonzero(self, tmp_path: Path) -> None:
        exit_code = rb.main(["--root", str(tmp_path / "nope")])
        assert exit_code == 2
