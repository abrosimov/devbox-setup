from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent))

import universal_logger as logger


def _stamp(event_name: str, payload: dict[str, object], root: Path) -> dict[str, object]:
    return cast("dict[str, object]", logger.build_log_entry(event_name, payload, root)["stamp"])


def _config_root(tmp_path: Path) -> Path:
    root = tmp_path / ".claude"
    root.mkdir()
    (root / "CLAUDE.md").write_bytes(b"# rules v1\n")
    (root / "settings.json").write_bytes(b'{"env": {}}\n')
    return root


def test_session_start_is_stamped_with_the_deployed_artefact_digests(tmp_path: Path) -> None:
    root = _config_root(tmp_path)

    stamp = _stamp("SessionStart", {"model": "claude-opus-5"}, root)

    assert stamp == {
        "rules_sha256": hashlib.sha256(b"# rules v1\n").hexdigest(),
        "settings_sha256": hashlib.sha256(b'{"env": {}}\n').hexdigest(),
        "model": "claude-opus-5",
    }


def test_the_stamp_changes_when_the_rules_change(tmp_path: Path) -> None:
    root = _config_root(tmp_path)
    before = _stamp("SessionStart", {}, root)
    (root / "CLAUDE.md").write_bytes(b"# rules v2\n")

    after = _stamp("SessionStart", {}, root)

    assert before["rules_sha256"] != after["rules_sha256"]
    assert before["settings_sha256"] == after["settings_sha256"]


def test_a_missing_artefact_or_model_is_recorded_as_null_not_an_error(tmp_path: Path) -> None:
    root = tmp_path / ".claude"
    root.mkdir()

    stamp = _stamp("SessionStart", {}, root)

    assert stamp == {"rules_sha256": None, "settings_sha256": None, "model": None}


def test_other_events_carry_no_stamp(tmp_path: Path) -> None:
    root = _config_root(tmp_path)

    entry = logger.build_log_entry("PreToolUse", {"tool_name": "Bash"}, root)

    assert "stamp" not in entry
    assert entry["event"] == "PreToolUse"
    assert entry["payload"] == {"tool_name": "Bash"}
