-- otelbox edge state for the bar: queue fill from :8888/metrics, mirroring
-- scripts/otelbox_edge/watch.py, plus that watcher's stall and disk verdicts.
-- Pure Lua (no hs.*), so it runs under plain `lua` in the tests.

local M = {}

M.WARNING_FILL = 0.5
M.CRITICAL_FILL = 0.8
-- watch.py's OBSERVATION_GAP_SECONDS: older verdicts come from a watcher that has stopped.
M.WATCH_MAX_AGE = 15 * 60
-- Display bound (±1000 %), so the percentage is always a small integer.
M.FILL_BOUND = 10
M.LEVELS = { "ok", "warning", "critical" }
-- watch.py conditions shown as a marker, in display order. Its queue_fill is
-- left out: the live fill is newer than the watcher's last run.
M.MARKERS = { "stall", "disk" }

local RANK = { ok = 1, warning = 2, critical = 3 }

local function is_finite(v)
	return v == v and v ~= math.huge and v ~= -math.huge
end

-- A sample value as Python's float() reads it, which is what watch.py uses:
-- decimal and exponent forms, inf/infinity/nan in any case and with a sign.
function M.sample_value(text)
	if type(text) ~= "string" then
		return nil
	end
	local lower = text:lower()
	local sign, word = lower:match("^([+-]?)(%a+)$")
	if word == "inf" or word == "infinity" then
		return sign == "-" and -math.huge or math.huge
	end
	if word == "nan" then
		return 0 / 0
	end
	-- Lua's tonumber also takes hex, which float() refuses.
	if lower:find("x", 1, true) then
		return nil
	end
	return tonumber(text)
end

-- Exporter queues from the exposition text: label set ("{...}", or "" for an
-- unlabelled series) -> { size, capacity }, for every queue with a positive
-- capacity. Returns nil when any queue sample is not finite, as watch.py's
-- queue_series does.
function M.queue_series(text)
	if type(text) ~= "string" then
		return nil
	end
	local sizes, capacities = {}, {}
	for raw in text:gmatch("[^\r\n]+") do
		local line = raw:match("^%s*(.-)%s*$")
		if line ~= "" and line:sub(1, 1) ~= "#" then
			local fields = {}
			for field in line:gmatch("%S+") do
				fields[#fields + 1] = field
			end
			local value = #fields >= 2 and M.sample_value(fields[#fields]) or nil
			if value ~= nil then
				local name, labels = fields[1]:match("^([^{]*)(.*)$")
				if name == "otelcol_exporter_queue_capacity" then
					if not is_finite(value) then
						return nil
					end
					capacities[labels] = value
				elseif name == "otelcol_exporter_queue_size" then
					if not is_finite(value) then
						return nil
					end
					sizes[labels] = value
				end
			end
		end
	end
	local series = {}
	for key, size in pairs(sizes) do
		local capacity = capacities[key]
		if capacity ~= nil and capacity > 0 then
			series[key] = { size = size, capacity = capacity }
		end
	end
	return series
end

-- Highest size / capacity across the queues; nil without a queue.
function M.max_fill(series)
	local highest
	for _, q in pairs(series or {}) do
		local fill = q.size / q.capacity
		if highest == nil or fill > highest then
			highest = fill
		end
	end
	return highest
end

function M.fill_level(fill)
	if fill == nil or fill < M.WARNING_FILL then
		return "ok"
	end
	if fill >= M.CRITICAL_FILL then
		return "critical"
	end
	return "warning"
end

-- The `notified` levels of a decoded watch.json: condition -> level, keeping
-- only the levels watch.py itself accepts. Anything unreadable, or a last_run
-- more than WATCH_MAX_AGE before `now` (epoch seconds), yields {}.
function M.watch_alerts(document, now)
	local alerts = {}
	if type(document) ~= "table" or type(document.notified) ~= "table" then
		return alerts
	end
	local last_run = document.last_run
	if type(last_run) ~= "number" or type(now) ~= "number" or now - last_run > M.WATCH_MAX_AGE then
		return alerts
	end
	for condition, level in pairs(document.notified) do
		if type(condition) == "string" and RANK[level] ~= nil then
			alerts[condition] = level
		end
	end
	return alerts
end

local function stronger(a, b)
	return RANK[b] > RANK[a] and b or a
end

-- What the bar item shows. `metrics` is the body of :8888/metrics, or nil when
-- the edge did not answer; `alerts` comes from watch_alerts. Returns one of
--   { state = "down" }     the edge did not answer;
--   { state = "unknown" }  it answered without a finite exporter queue;
--   { state = "ok", percent, level, markers } otherwise, where `level` is the
--     strongest of the fill level and the markers' levels.
function M.summarise(metrics, alerts)
	if metrics == nil then
		return { state = "down" }
	end
	local fill = M.max_fill(M.queue_series(metrics))
	if fill == nil then
		return { state = "unknown" }
	end
	local level = M.fill_level(fill)
	local markers = {}
	for _, condition in ipairs(M.MARKERS) do
		local marked = (alerts or {})[condition]
		if marked ~= nil and marked ~= "ok" then
			markers[#markers + 1] = condition
			level = stronger(level, marked)
		end
	end
	return {
		state = "ok",
		percent = math.floor(100 * math.max(-M.FILL_BOUND, math.min(M.FILL_BOUND, fill)) + 0.5),
		level = level,
		markers = markers,
	}
end

-- Whether `sketchybar --query bar` (decoded) lists the item: the rc declares
-- it only on machines that run the edge.
function M.declared(bar, item)
	if type(bar) ~= "table" or type(bar.items) ~= "table" then
		return false
	end
	for _, name in ipairs(bar.items) do
		if name == item then
			return true
		end
	end
	return false
end

return M
