local M = {}

-- A deploy writes the config one file at a time. Reloading on the first one
-- loads an init.lua whose modules are not there yet, so the reload waits
-- until no .lua file has changed for SETTLE seconds.
local SETTLE = 3

function M.start()
	M.timer = hs.timer.delayed.new(SETTLE, hs.reload)
	M.watcher = hs.pathwatcher
		.new(hs.configdir, function(files)
			for _, file in ipairs(files) do
				if file:sub(-4) == ".lua" then
					M.timer:start()
					return
				end
			end
		end)
		:start()
end

return M
