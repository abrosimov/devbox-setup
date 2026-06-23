from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_plan_code_guard

if TYPE_CHECKING:
    import pytest


def test_find_code_clean_prose() -> None:
    content = "# Plan\n\n| FR | AC |\n|----|----|\n| 1 | x |\n"
    assert pre_plan_code_guard.find_code(content) == []


def test_find_code_rejects_go_fence() -> None:
    violations = pre_plan_code_guard.find_code("## X\n\n```go\nfunc Foo() {}\n```\n")
    assert any("```go" in v for v in violations)


def test_find_code_rejects_python_fence() -> None:
    violations = pre_plan_code_guard.find_code("```python\ndef foo():\n    pass\n```\n")
    assert any("```python" in v for v in violations)


def test_find_code_accepts_json_block() -> None:
    assert pre_plan_code_guard.find_code('```json\n{"a": 1}\n```\n') == []


def test_find_code_accepts_mermaid_block() -> None:
    assert pre_plan_code_guard.find_code("```mermaid\ngraph TD; A-->B\n```\n") == []


def test_find_code_rejects_untagged_code() -> None:
    content = "```\nclass Foo:\n    def bar(self):\n        return 1\n```\n"
    violations = pre_plan_code_guard.find_code(content)
    assert any("untagged" in v for v in violations)


def test_find_code_accepts_untagged_prose() -> None:
    content = "```\nThis is just an example sentence.\nAnother sentence here.\n```\n"
    assert pre_plan_code_guard.find_code(content) == []


def test_find_code_accepts_bash_single_line() -> None:
    assert pre_plan_code_guard.find_code("```bash\ngo build ./...\n```\n") == []


def test_find_code_rejects_bash_with_code() -> None:
    violations = pre_plan_code_guard.find_code("```bash\nfunc main() {}\n```\n")
    assert violations


def test_is_plan_file_true_only_for_plan_md() -> None:
    assert pre_plan_code_guard.is_plan_file("/x/y/plan.md")
    assert pre_plan_code_guard.is_plan_file("plan.md")
    assert not pre_plan_code_guard.is_plan_file("/x/y/spec.md")
    assert not pre_plan_code_guard.is_plan_file("")


def test_collect_write_content_handles_multi_edit() -> None:
    payload: dict[str, object] = {
        "edits": [
            {"new_string": "first"},
            {"new_string": "second"},
            {"old_string": "ignore"},
        ],
    }
    assert pre_plan_code_guard.collect_write_content("MultiEdit", payload) == "first\nsecond"


def test_collect_write_content_edit_uses_new_string() -> None:
    assert pre_plan_code_guard.collect_write_content("Edit", {"new_string": "abc"}) == "abc"


def test_collect_write_content_write_uses_content() -> None:
    assert pre_plan_code_guard.collect_write_content("Write", {"content": "abc"}) == "abc"


def test_run_hook_passes_through_non_plan_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "/tmp/spec.md",
                        "content": "```go\nfunc x(){}\n```",
                    },
                }
            )
        ),
    )
    assert pre_plan_code_guard.run_hook() == 0


def test_run_hook_blocks_plan_with_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": "/x/plan.md", "content": "```go\nfunc x(){}\n```"},
                }
            )
        ),
    )
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_plan_code_guard.run_hook() == 2
    assert "BLOCKED" in err.getvalue()


def test_run_hook_allows_plan_with_only_prose(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": "/x/plan.md", "content": "# Plan\n\nProse only.\n"},
                }
            )
        ),
    )
    assert pre_plan_code_guard.run_hook() == 0


def test_run_cli_missing_file_returns_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_plan_code_guard.run_cli(["--file"]) == 10


def test_run_cli_pass_for_clean_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "plan.md"
    target.write_text("# Plan\n\nProse.\n", encoding="utf-8")
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert pre_plan_code_guard.run_cli(["--file", str(target)]) == 0
    assert "PASS" in out.getvalue()


def test_run_cli_fail_for_code_block(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "plan.md"
    target.write_text("```go\nfunc x(){}\n```\n", encoding="utf-8")
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    assert pre_plan_code_guard.run_cli(["--file", str(target)]) == 2
    assert "FAIL" in err.getvalue()


def test_self_test_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    assert pre_plan_code_guard.self_test() == 0
    assert "self-test: PASS" in out.getvalue()


# Hypothesis fuzz: detector never crashes on arbitrary markdown
_md_alphabet = st.characters(
    blacklist_categories=("Cs",),
    blacklist_characters=("\x00",),
)


@given(st.text(alphabet=_md_alphabet, max_size=500))
def test_find_code_handles_arbitrary_text(content: str) -> None:
    result = pre_plan_code_guard.find_code(content)
    assert isinstance(result, list)
    for entry in result:
        assert isinstance(entry, str)


@given(
    lang=st.sampled_from(sorted(pre_plan_code_guard.CODE_LANGS)),
    body=st.text(alphabet=_md_alphabet, min_size=0, max_size=100),
)
def test_code_langs_always_flagged(lang: str, body: str) -> None:
    body = body.replace("```", "")
    content = f"```{lang}\n{body}\n```\n"
    assert pre_plan_code_guard.find_code(content), f"lang={lang}"


@given(
    lang=st.sampled_from(sorted(pre_plan_code_guard.SAFE_LANGS)),
    body=st.text(alphabet=_md_alphabet, min_size=0, max_size=100),
)
def test_safe_langs_never_flagged(lang: str, body: str) -> None:
    body = body.replace("```", "")
    content = f"```{lang}\n{body}\n```\n"
    assert pre_plan_code_guard.find_code(content) == []


@given(
    word=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu")), min_size=1, max_size=10
    ),
    body=st.text(alphabet=_md_alphabet, min_size=0, max_size=50),
)
def test_unknown_lang_falls_back_to_signature_count(word: str, body: str) -> None:
    body = body.replace("```", "")
    if word.lower() in pre_plan_code_guard.CODE_LANGS:
        return
    if word.lower() in pre_plan_code_guard.SAFE_LANGS:
        return
    if word.lower() in pre_plan_code_guard.ALWAYS_LANGS:
        return
    content = f"```{word}\n{body}\n```\n"
    result = pre_plan_code_guard.find_code(content)
    assert isinstance(result, list)
