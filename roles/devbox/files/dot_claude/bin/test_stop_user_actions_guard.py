from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stop_user_actions_guard as guard

BIN_DIR = Path(__file__).resolve().parent
CODEX_COPY = BIN_DIR.parents[1] / "dot_codex" / "bin" / "stop_user_actions_guard.py"
FENCE = "```"
# Russian cases live in a data file so this source stays ASCII (ruff RUF001).
RU = json.loads(
    (BIN_DIR / "testdata" / "stop_user_actions_guard_ru.json").read_text(encoding="utf-8"),
)


def _raw(message: object, *, session: object = "s1", active: object = True) -> str:
    payload: dict[str, object] = {"session_id": session, "last_assistant_message": message}
    if active is not None:
        payload["stop_hook_active"] = active
    return json.dumps(payload)


def _reason(message: str, counter_dir: Path) -> str:
    output = guard.evaluate(_raw(message), counter_dir)
    assert output is not None, "expected a block"
    decoded = json.loads(output)
    assert decoded["decision"] == "block"
    return decoded["reason"]


def _allowed(message: str, counter_dir: Path) -> bool:
    return guard.evaluate(_raw(message), counter_dir) is None


def _section(body: str, heading: str = "## What I need from you") -> str:
    return f"Done: the parser is fixed.\n\n{heading}\n\n{body}\n"


class TestNothingRequired:
    def test_plain_report_without_section_is_allowed(self, tmp_path: Path) -> None:
        assert _allowed("Refactored the parser; all 42 tests pass.", tmp_path)

    def test_single_command_in_final_section_is_allowed(self, tmp_path: Path) -> None:
        message = _section(f"{FENCE}bash\nmake claude-push\n{FENCE}")
        assert _allowed(message, tmp_path)

    def test_russian_section_last_is_allowed(self, tmp_path: Path) -> None:
        message = _section(RU["section_body"], RU["section_headings"][0])
        assert _allowed(message, tmp_path)

    @pytest.mark.parametrize(
        "heading",
        [
            "# what i need from you",
            "#### WHAT I NEED FROM YOU:",
            "## What I need from you ##",
            "## **What I need from you**",
            *RU["section_headings"],
        ],
    )
    def test_heading_variants_are_recognised(self, tmp_path: Path, heading: str) -> None:
        message = _section("Approve the plan.", heading) + "\n## Next steps\n"
        assert "R1" in _reason(message, tmp_path)


class TestSectionMustBeLast:
    def test_heading_after_section_blocks(self, tmp_path: Path) -> None:
        message = _section("Approve the plan.") + "\n## Summary\n\nAll good.\n"
        reason = _reason(message, tmp_path)
        assert "R1" in reason
        assert '"Summary"' in reason

    def test_russian_section_followed_by_heading_blocks(self, tmp_path: Path) -> None:
        message = _section(RU["section_body"], RU["section_headings"][0])
        message += f"\n{RU['following_heading']}\n"
        assert "R1" in _reason(message, tmp_path)

    def test_hash_comment_inside_fence_is_not_a_heading(self, tmp_path: Path) -> None:
        message = _section(f"{FENCE}bash\n# deploy\nmake claude-push\n{FENCE}")
        assert _allowed(message, tmp_path)


class TestSectionCommandBlocks:
    @pytest.mark.parametrize("tag", ["bash", "sh", "zsh", "fish", "shell", "console", ""])
    def test_two_commands_in_shell_block_block(self, tmp_path: Path, tag: str) -> None:
        message = _section(f"{FENCE}{tag}\nmake lint\nmake test\n{FENCE}")
        reason = _reason(message, tmp_path)
        assert "R2" in reason
        assert "holds 2 command lines" in reason
        assert "ai_written_scripts/<slug>/" in reason

    def test_tilde_fence_is_recognised(self, tmp_path: Path) -> None:
        message = _section("~~~sh\nmake lint\nmake test\n~~~")
        assert "R2" in _reason(message, tmp_path)

    def test_non_shell_block_is_ignored(self, tmp_path: Path) -> None:
        message = _section(f"{FENCE}python\nimport os\nprint(os.getcwd())\n{FENCE}")
        assert _allowed(message, tmp_path)

    def test_blank_lines_comments_and_continuations_count_as_one(self, tmp_path: Path) -> None:
        body = "# push the config\n\nuv run pytest \\\n  --maxfail=1 \\\n  tests/\n"
        message = _section(f"{FENCE}bash\n{body}{FENCE}")
        assert _allowed(message, tmp_path)

    def test_console_prompt_is_stripped(self, tmp_path: Path) -> None:
        message = _section(f"{FENCE}console\n$ make qa\n{FENCE}")
        assert _allowed(message, tmp_path)

    @pytest.mark.parametrize(
        "command",
        [
            "for f in *.py; do ruff check $f; done",
            "if [ -f go.mod ]; then go test ./...; fi",
            "ls | while read -r f; do echo $f; done",
            "case $1 in a) echo a;; esac",
        ],
    )
    def test_single_line_control_flow_blocks(self, tmp_path: Path, command: str) -> None:
        message = _section(f"{FENCE}bash\n{command}\n{FENCE}")
        assert "contains shell control flow" in _reason(message, tmp_path)

    def test_heredoc_blocks(self, tmp_path: Path) -> None:
        message = _section(f"{FENCE}bash\ncat <<'EOF' > notes.txt\nhello\nEOF\n{FENCE}")
        assert "contains a heredoc" in _reason(message, tmp_path)

    def test_herestring_is_not_a_heredoc(self, tmp_path: Path) -> None:
        message = _section(f'{FENCE}bash\ngrep -c x <<< "$payload"\n{FENCE}')
        assert _allowed(message, tmp_path)

    def test_multi_command_block_outside_section_is_ignored(self, tmp_path: Path) -> None:
        message = f"I ran:\n\n{FENCE}bash\nmake lint\nmake test\n{FENCE}\n\nBoth passed.\n"
        assert _allowed(message, tmp_path)


class TestActionRequestsOutsideSection:
    @pytest.mark.parametrize(
        "sentence",
        [
            "Please run make lint before merging.",
            "You need to run the migration.",
            "You should run `make qa` next.",
            "Run the following to deploy:",
            *RU["requests"],
        ],
    )
    def test_request_in_prose_blocks(self, tmp_path: Path, sentence: str) -> None:
        reason = _reason(f"Fixed the bug.\n\n{sentence}\n", tmp_path)
        assert "R3" in reason
        assert '"What I need from you"' in reason

    @pytest.mark.parametrize(
        "sentence",
        [
            "I ran the following checks and all passed.",
            "The `please run` phrase is quoted as inline code.",
            *RU["reports"],
        ],
    )
    def test_reports_and_quoted_phrases_are_allowed(self, tmp_path: Path, sentence: str) -> None:
        assert _allowed(f"{sentence}\n", tmp_path)

    def test_request_inside_fence_is_allowed(self, tmp_path: Path) -> None:
        message = f"Log excerpt:\n\n{FENCE}text\nplease run the linter\n{FENCE}\n"
        assert _allowed(message, tmp_path)

    def test_request_inside_final_section_is_allowed(self, tmp_path: Path) -> None:
        message = _section(f"Please run:\n\n{FENCE}bash\nmake claude-push\n{FENCE}")
        assert _allowed(message, tmp_path)

    def test_every_violation_is_listed(self, tmp_path: Path) -> None:
        message = (
            "Please run the linter.\n\n## What I need from you\n\n"
            f"{FENCE}bash\nmake lint\nmake test\n{FENCE}\n\n## Notes\n"
        )
        reason = _reason(message, tmp_path)
        assert all(rule in reason for rule in ("R1", "R2", "R3"))


class TestLoopSafety:
    VIOLATION = "Please run make lint."

    def test_fourth_consecutive_violation_is_allowed_and_counter_resets(
        self,
        tmp_path: Path,
    ) -> None:
        outcomes = [
            guard.evaluate(_raw(self.VIOLATION, active=index > 0), tmp_path) for index in range(5)
        ]
        assert [outcome is not None for outcome in outcomes] == [True, True, True, False, True]

    def test_passing_message_resets_counter(self, tmp_path: Path) -> None:
        for _ in range(2):
            assert guard.evaluate(_raw(self.VIOLATION), tmp_path) is not None
        assert guard.evaluate(_raw("All done."), tmp_path) is None
        assert not list(tmp_path.glob("*.count"))

    def test_fresh_stop_chain_restarts_count(self, tmp_path: Path) -> None:
        for _ in range(3):
            assert guard.evaluate(_raw(self.VIOLATION), tmp_path) is not None
        assert guard.evaluate(_raw(self.VIOLATION, active=False), tmp_path) is not None

    def test_absent_flag_keeps_stored_count(self, tmp_path: Path) -> None:
        outcomes = [guard.evaluate(_raw(self.VIOLATION, active=None), tmp_path) for _ in range(4)]
        assert outcomes[3] is None

    def test_sessions_are_counted_separately(self, tmp_path: Path) -> None:
        for _ in range(3):
            assert guard.evaluate(_raw(self.VIOLATION, session="a"), tmp_path) is not None
        assert guard.evaluate(_raw(self.VIOLATION, session="b"), tmp_path) is not None

    def test_session_id_cannot_escape_counter_dir(self, tmp_path: Path) -> None:
        counter_dir = tmp_path / "counters"
        guard.evaluate(_raw(self.VIOLATION, session="../../escape"), counter_dir)
        assert [path.parent for path in tmp_path.rglob("*.count")] == [counter_dir]

    def test_unwritable_counter_fails_open(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("", encoding="utf-8")
        assert guard.evaluate(_raw(self.VIOLATION), blocker) is None
        assert "cannot persist block counter" in capsys.readouterr().err


class TestMalformedInput:
    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "not json",
            "[1, 2]",
            json.dumps({"session_id": "s1"}),
            json.dumps({"session_id": "s1", "last_assistant_message": 7}),
        ],
    )
    def test_malformed_input_fails_open(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        raw: str,
    ) -> None:
        assert guard.evaluate(raw, tmp_path) is None
        assert "allowing" in capsys.readouterr().err


class TestProcess:
    def _run(self, stdin: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BIN_DIR / "stop_user_actions_guard.py")],
            input=stdin,
            capture_output=True,
            text=True,
            env={**os.environ, "TMPDIR": str(tmp_path)},
            check=False,
            timeout=10,
        )

    def test_block_is_json_on_stdout_with_exit_zero(self, tmp_path: Path) -> None:
        completed = self._run(_raw("Please run make lint."), tmp_path)
        assert completed.returncode == 0
        assert json.loads(completed.stdout)["decision"] == "block"

    def test_malformed_input_exits_zero_silently(self, tmp_path: Path) -> None:
        completed = self._run("{", tmp_path)
        assert completed.returncode == 0
        assert completed.stdout == ""


def test_codex_copy_is_byte_identical() -> None:
    assert CODEX_COPY.read_bytes() == (BIN_DIR / "stop_user_actions_guard.py").read_bytes()
