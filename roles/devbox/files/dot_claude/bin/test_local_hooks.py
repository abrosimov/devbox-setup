from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import local_hooks

SCRIPT = Path(__file__).resolve().parent / "local_hooks.py"
PAYLOAD = b'{"session_id": "s1", "hook_event_name": "Stop", "note": "\xc3\xa9"}'


def _write_config(path: Path, config: object) -> Path:
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def _run_script(
    home: Path, *args: str, payload: bytes = PAYLOAD
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=payload,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        cwd=home,
        check=False,
        timeout=30,
    )


class TestLoadCommands:
    def test_missing_config_is_silent_noop(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert local_hooks.load_commands(tmp_path / "absent.json", "Stop") == []
        assert capsys.readouterr().err == ""

    def test_unknown_event_is_silent_noop(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config = _write_config(tmp_path / "c.json", {"SessionEnd": [{"command": "true"}]})
        assert local_hooks.load_commands(config, "Stop") == []
        assert capsys.readouterr().err == ""

    def test_valid_entries_keep_order_and_default_timeout(self, tmp_path: Path) -> None:
        config = _write_config(
            tmp_path / "c.json",
            {"Stop": [{"command": "first", "timeout": 5}, {"command": "second"}]},
        )
        assert local_hooks.load_commands(config, "Stop") == [
            local_hooks.LocalCommand("first", 5.0),
            local_hooks.LocalCommand("second", local_hooks.DEFAULT_TIMEOUT_SECONDS),
        ]

    @pytest.mark.parametrize("raw", ["{not json", "[]", '"Stop"'])
    def test_malformed_config_is_noted_and_ignored(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], raw: str
    ) -> None:
        config = tmp_path / "c.json"
        config.write_text(raw, encoding="utf-8")
        assert local_hooks.load_commands(config, "Stop") == []
        assert "[local-hooks]" in capsys.readouterr().err

    def test_event_value_not_a_list_is_noted(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config = _write_config(tmp_path / "c.json", {"Stop": {"command": "true"}})
        assert local_hooks.load_commands(config, "Stop") == []
        assert "not a list" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "entry",
        [
            "true",
            {},
            {"command": ""},
            {"command": "   "},
            {"command": 42},
            {"command": "true", "timeout": 0},
            {"command": "true", "timeout": -1},
            {"command": "true", "timeout": "10"},
            {"command": "true", "timeout": True},
            {"command": "true", "timeout": None},
        ],
    )
    def test_invalid_entry_is_skipped_but_valid_ones_survive(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], entry: object
    ) -> None:
        config = _write_config(tmp_path / "c.json", {"Stop": [entry, {"command": "kept"}]})
        assert local_hooks.load_commands(config, "Stop") == [
            local_hooks.LocalCommand("kept", local_hooks.DEFAULT_TIMEOUT_SECONDS),
        ]
        assert "Stop[0] skipped" in capsys.readouterr().err

    def test_non_finite_timeout_is_skipped(self, tmp_path: Path) -> None:
        config = tmp_path / "c.json"
        config.write_text('{"Stop": [{"command": "true", "timeout": Infinity}]}', encoding="utf-8")
        assert local_hooks.load_commands(config, "Stop") == []


class TestRunCommand:
    def test_payload_reaches_command_unchanged(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        local_hooks.run_command(local_hooks.LocalCommand(f"cat > '{out}'", 10), PAYLOAD)
        assert out.read_bytes() == PAYLOAD

    def test_failing_command_is_noted_with_stderr_tail(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        local_hooks.run_command(local_hooks.LocalCommand("echo boom >&2; exit 3", 10), PAYLOAD)
        err = capsys.readouterr().err
        assert "exited 3" in err
        assert "boom" in err

    def test_timeout_kills_the_whole_process_group(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        marker = tmp_path / "marker"
        command = f"(sleep 1; touch '{marker}') & wait"
        started = time.monotonic()
        local_hooks.run_command(local_hooks.LocalCommand(command, 0.2), PAYLOAD)
        assert time.monotonic() - started < 1
        assert "timed out after 0.2s" in capsys.readouterr().err
        time.sleep(1.5)
        assert not marker.exists()


class TestScript:
    def test_runs_event_commands_in_order_without_stdout(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        log = tmp_path / "log"
        _write_config(
            claude_dir / "local-hooks.json",
            {
                "Stop": [
                    {"command": f"echo leaked; echo first >> '{log}'"},
                    {"command": f"cat >> '{log}'"},
                ],
                "SessionEnd": [{"command": f"echo wrong-event >> '{log}'"}],
            },
        )
        result = _run_script(tmp_path, "Stop")
        assert result.returncode == 0
        assert result.stdout == b""
        assert log.read_bytes() == b"first\n" + PAYLOAD

    def test_failing_and_timing_out_commands_still_exit_zero(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        _write_config(
            claude_dir / "local-hooks.json",
            {"Stop": [{"command": "exit 2"}, {"command": "sleep 5", "timeout": 0.2}]},
        )
        result = _run_script(tmp_path, "Stop")
        assert result.returncode == 0
        assert result.stdout == b""

    @pytest.mark.parametrize("args", [(), ("Stop",)])
    def test_missing_argument_or_config_exits_zero(
        self, tmp_path: Path, args: tuple[str, ...]
    ) -> None:
        result = _run_script(tmp_path, *args)
        assert result.returncode == 0
        assert result.stdout == b""
