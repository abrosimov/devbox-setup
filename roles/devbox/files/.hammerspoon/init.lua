-- The reload watcher starts first and every other module is isolated, so a
-- module that fails to load (a deploy still writing files, a bug) neither
-- stops the others nor the reload that picks up the fix.
require("modules.reload_watcher").start()

-- A failure is still reported the way an uncaught error is (notification,
-- Console, traceback); only the other modules carry on.
local function start(name)
	local ok, result = xpcall(function()
		local module = require(name)
		module.start()
		return module
	end, debug.traceback)
	if not ok then
		hs.showError("init.lua: " .. name .. " failed to start: " .. tostring(result))
		return nil
	end
	return result
end

start("modules.input_source")

-- start("modules.hyper")

local bar = start("modules.bar")
if bar ~= nil then
	hs.shutdownCallback = bar.stop
end
