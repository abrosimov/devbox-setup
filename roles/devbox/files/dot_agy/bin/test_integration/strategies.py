"""Hypothesis strategies for generating Claude Code hook payloads.

One strategy per lifecycle ID (matching the bucket names used by recorded
fixtures: ``pre_tool_use_bash``, ``pre_tool_use_edit``, ``post_tool_use_*``,
``stop``, ``permission_request``, ``pre_compact``).

Used by:
- ``test_integration.py`` — hypothesis property tests with permanent
  ``@example`` regression pins.
- ``generate_fixtures.py`` — materialises N examples per lifecycle to disk
  as synthetic fixtures consumed by the smoke regression.

Schemas follow Claude Code 2026 hooks reference. PreToolUse / PostToolUse /
Stop / PreCompact shapes verified against:
- https://code.claude.com/docs/en/hooks (fetched 2026-06-21)
- https://gist.github.com/FrancisBourre/50dca37124ecc43eaf08328cdcccdb34
PermissionRequest mirrors PreToolUse (``tool_name`` + ``tool_input``); the
shape diverges only on the OUTPUT side (``hookSpecificOutput.decision.behavior``).
"""

from __future__ import annotations

from typing import Final

from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

# Restrict to printable ASCII minus a few shell-hostile characters. Anonymise
# would replace any leftover PII but we keep the input space modest so the
# generator runs in seconds, not minutes.
_SAFE_TEXT_CHARS: Final = st.characters(
    min_codepoint=0x20,
    max_codepoint=0x7E,
    blacklist_characters="`\\\0",
)

_SHORT_TEXT: Final = st.text(_SAFE_TEXT_CHARS, min_size=0, max_size=40)
_LINE_TEXT: Final = st.text(_SAFE_TEXT_CHARS, min_size=0, max_size=120)
_MULTILINE_TEXT: Final = st.text(_SAFE_TEXT_CHARS, min_size=0, max_size=400)

# A handful of canonical file-path shapes. We deliberately bias toward
# placeholder paths (<HOME>, <TMPDIR>) and known-safe absolute paths so the
# scripts under test see realistic input rather than fuzzed nonsense.
_FILE_PATH_TEMPLATES: Final[tuple[str, ...]] = (
    "<HOME>/Projects/repo/file.py",
    "<HOME>/Projects/repo/src/lib.rs",
    "<HOME>/Projects/repo/internal/foo/bar.go",
    "<HOME>/Projects/repo/README.md",
    "<HOME>/.config/fish/config.fish",
    "<TMPDIR>/scratch.txt",
    "/etc/hostname",
    "/nonexistent/path.txt",
    "/usr/local/bin/something",
)


def file_path() -> st.SearchStrategy[str]:
    return st.sampled_from(_FILE_PATH_TEMPLATES)


# ---------------------------------------------------------------------------
# Bash command shapes — re-uses the templates from test_hypothesis_parity.py.
# Kept here so generate_fixtures.py can import independently.
# ---------------------------------------------------------------------------

_BASH_COMMAND_TEMPLATES: Final[tuple[str, ...]] = (
    "echo {}",
    "ls {}",
    "cat {}",
    "rm -rf {}",
    "rm {}",
    "git status",
    "git push origin master",
    "git reset --hard",
    "git rebase main",
    "git commit --amend",
    "go build ./...",
    "go fmt",
    "gofmt -w .",
    "pip install requests",
    "python -m venv .venv",
    "pytest -k {}",
    "mypy {}",
    "uv run pytest",
    "kubectl delete ns prod",
    "find / -name *.log",
    "rm -rf /tmp/{}",
    "ENV=prod {} ./script.sh",
    "cd /tmp && ls",
    'echo "$(cat /etc/passwd)"',
    "drop table users",
    "DROP DATABASE foo",
    "echo hello",
)

_BASH_FRAGMENT: Final = st.text(_SAFE_TEXT_CHARS, min_size=0, max_size=40)


def bash_command() -> st.SearchStrategy[str]:
    return st.builds(
        lambda template, fragment: template.format(fragment) if "{}" in template else template,
        st.sampled_from(_BASH_COMMAND_TEMPLATES),
        _BASH_FRAGMENT,
    )


# ---------------------------------------------------------------------------
# Hook payload strategies — one per lifecycle bucket.
# ---------------------------------------------------------------------------


def pre_tool_use_bash() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda cmd, desc: {
            "tool_name": "Bash",
            "tool_input": {"command": cmd, "description": desc},
            "hook_event_name": "PreToolUse",
        },
        bash_command(),
        _SHORT_TEXT,
    )


def pre_tool_use_edit() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda path, old, new, replace_all: {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": path,
                "old_string": old,
                "new_string": new,
                "replace_all": replace_all,
            },
            "hook_event_name": "PreToolUse",
        },
        file_path(),
        _LINE_TEXT,
        _LINE_TEXT,
        st.booleans(),
    )


def pre_tool_use_write() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda path, content: {
            "tool_name": "Write",
            "tool_input": {"file_path": path, "content": content},
            "hook_event_name": "PreToolUse",
        },
        file_path(),
        _MULTILINE_TEXT,
    )


def pre_tool_use_multiedit() -> st.SearchStrategy[dict[str, object]]:
    edit_entry = st.builds(
        lambda old, new, replace_all: {
            "old_string": old,
            "new_string": new,
            "replace_all": replace_all,
        },
        _LINE_TEXT,
        _LINE_TEXT,
        st.booleans(),
    )
    return st.builds(
        lambda path, edits: {
            "tool_name": "MultiEdit",
            "tool_input": {"file_path": path, "edits": edits},
            "hook_event_name": "PreToolUse",
        },
        file_path(),
        st.lists(edit_entry, min_size=1, max_size=4),
    )


def post_tool_use_edit() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda path, old, new, response: {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": path,
                "old_string": old,
                "new_string": new,
                "replace_all": False,
            },
            "tool_response": response,
            "hook_event_name": "PostToolUse",
        },
        file_path(),
        _LINE_TEXT,
        _LINE_TEXT,
        _SHORT_TEXT,
    )


def post_tool_use_write() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda path, content, response: {
            "tool_name": "Write",
            "tool_input": {"file_path": path, "content": content},
            "tool_response": response,
            "hook_event_name": "PostToolUse",
        },
        file_path(),
        _MULTILINE_TEXT,
        _SHORT_TEXT,
    )


# ---------------------------------------------------------------------------
# Stop / PreCompact / PermissionRequest.
# Schema sources cited at module docstring.
# ---------------------------------------------------------------------------


_SESSION_ID = st.from_regex(r"sess_[a-z0-9]{8,16}", fullmatch=True)
_TRANSCRIPT_PATH = st.sampled_from(
    [
        "<HOME>/.claude/sessions/sess_aaaaaaaa/transcript.jsonl",
        "<HOME>/.claude/sessions/sess_bbbbbbbb/transcript.jsonl",
        "<TMPDIR>/transcript.jsonl",
    ],
)
_CWD = st.sampled_from(
    [
        "<HOME>/Projects/repo",
        "<HOME>/Projects/other",
        "<TMPDIR>",
    ],
)


def stop() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda sid, tpath, cwd, active: {
            "session_id": sid,
            "transcript_path": tpath,
            "cwd": cwd,
            "hook_event_name": "Stop",
            "stop_hook_active": active,
        },
        _SESSION_ID,
        _TRANSCRIPT_PATH,
        _CWD,
        st.booleans(),
    )


def pre_compact() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda sid, tpath, cwd, trigger, instr: {
            "session_id": sid,
            "transcript_path": tpath,
            "cwd": cwd,
            "hook_event_name": "PreCompact",
            "trigger": trigger,
            "custom_instructions": instr,
        },
        _SESSION_ID,
        _TRANSCRIPT_PATH,
        _CWD,
        st.sampled_from(["manual", "auto"]),
        _SHORT_TEXT,
    )


# PermissionRequest shares the PreToolUse stdin shape — same fields plus
# ``hook_event_name`` set to ``PermissionRequest`` and (optionally) a
# ``permission_suggestions`` array. We sample tool_name from the four matchers
# the auto-approve hook actually distinguishes.
_PERMISSION_TOOLS: Final[tuple[str, ...]] = ("Bash", "Edit", "Write", "MultiEdit")


def _permission_tool_input(tool: str) -> st.SearchStrategy[dict[str, object]]:
    if tool == "Bash":
        return st.builds(
            lambda cmd: {"command": cmd},
            bash_command(),
        )
    if tool == "Write":
        return st.builds(
            lambda path, content: {"file_path": path, "content": content},
            file_path(),
            _MULTILINE_TEXT,
        )
    if tool == "Edit":
        return st.builds(
            lambda path, old, new: {
                "file_path": path,
                "old_string": old,
                "new_string": new,
                "replace_all": False,
            },
            file_path(),
            _LINE_TEXT,
            _LINE_TEXT,
        )
    # MultiEdit
    edit_entry = st.builds(
        lambda old, new: {"old_string": old, "new_string": new, "replace_all": False},
        _LINE_TEXT,
        _LINE_TEXT,
    )
    return st.builds(
        lambda path, edits: {"file_path": path, "edits": edits},
        file_path(),
        st.lists(edit_entry, min_size=1, max_size=3),
    )


def permission_request() -> st.SearchStrategy[dict[str, object]]:
    def _build(tool: str, tool_input: dict[str, object], sid: str) -> dict[str, object]:
        return {
            "session_id": sid,
            "hook_event_name": "PermissionRequest",
            "tool_name": tool,
            "tool_input": tool_input,
        }

    return st.sampled_from(_PERMISSION_TOOLS).flatmap(
        lambda tool: st.builds(_build, st.just(tool), _permission_tool_input(tool), _SESSION_ID),
    )


# ---------------------------------------------------------------------------
# Lifecycle → strategy table (used by generate_fixtures.py).
# ---------------------------------------------------------------------------


LIFECYCLE_STRATEGIES: dict[str, st.SearchStrategy[dict[str, object]]] = {
    "pre_tool_use_bash": pre_tool_use_bash(),
    "pre_tool_use_edit": pre_tool_use_edit(),
    "pre_tool_use_write": pre_tool_use_write(),
    "pre_tool_use_multiedit": pre_tool_use_multiedit(),
    "post_tool_use_edit": post_tool_use_edit(),
    "post_tool_use_write": post_tool_use_write(),
    "stop": stop(),
    "pre_compact": pre_compact(),
    "permission_request": permission_request(),
}
