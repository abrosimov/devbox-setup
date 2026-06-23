from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_fix_perms as cfp


def test_parse_args_empty_defaults_to_no_flags() -> None:
    parsed = cfp.parse_args([])
    assert isinstance(parsed, cfp.ParsedArgs)
    assert not parsed.with_git
    assert not parsed.with_go
    assert not parsed.with_python
    assert not parsed.with_node
    assert not parsed.no_detect
    assert not parsed.show_usage


def test_parse_args_with_git() -> None:
    parsed = cfp.parse_args(["--with-git"])
    assert isinstance(parsed, cfp.ParsedArgs)
    assert parsed.with_git


def test_parse_args_all_expands() -> None:
    parsed = cfp.parse_args(["--all"])
    assert isinstance(parsed, cfp.ParsedArgs)
    assert parsed.with_go
    assert parsed.with_python
    assert parsed.with_node
    assert not parsed.with_git


def test_parse_args_combined() -> None:
    parsed = cfp.parse_args(["--with-git", "--python", "--no-detect"])
    assert isinstance(parsed, cfp.ParsedArgs)
    assert parsed.with_git
    assert parsed.with_python
    assert not parsed.with_go
    assert parsed.no_detect


def test_parse_args_help() -> None:
    parsed = cfp.parse_args(["--help"])
    assert isinstance(parsed, cfp.ParsedArgs)
    assert parsed.show_usage


def test_parse_args_h_short() -> None:
    parsed = cfp.parse_args(["-h"])
    assert isinstance(parsed, cfp.ParsedArgs)
    assert parsed.show_usage


def test_parse_args_unknown_returns_failure() -> None:
    parsed = cfp.parse_args(["--bogus"])
    assert isinstance(parsed, cfp.ParseFailure)
    assert "bogus" in parsed.message


@pytest.mark.parametrize(
    ("markers", "expected"),
    [
        ([], []),
        ([".git/"], ["git"]),
        (["go.mod"], ["go"]),
        (["pyproject.toml"], ["python"]),
        (["setup.py"], ["python"]),
        (["requirements.txt"], ["python"]),
        (["package.json"], ["node"]),
        ([".git/", "go.mod"], ["git", "go"]),
        ([".git/", "pyproject.toml", "package.json"], ["git", "python", "node"]),
        ([".git/", "go.mod", "pyproject.toml", "package.json"], ["git", "go", "python", "node"]),
        # pyproject + setup.py — single 'python' entry, not duplicate
        (["pyproject.toml", "setup.py"], ["python"]),
    ],
)
def test_detect_project_combinations(
    tmp_path: Path, markers: list[str], expected: list[str]
) -> None:
    for m in markers:
        target = tmp_path / m.rstrip("/")
        if m.endswith("/"):
            target.mkdir(parents=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
    result = cfp.detect_project(tmp_path)
    assert result.detected == expected


def test_apply_detection_sets_flags() -> None:
    args = cfp.ParsedArgs()
    det = cfp.DetectionResult(detected=["git", "go", "python"])
    cfp.apply_detection(args, det)
    assert args.with_git
    assert args.with_go
    assert args.with_python
    assert not args.with_node


def test_apply_detection_does_not_unset() -> None:
    args = cfp.ParsedArgs(with_git=True)
    cfp.apply_detection(args, cfp.DetectionResult(detected=[]))
    assert args.with_git


def test_merge_creates_default_mode_on_empty() -> None:
    merged = cfp.merge_permissions({}, ["A"], ["D1"], [], [])
    assert merged.permissions.default_mode == "acceptEdits"
    assert merged.permissions.allow == ["A"]
    assert merged.permissions.deny == ["D1"]


def test_merge_preserves_existing_default_mode() -> None:
    existing: dict[str, object] = {"permissions": {"defaultMode": "plan", "allow": [], "deny": []}}
    merged = cfp.merge_permissions(existing, [], [], [], [])
    assert merged.permissions.default_mode == "plan"


def test_merge_deduplicates_overlap() -> None:
    existing: dict[str, object] = {"permissions": {"allow": ["A", "B"], "deny": ["X"]}}
    merged = cfp.merge_permissions(existing, ["B", "C"], ["X", "Y"], ["A"], ["Z"])
    assert merged.permissions.allow == ["A", "B", "C"]
    assert merged.permissions.deny == ["X", "Y", "Z"]


def test_merge_sorts_alphabetically() -> None:
    merged = cfp.merge_permissions({}, ["C", "A", "B"], ["Z", "Y"], [], [])
    assert merged.permissions.allow == ["A", "B", "C"]
    assert merged.permissions.deny == ["Y", "Z"]


def test_merge_never_drops_existing_rules() -> None:
    existing: dict[str, object] = {
        "permissions": {"allow": ["LegacyRule(*)", "Custom(*)"], "deny": ["OldDeny(*)"]}
    }
    merged = cfp.merge_permissions(existing, cfp.BASE_ALLOW, cfp.BASE_DENY, [], [])
    assert "LegacyRule(*)" in merged.permissions.allow
    assert "Custom(*)" in merged.permissions.allow
    assert "OldDeny(*)" in merged.permissions.deny


def test_merge_ignores_non_string_entries() -> None:
    existing: dict[str, object] = {
        "permissions": {"allow": ["valid", 42, None, "alsoValid"], "deny": [True, "ok"]}
    }
    merged = cfp.merge_permissions(existing, [], [], [], [])
    assert "valid" in merged.permissions.allow
    assert "alsoValid" in merged.permissions.allow
    assert "42" not in merged.permissions.allow
    assert "ok" in merged.permissions.deny


def test_merge_ignores_corrupt_permissions_block() -> None:
    existing: dict[str, object] = {"permissions": "broken"}
    merged = cfp.merge_permissions(existing, ["A"], ["D"], [], [])
    assert merged.permissions.default_mode == "acceptEdits"
    assert merged.permissions.allow == ["A"]
    assert merged.permissions.deny == ["D"]


def test_merge_preserves_extra_top_level_keys() -> None:
    existing: dict[str, object] = {
        "permissions": {"allow": []},
        "customField": {"foo": "bar"},
    }
    merged = cfp.merge_permissions(existing, [], [], [], [])
    rendered = merged.to_json()
    assert rendered.get("customField") == {"foo": "bar"}


_perm_strings = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=30
)


@given(
    existing_allow=st.lists(_perm_strings, max_size=20),
    existing_deny=st.lists(_perm_strings, max_size=20),
    base_allow=st.lists(_perm_strings, max_size=20),
    base_deny=st.lists(_perm_strings, max_size=20),
    add_allow=st.lists(_perm_strings, max_size=20),
    add_deny=st.lists(_perm_strings, max_size=20),
)
def test_merge_property_unique_sorted_superset(
    existing_allow: list[str],
    existing_deny: list[str],
    base_allow: list[str],
    base_deny: list[str],
    add_allow: list[str],
    add_deny: list[str],
) -> None:
    existing: dict[str, object] = {"permissions": {"allow": existing_allow, "deny": existing_deny}}
    merged = cfp.merge_permissions(existing, base_allow, base_deny, add_allow, add_deny)
    allow_out = merged.permissions.allow
    deny_out = merged.permissions.deny

    assert len(allow_out) == len(set(allow_out))
    assert len(deny_out) == len(set(deny_out))
    assert allow_out == sorted(allow_out)
    assert deny_out == sorted(deny_out)

    expected_allow = set(existing_allow) | set(base_allow) | set(add_allow)
    expected_deny = set(existing_deny) | set(base_deny) | set(add_deny)
    assert set(allow_out) == expected_allow
    assert set(deny_out) == expected_deny


def test_run_creates_settings_file(tmp_path: Path) -> None:
    code, report = cfp.run(["--no-detect"], tmp_path)
    assert code == 0
    target = tmp_path / cfp.SETTINGS_RELATIVE
    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    perms = data["permissions"]
    assert perms["defaultMode"] == "acceptEdits"
    assert set(cfp.BASE_ALLOW).issubset(set(perms["allow"]))
    assert set(cfp.BASE_DENY).issubset(set(perms["deny"]))
    assert isinstance(report, cfp.RunReport)
    assert report.detected == []


def test_run_preserves_existing_rules(tmp_path: Path) -> None:
    target = tmp_path / cfp.SETTINGS_RELATIVE
    target.parent.mkdir(parents=True)
    existing_payload = {
        "permissions": {
            "defaultMode": "plan",
            "allow": ["CustomTool(*)"],
            "deny": ["BannedTool(*)"],
        }
    }
    target.write_text(json.dumps(existing_payload), encoding="utf-8")

    code, _ = cfp.run(["--no-detect"], tmp_path)
    assert code == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    perms = data["permissions"]
    assert perms["defaultMode"] == "plan"  # never overwritten
    assert "CustomTool(*)" in perms["allow"]
    assert "BannedTool(*)" in perms["deny"]


def test_run_with_git_adds_commit_rule(tmp_path: Path) -> None:
    code, _ = cfp.run(["--with-git", "--no-detect"], tmp_path)
    assert code == 0
    data = json.loads((tmp_path / cfp.SETTINGS_RELATIVE).read_text(encoding="utf-8"))
    perms = data["permissions"]
    assert "Bash(git commit -m *)" in perms["allow"]
    assert "Bash(git merge main *)" in perms["deny"]


def test_run_auto_detect_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    code, report = cfp.run([], tmp_path)
    assert code == 0
    assert isinstance(report, cfp.RunReport)
    assert "python" in report.detected
    assert "git" in report.detected
    assert report.with_python
    assert report.with_git


def test_run_no_detect_skips_marker_detection(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
    code, report = cfp.run(["--no-detect"], tmp_path)
    assert code == 0
    assert isinstance(report, cfp.RunReport)
    assert report.detected == []
    assert not report.with_go


def test_run_unknown_arg_returns_one(tmp_path: Path) -> None:
    code, payload = cfp.run(["--bogus"], tmp_path)
    assert code == 1
    assert isinstance(payload, str)
    assert "bogus" in payload


def test_run_help_returns_zero_with_usage(tmp_path: Path) -> None:
    code, payload = cfp.run(["--help"], tmp_path)
    assert code == 0
    assert isinstance(payload, str)
    assert "Usage:" in payload


def test_run_idempotent(tmp_path: Path) -> None:
    cfp.run(["--with-git", "--no-detect"], tmp_path)
    target = tmp_path / cfp.SETTINGS_RELATIVE
    first = target.read_text(encoding="utf-8")
    cfp.run(["--with-git", "--no-detect"], tmp_path)
    second = target.read_text(encoding="utf-8")
    assert first == second


def test_run_writes_via_io_json_atomic(tmp_path: Path) -> None:
    # Trigger run, then assert no stale .tmp files left behind.
    cfp.run(["--no-detect"], tmp_path)
    tmps = list((tmp_path / ".claude").glob(".*tmp*"))
    assert tmps == []
    target = tmp_path / cfp.SETTINGS_RELATIVE
    assert target.is_file()


def test_format_report_includes_detected() -> None:
    report = cfp.RunReport(
        detected=["git", "python"],
        default_mode="acceptEdits",
        after_allow=100,
        after_deny=40,
        new_allow=10,
        new_deny=5,
        with_git=True,
        with_go=False,
        with_python=True,
        with_node=False,
        git_commit_missing=False,
    )
    text = cfp.format_report(report)
    assert "detected:" in text
    assert "git, python" in text
    assert "allow rules: 100 (+10 new)" in text
    assert "deny rules:  40 (+5 new)" in text
    assert "git write:   ENABLED" in text
    assert "python:      OK" in text
    assert "go:" not in text


def test_format_report_disabled_git_hint() -> None:
    report = cfp.RunReport(
        detected=[],
        default_mode="acceptEdits",
        after_allow=0,
        after_deny=0,
        new_allow=0,
        new_deny=0,
        with_git=False,
        with_go=False,
        with_python=False,
        with_node=False,
        git_commit_missing=True,
    )
    text = cfp.format_report(report)
    assert "git write:   disabled" in text


def test_main_prints_report_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    code = cfp.main(["--no-detect"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Permissions updated" in out


def test_main_help_prints_usage_to_stdout(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    code = cfp.main(["--help"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Usage:" in out


def test_main_bad_arg_prints_to_stderr_and_returns_one(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    code = cfp.main(["--garbage"])
    assert code == 1
    err = capsys.readouterr().err
    assert "garbage" in err
    assert "Usage:" in err
