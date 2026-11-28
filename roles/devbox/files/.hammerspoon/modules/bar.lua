-- Sole source of what SketchyBar shows; the bar runs no scripts. The whole bar
-- is re-pushed and Rift re-queried every TICK, so a restarted SketchyBar or a
-- missed Rift event heals within one tick.

local model = require("modules.bar_model")
local render = require("modules.bar_render")
local edge_model = require("modules.bar_edge")

local M = {}

local TICK = 2
local CPU_SAMPLE = 1.0
local REFRESH_DELAY = 0.05
local RESTART_MIN, RESTART_MAX = 2, 60

local HOME = os.getenv("HOME")
local RIFT_CLI = HOME .. "/.local/bin/rift-cli"
local RIFT_BUNDLE = "git.acsandmann.rift"

local EDGE_ITEM = "edge"
local EDGE_POLL = 15
local EDGE_METRICS_URL = "http://127.0.0.1:8888/metrics"
local EDGE_WATCH_STATE = HOME .. "/.local/state/otelbox/watch.json"

-- Messengers never raise an activity mark: they signal on their own. Apps that
-- declare the social-networking category are caught by category; this list
-- holds the ones that declare another (Slack and Teams say "business").
local QUIET_BUNDLES = {
	["com.tinyspeck.slackmacgap"] = true,
	["com.microsoft.teams2"] = true,
	["com.hnc.Discord"] = true,
	["ru.keepcoder.Telegram"] = true,
	["org.telegram.desktop"] = true,
	["net.whatsapp.WhatsApp"] = true,
	["org.whispersystems.signal-desktop"] = true,
	["com.apple.MobileSMS"] = true,
}
local QUIET_CATEGORY = "public.app-category.social-networking"

local function find_sketchybar()
	for _, path in ipairs({ "/opt/homebrew/bin/sketchybar", "/usr/local/bin/sketchybar" }) do
		if hs.fs.attributes(path, "mode") == "file" then
			return path
		end
	end
	return nil
end

local sketchybar
local state = model.new()
local view = {}
local display_index = {}
local status = {}
-- nil until SketchyBar has answered. The rc declares the item only where the
-- edge runs, and a --set on an undeclared item must not reach the push.
local edge_declared
local edge

local quiet_cache = {}
local function is_quiet(bundle_id)
	if bundle_id == nil then
		return false
	end
	local cached = quiet_cache[bundle_id]
	if cached ~= nil then
		return cached
	end
	local quiet = QUIET_BUNDLES[bundle_id] == true
	if not quiet then
		local info = hs.application.infoForBundleID(bundle_id)
		quiet = info ~= nil and info.LSApplicationCategoryType == QUIET_CATEGORY
	end
	quiet_cache[bundle_id] = quiet
	return quiet
end

local push_task, push_again
local function push()
	if sketchybar == nil then
		return
	end
	if push_task ~= nil and push_task:isRunning() then
		push_again = true
		return
	end
	push_again = false
	local args = render.workspace_args(view, display_index)
	for _, v in ipairs(render.status_args(status)) do
		args[#args + 1] = v
	end
	if edge_declared then
		for _, v in ipairs(render.edge_args(edge)) do
			args[#args + 1] = v
		end
	end
	push_task = hs.task.new(sketchybar, function()
		push_task = nil
		if push_again then
			push()
		end
	end, args)
	if not push_task:start() then
		push_task = nil
	end
end

local displays_task
local function refresh_displays()
	if sketchybar == nil or (displays_task ~= nil and displays_task:isRunning()) then
		return
	end
	displays_task = hs.task.new(sketchybar, function(code, out)
		displays_task = nil
		if code ~= 0 then
			return
		end
		local ok, decoded = pcall(hs.json.decode, out)
		if ok and type(decoded) == "table" then
			display_index = render.display_index(decoded)
			push()
		end
	end, { "--query", "displays" })
	if not displays_task:start() then
		displays_task = nil
	end
end

local query_task, query_again
local function refresh_workspaces()
	if query_task ~= nil and query_task:isRunning() then
		query_again = true
		return
	end
	query_again = false
	query_task = hs.task.new(RIFT_CLI, function(code, out)
		query_task = nil
		if code == 0 then
			local ok, decoded = pcall(hs.json.decode, out)
			if ok and type(decoded) == "table" then
				view = model.update(state, decoded, is_quiet)
				push()
			end
		end
		if query_again then
			refresh_workspaces()
		end
	end, { "query", "workspaces" })
	if not query_task:start() then
		query_task = nil
	end
end

-- Leading-edge debounce: a burst of events yields one query REFRESH_DELAY
-- after its first event, and a steady stream cannot postpone it.
local refresh_timer = hs.timer.delayed.new(REFRESH_DELAY, refresh_workspaces)
local function schedule_refresh()
	if not refresh_timer:running() then
		refresh_timer:start()
	end
end

-- The subscriber never exits when Rift dies: rift-cli blocks on its Mach port
-- with no timeout and no dead-name notification. Rift's pid is therefore
-- checked every tick, and a new Rift gets a new subscriber.
local subscriber, restart_timer, rift_pid
local restart_delay = RESTART_MIN
local subscribe

local function schedule_subscribe()
	restart_timer = hs.timer.doAfter(restart_delay, subscribe)
	restart_delay = math.min(restart_delay * 2, RESTART_MAX)
end

subscribe = function()
	restart_timer = nil
	subscriber = hs.task.new(RIFT_CLI, function()
		subscriber = nil
		schedule_subscribe()
	end, function(_, out)
		if out ~= nil and out ~= "" then
			restart_delay = RESTART_MIN
			schedule_refresh()
		end
		return true
	end, { "subscribe", "mach", "*" })
	if subscriber:start() then
		schedule_refresh()
	else
		subscriber = nil
		schedule_subscribe()
	end
end

local function current_rift_pid()
	local app = hs.application.applicationsForBundleID(RIFT_BUNDLE)[1]
	return app and app:pid() or nil
end

local function check_rift()
	local pid = current_rift_pid()
	if pid == rift_pid then
		return
	end
	rift_pid = pid
	if pid == nil then
		return
	end
	restart_delay = RESTART_MIN
	if subscriber ~= nil then
		-- Its exit callback schedules the new subscriber.
		subscriber:terminate()
	elseif restart_timer ~= nil then
		restart_timer:stop()
		subscribe()
	end
end

local function read_battery()
	local percent = hs.battery.percentage()
	if percent == nil then
		return nil
	end
	return { percent = percent, charging = hs.battery.isCharging() == true }
end

local function read_input()
	status.input = render.input_label(hs.keycodes.currentSourceID())
end

local function read_app()
	local app = hs.application.frontmostApplication()
	status.app = app and app:name() or ""
end

local function read_watch_alerts()
	local file = io.open(EDGE_WATCH_STATE, "r")
	if file == nil then
		return {}
	end
	local content = file:read("a")
	file:close()
	local ok, decoded = pcall(hs.json.decode, content or "")
	-- The same epoch as watch.py's time.time().
	return edge_model.watch_alerts(ok and decoded or nil, hs.timer.secondsSinceEpoch())
end

-- hs.http cannot cancel a request: one still outstanding at the next poll
-- counts as no answer, and its late answer is ignored.
local edge_request_since
local function fetch_edge()
	local now = hs.timer.secondsSinceEpoch()
	if edge_request_since ~= nil then
		edge = edge_model.summarise(nil, {})
		push()
	end
	edge_request_since = now
	hs.http.asyncGet(EDGE_METRICS_URL, nil, function(code, body)
		if edge_request_since ~= now then
			return
		end
		edge_request_since = nil
		edge = edge_model.summarise(code == 200 and body or nil, read_watch_alerts())
		push()
	end)
end

-- SketchyBar is asked every poll whether the item exists, so a reloaded rc
-- that adds or drops it is followed, and a machine without it never polls :8888.
local bar_task
local function poll_edge()
	if sketchybar == nil or (bar_task ~= nil and bar_task:isRunning()) then
		return
	end
	bar_task = hs.task.new(sketchybar, function(code, out)
		bar_task = nil
		if code ~= 0 then
			return
		end
		local ok, decoded = pcall(hs.json.decode, out)
		if not ok or type(decoded) ~= "table" then
			return
		end
		edge_declared = edge_model.declared(decoded, EDGE_ITEM)
		if edge_declared then
			fetch_edge()
		end
	end, { "--query", "bar" })
	if not bar_task:start() then
		bar_task = nil
	end
end

local cpu_sampler
local function tick()
	status.ram = render.memory_percent(hs.host.vmStat())
	status.battery = read_battery()
	status.clock = os.date("%a %d %b %H:%M")
	if cpu_sampler == nil or cpu_sampler:finished() then
		cpu_sampler = hs.host.cpuUsage(CPU_SAMPLE, function(result)
			local overall = result and result.overall
			if overall and overall.active == overall.active then -- not NaN
				status.cpu = overall.active
			end
		end)
	end
	if next(display_index) == nil then
		refresh_displays()
	end
	check_rift()
	refresh_workspaces()
	push()
end

local tick_timer, edge_timer, screen_watcher, app_watcher, input_watcher

function M.start()
	sketchybar = find_sketchybar()
	if sketchybar == nil then
		return
	end

	read_input()
	read_app()

	input_watcher = hs.distributednotifications.new(function()
		read_input()
		push()
	end, "com.apple.Carbon.TISNotifySelectedKeyboardInputSourceChanged")
	input_watcher:start()

	app_watcher = hs.application.watcher.new(function(name, event)
		if event == hs.application.watcher.activated then
			status.app = name or ""
			push()
		end
	end)
	app_watcher:start()

	screen_watcher = hs.screen.watcher.new(function()
		refresh_displays()
		schedule_refresh()
	end)
	screen_watcher:start()

	rift_pid = current_rift_pid()
	refresh_displays()
	subscribe()
	tick_timer = hs.timer.doEvery(TICK, tick)
	tick()
	edge_timer = hs.timer.doEvery(EDGE_POLL, poll_edge)
	poll_edge()
end

-- Called on reload too (init.lua), so the subscriber process does not outlive
-- the Lua state that reads it.
function M.stop()
	refresh_timer:stop()
	for _, obj in pairs({ tick_timer, edge_timer, restart_timer, screen_watcher, app_watcher, input_watcher, cpu_sampler }) do
		obj:stop()
	end
	if subscriber ~= nil then
		local running = subscriber
		subscriber = nil
		running:setCallback(nil)
		running:terminate()
	end
end

return M
