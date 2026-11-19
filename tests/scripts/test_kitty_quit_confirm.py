from __future__ import annotations

import functools
import importlib.util
import inspect
import json
import logging
import shlex
import subprocess
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

KITTY_DIR = Path(__file__).resolve().parents[2] / "roles/devbox/files/.config/kitty"
QUIT_CONFIRM = KITTY_DIR / "quit_confirm.py"
KITTY_SESSION = KITTY_DIR / "kitty_session.py"
SESSION_ID = "0f3c9a52-7b1e-4d6a-9c10-5e8d2a4b6f70"

IDLE_FISH = {"pid": 100, "cwd": "/work", "cmdline": ["/opt/homebrew/bin/fish"]}
BUSY_VIM = {"pid": 200, "cwd": "/work", "cmdline": ["vim", "notes.txt"]}


@dataclass
class FakeTimer:
    delay: float
    callback: Callable[[], None]
    cancelled: bool = False
    fired: bool = False

    def cancel(self) -> None:
        self.cancelled = True


class FakeAsyncioLoop:
    def __init__(self) -> None:
        self.timers: list[FakeTimer] = []

    def call_later(self, delay: float, callback: Callable[[], None]) -> FakeTimer:
        timer = FakeTimer(delay, callback)
        self.timers.append(timer)
        return timer

    def pending(self) -> list[FakeTimer]:
        return [timer for timer in self.timers if not timer.cancelled and not timer.fired]

    def fire(self, timer: FakeTimer) -> None:
        timer.fired = True
        timer.callback()

    def fire_pending(self) -> None:
        (timer,) = self.pending()
        self.fire(timer)


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.start = start
        self.elapsed = 0.0

    def __call__(self) -> float:
        return self.start + self.elapsed


class StubHandler:
    def __init__(self) -> None:
        self.printed: list[str] = []
        self.screen: list[str] = []
        self.quit_code: int | None = None
        self.asyncio_loop = FakeAsyncioLoop()
        self.cmd = types.SimpleNamespace(
            set_window_title=lambda _title: None,
            clear_screen=self.screen.clear,
        )

    def print(self, *parts: str) -> None:
        self.printed.append("".join(parts))
        self.screen.append("".join(parts))

    def quit_loop(self, code: int) -> None:
        self.quit_code = code


class StubKeyEvent:
    def __init__(self, *names: str) -> None:
        self.names = names

    def matches(self, name: str) -> bool:
        return name in self.names


class Dialog(Protocol):
    printed: list[str]
    screen: list[str]
    quit_code: int | None
    answer: str
    asyncio_loop: FakeAsyncioLoop

    def initialize(self) -> None: ...

    def on_text(self, text: str) -> None: ...

    def on_key(self, key_event: StubKeyEvent) -> None: ...


def type_yes(dialog: Dialog) -> None:
    dialog.on_text("y")


@dataclass
class TuiScript:
    keystroke: Callable[[Dialog], None] = type_yes
    dialogs: list[Dialog] = field(default_factory=list)

    def shown_text(self) -> str:
        return "".join("".join(dialog.printed) for dialog in self.dialogs)


class ScriptedLoop:
    def __init__(self, script: TuiScript) -> None:
        self.script = script

    def loop(self, handler: Dialog) -> None:
        self.script.dialogs.append(handler)
        handler.initialize()
        self.script.keystroke(handler)


def passthrough_result_handler(
    **_options: object,
) -> Callable[[Callable[..., None]], Callable[..., None]]:
    return lambda function: function


class HandlerModule(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("kittens.tui.handler")
        self.Handler = StubHandler
        self.result_handler = passthrough_result_handler


class LoopModule(types.ModuleType):
    def __init__(self, script: TuiScript) -> None:
        super().__init__("kittens.tui.loop")
        self.Loop = lambda: ScriptedLoop(script)


@pytest.fixture
def tui(monkeypatch: pytest.MonkeyPatch) -> TuiScript:
    script = TuiScript()
    monkeypatch.setitem(sys.modules, "kittens", types.ModuleType("kittens"))
    monkeypatch.setitem(sys.modules, "kittens.tui", types.ModuleType("kittens.tui"))
    monkeypatch.setitem(sys.modules, "kittens.tui.handler", HandlerModule())
    monkeypatch.setitem(sys.modules, "kittens.tui.loop", LoopModule(script))
    return script


@dataclass
class SnapshotSpy:
    calls: int = 0
    error: Exception | None = None


class SnapshotModule(types.ModuleType):
    def __init__(self, spy: SnapshotSpy) -> None:
        super().__init__("kitty_session")
        self.spy = spy

    def save_snapshot(self) -> int:
        self.spy.calls += 1
        if self.spy.error is not None:
            raise self.spy.error
        return 1


@pytest.fixture
def snapshot(monkeypatch: pytest.MonkeyPatch) -> SnapshotSpy:
    spy = SnapshotSpy()
    monkeypatch.setitem(sys.modules, "kitty_session", SnapshotModule(spy))
    return spy


def load_module(name: str, path: Path, monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def kitty_ls(monkeypatch: pytest.MonkeyPatch, windows: list[dict[str, object]]) -> None:
    tab = {"id": 1, "title": "main", "layout": "splits", "windows": windows}
    tab["groups"] = [{"id": window["id"], "windows": [window["id"]]} for window in windows]
    output = json.dumps([{"is_focused": True, "tabs": [tab]}])

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    monkeypatch.setattr(subprocess, "run", run)


def idle_window() -> dict[str, object]:
    return {"id": 1, "cwd": "/work", "foreground_processes": [IDLE_FISH]}


def busy_window() -> dict[str, object]:
    return {"id": 1, "cwd": "/work", "foreground_processes": [IDLE_FISH, BUSY_VIM]}


@pytest.fixture
def quit_confirm(
    tui: TuiScript, snapshot: SnapshotSpy, monkeypatch: pytest.MonkeyPatch
) -> types.ModuleType:
    assert tui.dialogs == []
    assert snapshot.calls == 0
    return load_module("quit_confirm", QUIT_CONFIRM, monkeypatch)


class TestMainWithNothingBusy:
    def test_saves_the_snapshot_and_closes_without_a_dialog(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        kitty_ls(monkeypatch, [idle_window()])

        answer = quit_confirm.main([])

        assert answer == "close"
        assert snapshot.calls == 1
        assert tui.dialogs == []

    def test_unreadable_kitty_ls_still_saves_and_closes(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def failing(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(1, command)

        monkeypatch.setattr(subprocess, "run", failing)

        answer = quit_confirm.main([])

        assert answer == "close"
        assert snapshot.calls == 1
        assert tui.dialogs == []


class TestMainWithBusyTabs:
    def test_confirmed_close_lists_the_busy_tab_then_saves(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        kitty_ls(monkeypatch, [busy_window()])

        answer = quit_confirm.main([])

        assert answer == "close"
        assert snapshot.calls == 1
        assert len(tui.dialogs) == 1
        assert "main: vim notes.txt" in tui.shown_text()

    @pytest.mark.parametrize("text", ["n", "N", "x", "\r", ""])
    def test_declining_cancels_and_saves_nothing(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
        text: str,
    ) -> None:
        kitty_ls(monkeypatch, [busy_window()])
        tui.keystroke = lambda handler: handler.on_text(text)

        answer = quit_confirm.main([])

        assert answer == "cancel"
        assert snapshot.calls == 0

    @pytest.mark.parametrize("key", ["esc", "ctrl+c"])
    def test_escape_and_interrupt_cancel_and_save_nothing(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
        key: str,
    ) -> None:
        kitty_ls(monkeypatch, [busy_window()])
        tui.keystroke = lambda handler: handler.on_key(StubKeyEvent(key))

        answer = quit_confirm.main([])

        assert answer == "cancel"
        assert snapshot.calls == 0

    def test_closing_the_dialog_without_an_answer_cancels(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        kitty_ls(monkeypatch, [busy_window()])
        tui.keystroke = lambda _handler: None

        answer = quit_confirm.main([])

        assert answer == "cancel"
        assert snapshot.calls == 0


class TestSnapshotFailureNeverBlocksClosing:
    @pytest.mark.parametrize(
        "error",
        [
            pytest.param(RuntimeError("boom"), id="runtime-error"),
            pytest.param(OSError("disk full"), id="os-error"),
            pytest.param(KeyError("tabs"), id="key-error"),
            pytest.param(TypeError("unhashable type"), id="type-error"),
            pytest.param(UnicodeError("bad bytes"), id="unicode-error"),
        ],
    )
    @pytest.mark.parametrize("window", [idle_window, busy_window], ids=["idle", "confirmed-busy"])
    def test_failed_save_still_closes_and_logs_the_failure(
        self,
        quit_confirm: types.ModuleType,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        error: Exception,
        window: Callable[[], dict[str, object]],
    ) -> None:
        kitty_ls(monkeypatch, [window()])
        snapshot.error = error

        with caplog.at_level(logging.ERROR):
            answer = quit_confirm.main([])

        assert answer == "close"
        assert snapshot.calls == 1
        assert [record.levelno for record in caplog.records] == [logging.ERROR]

    def test_snapshot_error_from_the_real_module_still_closes(
        self,
        tui: TuiScript,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        load_module("kitty_session", KITTY_SESSION, monkeypatch)
        quit_confirm = load_module("quit_confirm", QUIT_CONFIRM, monkeypatch)

        def no_remote_control(
            _command: list[str], **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            message = "kitty"
            raise FileNotFoundError(message)

        monkeypatch.setattr(subprocess, "run", no_remote_control)

        answer = quit_confirm.main([])

        assert answer == "close"
        assert tui.dialogs == []
        assert not (tmp_path / ".config" / "kitty" / "last-session.conf").exists()


class TestKittySessionImportFailure:
    @pytest.mark.parametrize(
        "source",
        [
            pytest.param("message = 'boom'\nraise RuntimeError(message)\n", id="runtime-error"),
            pytest.param("def broken(:\n", id="syntax-error"),
            pytest.param("import dependency_that_is_not_installed_anywhere\n", id="missing-import"),
        ],
    )
    def test_a_sibling_that_fails_to_import_does_not_stop_closing(
        self,
        tui: TuiScript,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
        source: str,
    ) -> None:
        (tmp_path / "kitty_session.py").write_text(source, encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.delitem(sys.modules, "kitty_session", raising=False)
        kitty_ls(monkeypatch, [idle_window()])

        with caplog.at_level(logging.ERROR):
            quit_confirm = load_module("quit_confirm", QUIT_CONFIRM, monkeypatch)
            answer = quit_confirm.main([])

        assert answer == "close"
        assert tui.dialogs == []
        assert any(record.levelno == logging.ERROR for record in caplog.records)

    def test_an_absent_sibling_does_not_stop_closing_or_confirming(
        self,
        tui: TuiScript,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setitem(sys.modules, "kitty_session", None)
        quit_confirm = load_module("quit_confirm", QUIT_CONFIRM, monkeypatch)

        kitty_ls(monkeypatch, [busy_window()])
        assert quit_confirm.main([]) == "close"
        assert len(tui.dialogs) == 1

        tui.keystroke = lambda handler: handler.on_text("n")
        assert quit_confirm.main([]) == "cancel"


class TestSnapshotOnQuit:
    def test_quitting_writes_the_session_file_with_the_claude_conversation(
        self,
        tui: TuiScript,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        sessions_dir = tmp_path / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        record = {"pid": 300, "kind": "interactive", "sessionId": SESSION_ID, "cwd": "/repo"}
        (sessions_dir / "300.json").write_text(json.dumps(record), encoding="utf-8")
        load_module("kitty_session", KITTY_SESSION, monkeypatch)
        quit_confirm = load_module("quit_confirm", QUIT_CONFIRM, monkeypatch)
        claude_window: dict[str, object] = {
            "id": 1,
            "cwd": "/repo",
            "foreground_processes": [
                IDLE_FISH,
                {"pid": 300, "cwd": "/repo", "cmdline": ["claude"]},
            ],
        }
        kitty_ls(monkeypatch, [claude_window])
        tui.keystroke = lambda handler: handler.on_text("y")

        answer = quit_confirm.main([])

        saved = (tmp_path / ".config" / "kitty" / "last-session.conf").read_text(encoding="utf-8")
        launch = next(line for line in saved.splitlines() if line.startswith("launch "))
        assert answer == "close"
        assert shlex.split(launch) == [
            "launch",
            "--cwd",
            "/repo",
            "fish",
            "-C",
            f"claude --resume {SESSION_ID}",
        ]

    def test_cancelling_leaves_the_previous_session_file_untouched(
        self,
        tui: TuiScript,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        session_file = tmp_path / ".config" / "kitty" / "last-session.conf"
        session_file.parent.mkdir(parents=True)
        session_file.write_bytes(b"previous snapshot")
        load_module("kitty_session", KITTY_SESSION, monkeypatch)
        quit_confirm = load_module("quit_confirm", QUIT_CONFIRM, monkeypatch)
        kitty_ls(monkeypatch, [busy_window()])
        tui.keystroke = lambda handler: handler.on_text("n")

        answer = quit_confirm.main([])

        assert answer == "cancel"
        assert session_file.read_bytes() == b"previous snapshot"


BUSY_TABS = [("main", "vim notes.txt")]
PROMPT = "Close this window anyway? [y/N]: "


def screen_of(dialog: Dialog) -> str:
    return "".join(dialog.screen)


def open_dialog(quit_confirm: types.ModuleType, clock: FakeClock, **options: object) -> Dialog:
    dialog = quit_confirm.QuitDialog(BUSY_TABS, clock=clock, **options)
    dialog.initialize()
    return dialog


def tick_at(dialog: Dialog, clock: FakeClock, elapsed: float) -> None:
    clock.elapsed = elapsed
    dialog.asyncio_loop.fire_pending()


def answer_y(dialog: Dialog) -> None:
    dialog.on_text("y")


def answer_upper_y(dialog: Dialog) -> None:
    dialog.on_text("Y")


def answer_n(dialog: Dialog) -> None:
    dialog.on_text("n")


def answer_other_text(dialog: Dialog) -> None:
    dialog.on_text("x")


def answer_escape(dialog: Dialog) -> None:
    dialog.on_key(StubKeyEvent("esc"))


def answer_interrupt(dialog: Dialog) -> None:
    dialog.on_key(StubKeyEvent("ctrl+c"))


ANSWERS = [
    pytest.param(answer_y, "close", id="y"),
    pytest.param(answer_upper_y, "close", id="upper-y"),
    pytest.param(answer_n, "cancel", id="n"),
    pytest.param(answer_other_text, "cancel", id="other-text"),
    pytest.param(answer_escape, "cancel", id="escape"),
    pytest.param(answer_interrupt, "cancel", id="interrupt"),
]


class TestCountdownDisplay:
    def test_default_timeout_is_five_minutes(self, quit_confirm: types.ModuleType) -> None:
        parameters = inspect.signature(quit_confirm.QuitDialog).parameters

        assert quit_confirm.CONFIRM_TIMEOUT_SECONDS == 300
        assert parameters["timeout_seconds"].default == quit_confirm.CONFIRM_TIMEOUT_SECONDS

    def test_first_draw_shows_five_minutes_and_ticks_again_in_a_second(
        self, quit_confirm: types.ModuleType
    ) -> None:
        dialog = open_dialog(quit_confirm, FakeClock())

        assert "Closing automatically in 5:00\r\n" in screen_of(dialog)
        (timer,) = dialog.asyncio_loop.timers
        assert timer.delay == pytest.approx(1.0)
        assert dialog.answer == "cancel"
        assert dialog.quit_code is None

    def test_a_tick_inside_the_same_second_keeps_the_display_and_waits_the_rest(
        self, quit_confirm: types.ModuleType
    ) -> None:
        clock = FakeClock()
        dialog = open_dialog(quit_confirm, clock)

        tick_at(dialog, clock, 0.6)

        assert "Closing automatically in 5:00\r\n" in screen_of(dialog)
        assert dialog.asyncio_loop.timers[-1].delay == pytest.approx(0.4)

    def test_the_display_drops_to_4_59_once_a_full_second_has_passed(
        self, quit_confirm: types.ModuleType
    ) -> None:
        clock = FakeClock()
        dialog = open_dialog(quit_confirm, clock)
        tick_at(dialog, clock, 0.6)

        tick_at(dialog, clock, 1.0)

        assert "Closing automatically in 4:59\r\n" in screen_of(dialog)
        assert "5:00" not in screen_of(dialog)
        assert dialog.asyncio_loop.timers[-1].delay == pytest.approx(1.0)

    @pytest.mark.parametrize(
        ("timeout_seconds", "expected"),
        [(61, "1:01"), (9, "0:09"), (60, "1:00"), (1, "0:01"), (3600, "60:00")],
    )
    def test_first_draw_formats_minutes_and_zero_padded_seconds(
        self, quit_confirm: types.ModuleType, timeout_seconds: int, expected: str
    ) -> None:
        dialog = open_dialog(quit_confirm, FakeClock(), timeout_seconds=timeout_seconds)

        assert f"Closing automatically in {expected}\r\n" in screen_of(dialog)

    def test_countdown_line_sits_right_before_the_prompt_and_busy_lines_are_unchanged(
        self, quit_confirm: types.ModuleType
    ) -> None:
        busy = [("main", "vim notes.txt"), ("logs", "tail -f app.log")]
        dialog = quit_confirm.QuitDialog(busy, clock=FakeClock())

        dialog.initialize()

        assert screen_of(dialog) == (
            "Active sessions in this window:\r\n\r\n"
            "  main: vim notes.txt\r\n"
            "  logs: tail -f app.log\r\n"
            "\r\nClosing automatically in 5:00\r\n"
            f"{PROMPT}"
        )

    @pytest.mark.parametrize("start", [1000.0, 1000.37, 123456.789])
    @pytest.mark.parametrize(
        "elapsed",
        [0.0, 0.1, 0.5, 0.9, 0.999999, 1.0, 2.3, 59.999, 60.0, 299.5, 299.999],
    )
    def test_every_tick_delay_is_positive_and_at_most_one_second(
        self, quit_confirm: types.ModuleType, start: float, elapsed: float
    ) -> None:
        clock = FakeClock(start)
        dialog = open_dialog(quit_confirm, clock)

        tick_at(dialog, clock, elapsed)

        assert 0 < dialog.asyncio_loop.timers[-1].delay <= 1

    def test_ticks_woken_slightly_late_count_down_one_second_at_a_time(
        self, quit_confirm: types.ModuleType
    ) -> None:
        clock = FakeClock(1000.25)
        dialog = open_dialog(quit_confirm, clock, timeout_seconds=5)
        shown = [screen_of(dialog)]

        while dialog.asyncio_loop.pending():
            clock.elapsed += dialog.asyncio_loop.timers[-1].delay + 1e-6
            dialog.asyncio_loop.fire_pending()
            shown.append(screen_of(dialog))

        seconds = [text.split("Closing automatically in 0:0")[1][0] for text in shown[:-1]]
        assert seconds == ["5", "4", "3", "2", "1"]
        assert dialog.answer == "close"
        assert dialog.quit_code == 0


class TestCountdownExpiry:
    @pytest.mark.parametrize("elapsed", [300.0, 300.0001, 305.0, 10_000.0])
    def test_a_tick_at_or_past_the_deadline_closes_and_schedules_nothing_more(
        self, quit_confirm: types.ModuleType, elapsed: float
    ) -> None:
        clock = FakeClock()
        dialog = open_dialog(quit_confirm, clock)

        tick_at(dialog, clock, elapsed)

        assert dialog.answer == "close"
        assert dialog.quit_code == 0
        assert len(dialog.asyncio_loop.timers) == 1
        assert dialog.asyncio_loop.pending() == []

    @pytest.mark.parametrize("timeout_seconds", [0, -5])
    def test_a_timeout_that_is_already_over_closes_at_once(
        self, quit_confirm: types.ModuleType, timeout_seconds: int
    ) -> None:
        dialog = open_dialog(quit_confirm, FakeClock(), timeout_seconds=timeout_seconds)

        assert dialog.answer == "close"
        assert dialog.quit_code == 0
        assert dialog.asyncio_loop.timers == []

    def test_the_dialog_stays_unanswered_just_before_the_deadline(
        self, quit_confirm: types.ModuleType
    ) -> None:
        clock = FakeClock()
        dialog = open_dialog(quit_confirm, clock)

        tick_at(dialog, clock, 299.999)

        assert dialog.answer == "cancel"
        assert dialog.quit_code is None
        assert "Closing automatically in 0:01\r\n" in screen_of(dialog)
        assert len(dialog.asyncio_loop.pending()) == 1


class TestAnswersCancelTheCountdown:
    @pytest.mark.parametrize(("answer", "expected"), ANSWERS)
    def test_each_answer_cancels_the_pending_tick(
        self,
        quit_confirm: types.ModuleType,
        answer: Callable[[Dialog], None],
        expected: str,
    ) -> None:
        clock = FakeClock()
        dialog = open_dialog(quit_confirm, clock)
        tick_at(dialog, clock, 2.0)
        pending = dialog.asyncio_loop.pending()

        answer(dialog)

        assert [timer.cancelled for timer in pending] == [True]
        assert dialog.asyncio_loop.pending() == []
        assert dialog.answer == expected
        assert dialog.quit_code == 0

    def test_a_key_that_is_neither_escape_nor_interrupt_changes_nothing(
        self, quit_confirm: types.ModuleType
    ) -> None:
        dialog = open_dialog(quit_confirm, FakeClock())

        dialog.on_key(StubKeyEvent("tab"))

        assert dialog.answer == "cancel"
        assert dialog.quit_code is None
        assert len(dialog.asyncio_loop.pending()) == 1

    @pytest.mark.parametrize(("answer", "expected"), ANSWERS)
    def test_a_stale_tick_run_after_the_deadline_does_not_change_the_answer(
        self,
        quit_confirm: types.ModuleType,
        answer: Callable[[Dialog], None],
        expected: str,
    ) -> None:
        clock = FakeClock()
        dialog = open_dialog(quit_confirm, clock)
        stale = dialog.asyncio_loop.timers[-1]
        answer(dialog)
        clock.elapsed = 400.0

        dialog.asyncio_loop.fire(stale)

        assert dialog.answer == expected


class TestMainWithCountdown:
    @staticmethod
    def with_clock(quit_confirm: types.ModuleType, monkeypatch: pytest.MonkeyPatch) -> FakeClock:
        clock = FakeClock()
        monkeypatch.setattr(
            quit_confirm, "QuitDialog", functools.partial(quit_confirm.QuitDialog, clock=clock)
        )
        return clock

    def test_unanswered_busy_tabs_close_after_the_timeout_and_save_once(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        clock = self.with_clock(quit_confirm, monkeypatch)
        kitty_ls(monkeypatch, [busy_window()])

        def let_the_countdown_run_out(dialog: Dialog) -> None:
            clock.elapsed = quit_confirm.CONFIRM_TIMEOUT_SECONDS
            dialog.asyncio_loop.fire_pending()

        tui.keystroke = let_the_countdown_run_out

        answer = quit_confirm.main([])

        assert answer == "close"
        assert snapshot.calls == 1
        (dialog,) = tui.dialogs
        assert dialog.quit_code == 0
        assert dialog.asyncio_loop.pending() == []

    @pytest.mark.parametrize("cancel", [answer_n, answer_escape, answer_interrupt])
    def test_cancelling_before_the_timeout_never_saves(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
        cancel: Callable[[Dialog], None],
    ) -> None:
        clock = self.with_clock(quit_confirm, monkeypatch)
        kitty_ls(monkeypatch, [busy_window()])

        def cancel_midway(dialog: Dialog) -> None:
            clock.elapsed = 100.0
            dialog.asyncio_loop.fire_pending()
            cancel(dialog)

        tui.keystroke = cancel_midway

        answer = quit_confirm.main([])

        assert answer == "cancel"
        assert snapshot.calls == 0
        assert tui.dialogs[0].asyncio_loop.pending() == []

    def test_confirming_midway_saves_exactly_once(
        self,
        quit_confirm: types.ModuleType,
        tui: TuiScript,
        snapshot: SnapshotSpy,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        clock = self.with_clock(quit_confirm, monkeypatch)
        kitty_ls(monkeypatch, [busy_window()])

        def confirm_midway(dialog: Dialog) -> None:
            clock.elapsed = 100.0
            dialog.asyncio_loop.fire_pending()
            answer_y(dialog)

        tui.keystroke = confirm_midway

        answer = quit_confirm.main([])

        assert answer == "close"
        assert snapshot.calls == 1
