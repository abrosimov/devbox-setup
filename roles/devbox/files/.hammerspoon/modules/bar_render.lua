-- Builds the `sketchybar` arguments for the whole bar from the workspace view
-- (modules/bar_model.lua) and the system readings. Item names match the ones
-- declared in ~/.config/sketchybar/sketchybarrc.
--
-- Pure Lua (no hs.*), so it runs under plain `lua` in the tests.

local M = {}

-- Kanagawa, as in the kitty theme and bordersrc; SketchyBar wants 0xAARRGGBB.
M.COLOURS = {
	bg = "0xff1f1f28", -- sumiInk1
	selection = "0xff363646", -- sumiInk3
	fg = "0xffdcd7ba", -- fujiWhite
	dim = "0xff727169", -- fujiGray
	accent = "0xff7e9cd8", -- crystalBlue
	warn = "0xffff9e3b", -- roninYellow
	alert = "0xffe46876", -- waveRed
	transparent = "0x00000000",
}

local C = M.COLOURS

-- Memory in use as Activity Monitor counts it: app memory (anonymous minus
-- purgeable) plus wired plus compressed, as a share of physical memory.
function M.memory_percent(vm)
	if type(vm) ~= "table" or not vm.memSize or vm.memSize <= 0 or not vm.pageSize then
		return nil
	end
	local app = (vm.anonymousPages or 0) - (vm.pagesPurgeable or 0)
	if app < 0 then
		app = 0
	end
	local pages = app + (vm.pagesWiredDown or 0) + (vm.pagesUsedByVMCompressor or 0)
	local percent = pages * vm.pageSize * 100 / vm.memSize
	return math.max(0, math.min(100, math.floor(percent + 0.5)))
end

local function load_colour(percent)
	if percent == nil then
		return C.dim
	end
	if percent >= 85 then
		return C.alert
	end
	if percent >= 60 then
		return C.warn
	end
	return C.fg
end

local function percent_label(percent)
	if percent == nil then
		return "--"
	end
	return string.format("%d%%", math.floor(percent + 0.5))
end

-- Nerd Font glyphs, written as UTF-8 bytes: a private-use glyph is invisible
-- in most editors. nf-oct-cpu (U+F4BC) and nf-fa-memory (U+EFC5).
M.CPU_ICON = "\239\146\188"
M.RAM_ICON = "\238\191\133"

local function workspace_colours(ws)
	if ws.focused then
		return C.bg, C.accent
	end
	if ws.marked then
		return C.warn, ws.visible and C.selection or C.transparent
	end
	if ws.visible then
		return C.fg, C.selection
	end
	if ws.occupied then
		return C.fg, C.transparent
	end
	return C.dim, C.transparent
end

-- `display_index` maps a display UUID to SketchyBar's arrangement index. A
-- workspace whose display is unknown is hidden rather than drawn on a guess.
function M.workspace_args(view, display_index)
	local args = {}
	local function add(...)
		for _, v in ipairs({ ... }) do
			args[#args + 1] = v
		end
	end
	for _, ws in ipairs(view or {}) do
		local item = "ws." .. ws.name
		local index = display_index and display_index[ws.display_uuid]
		if index == nil then
			add("--set", item, "drawing=off")
		else
			local fg, bg = workspace_colours(ws)
			add(
				"--set",
				item,
				"drawing=on",
				"display=" .. tostring(index),
				"label=" .. ws.name .. " " .. ws.layout,
				"label.color=" .. fg,
				"background.color=" .. bg
			)
		end
	end
	return args
end

-- `s` holds the readings; any of them may be nil when not yet known.
--   cpu, ram: percent; battery: { percent, charging } or nil without one;
--   clock, input, app: strings.
function M.status_args(s)
	s = s or {}
	-- The colour is judged on the rounded value the label shows.
	local cpu = s.cpu and math.floor(s.cpu + 0.5)
	local ram = s.ram and math.floor(s.ram + 0.5)
	local args = {
		"--set",
		"cpu",
		"icon=" .. M.CPU_ICON,
		"icon.color=" .. load_colour(cpu),
		"label=" .. percent_label(cpu),
		"label.color=" .. load_colour(cpu),
		"--set",
		"ram",
		"icon=" .. M.RAM_ICON,
		"icon.color=" .. load_colour(ram),
		"label=" .. percent_label(ram),
		"label.color=" .. load_colour(ram),
		"--set",
		"clock",
		"label=" .. (s.clock or ""),
		"--set",
		"input",
		"label=" .. (s.input or ""),
		"--set",
		"front_app",
		"label=" .. (s.app or ""),
	}
	local b = s.battery
	if b == nil or b.percent == nil then
		args[#args + 1] = "--set"
		args[#args + 1] = "battery"
		args[#args + 1] = "drawing=off"
	else
		local colour = C.fg
		if not b.charging and b.percent <= 20 then
			colour = C.alert
		end
		args[#args + 1] = "--set"
		args[#args + 1] = "battery"
		args[#args + 1] = "drawing=on"
		args[#args + 1] = string.format("label=BAT %d%%%s", math.floor(b.percent + 0.5), b.charging and "+" or "")
		args[#args + 1] = "label.color=" .. colour
	end
	return args
end

-- nf-fa-upload (U+F093) from the bar's Nerd Font. Written as UTF-8 bytes: a
-- private-use glyph is invisible in most editors.
M.EDGE_ICON = "\239\130\147"

local EDGE_COLOURS = { ok = C.fg, warning = C.warn, critical = C.alert }

-- `e` is bar_edge.summarise's result, or nil before the first poll.
function M.edge_args(e)
	local label, colour = "--", C.dim
	if e ~= nil and e.state == "down" then
		label = "✕"
	elseif e ~= nil and e.state == "ok" then
		label = string.format("%d%%", e.percent)
		for _, marker in ipairs(e.markers or {}) do
			label = label .. " " .. marker
		end
		colour = EDGE_COLOURS[e.level] or C.fg
	end
	return {
		"--set",
		"edge",
		"icon=" .. M.EDGE_ICON,
		"icon.color=" .. colour,
		"label=" .. label,
		"label.color=" .. colour,
	}
end

-- SketchyBar's `--query displays` output decoded from JSON: UUID → arrangement-id.
function M.display_index(displays)
	local index = {}
	for _, d in ipairs(displays or {}) do
		if d.UUID and d["arrangement-id"] then
			index[d.UUID] = d["arrangement-id"]
		end
	end
	return index
end

-- Short name of the current input source, from its source ID
-- ("com.apple.keylayout.Russian" → "RU", "com.apple.keylayout.ABC" → "EN").
function M.input_label(source_id)
	if type(source_id) ~= "string" or source_id == "" then
		return ""
	end
	local name = source_id:match("([^.]+)$") or source_id
	local known = { ABC = "EN", US = "EN", British = "EN", Russian = "RU", RussianWin = "RU" }
	if known[name] then
		return known[name]
	end
	if name:match("^Russian") then
		return "RU"
	end
	return name:sub(1, 2):upper()
end

return M
