#!/usr/bin/env python3
"""Tests for validate_skill_evals.py — structural skill/eval validation.

Run from any directory:
    pytest roles/devbox/files/dot_claude/bin/test_validate_skill_evals.py

Covers the four validation surfaces exposed by validate_skill_evals.py:
  - SKILL.md frontmatter (validate_skill_md)
  - content evals (validate_evals_json)
  - trigger evals (validate_trigger_evals_json)
  - negative-test heuristic (is_negative_test)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import validate_skill_evals as vse

if TYPE_CHECKING:
    from pathlib import Path


# --- Helpers -----------------------------------------------------------------


def _make_skill(
    tmp_path: Path,
    name: str,
    *,
    frontmatter: str | None = None,
    evals: dict | None = None,
    trigger_evals: list | None = None,
) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    if frontmatter is None:
        frontmatter = f"---\nname: {name}\ndescription: test description\n---\nBody.\n"
    (skill_dir / "SKILL.md").write_text(frontmatter)
    if evals is not None:
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir(exist_ok=True)
        (evals_dir / "evals.json").write_text(json.dumps(evals))
    if trigger_evals is not None:
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir(exist_ok=True)
        (evals_dir / "trigger_evals.json").write_text(json.dumps(trigger_evals))
    return skill_dir


# --- validate_skill_md -------------------------------------------------------


def test_skill_md_valid_passes(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "good-skill")
    errors = vse.validate_skill_md(skill_dir)
    assert errors == []


def test_skill_md_missing_file(tmp_path: Path) -> None:
    skill_dir = tmp_path / "empty-skill"
    skill_dir.mkdir()
    errors = vse.validate_skill_md(skill_dir)
    assert any("SKILL.md not found" in e for e in errors)


def test_skill_md_no_frontmatter(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "bad-skill",
        frontmatter="No frontmatter here.\n",
    )
    errors = vse.validate_skill_md(skill_dir)
    assert any("frontmatter" in e for e in errors)


def test_skill_md_unclosed_frontmatter(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "bad-skill",
        frontmatter="---\nname: bad-skill\ndescription: x\nbody never closes\n",
    )
    errors = vse.validate_skill_md(skill_dir)
    assert any("closing ---" in e for e in errors)


def test_skill_md_missing_name(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "no-name",
        frontmatter="---\ndescription: anything\n---\nBody.\n",
    )
    errors = vse.validate_skill_md(skill_dir)
    assert any("missing 'name'" in e for e in errors)


def test_skill_md_missing_description(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "no-desc",
        frontmatter="---\nname: no-desc\n---\nBody.\n",
    )
    errors = vse.validate_skill_md(skill_dir)
    assert any("missing 'description'" in e for e in errors)


def test_skill_md_name_dir_mismatch(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "actual-name",
        frontmatter="---\nname: other-name\ndescription: x\n---\nBody.\n",
    )
    errors = vse.validate_skill_md(skill_dir)
    assert any("doesn't match directory" in e for e in errors)


def test_skill_md_invalid_kebab_case(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "BadName",
        frontmatter="---\nname: BadName\ndescription: x\n---\nBody.\n",
    )
    errors = vse.validate_skill_md(skill_dir)
    assert any("kebab-case" in e for e in errors)


def test_skill_md_unexpected_frontmatter_key(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "extra-key",
        frontmatter=("---\nname: extra-key\ndescription: x\nrogue: rogue-value\n---\nBody.\n"),
    )
    errors = vse.validate_skill_md(skill_dir)
    assert any("unexpected frontmatter key" in e for e in errors)


def test_skill_md_allows_custom_keys(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "with-extensions",
        frontmatter=(
            "---\n"
            "name: with-extensions\n"
            "description: x\n"
            "alwaysApply: true\n"
            "triggers: lint, format\n"
            "version: 1\n"
            "---\nBody.\n"
        ),
    )
    errors = vse.validate_skill_md(skill_dir)
    assert errors == []


# --- validate_evals_json -----------------------------------------------------


def _good_evals(skill_name: str) -> dict:
    return {
        "skill_name": skill_name,
        "evals": [
            {
                "id": "e1",
                "prompt": "do thing",
                "expected_output": "did the thing",
                "expectations": ["mentions thing"],
            },
            {
                "id": "e2",
                "prompt": "do other",
                "expected_output": "did other",
                "expectations": ["mentions other"],
            },
            {
                "id": "e3",
                "prompt": "no trigger context",
                "expected_output": "skill does not trigger and writes python code",
                "expectations": ["should not trigger"],
            },
        ],
    }


def test_evals_json_missing_is_not_error(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "no-evals")
    errors, stats = vse.validate_evals_json(skill_dir)
    assert errors == []
    assert stats == {"evals": 0, "expectations": 0, "positive": 0, "negative": 0}


def test_evals_json_valid_passes(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "good", evals=_good_evals("good"))
    errors, stats = vse.validate_evals_json(skill_dir)
    assert errors == []
    assert stats["evals"] == 3
    assert stats["expectations"] == 3
    assert stats["negative"] == 1
    assert stats["positive"] == 2


def test_evals_json_invalid_json(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "bad-json")
    (skill_dir / "evals").mkdir()
    (skill_dir / "evals" / "evals.json").write_text("{ not valid json")
    errors, _ = vse.validate_evals_json(skill_dir)
    assert any("invalid JSON" in e for e in errors)


def test_evals_json_skill_name_mismatch(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "actual", evals=_good_evals("wrong"))
    errors, _ = vse.validate_evals_json(skill_dir)
    assert any("doesn't match directory" in e for e in errors)


def test_evals_json_too_few_evals(tmp_path: Path) -> None:
    evals = {
        "skill_name": "tiny",
        "evals": [
            {
                "id": "e1",
                "prompt": "x",
                "expected_output": "should not trigger",
                "expectations": ["x"],
            },
        ],
    }
    skill_dir = _make_skill(tmp_path, "tiny", evals=evals)
    errors, _ = vse.validate_evals_json(skill_dir)
    assert any("minimum 3 evals" in e for e in errors)


def test_evals_json_duplicate_id(tmp_path: Path) -> None:
    payload = _good_evals("dup")
    payload["evals"][1]["id"] = "e1"
    skill_dir = _make_skill(tmp_path, "dup", evals=payload)
    errors, _ = vse.validate_evals_json(skill_dir)
    assert any("duplicate eval id" in e for e in errors)


def test_evals_json_missing_required_fields(tmp_path: Path) -> None:
    payload = _good_evals("missing")
    payload["evals"][0].pop("prompt")
    payload["evals"][1].pop("expected_output")
    payload["evals"][2]["expectations"] = []
    skill_dir = _make_skill(tmp_path, "missing", evals=payload)
    errors, _ = vse.validate_evals_json(skill_dir)
    assert any("missing 'prompt'" in e for e in errors)
    assert any("missing 'expected_output'" in e for e in errors)
    assert any("missing or empty 'expectations'" in e for e in errors)


def test_evals_json_no_negative_test_errors(tmp_path: Path) -> None:
    payload = _good_evals("all-positive")
    # Strip negative markers from the third eval so heuristic finds none.
    payload["evals"][2]["expected_output"] = "did a third thing"
    payload["evals"][2]["expectations"] = ["mentions third"]
    skill_dir = _make_skill(tmp_path, "all-positive", evals=payload)
    errors, _ = vse.validate_evals_json(skill_dir)
    assert any("no negative test" in e for e in errors)


# --- validate_trigger_evals_json ---------------------------------------------


def _good_trigger() -> list[dict]:
    return [
        {"query": "matches", "should_trigger": True},
        {"query": "also matches", "should_trigger": True},
        {"query": "irrelevant", "should_trigger": False},
    ]


def test_trigger_evals_missing_is_not_error(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "no-triggers")
    errors, stats = vse.validate_trigger_evals_json(skill_dir)
    assert errors == []
    assert stats == {"total": 0, "positive": 0, "negative": 0}


def test_trigger_evals_valid_passes(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "trig", trigger_evals=_good_trigger())
    errors, stats = vse.validate_trigger_evals_json(skill_dir)
    assert errors == []
    assert stats == {"total": 3, "positive": 2, "negative": 1}


def test_trigger_evals_not_an_array(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "obj-trig")
    (skill_dir / "evals").mkdir()
    (skill_dir / "evals" / "trigger_evals.json").write_text('{"query": "x"}')
    errors, _ = vse.validate_trigger_evals_json(skill_dir)
    assert any("must be a JSON array" in e for e in errors)


def test_trigger_evals_too_few(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "tiny",
        trigger_evals=[
            {"query": "a", "should_trigger": True},
            {"query": "b", "should_trigger": False},
        ],
    )
    errors, _ = vse.validate_trigger_evals_json(skill_dir)
    assert any("minimum 3 items" in e for e in errors)


def test_trigger_evals_missing_should_trigger(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "incomplete",
        trigger_evals=[
            {"query": "a"},
            {"query": "b", "should_trigger": True},
            {"query": "c", "should_trigger": False},
        ],
    )
    errors, _ = vse.validate_trigger_evals_json(skill_dir)
    assert any("should_trigger" in e for e in errors)


def test_trigger_evals_all_positive_errors(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "all-pos",
        trigger_evals=[
            {"query": "a", "should_trigger": True},
            {"query": "b", "should_trigger": True},
            {"query": "c", "should_trigger": True},
        ],
    )
    errors, _ = vse.validate_trigger_evals_json(skill_dir)
    assert any("no negative tests" in e for e in errors)


def test_trigger_evals_all_negative_errors(tmp_path: Path) -> None:
    skill_dir = _make_skill(
        tmp_path,
        "all-neg",
        trigger_evals=[
            {"query": "a", "should_trigger": False},
            {"query": "b", "should_trigger": False},
            {"query": "c", "should_trigger": False},
        ],
    )
    errors, _ = vse.validate_trigger_evals_json(skill_dir)
    assert any("no positive tests" in e for e in errors)


# --- is_negative_test heuristic ---------------------------------------------


def test_is_negative_pattern_match() -> None:
    assert vse.is_negative_test({"expected_output": "should not trigger", "expectations": []})


def test_is_negative_regex_match() -> None:
    assert vse.is_negative_test(
        {"expected_output": "answers without triggering", "expectations": []}
    )


def test_is_negative_positive_case() -> None:
    assert not vse.is_negative_test(
        {"expected_output": "did the thing", "expectations": ["mentions thing"]}
    )
