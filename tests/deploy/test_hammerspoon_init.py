"""Hammerspoon start-up after a deploy: the reload watcher and the isolated module start.

Ansible copies ~/.hammerspoon one file per second. A reload on the first changed .lua file
loaded an init.lua whose modules were not there yet, and the failed `require` stopped the
watcher from ever restarting. Both files run here against a fake `hs` table.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

type RunLua = Callable[..., object]
type Doc = dict[str, object]

HAMMERSPOON: Final = Path(__file__).resolve().parents[2] / "roles/devbox/files/.hammerspoon"
WATCHER: Final = str(HAMMERSPOON / "modules/reload_watcher.lua")
INIT: Final = str(HAMMERSPOON / "init.lua")

WATCHER_SCRIPT: Final = """
local calls = { reload = 0, timers = {}, watchers = {} }
local function reload() calls.reload = calls.reload + 1 end
hs = {
  configdir = "/cfg",
  reload = reload,
  timer = { delayed = { new = function(delay, fn)
    local timer = { delay = delay, fn = fn, started = 0 }
    function timer:start() self.started = self.started + 1; return self end
    calls.timers[#calls.timers + 1] = timer
    return timer
  end } },
  pathwatcher = { new = function(path, callback)
    local watcher = { path = path, callback = callback, started = false }
    function watcher:start() self.started = true; return self end
    calls.watchers[#calls.watchers + 1] = watcher
    return watcher
  end },
}
local module = dofile(DATA.module)
module.start()

local function snapshot()
  local timer = calls.timers[1]
  return { timers = #calls.timers, started = timer and timer.started or 0, reload = calls.reload }
end

local trace = { snapshot() }
for _, step in ipairs(DATA.steps) do
  if step.expire then
    calls.timers[1].fn()
  else
    calls.watchers[1].callback(step.files)
  end
  trace[#trace + 1] = snapshot()
end
print(encode({
  trace = trace,
  delay = calls.timers[1].delay,
  fn_is_reload = calls.timers[1].fn == reload,
  watchers = #calls.watchers,
  watcher_path = calls.watchers[1].path,
  watcher_started = calls.watchers[1].started,
}))
"""

INIT_SCRIPT: Final = """
package.path = ""
package.cpath = ""
local events, errors, stops = {}, {}, {}
local function log(event) events[#events + 1] = event end

local modes = DATA.modes
for _, name in ipairs({ "reload_watcher", "input_source", "hyper", "bar" }) do
  local mode = modes[name] or "ok"
  if mode ~= "missing" then
    package.preload["modules." .. name] = function()
      log("require:" .. name)
      if mode == "require_error" then error("boom in " .. name .. " require", 0) end
      local module = {}
      stops[name] = function() end
      module.stop = stops[name]
      module.start = function()
        log("start:" .. name)
        if mode == "start_error" then error("boom in " .. name .. " start", 0) end
      end
      return module
    end
  end
end

hs = { showError = function(message) errors[#errors + 1] = message end }

dofile(DATA.init)

io.write(encode({
  events = events,
  errors = errors,
  shutdown_is_bar_stop = stops.bar ~= nil and hs.shutdownCallback == stops.bar,
  shutdown_is_nil = hs.shutdownCallback == nil,
}))
"""


def _watch(run_lua: RunLua, steps: list[Doc]) -> Doc:
    return cast("Doc", run_lua(WATCHER_SCRIPT, {"module": WATCHER, "steps": steps}))


def _touched(*files: str) -> Doc:
    return {"files": list(files)}


EXPIRE: Final[Doc] = {"expire": True}


def _trace(result: Doc) -> list[dict[str, int]]:
    return cast("list[dict[str, int]]", result["trace"])


class TestReloadWatcher:
    def test_it_watches_the_config_directory_and_arms_nothing_until_a_file_changes(
        self, run_lua: RunLua
    ) -> None:
        result = _watch(run_lua, [])

        assert result["watchers"] == 1
        assert result["watcher_path"] == "/cfg"
        assert result["watcher_started"] is True
        assert _trace(result) == [{"timers": 1, "started": 0, "reload": 0}]

    def test_the_reload_waits_three_quiet_seconds_and_is_hs_reload_itself(
        self, run_lua: RunLua
    ) -> None:
        result = _watch(run_lua, [])

        assert result["delay"] == 3
        assert result["fn_is_reload"] is True

    def test_a_lua_change_arms_the_timer_and_does_not_reload_at_once(self, run_lua: RunLua) -> None:
        result = _watch(run_lua, [_touched("/cfg/init.lua")])

        assert _trace(result)[-1] == {"timers": 1, "started": 1, "reload": 0}

    def test_a_burst_of_changes_restarts_one_timer_and_reloads_only_when_it_fires(
        self, run_lua: RunLua
    ) -> None:
        burst = [
            _touched("/cfg/init.lua"),
            _touched("/cfg/modules/bar.lua"),
            _touched("/cfg/modules/bar_model.lua"),
            _touched("/cfg/modules/bar_render.lua"),
        ]

        result = _watch(run_lua, [*burst, EXPIRE])

        trace = _trace(result)
        assert [step["started"] for step in trace[:-1]] == [0, 1, 2, 3, 4]
        assert {step["timers"] for step in trace} == {1}
        assert [step["reload"] for step in trace] == [0, 0, 0, 0, 0, 1]

    def test_several_lua_files_in_one_notification_arm_the_timer_once(
        self, run_lua: RunLua
    ) -> None:
        result = _watch(run_lua, [_touched("/cfg/a.lua", "/cfg/b.lua", "/cfg/c.lua")])

        assert _trace(result)[-1]["started"] == 1

    def test_a_lua_file_after_other_files_in_the_notification_still_arms_it(
        self, run_lua: RunLua
    ) -> None:
        result = _watch(run_lua, [_touched("/cfg/notes.md", "/cfg/.DS_Store", "/cfg/x.lua")])

        assert _trace(result)[-1]["started"] == 1

    @pytest.mark.parametrize(
        "files",
        [
            pytest.param([], id="empty-notification"),
            pytest.param(["/cfg/README.md"], id="markdown"),
            pytest.param(["/cfg/.DS_Store"], id="ds-store"),
            pytest.param(["/cfg/init.lua.bak"], id="lua-in-the-middle"),
            pytest.param(["/cfg/Spoons/x.luac"], id="luac"),
            pytest.param(["/cfg/lua"], id="named-lua-without-a-dot"),
            pytest.param(["/cfg/modules/bar.LUA"], id="uppercase-extension"),
            pytest.param(["/cfg/a.json", "/cfg/b.txt"], id="several-other-files"),
        ],
    )
    def test_changes_to_files_that_are_not_lua_do_nothing(
        self, run_lua: RunLua, files: list[str]
    ) -> None:
        result = _watch(run_lua, [_touched(*files)])

        assert _trace(result)[-1] == {"timers": 1, "started": 0, "reload": 0}

    def test_a_change_after_the_timer_fired_arms_the_same_timer_again(
        self, run_lua: RunLua
    ) -> None:
        result = _watch(run_lua, [_touched("/cfg/init.lua"), EXPIRE, _touched("/cfg/init.lua")])

        trace = _trace(result)
        assert trace[-1] == {"timers": 1, "started": 2, "reload": 1}


def _start(run_lua: RunLua, modes: dict[str, str] | None = None) -> Doc:
    return cast("Doc", run_lua(INIT_SCRIPT, {"init": INIT, "modes": modes or {}}))


def _events(result: Doc) -> list[str]:
    return cast("list[str]", result["events"])


def _errors(result: Doc) -> list[str]:
    return cast("list[str]", result["errors"])


class TestInit:
    def test_every_module_loads_and_starts_with_the_watcher_first(self, run_lua: RunLua) -> None:
        result = _start(run_lua)

        assert _events(result) == [
            "require:reload_watcher",
            "start:reload_watcher",
            "require:input_source",
            "start:input_source",
            "require:bar",
            "start:bar",
        ]
        assert _errors(result) == []

    def test_a_module_that_is_commented_out_is_never_loaded(self, run_lua: RunLua) -> None:
        assert "require:hyper" not in _events(_start(run_lua))

    def test_the_shutdown_callback_is_the_bars_stop_when_it_started(self, run_lua: RunLua) -> None:
        result = _start(run_lua)

        assert result["shutdown_is_bar_stop"] is True

    @pytest.mark.parametrize("failure", ["require_error", "start_error", "missing"])
    def test_the_watcher_starts_before_any_other_module_is_even_loaded_whatever_fails_later(
        self, run_lua: RunLua, failure: str
    ) -> None:
        result = _start(run_lua, {"input_source": failure, "bar": failure})

        assert _events(result)[:2] == ["require:reload_watcher", "start:reload_watcher"]

    @pytest.mark.parametrize("failure", ["require_error", "start_error", "missing"])
    def test_a_failing_input_source_does_not_stop_the_bar(
        self, run_lua: RunLua, failure: str
    ) -> None:
        result = _start(run_lua, {"input_source": failure})

        assert "start:bar" in _events(result)
        assert result["shutdown_is_bar_stop"] is True
        assert len(_errors(result)) == 1
        assert "modules.input_source" in _errors(result)[0]

    @pytest.mark.parametrize("failure", ["require_error", "start_error", "missing"])
    def test_a_failing_bar_does_not_stop_the_input_source_and_leaves_no_shutdown_callback(
        self, run_lua: RunLua, failure: str
    ) -> None:
        result = _start(run_lua, {"bar": failure})

        assert "start:input_source" in _events(result)
        assert result["shutdown_is_nil"] is True
        assert len(_errors(result)) == 1
        assert "modules.bar" in _errors(result)[0]

    @pytest.mark.parametrize(
        ("failure", "message"),
        [
            ("require_error", "boom in bar require"),
            ("start_error", "boom in bar start"),
        ],
    )
    def test_the_error_is_shown_once_naming_the_module_with_the_cause_and_a_traceback(
        self, run_lua: RunLua, failure: str, message: str
    ) -> None:
        result = _start(run_lua, {"bar": failure})

        (shown,) = _errors(result)
        assert shown.startswith("init.lua: modules.bar failed to start: ")
        assert message in shown
        assert "stack traceback" in shown
        assert "start:input_source" in _events(result)

    def test_a_module_missing_while_a_deploy_is_still_copying_is_shown_not_raised(
        self, run_lua: RunLua
    ) -> None:
        result = _start(run_lua, {"bar": "missing"})

        (shown,) = _errors(result)
        assert "modules.bar" in shown
        assert "not found" in shown
        assert "stack traceback" in shown

    def test_when_every_module_fails_the_watcher_is_still_running_and_each_error_is_shown(
        self, run_lua: RunLua
    ) -> None:
        result = _start(run_lua, {"input_source": "start_error", "bar": "require_error"})

        assert "start:reload_watcher" in _events(result)
        assert len(_errors(result)) == 2
        assert result["shutdown_is_nil"] is True

    def test_a_bar_whose_start_raised_is_not_registered_for_shutdown(self, run_lua: RunLua) -> None:
        result = _start(run_lua, {"bar": "start_error"})

        assert "start:bar" in _events(result)
        assert result["shutdown_is_bar_stop"] is False
        assert result["shutdown_is_nil"] is True
