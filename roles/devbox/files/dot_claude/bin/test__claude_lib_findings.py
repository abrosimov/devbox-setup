from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import findings


def test_located_lines_cover_ruff_golangci_and_hadolint_shapes(tmp_path: Path) -> None:
    output = (
        "a.py:3:5: F541 f-string without any placeholders\n"
        "pkg/b.go:7:2: Error return value is not checked (errcheck)\n"
        "Dockerfile:4 DL4000 error: MAINTAINER is deprecated\n"
        "Found 1 error.\n"
        "* errcheck: 1\n"
        'level=warning msg="cache: operation not permitted"\n'
    )
    parsed = findings.parse_located_lines(output, tmp_path)
    assert [(item.path.name, item.line) for item in parsed] == [
        ("a.py", 3),
        ("b.go", 7),
        ("Dockerfile", 4),
    ]
    assert parsed[0].message == "F541 f-string without any placeholders"


def test_json_report_covers_eslint_and_dclint_shapes(tmp_path: Path) -> None:
    output = json.dumps(
        [
            {
                "filePath": str(tmp_path / "a.ts"),
                "messages": [{"ruleId": "no-var", "severity": 2, "message": "No var.", "line": 2}],
            },
            {
                "filePath": "compose.yml",
                "messages": [{"rule": "r", "type": "warning", "message": "Quote.", "line": 6}],
            },
        ],
    )
    parsed = findings.parse_json_report(output, tmp_path)
    assert [item.render() for item in parsed] == [
        "a.ts:2: error No var. (no-var)",
        "compose.yml:6: warning Quote. (r)",
    ]


def test_json_report_tolerates_garbage(tmp_path: Path) -> None:
    assert findings.parse_json_report("not json", tmp_path) == []
    assert findings.parse_json_report('{"a": 1}', tmp_path) == []


def test_on_lines_keeps_only_touched_lines_and_none_keeps_all(tmp_path: Path) -> None:
    items = [findings.Finding(tmp_path / "a.py", line, "m") for line in (1, 2, 3)]
    assert [item.line for item in findings.on_lines(items, frozenset({2}))] == [2]
    assert findings.on_lines(items, None) == items


def test_dedupe_key_survives_line_shift_but_not_a_different_site(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    before = findings.Finding(path, 2, "F541 f-string").dedupe_key("ruff", ["x", "f'a'"])
    shifted = findings.Finding(path, 3, "F541 f-string").dedupe_key("ruff", ["new", "x", "f'a'"])
    other = findings.Finding(path, 1, "F541 f-string").dedupe_key("ruff", ["f'b'", "x"])
    assert before == shifted
    assert before != other


def test_hadolint_low_severity_lines_are_dropped() -> None:
    output = (
        "Dockerfile:1 DL3006 warning: tag\nDockerfile:2 DL3015 info: x\nDockerfile:3 X style: y"
    )
    assert findings.drop_hadolint_low_severity_lines(output) == "Dockerfile:1 DL3006 warning: tag"
