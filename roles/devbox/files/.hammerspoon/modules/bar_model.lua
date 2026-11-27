-- Workspace model for the SketchyBar indicator: turns successive snapshots of
-- `rift-cli query workspaces` into one view entry per workspace.
--
-- Pure Lua (no hs.*), so it runs under plain `lua` in the tests.
--
-- Rift's own events cannot be trusted for attribution: title and focus events
-- carry the *active* workspace, not the window's. The model therefore diffs
-- whole snapshots, where every window sits under the workspace that holds it.

local M = {}

-- One letter per Rift layout mode (LayoutMode in Rift's config types).
M.LAYOUT_TAGS = {
	master_stack = "M",
	bsp = "B",
	stack = "S",
	traditional = "T",
	scrolling = "C",
	floating = "F",
}

local function window_key(win)
	if win.window_server_id ~= nil then
		return tostring(win.window_server_id)
	end
	if type(win.id) == "table" and win.id.pid ~= nil and win.id.idx ~= nil then
		return tostring(win.id.pid) .. ":" .. tostring(win.id.idx)
	end
	return nil
end

-- Unread counter that apps put at the start of a window title: "(3) Inbox",
-- "[12] Chat". Returns 0 when the title carries none.
function M.unread_count(title)
	if type(title) ~= "string" then
		return 0
	end
	local n = title:match("^%((%d+)%)") or title:match("^%[(%d+)%]")
	return n and tonumber(n) or 0
end

function M.layout_tag(mode)
	return M.LAYOUT_TAGS[mode] or "?"
end

function M.new()
	-- titles == nil until the first snapshot: nothing that already exists at
	-- start is reported as activity.
	return { titles = nil, marks = {} }
end

-- Applies one snapshot. `workspaces` is the decoded JSON array; `is_quiet`
-- takes a bundle ID and returns true for apps that never raise a mark
-- (messengers). Returns the view: one table per workspace, in Rift's order.
function M.update(state, workspaces, is_quiet)
	is_quiet = is_quiet or function()
		return false
	end
	local baseline = state.titles == nil
	local previous = state.titles or {}
	local titles = {}
	local view = {}

	for _, ws in ipairs(workspaces or {}) do
		local name = tostring(ws.name)
		local visible = ws.is_active == true
		if visible then
			state.marks[name] = nil
		end

		for _, win in ipairs(ws.windows or {}) do
			local key = window_key(win)
			if key ~= nil then
				local title = win.title or ""
				titles[key] = title
				if not baseline and not visible and not is_quiet(win.bundle_id) then
					local old = previous[key]
					if old == nil then
						state.marks[name] = true
					elseif old ~= title and M.unread_count(title) > M.unread_count(old) then
						state.marks[name] = true
					end
				end
			end
		end

		local count = ws.window_count or #(ws.windows or {})
		view[#view + 1] = {
			name = name,
			display_uuid = ws.display_uuid,
			focused = ws.is_focused == true,
			visible = visible,
			occupied = count > 0,
			marked = state.marks[name] == true,
			layout = M.layout_tag(ws.layout_mode),
		}
	end

	-- A snapshot without a single window (Rift still enumerating at login or
	-- after a restart) never replaces the known windows: the next snapshot
	-- would report every window as new.
	if next(titles) ~= nil then
		state.titles = titles
	end
	return view
end

return M
