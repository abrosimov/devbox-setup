"""Behaviour of the pure-Lua halves of the SketchyBar feed: bar_model and bar_render.

Both modules are plain Lua with no hs.* calls, so they run under the `lua` interpreters
that tests/deploy/conftest.py finds. Snapshots shaped like `rift-cli query workspaces`
go in, the view or the `sketchybar` arguments come out as JSON.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

type RunLua = Callable[..., object]

MODULES: Final = Path(__file__).resolve().parents[2] / "roles/devbox/files/.hammerspoon/modules"
MODEL: Final = str(MODULES / "bar_model.lua")
RENDER: Final = str(MODULES / "bar_render.lua")

BG: Final = "0xff1f1f28"
SELECTION: Final = "0xff363646"
FG: Final = "0xffdcd7ba"
DIM: Final = "0xff727169"
ACCENT: Final = "0xff7e9cd8"
WARN: Final = "0xffff9e3b"
ALERT: Final = "0xffe46876"
TRANSPARENT: Final = "0x00000000"
CPU_ICON: Final = "\uf4bc"
RAM_ICON: Final = "\uefc5"
LOAD_COLOURS: Final = [(0, FG), (59, FG), (60, WARN), (84, WARN), (85, ALERT), (100, ALERT)]

type Doc = dict[str, object]
type View = list[dict[str, object]]


def _win(
    wsid: int | None,
    title: str | None = "",
    bundle: str | None = "com.example.app",
    pid: int = 100,
) -> Doc:
    return {
        "window_server_id": wsid,
        "id": {"pid": pid, "idx": wsid},
        "bundle_id": bundle,
        "title": title,
    }


def _ws(
    name: str | int,
    *windows: Doc,
    active: bool = False,
    focused: bool = False,
    layout: str = "master_stack",
    display: str = "DISPLAY-1",
) -> Doc:
    return {
        "name": name,
        "display_uuid": display,
        "is_active": active,
        "is_focused": focused,
        "layout_mode": layout,
        "window_count": len(windows),
        "windows": list(windows),
    }


def _bare(*, active: str = "1") -> list[Doc]:
    return [_ws(name, active=name == active, focused=name == active) for name in ("1", "2", "3")]


def _desk(windows: dict[str, list[Doc]] | None = None, *, active: str = "1") -> list[Doc]:
    windows = {"1": [_win(999)], **(windows or {})}
    return [
        _ws(name, *windows.get(name, []), active=name == active, focused=name == active)
        for name in ("1", "2", "3")
    ]


def _run_model(
    run_lua: RunLua, snapshots: list[list[Doc]], quiet: list[str] | None = None
) -> list[View]:
    script = """
local model = dofile(DATA.model)
local quiet = {}
for _, bundle in ipairs(DATA.quiet) do quiet[bundle] = true end
local is_quiet = nil
if DATA.use_quiet then
  is_quiet = function(bundle) return quiet[bundle] == true end
end
local state = model.new()
local views = {}
for i, snapshot in ipairs(DATA.snapshots) do
  views[i] = model.update(state, snapshot, is_quiet)
end
print(encode(views))
"""
    data = {
        "model": MODEL,
        "snapshots": snapshots,
        "quiet": quiet or [],
        "use_quiet": quiet is not None,
    }
    return cast("list[View]", run_lua(script, data))


def _marks(view: View) -> dict[str, bool]:
    return {str(entry["name"]): bool(entry["marked"]) for entry in view}


def _marked(view: View) -> list[str]:
    return [name for name, marked in _marks(view).items() if marked]


class TestUnreadCount:
    @pytest.mark.parametrize(
        ("title", "count"),
        [
            pytest.param("(3) Inbox", 3, id="round-brackets"),
            pytest.param("[12] Chat", 12, id="square-brackets"),
            pytest.param("(3)", 3, id="counter-only"),
            pytest.param("(007) Inbox", 7, id="leading-zeros"),
            pytest.param("(0) Inbox", 0, id="zero"),
            pytest.param("[1] (5) Inbox", 1, id="first-counter-wins"),
            pytest.param("Inbox (3)", 0, id="trailing-counter"),
            pytest.param(" (3) Inbox", 0, id="leading-space"),
            pytest.param("(3 Inbox", 0, id="unclosed"),
            pytest.param("[3) Inbox", 0, id="mismatched-brackets"),
            pytest.param("(x) Inbox", 0, id="not-a-number"),
            pytest.param("() Inbox", 0, id="empty-counter"),
            pytest.param("((3)) Inbox", 0, id="nested"),
            pytest.param("(-3) Inbox", 0, id="negative"),
            pytest.param("", 0, id="empty-title"),
        ],
    )
    def test_counts_only_a_leading_bracketed_number(
        self, run_lua: RunLua, title: str, count: int
    ) -> None:
        script = "local model = dofile(DATA.model)\nprint(encode(model.unread_count(DATA.title)))"

        assert run_lua(script, {"model": MODEL, "title": title}) == count

    def test_a_missing_or_non_string_title_counts_as_zero(self, run_lua: RunLua) -> None:
        script = """
local model = dofile(DATA.model)
print(encode({ model.unread_count(nil), model.unread_count(42), model.unread_count({}) }))
"""

        assert run_lua(script, {"model": MODEL}) == [0, 0, 0]


class TestLayoutTag:
    @pytest.mark.parametrize(
        ("mode", "tag"),
        [
            ("master_stack", "M"),
            ("bsp", "B"),
            ("stack", "S"),
            ("traditional", "T"),
            ("scrolling", "C"),
            ("floating", "F"),
        ],
    )
    def test_every_rift_layout_mode_has_its_own_letter(
        self, run_lua: RunLua, mode: str, tag: str
    ) -> None:
        script = "local model = dofile(DATA.model)\nprint(encode(model.layout_tag(DATA.mode)))"

        assert run_lua(script, {"model": MODEL, "mode": mode}) == tag

    def test_the_letters_are_distinct(self, run_lua: RunLua) -> None:
        script = """
local model = dofile(DATA.model)
local tags = {}
for _, mode in ipairs(DATA.modes) do tags[#tags + 1] = model.layout_tag(mode) end
print(encode(tags))
"""
        modes = ["master_stack", "bsp", "stack", "traditional", "scrolling", "floating"]

        tags = cast("list[str]", run_lua(script, {"model": MODEL, "modes": modes}))

        assert len(set(tags)) == len(modes)

    @pytest.mark.parametrize("mode", ["spiral", "", "MASTER_STACK", "Master_Stack"])
    def test_an_unknown_mode_is_a_question_mark(self, run_lua: RunLua, mode: str) -> None:
        script = "local model = dofile(DATA.model)\nprint(encode(model.layout_tag(DATA.mode)))"

        assert run_lua(script, {"model": MODEL, "mode": mode}) == "?"

    def test_a_missing_mode_is_a_question_mark(self, run_lua: RunLua) -> None:
        script = "local model = dofile(DATA.model)\nprint(encode(model.layout_tag(nil)))"

        assert run_lua(script, {"model": MODEL}) == "?"


class TestViewShape:
    def test_each_workspace_becomes_one_entry_with_every_field_the_renderer_reads(
        self, run_lua: RunLua
    ) -> None:
        snapshot = [
            _ws("1", _win(1), active=True, focused=True, layout="bsp", display="D1"),
            _ws("2", _win(2), _win(3), layout="master_stack", display="D2"),
            _ws("3", layout="scrolling", display="D2"),
        ]

        (view,) = _run_model(run_lua, [snapshot])

        assert view == [
            {
                "name": "1",
                "display_uuid": "D1",
                "focused": True,
                "visible": True,
                "occupied": True,
                "marked": False,
                "layout": "B",
            },
            {
                "name": "2",
                "display_uuid": "D2",
                "focused": False,
                "visible": False,
                "occupied": True,
                "marked": False,
                "layout": "M",
            },
            {
                "name": "3",
                "display_uuid": "D2",
                "focused": False,
                "visible": False,
                "occupied": False,
                "marked": False,
                "layout": "C",
            },
        ]

    def test_entries_keep_the_order_rift_reports(self, run_lua: RunLua) -> None:
        snapshot = [_ws("3"), _ws("1"), _ws("2")]

        (view,) = _run_model(run_lua, [snapshot])

        assert [entry["name"] for entry in view] == ["3", "1", "2"]

    def test_a_numeric_workspace_name_becomes_a_string(self, run_lua: RunLua) -> None:
        (view,) = _run_model(run_lua, [[_ws(7)]])

        assert view[0]["name"] == "7"

    def test_focus_and_visibility_are_separate_flags(self, run_lua: RunLua) -> None:
        snapshot = [
            _ws("1", active=True, focused=False),
            _ws("2", active=False, focused=True),
        ]

        (view,) = _run_model(run_lua, [snapshot])

        assert [(e["visible"], e["focused"]) for e in view] == [(True, False), (False, True)]

    def test_occupancy_falls_back_to_the_window_list_without_a_count(self, run_lua: RunLua) -> None:
        with_window: Doc = {"name": "1", "windows": [_win(1)]}
        empty: Doc = {"name": "2", "windows": []}
        bare: Doc = {"name": "3"}

        (view,) = _run_model(run_lua, [[with_window, empty, bare]])

        assert [entry["occupied"] for entry in view] == [True, False, False]

    def test_a_zero_window_count_means_unoccupied(self, run_lua: RunLua) -> None:
        (view,) = _run_model(run_lua, [[_ws("1")]])

        assert view[0]["occupied"] is False

    def test_an_empty_snapshot_gives_an_empty_view(self, run_lua: RunLua) -> None:
        assert _run_model(run_lua, [[]]) == [[]]

    def test_a_missing_snapshot_gives_an_empty_view(self, run_lua: RunLua) -> None:
        script = "local model = dofile(DATA.model)\nprint(encode(model.update(model.new(), nil)))"

        assert run_lua(script, {"model": MODEL}) == []

    def test_states_are_independent(self, run_lua: RunLua) -> None:
        script = """
local model = dofile(DATA.model)
local a = model.new()
model.update(a, DATA.before)
local marked = model.update(a, DATA.after)
local fresh = model.update(model.new(), DATA.after)
print(encode({ marked[2].marked, fresh[2].marked }))
"""
        before = _desk()
        after = _desk({"2": [_win(5)]})

        result = run_lua(script, {"model": MODEL, "before": before, "after": after})

        assert result == [True, False]


class TestActivityMarks:
    def test_the_first_snapshot_never_marks_anything(self, run_lua: RunLua) -> None:
        snapshot = _desk(
            {"2": [_win(5)], "3": [_win(6, "(9) Inbox"), _win(7, "[4] Chat")]},
        )

        (view,) = _run_model(run_lua, [snapshot])

        assert _marked(view) == []

    def test_a_window_new_to_a_hidden_workspace_marks_it(self, run_lua: RunLua) -> None:
        first = _desk()
        second = _desk({"2": [_win(5)]})

        _, view = _run_model(run_lua, [first, second])

        assert _marks(view) == {"1": False, "2": True, "3": False}

    def test_the_mark_stays_until_the_workspace_is_visited(self, run_lua: RunLua) -> None:
        windows = {"2": [_win(5)]}
        snapshots = [_desk(), _desk(windows), _desk(windows), _desk(windows)]

        views = _run_model(run_lua, snapshots)

        assert [_marked(view) for view in views] == [[], ["2"], ["2"], ["2"]]

    def test_visiting_the_workspace_clears_the_mark_and_it_does_not_return(
        self, run_lua: RunLua
    ) -> None:
        windows = {"2": [_win(5)]}
        snapshots = [
            _desk(),
            _desk(windows),
            _desk(windows, active="2"),
            _desk(windows, active="1"),
            _desk(windows, active="1"),
        ]

        views = _run_model(run_lua, snapshots)

        assert [_marked(view) for view in views] == [[], ["2"], [], [], []]

    def test_a_new_window_on_a_visible_workspace_does_not_mark_it(self, run_lua: RunLua) -> None:
        _, view = _run_model(run_lua, [_desk(), _desk({"1": [_win(5)]})])

        assert _marked(view) == []

    def test_a_new_window_on_the_workspace_being_visited_does_not_mark_it(
        self, run_lua: RunLua
    ) -> None:
        views = _run_model(run_lua, [_desk(), _desk({"2": [_win(5)]}, active="2")])

        assert _marked(views[1]) == []

    def test_each_workspace_is_marked_and_cleared_on_its_own(self, run_lua: RunLua) -> None:
        windows = {"2": [_win(5)], "3": [_win(6)]}
        snapshots = [_desk(), _desk(windows), _desk(windows, active="2")]

        views = _run_model(run_lua, snapshots)

        assert _marked(views[1]) == ["2", "3"]
        assert _marked(views[2]) == ["3"]

    @pytest.mark.parametrize(
        ("source", "target"),
        [("1", "2"), ("2", "3"), ("3", "1")],
        ids=["visible-to-hidden", "hidden-to-hidden", "hidden-to-visible"],
    )
    def test_a_window_moved_between_workspaces_is_not_new(
        self, run_lua: RunLua, source: str, target: str
    ) -> None:
        before = _desk({source: [_win(5)]})
        after = _desk({target: [_win(5)]})

        _, view = _run_model(run_lua, [before, after])

        assert _marked(view) == []

    def test_a_window_that_left_and_came_back_is_new_again(self, run_lua: RunLua) -> None:
        snapshots = [_desk(), _desk({"2": [_win(5)]}, active="2"), _desk(), _desk({"3": [_win(5)]})]

        views = _run_model(run_lua, snapshots)

        assert _marked(views[3]) == ["3"]

    @pytest.mark.parametrize(
        ("old", "new", "marks"),
        [
            pytest.param("(1) Inbox", "(2) Inbox", True, id="round-grows"),
            pytest.param("[1] Chat", "[4] Chat", True, id="square-grows"),
            pytest.param("(9) Inbox", "(10) Inbox", True, id="compared-as-numbers"),
            pytest.param("Inbox", "(1) Inbox", True, id="counter-appears"),
            pytest.param("[1] Chat", "(2) Chat", True, id="bracket-style-changes-and-grows"),
            pytest.param("(2) Inbox", "(2) Inbox", False, id="unchanged"),
            pytest.param("(2) Inbox", "(2) Inbox - Mail", False, id="same-count-new-text"),
            pytest.param("(3) Inbox", "(2) Inbox", False, id="shrinks"),
            pytest.param("(1) Inbox", "Inbox", False, id="counter-disappears"),
            pytest.param("(5) Inbox", "(0) Inbox", False, id="counter-to-zero"),
            pytest.param("Inbox", "Inbox - new tab", False, id="no-counter-either-side"),
            pytest.param(
                "(5) Inbox", "(5) Inbox (6)", False, id="trailing-number-is-not-a-counter"
            ),
            pytest.param("Inbox", "Inbox (3)", False, id="trailing-counter-appears"),
        ],
    )
    def test_a_hidden_title_marks_only_when_its_unread_counter_grows(
        self, run_lua: RunLua, old: str, new: str, *, marks: bool
    ) -> None:
        before = _desk({"2": [_win(5, old)]})
        after = _desk({"2": [_win(5, new)]})

        _, view = _run_model(run_lua, [before, after])

        assert _marks(view)["2"] is marks

    def test_counter_growth_on_a_visible_workspace_does_not_mark_it(self, run_lua: RunLua) -> None:
        before = _desk({"1": [_win(5, "(1) Inbox")]})
        after = _desk({"1": [_win(5, "(7) Inbox")]})

        _, view = _run_model(run_lua, [before, after])

        assert _marked(view) == []

    def test_counter_growth_on_the_second_snapshot_in_a_row_marks_again_after_a_visit(
        self, run_lua: RunLua
    ) -> None:
        snapshots = [
            _desk({"2": [_win(5, "(1) Inbox")]}),
            _desk({"2": [_win(5, "(2) Inbox")]}),
            _desk({"2": [_win(5, "(2) Inbox")]}, active="2"),
            _desk({"2": [_win(5, "(2) Inbox")]}),
            _desk({"2": [_win(5, "(3) Inbox")]}),
        ]

        views = _run_model(run_lua, snapshots)

        assert [_marked(view) for view in views] == [[], ["2"], [], [], ["2"]]

    def test_a_missing_title_counts_as_empty(self, run_lua: RunLua) -> None:
        before = _desk({"2": [_win(5, None)]})
        after = _desk({"2": [_win(5, "(1) Inbox")]})

        views = _run_model(run_lua, [before, after])

        assert _marked(views[1]) == ["2"]


_EXISTING: Final = {"2": [_win(5)], "3": [_win(6, "(4) Inbox")]}


class TestBaselineWaitsForAWindow:
    EXISTING: Final = _EXISTING

    @pytest.mark.parametrize(
        "leading",
        [
            pytest.param([[]], id="empty-snapshot"),
            pytest.param([_bare()], id="workspaces-without-windows"),
            pytest.param([[], _bare(), []], id="several-windowless-snapshots"),
        ],
    )
    def test_windows_present_when_the_first_window_appears_are_not_new(
        self, run_lua: RunLua, leading: list[list[Doc]]
    ) -> None:
        views = _run_model(run_lua, [*leading, _desk(self.EXISTING)])

        assert _marked(views[-1]) == []

    @pytest.mark.parametrize(
        "leading",
        [
            pytest.param([[]], id="empty-snapshot"),
            pytest.param([_bare()], id="workspaces-without-windows"),
        ],
    )
    def test_a_window_opened_after_that_baseline_marks(
        self, run_lua: RunLua, leading: list[list[Doc]]
    ) -> None:
        baseline = _desk(self.EXISTING)
        opened = _desk({**self.EXISTING, "3": [*self.EXISTING["3"], _win(7)]})

        views = _run_model(run_lua, [*leading, baseline, opened])

        assert _marked(views[-2]) == []
        assert _marked(views[-1]) == ["3"]

    def test_a_missing_snapshot_is_not_a_baseline_either(self, run_lua: RunLua) -> None:
        script = """
local model = dofile(DATA.model)
local state = model.new()
model.update(state, nil)
local baseline = model.update(state, DATA.baseline)
local opened = model.update(state, DATA.opened)
print(encode({ baseline[2].marked, baseline[3].marked, opened[2].marked, opened[3].marked }))
"""
        baseline = _desk({"2": [_win(5)]})
        opened = _desk({"2": [_win(5)], "3": [_win(6)]})

        result = run_lua(script, {"model": MODEL, "baseline": baseline, "opened": opened})

        assert result == [False, False, False, True]

    def test_a_real_baseline_followed_by_a_new_window_still_marks(self, run_lua: RunLua) -> None:
        views = _run_model(run_lua, [_desk(), _desk({"2": [_win(5)]})])

        assert [_marked(view) for view in views] == [[], ["2"]]

    def test_a_windowless_snapshot_never_replaces_the_known_windows(self, run_lua: RunLua) -> None:
        snapshots = [_desk({"2": [_win(5)]}), _bare(), _desk({"2": [_win(5)]})]

        views = _run_model(run_lua, snapshots)

        assert [_marked(view) for view in views] == [[], [], []]

    def test_a_new_window_after_a_windowless_snapshot_still_marks(self, run_lua: RunLua) -> None:
        snapshots = [
            _desk({"2": [_win(5)]}),
            _bare(),
            _desk({"2": [_win(5)], "3": [_win(6)]}),
        ]

        views = _run_model(run_lua, snapshots)

        assert [_marked(view) for view in views] == [[], [], ["3"]]

    def test_counter_growth_across_a_windowless_snapshot_still_marks(self, run_lua: RunLua) -> None:
        snapshots = [
            _desk({"2": [_win(5, "(1) Inbox")]}),
            _bare(),
            _desk({"2": [_win(5, "(2) Inbox")]}),
        ]

        views = _run_model(run_lua, snapshots)

        assert [_marked(view) for view in views] == [[], [], ["2"]]


class TestQuietApps:
    QUIET = "com.example.messenger"

    def test_a_new_window_of_a_quiet_app_does_not_mark(self, run_lua: RunLua) -> None:
        after = _desk({"2": [_win(5, bundle=self.QUIET)]})

        _, view = _run_model(run_lua, [_desk(), after], quiet=[self.QUIET])

        assert _marked(view) == []

    def test_counter_growth_in_a_quiet_app_does_not_mark(self, run_lua: RunLua) -> None:
        before = _desk({"2": [_win(5, "(1) Chat", bundle=self.QUIET)]})
        after = _desk({"2": [_win(5, "(9) Chat", bundle=self.QUIET)]})

        _, view = _run_model(run_lua, [before, after], quiet=[self.QUIET])

        assert _marked(view) == []

    def test_the_same_events_in_an_app_that_is_not_quiet_do_mark(self, run_lua: RunLua) -> None:
        new_window = _desk({"2": [_win(5, bundle="com.example.mail")]})
        growth_before = _desk({"3": [_win(6, "(1) Chat", bundle="com.example.mail")]})
        growth_after = _desk({"3": [_win(6, "(9) Chat", bundle="com.example.mail")]})

        _, opened = _run_model(run_lua, [_desk(), new_window], quiet=[self.QUIET])
        _, grown = _run_model(run_lua, [growth_before, growth_after], quiet=[self.QUIET])

        assert _marked(opened) == ["2"]
        assert _marked(grown) == ["3"]

    def test_a_quiet_window_does_not_hide_a_loud_one_on_the_same_workspace(
        self, run_lua: RunLua
    ) -> None:
        after = _desk({"2": [_win(5, bundle=self.QUIET), _win(6, bundle="com.example.mail")]})

        _, view = _run_model(run_lua, [_desk(), after], quiet=[self.QUIET])

        assert _marked(view) == ["2"]

    def test_a_window_without_a_bundle_id_is_not_quiet(self, run_lua: RunLua) -> None:
        after = _desk({"2": [_win(5, bundle=None)]})

        _, view = _run_model(run_lua, [_desk(), after], quiet=[self.QUIET])

        assert _marked(view) == ["2"]

    def test_without_a_predicate_nothing_is_quiet(self, run_lua: RunLua) -> None:
        after = _desk({"2": [_win(5, bundle=self.QUIET)]})

        _, view = _run_model(run_lua, [_desk(), after])

        assert _marked(view) == ["2"]


class TestWindowIdentity:
    def test_a_window_without_any_identity_is_ignored(self, run_lua: RunLua) -> None:
        nameless: Doc = {"title": "(5) Inbox", "bundle_id": "com.example.app"}
        before = _desk()
        after = _desk({"2": [nameless]})

        views = _run_model(run_lua, [before, after, after])

        assert [_marked(view) for view in views] == [[], [], []]

    def test_an_id_without_an_index_is_not_an_identity(self, run_lua: RunLua) -> None:
        half: Doc = {"id": {"pid": 5}, "title": "", "bundle_id": "com.example.app"}

        _, view = _run_model(run_lua, [_desk(), _desk({"2": [half]})])

        assert _marked(view) == []

    def test_the_pid_and_index_identify_a_window_that_has_no_server_id(
        self, run_lua: RunLua
    ) -> None:
        window: Doc = {"id": {"pid": 7, "idx": 2}, "title": "", "bundle_id": "com.example.app"}
        snapshots = [
            _desk(),
            _desk({"2": [window]}),
            _desk({"2": [window]}, active="2"),
            _desk({"2": [window]}),
        ]

        views = _run_model(run_lua, snapshots)

        assert [_marked(view) for view in views] == [[], ["2"], [], []]

    def test_the_same_index_under_another_pid_is_another_window(self, run_lua: RunLua) -> None:
        one: Doc = {"id": {"pid": 100, "idx": 1}, "title": "", "bundle_id": "com.example.app"}
        other: Doc = {"id": {"pid": 200, "idx": 1}, "title": "", "bundle_id": "com.example.app"}

        _, view = _run_model(run_lua, [_desk({"2": [one]}), _desk({"2": [one, other]})])

        assert _marked(view) == ["2"]

    def test_a_server_id_of_zero_is_an_identity(self, run_lua: RunLua) -> None:
        _, view = _run_model(run_lua, [_desk(), _desk({"2": [_win(0)]})])

        assert _marked(view) == ["2"]


class TestWorkspaceArgs:
    @pytest.mark.parametrize(
        ("flags", "fg", "bg"),
        [
            pytest.param("focused", BG, ACCENT, id="focused"),
            pytest.param("focused-marked", BG, ACCENT, id="focus-outranks-the-mark"),
            pytest.param("focused-empty", BG, ACCENT, id="focused-empty"),
            pytest.param("marked-visible", WARN, SELECTION, id="marked-visible"),
            pytest.param("marked-hidden", WARN, TRANSPARENT, id="marked-hidden"),
            pytest.param("marked-empty", WARN, TRANSPARENT, id="marked-empty"),
            pytest.param("visible", FG, SELECTION, id="visible"),
            pytest.param("visible-empty", FG, SELECTION, id="visible-empty"),
            pytest.param("occupied", FG, TRANSPARENT, id="occupied"),
            pytest.param("empty", DIM, TRANSPARENT, id="empty"),
        ],
    )
    def test_the_state_picks_the_colours(
        self, run_lua: RunLua, flags: str, fg: str, bg: str
    ) -> None:
        view = {
            "focused": {"focused": True, "visible": True, "occupied": True},
            "focused-marked": {"focused": True, "marked": True, "visible": True, "occupied": True},
            "focused-empty": {"focused": True, "visible": True},
            "marked-visible": {"marked": True, "visible": True, "occupied": True},
            "marked-hidden": {"marked": True, "occupied": True},
            "marked-empty": {"marked": True},
            "visible": {"visible": True, "occupied": True},
            "visible-empty": {"visible": True},
            "occupied": {"occupied": True},
            "empty": {},
        }[flags]
        entry = {"name": "4", "display_uuid": "D1", "layout": "M", **view}

        args = _workspace_args(run_lua, [entry], {"D1": 1})

        assert _settings(args)["ws.4"]["label.color"] == fg
        assert _settings(args)["ws.4"]["background.color"] == bg

    def test_a_workspace_on_a_known_display_is_drawn_there_with_its_name_and_layout(
        self, run_lua: RunLua
    ) -> None:
        entry = {
            "name": "3",
            "display_uuid": "D2",
            "layout": "B",
            "visible": True,
            "occupied": True,
        }

        args = _workspace_args(run_lua, [entry], {"D1": 1, "D2": 2})

        assert args == [
            "--set",
            "ws.3",
            "drawing=on",
            "display=2",
            "label=3 B",
            f"label.color={FG}",
            f"background.color={SELECTION}",
        ]

    @pytest.mark.parametrize(
        "index",
        [{"OTHER": 1}, {}, None],
        ids=["display-not-in-the-map", "empty-map", "no-map"],
    )
    def test_a_workspace_on_an_unknown_display_is_hidden_and_nothing_else_is_set(
        self, run_lua: RunLua, index: dict[str, int] | None
    ) -> None:
        entry = {"name": "4", "display_uuid": "D1", "layout": "M", "occupied": True}

        assert _workspace_args(run_lua, [entry], index) == ["--set", "ws.4", "drawing=off"]

    def test_a_workspace_without_a_display_is_hidden(self, run_lua: RunLua) -> None:
        entry = {"name": "4", "layout": "M", "occupied": True}

        assert _workspace_args(run_lua, [entry], {"D1": 1}) == ["--set", "ws.4", "drawing=off"]

    def test_each_workspace_gets_its_own_display_and_the_order_is_kept(
        self, run_lua: RunLua
    ) -> None:
        view = [
            {"name": "5", "display_uuid": "D2", "layout": "M"},
            {"name": "1", "display_uuid": "D1", "layout": "S"},
            {"name": "9", "display_uuid": "GONE", "layout": "F"},
        ]

        settings = _settings(_workspace_args(run_lua, view, {"D1": 1, "D2": 2}))

        assert list(settings) == ["ws.5", "ws.1", "ws.9"]
        assert settings["ws.5"]["display"] == "2"
        assert settings["ws.5"]["label"] == "5 M"
        assert settings["ws.1"]["display"] == "1"
        assert settings["ws.1"]["label"] == "1 S"
        assert settings["ws.9"] == {"drawing": "off"}

    @pytest.mark.parametrize("view", [[], None], ids=["empty", "missing"])
    def test_no_workspaces_means_no_arguments(
        self, run_lua: RunLua, view: list[Doc] | None
    ) -> None:
        script = (
            "local r = dofile(DATA.render)\nprint(encode(r.workspace_args(DATA.view, DATA.index)))"
        )

        assert run_lua(script, {"render": RENDER, "view": view, "index": {"D1": 1}}) == []


class TestStatusArgs:
    FULL: Final = {
        "cpu": 7,
        "ram": 42,
        "clock": "Fri 27 Nov 15:28",
        "input": "EN",
        "app": "Kitty",
        "battery": {"percent": 87, "charging": True},
    }

    def test_every_reading_is_pushed_to_its_item(self, run_lua: RunLua) -> None:
        assert _status_args(run_lua, self.FULL) == [
            "--set",
            "cpu",
            f"icon={CPU_ICON}",
            f"icon.color={FG}",
            "label=7%",
            f"label.color={FG}",
            "--set",
            "ram",
            f"icon={RAM_ICON}",
            f"icon.color={FG}",
            "label=42%",
            f"label.color={FG}",
            "--set",
            "clock",
            "label=Fri 27 Nov 15:28",
            "--set",
            "input",
            "label=EN",
            "--set",
            "front_app",
            "label=Kitty",
            "--set",
            "battery",
            "drawing=on",
            "label=BAT 87%+",
            f"label.color={FG}",
        ]

    @pytest.mark.parametrize("readings", [{}, None], ids=["empty", "missing"])
    def test_unknown_readings_show_dashes_dimmed_and_hide_the_battery(
        self, run_lua: RunLua, readings: Doc | None
    ) -> None:
        settings = _settings(_status_args(run_lua, readings))

        assert settings == {
            "cpu": {"icon": CPU_ICON, "icon.color": DIM, "label": "--", "label.color": DIM},
            "ram": {"icon": RAM_ICON, "icon.color": DIM, "label": "--", "label.color": DIM},
            "clock": {"label": ""},
            "input": {"label": ""},
            "front_app": {"label": ""},
            "battery": {"drawing": "off"},
        }

    def test_the_same_six_items_are_always_set_once_each(self, run_lua: RunLua) -> None:
        for readings in ({}, self.FULL, {**self.FULL, "battery": None}):
            assert set(_settings(_status_args(run_lua, readings))) == {
                "cpu",
                "ram",
                "clock",
                "input",
                "front_app",
                "battery",
            }

    @pytest.mark.parametrize("item", ["cpu", "ram"])
    @pytest.mark.parametrize(("percent", "colour"), LOAD_COLOURS)
    def test_load_turns_amber_at_sixty_and_red_at_eighty_five(
        self, run_lua: RunLua, item: str, percent: int, colour: str
    ) -> None:
        settings = _settings(_status_args(run_lua, {item: percent}))

        assert settings[item]["label.color"] == colour
        assert settings[item]["label"] == f"{percent}%"

    @pytest.mark.parametrize("item", ["cpu", "ram"])
    @pytest.mark.parametrize(("percent", "colour"), LOAD_COLOURS)
    def test_the_icon_takes_the_colour_of_the_label_at_every_load_threshold(
        self, run_lua: RunLua, item: str, percent: int, colour: str
    ) -> None:
        settings = _settings(_status_args(run_lua, {item: percent}))

        assert settings[item]["icon.color"] == colour
        assert settings[item]["icon.color"] == settings[item]["label.color"]

    @pytest.mark.parametrize("item", ["cpu", "ram"])
    def test_an_unknown_reading_dims_its_icon_and_label_while_the_other_keeps_its_load_colour(
        self, run_lua: RunLua, item: str
    ) -> None:
        other = "ram" if item == "cpu" else "cpu"

        settings = _settings(_status_args(run_lua, {other: 90}))

        assert settings[item]["icon.color"] == DIM
        assert settings[item]["label.color"] == DIM
        assert settings[other]["icon.color"] == ALERT
        assert settings[other]["label.color"] == ALERT

    @pytest.mark.parametrize(
        ("item", "icon"), [("cpu", CPU_ICON), ("ram", RAM_ICON)], ids=["cpu", "ram"]
    )
    @pytest.mark.parametrize("readings", [{}, {"cpu": 5, "ram": 5}, {"cpu": 95, "ram": 95}])
    def test_each_item_keeps_its_own_icon_whatever_the_reading(
        self, run_lua: RunLua, item: str, icon: str, readings: Doc
    ) -> None:
        settings = _settings(_status_args(run_lua, readings))

        assert settings[item]["icon"] == icon
        assert "CPU" not in settings[item]["label"]
        assert "RAM" not in settings[item]["label"]

    @pytest.mark.parametrize("item", ["cpu", "ram"])
    @pytest.mark.parametrize(
        ("percent", "shown"),
        [(7.5, 8), (62.4, 62), (0.4, 0), (99.6, 100), (12.0, 12)],
    )
    def test_a_fractional_percentage_is_rounded_to_a_whole_number_not_an_error(
        self, run_lua: RunLua, item: str, percent: float, shown: int
    ) -> None:
        settings = _settings(_status_args(run_lua, {item: percent}))

        assert settings[item]["label"] == f"{shown}%"

    def test_cpu_and_ram_are_coloured_independently(self, run_lua: RunLua) -> None:
        settings = _settings(_status_args(run_lua, {"cpu": 90, "ram": 10}))

        assert settings["cpu"]["label.color"] == settings["cpu"]["icon.color"] == ALERT
        assert settings["ram"]["label.color"] == settings["ram"]["icon.color"] == FG

    def test_the_cpu_and_ram_icons_are_the_nerd_font_cpu_and_memory_glyphs(
        self, run_lua: RunLua
    ) -> None:
        script = "local r = dofile(DATA.render)\nprint(encode({ r.CPU_ICON, r.RAM_ICON }))"

        cpu, ram = cast("list[str]", run_lua(script, {"render": RENDER}))

        assert [hex(ord(char)) for char in cpu] == ["0xf4bc"]
        assert [hex(ord(char)) for char in ram] == ["0xefc5"]

    @pytest.mark.parametrize(
        ("battery", "label", "colour"),
        [
            pytest.param({"percent": 100, "charging": True}, "BAT 100%+", FG, id="full-charging"),
            pytest.param({"percent": 87, "charging": False}, "BAT 87%", FG, id="discharging"),
            pytest.param({"percent": 21, "charging": False}, "BAT 21%", FG, id="just-above-low"),
            pytest.param({"percent": 20, "charging": False}, "BAT 20%", ALERT, id="low"),
            pytest.param({"percent": 0, "charging": False}, "BAT 0%", ALERT, id="empty"),
            pytest.param({"percent": 20, "charging": True}, "BAT 20%+", FG, id="low-but-charging"),
            pytest.param({"percent": 3, "charging": True}, "BAT 3%+", FG, id="empty-charging"),
            pytest.param({"percent": 50}, "BAT 50%", FG, id="charging-unknown"),
            pytest.param({"percent": 87.4, "charging": False}, "BAT 87%", FG, id="rounds-down"),
            pytest.param({"percent": 87.5, "charging": False}, "BAT 88%", FG, id="rounds-half-up"),
        ],
    )
    def test_the_battery_shows_its_level_and_turns_red_when_low_and_not_charging(
        self, run_lua: RunLua, battery: Doc, label: str, colour: str
    ) -> None:
        settings = _settings(_status_args(run_lua, {"battery": battery}))

        assert settings["battery"] == {"drawing": "on", "label": label, "label.color": colour}

    @pytest.mark.parametrize(
        "battery", [None, {}, {"charging": True}], ids=["none", "empty", "no-percent"]
    )
    def test_a_machine_without_a_battery_hides_the_item(
        self, run_lua: RunLua, battery: Doc | None
    ) -> None:
        settings = _settings(_status_args(run_lua, {"battery": battery}))

        assert settings["battery"] == {"drawing": "off"}

    @pytest.mark.parametrize(
        "text",
        ["Visual Studio Code", "A=B", "50% off %d %s", "it's", "$HOME `x`", "Café"],
    )
    def test_text_readings_are_passed_through_untouched_as_one_argument(
        self, run_lua: RunLua, text: str
    ) -> None:
        args = _status_args(run_lua, {"app": text, "clock": text, "input": text})
        settings = _settings(args)

        assert f"label={text}" in args
        assert settings["front_app"]["label"] == text
        assert settings["clock"]["label"] == text
        assert settings["input"]["label"] == text


class TestEdgeArgs:
    # The private-use glyph U+F093 appears as an invisible character in some literals below.
    @staticmethod
    def _args(run_lua: RunLua, summary: Mapping[str, object] | None) -> list[str]:
        script = "local r = dofile(DATA.render)\nprint(encode(r.edge_args(DATA.summary)))"
        return cast("list[str]", run_lua(script, {"render": RENDER, "summary": summary}))

    @staticmethod
    def _ok(percent: int, level: str | None, markers: list[str] | None = None) -> Doc:
        return {"state": "ok", "percent": percent, "level": level, "markers": markers}

    def test_the_icon_is_the_nerd_font_upload_glyph(self, run_lua: RunLua) -> None:
        script = "local r = dofile(DATA.render)\nprint(encode(r.EDGE_ICON))"

        assert run_lua(script, {"render": RENDER}) == ""

    def test_the_icon_is_code_point_f093(self, run_lua: RunLua) -> None:
        script = "local r = dofile(DATA.render)\nprint(encode(r.EDGE_ICON))"

        icon = cast("str", run_lua(script, {"render": RENDER}))

        assert [hex(ord(char)) for char in icon] == ["0xf093"]

    def test_a_healthy_edge_is_the_whole_argument_list(self, run_lua: RunLua) -> None:
        assert self._args(run_lua, self._ok(37, "ok", [])) == [
            "--set",
            "edge",
            "icon=",
            f"icon.color={FG}",
            "label=37%",
            f"label.color={FG}",
        ]

    def test_only_the_edge_item_is_set_once(self, run_lua: RunLua) -> None:
        for summary in (None, {"state": "down"}, {"state": "unknown"}, self._ok(90, "critical")):
            assert list(_settings(self._args(run_lua, summary))) == ["edge"]

    @pytest.mark.parametrize(
        ("level", "colour"),
        [("ok", FG), ("warning", WARN), ("critical", ALERT)],
    )
    def test_the_level_picks_the_colour_of_the_icon_and_the_label(
        self, run_lua: RunLua, level: str, colour: str
    ) -> None:
        settings = _settings(self._args(run_lua, self._ok(55, level, [])))["edge"]

        assert settings["icon.color"] == colour
        assert settings["label.color"] == colour

    @pytest.mark.parametrize("level", [None, "", "bogus", "CRITICAL"])
    def test_a_missing_or_unknown_level_is_drawn_in_the_normal_colour(
        self, run_lua: RunLua, level: str | None
    ) -> None:
        settings = _settings(self._args(run_lua, self._ok(10, level, [])))["edge"]

        assert settings["label.color"] == FG
        assert settings["icon.color"] == FG

    @pytest.mark.parametrize("percent", [0, 1, 49, 50, 80, 100, 150])
    def test_the_label_is_the_whole_percentage(self, run_lua: RunLua, percent: int) -> None:
        settings = _settings(self._args(run_lua, self._ok(percent, "ok", [])))["edge"]

        assert settings["label"] == f"{percent}%"

    @pytest.mark.parametrize(
        ("markers", "label"),
        [
            pytest.param(["stall"], "62% stall", id="stall"),
            pytest.param(["disk"], "62% disk", id="disk"),
            pytest.param(["stall", "disk"], "62% stall disk", id="both-in-the-given-order"),
            pytest.param(["disk", "stall"], "62% disk stall", id="order-is-the-callers"),
            pytest.param([], "62%", id="none"),
            pytest.param(None, "62%", id="missing"),
        ],
    )
    def test_each_marker_follows_the_percentage(
        self, run_lua: RunLua, markers: list[str] | None, label: str
    ) -> None:
        settings = _settings(self._args(run_lua, self._ok(62, "warning", markers)))["edge"]

        assert settings["label"] == label

    def test_markers_do_not_change_the_colour(self, run_lua: RunLua) -> None:
        plain = _settings(self._args(run_lua, self._ok(62, "warning", [])))["edge"]
        marked = _settings(self._args(run_lua, self._ok(62, "warning", ["stall", "disk"])))["edge"]

        assert marked["label.color"] == plain["label.color"] == WARN

    def test_an_edge_that_did_not_answer_is_a_dimmed_cross(self, run_lua: RunLua) -> None:
        settings = _settings(self._args(run_lua, {"state": "down"}))["edge"]

        assert settings == {
            "icon": "",
            "icon.color": DIM,
            "label": "✕",
            "label.color": DIM,
        }

    @pytest.mark.parametrize(
        "summary",
        [
            pytest.param({"state": "unknown"}, id="unknown"),
            pytest.param(None, id="before-the-first-poll"),
            pytest.param({}, id="no-state"),
            pytest.param({"state": "bogus", "percent": 40, "level": "critical"}, id="bogus-state"),
        ],
    )
    def test_no_reading_yet_or_an_unreadable_one_is_dimmed_dashes(
        self, run_lua: RunLua, summary: Mapping[str, object] | None
    ) -> None:
        settings = _settings(self._args(run_lua, summary))["edge"]

        assert settings == {
            "icon": "",
            "icon.color": DIM,
            "label": "--",
            "label.color": DIM,
        }

    def test_a_down_state_ignores_stale_fields(self, run_lua: RunLua) -> None:
        summary = {"state": "down", "percent": 99, "level": "critical", "markers": ["stall"]}

        settings = _settings(self._args(run_lua, summary))["edge"]

        assert settings["label"] == "✕"
        assert settings["label.color"] == DIM


class TestMemoryPercent:
    PAGE: Final = 4096
    MEM: Final = 1000 * 4096

    def _vm(self, **fields: float) -> Doc:
        return {"memSize": self.MEM, "pageSize": self.PAGE, **fields}

    def _percent(self, run_lua: RunLua, vm: object) -> object:
        script = """
local r = dofile(DATA.render)
local v = r.memory_percent(DATA.vm)
if v == nil then v = "nil" end
print(encode(v))
"""
        return run_lua(script, {"render": RENDER, "vm": vm})

    def test_app_memory_wired_and_compressed_count_and_purgeable_does_not(
        self, run_lua: RunLua
    ) -> None:
        vm = self._vm(
            anonymousPages=400, pagesPurgeable=100, pagesWiredDown=150, pagesUsedByVMCompressor=50
        )

        assert self._percent(run_lua, vm) == 50

    @pytest.mark.parametrize(
        ("used_pages", "percent"),
        [(504, 50), (505, 51), (506, 51), (0, 0), (1000, 100)],
    )
    def test_the_share_is_rounded_to_the_nearest_whole_percent(
        self, run_lua: RunLua, used_pages: int, percent: int
    ) -> None:
        assert self._percent(run_lua, self._vm(pagesWiredDown=used_pages)) == percent

    def test_purgeable_memory_beyond_anonymous_does_not_go_negative(self, run_lua: RunLua) -> None:
        vm = self._vm(anonymousPages=50, pagesPurgeable=100, pagesWiredDown=100)

        assert self._percent(run_lua, vm) == 10

    def test_more_pages_than_memory_is_capped_at_one_hundred(self, run_lua: RunLua) -> None:
        assert self._percent(run_lua, self._vm(pagesWiredDown=1500)) == 100

    def test_absent_counters_count_as_zero(self, run_lua: RunLua) -> None:
        assert self._percent(run_lua, self._vm(anonymousPages=200)) == 20
        assert self._percent(run_lua, self._vm()) == 0

    def test_float_counters_are_accepted(self, run_lua: RunLua) -> None:
        vm = {"memSize": float(self.MEM), "pageSize": float(self.PAGE), "pagesWiredDown": 400.0}

        assert self._percent(run_lua, vm) == 40

    @pytest.mark.parametrize(
        "vm",
        [
            pytest.param({"pageSize": 4096, "pagesWiredDown": 10}, id="no-memsize"),
            pytest.param({"memSize": 0, "pageSize": 4096}, id="zero-memsize"),
            pytest.param({"memSize": -4096, "pageSize": 4096}, id="negative-memsize"),
            pytest.param({"memSize": 4096000, "pagesWiredDown": 10}, id="no-pagesize"),
            pytest.param({}, id="empty-table"),
            pytest.param("vm_stat output", id="string"),
        ],
    )
    def test_a_reading_that_cannot_be_trusted_is_unknown(self, run_lua: RunLua, vm: object) -> None:
        assert self._percent(run_lua, vm) == "nil"

    def test_no_reading_at_all_is_unknown(self, run_lua: RunLua) -> None:
        script = "local r = dofile(DATA.render)\nprint(encode(r.memory_percent(nil) == nil))"

        assert run_lua(script, {"render": RENDER}) is True


class TestDisplayIndex:
    def _index(self, run_lua: RunLua, displays: object) -> object:
        script = "local r = dofile(DATA.render)\nprint(encode(r.display_index(DATA.displays)))"
        return run_lua(script, {"render": RENDER, "displays": displays})

    def test_the_uuid_maps_to_the_arrangement_id(self, run_lua: RunLua) -> None:
        displays = [
            {"UUID": "AAAA-1", "arrangement-id": 1, "frame": {"w": 1.0}},
            {"UUID": "BBBB-2", "arrangement-id": 2},
        ]

        assert self._index(run_lua, displays) == {"AAAA-1": 1, "BBBB-2": 2}

    def test_an_entry_missing_either_key_is_left_out(self, run_lua: RunLua) -> None:
        displays = [
            {"UUID": "AAAA-1"},
            {"arrangement-id": 2},
            {"UUID": "CCCC-3", "arrangement-id": 3},
            {},
        ]

        assert self._index(run_lua, displays) == {"CCCC-3": 3}

    def test_an_arrangement_id_of_zero_is_kept(self, run_lua: RunLua) -> None:
        assert self._index(run_lua, [{"UUID": "AAAA-1", "arrangement-id": 0}]) == {"AAAA-1": 0}

    def test_the_last_entry_wins_for_a_repeated_uuid(self, run_lua: RunLua) -> None:
        displays = [
            {"UUID": "AAAA-1", "arrangement-id": 1},
            {"UUID": "AAAA-1", "arrangement-id": 2},
        ]

        assert self._index(run_lua, displays) == {"AAAA-1": 2}

    @pytest.mark.parametrize("displays", [[], None], ids=["empty", "missing"])
    def test_no_displays_give_an_empty_index(self, run_lua: RunLua, displays: object) -> None:
        assert not self._index(run_lua, displays)


class TestInputLabel:
    @pytest.mark.parametrize(
        ("source", "label"),
        [
            ("com.apple.keylayout.ABC", "EN"),
            ("com.apple.keylayout.US", "EN"),
            ("com.apple.keylayout.British", "EN"),
            ("com.apple.keylayout.Russian", "RU"),
            ("com.apple.keylayout.RussianWin", "RU"),
            ("com.apple.keylayout.Russian-Phonetic", "RU"),
            ("com.apple.keylayout.RussianPC", "RU"),
            ("com.apple.keylayout.Dvorak", "DV"),
            ("ABC", "EN"),
            ("Russian", "RU"),
        ],
    )
    def test_known_layouts_get_their_language_and_others_two_capitals(
        self, run_lua: RunLua, source: str, label: str
    ) -> None:
        script = "local r = dofile(DATA.render)\nprint(encode(r.input_label(DATA.source)))"

        assert run_lua(script, {"render": RENDER, "source": source}) == label

    @pytest.mark.parametrize("source", ["", None, 42])
    def test_a_missing_or_malformed_source_gives_an_empty_label(
        self, run_lua: RunLua, source: object
    ) -> None:
        script = "local r = dofile(DATA.render)\nprint(encode(r.input_label(DATA.source)))"

        assert run_lua(script, {"render": RENDER, "source": source}) == ""


def _workspace_args(
    run_lua: RunLua, view: Sequence[Mapping[str, object]], index: Mapping[str, int] | None
) -> list[str]:
    script = "local r = dofile(DATA.render)\nprint(encode(r.workspace_args(DATA.view, DATA.index)))"
    return cast("list[str]", run_lua(script, {"render": RENDER, "view": view, "index": index}))


def _status_args(run_lua: RunLua, readings: Mapping[str, object] | None) -> list[str]:
    script = "local r = dofile(DATA.render)\nprint(encode(r.status_args(DATA.readings)))"
    return cast("list[str]", run_lua(script, {"render": RENDER, "readings": readings}))


def _settings(args: list[str]) -> dict[str, dict[str, str]]:
    settings: dict[str, dict[str, str]] = {}
    item = ""
    position = 0
    while position < len(args):
        if args[position] == "--set":
            item = args[position + 1]
            assert item not in settings, f"{item} is set twice"
            settings[item] = {}
            position += 2
            continue
        key, separator, value = args[position].partition("=")
        assert separator == "=", f"argument {args[position]!r} is not key=value"
        settings[item][key] = value
        position += 1
    return settings
