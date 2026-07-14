from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_lint_settings as cls


def test_parse_args_defaults() -> None:
    parsed = cls.parse_args([])
    assert isinstance(parsed, cls.ParsedArgs)
    assert not parsed.scan_all
    assert not parsed.as_json
    assert not parsed.quiet
    assert not parsed.show_usage


def test_parse_args_flags() -> None:
    parsed = cls.parse_args(["--all", "--json", "--quiet"])
    assert isinstance(parsed, cls.ParsedArgs)
    assert parsed.scan_all
    assert parsed.as_json
    assert parsed.quiet


def test_parse_args_help() -> None:
    parsed = cls.parse_args(["-h"])
    assert isinstance(parsed, cls.ParsedArgs)
    assert parsed.show_usage


def test_parse_args_unknown() -> None:
    parsed = cls.parse_args(["--nope"])
    assert isinstance(parsed, cls.ParseFailure)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Bash(git push *)", ("Bash", "git push *")),
        ("Read", ("Read", None)),
        ("mcp__*", ("mcp__*", None)),
        ("Edit(**/*.pem)", ("Edit", "**/*.pem")),
    ],
)
def test_split_rule(raw: str, expected: tuple[str, str | None]) -> None:
    assert cls.split_rule(raw) == expected


@pytest.mark.parametrize(
    ("inner", "expected"),
    [
        (None, ""),
        ("git reset:*", "git reset"),
        ("git push origin *", "git push origin"),
        ("git push * :*", None),  # interior '*' -> unsafe, not a clean prefix
        ("git push * main", None),  # not a trailing wildcard
        ("git status", None),  # exact rule
    ],
)
def test_deny_prefix(inner: str | None, expected: str | None) -> None:
    assert cls.deny_prefix(inner) == expected


@pytest.mark.parametrize(
    ("inner", "expected"),
    [
        ("git reset:*", "git reset"),
        ("git reset *", "git reset"),
        ("git status", None),
        (None, None),
    ],
)
def test_wildcard_base(inner: str | None, expected: str | None) -> None:
    assert cls.wildcard_base(inner) == expected


def _allow(raw: str, layer: str = "project") -> cls.Rule:
    tool, inner = cls.split_rule(raw)
    return cls.Rule(tool=tool, inner=inner, raw=raw, layer=layer, verb="allow")


def _deny(raw: str, layer: str = "user") -> cls.Rule:
    tool, inner = cls.split_rule(raw)
    return cls.Rule(tool=tool, inner=inner, raw=raw, layer=layer, verb="deny")


def test_deny_covers_allow_glob() -> None:
    assert cls.deny_covers_allow(_deny("Bash(git push *)"), _allow("Bash(git push origin main)"))


def test_deny_covers_allow_prefix_form() -> None:
    assert cls.deny_covers_allow(_deny("Bash(git reset:*)"), _allow("Bash(git reset --hard HEAD)"))


def test_deny_covers_allow_colon_boundary() -> None:
    assert cls.deny_covers_allow(_deny("Bash(rm:*)"), _allow("Bash(rm:roles/skills/**)"))


def test_deny_does_not_cover_other_tool() -> None:
    assert not cls.deny_covers_allow(_deny("Bash(rm *)"), _allow("Edit(rm anything)"))


def test_deny_does_not_over_match() -> None:
    assert not cls.deny_covers_allow(_deny("Bash(git push *)"), _allow("Bash(git status)"))


def test_deny_respects_word_boundary() -> None:
    # `ls *` must not swallow `lsof` -- the prefix has to end at a boundary.
    assert not cls.deny_covers_allow(_deny("Bash(ls *)"), _allow("Bash(lsof -i)"))


def test_interior_wildcard_deny_makes_no_claim() -> None:
    # `git push * :*` has a literal ' :' Claude keeps literal; it does NOT
    # subsume `git push origin main`, so the allow stays alive.
    assert not cls.deny_covers_allow(
        _deny("Bash(git push * :*)"), _allow("Bash(git push origin *)")
    )


def _layer(rules: list[cls.Rule], name: str) -> cls.LoadedLayer:
    return cls.LoadedLayer(name, Path(f"/{name}"), rules, None, [])


def test_analyse_dead_allow() -> None:
    layers = [
        _layer([_deny("Bash(git push *)", "user")], "user"),
        _layer([_allow("Bash(git push origin main)", "project")], "project"),
    ]
    kinds = {f.kind for f in cls.analyse(layers)}
    assert "dead-allow" in kinds


def test_analyse_exact_conflict() -> None:
    layers = [
        _layer([_deny("Bash(rm *)", "user")], "user"),
        _layer([_allow("Bash(rm *)", "local")], "local"),
    ]
    kinds = {f.kind for f in cls.analyse(layers)}
    assert "allow-deny-conflict" in kinds
    assert "dead-allow" not in kinds  # exact match is reported once, as conflict


def test_analyse_syntax_variant() -> None:
    layers = [
        _layer([_deny("Bash(git reset:*)", "user")], "user"),
        _layer([_deny("Bash(git reset *)", "project")], "project"),
    ]
    kinds = {f.kind for f in cls.analyse(layers)}
    assert "syntax-variant" in kinds


def test_analyse_clean() -> None:
    layers = [
        _layer([_allow("Bash(go test *)", "project"), _deny("Bash(rm *)", "user")], "mix"),
    ]
    assert cls.analyse(layers) == []


def test_load_layer_unparseable(tmp_path: Path) -> None:
    bad = tmp_path / "settings.json"
    bad.write_text("{ not json", encoding="utf-8")
    loaded = cls.load_layer(bad, "project")
    assert loaded.parse_error is not None


def test_load_layer_duplicate(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps({"permissions": {"allow": ["Bash(ls *)", "Bash(ls *)"]}}),
        encoding="utf-8",
    )
    loaded = cls.load_layer(target, "project")
    assert any(f.kind == "duplicate" for f in loaded.dup_findings)


def test_run_clean_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    claude = tmp_path / "proj" / ".claude"
    claude.mkdir(parents=True)
    (claude / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(go build *)"], "deny": ["Bash(rm *)"]}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    exit_code, reports = cls.run([], claude.parent)
    assert exit_code == 0
    assert isinstance(reports, list)


def test_run_reports_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"deny": ["Bash(git push *)"]}}),
        encoding="utf-8",
    )
    claude = tmp_path / "proj" / ".claude"
    claude.mkdir(parents=True)
    (claude / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(git push origin main)"]}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    exit_code, reports = cls.run([], claude.parent)
    assert exit_code == 1
    assert isinstance(reports, list)
    assert any(f.kind == "dead-allow" for r in reports for f in r.findings)


def test_run_no_claude_dir(tmp_path: Path) -> None:
    exit_code, payload = cls.run([], tmp_path)
    assert exit_code == 2
    assert isinstance(payload, str)
