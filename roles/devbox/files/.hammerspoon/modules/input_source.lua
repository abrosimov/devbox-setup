local M = {}

local windowLayouts = {}
local inputSourceWatcher, windowFilter

function M.start()
	inputSourceWatcher = hs.distributednotifications.new(function()
		local win = hs.window.focusedWindow()
		if win then
			windowLayouts[win:id()] = hs.keycodes.currentSourceID()
		end
	end, "com.apple.Carbon.TISNotifySelectedKeyboardInputSourceChanged")
	inputSourceWatcher:start()

	windowFilter = hs.window.filter.default
	windowFilter:subscribe(hs.window.filter.windowFocused, function(win)
		if not win then
			return
		end
		local saved = windowLayouts[win:id()]
		if saved and saved ~= hs.keycodes.currentSourceID() then
			hs.keycodes.currentSourceID(saved)
		end
	end)
	windowFilter:subscribe(hs.window.filter.windowDestroyed, function(win)
		if win then
			windowLayouts[win:id()] = nil
		end
	end)
end

function M.stop()
	if inputSourceWatcher then
		inputSourceWatcher:stop()
	end
	if windowFilter then
		windowFilter:unsubscribeAll()
	end
end

return M
