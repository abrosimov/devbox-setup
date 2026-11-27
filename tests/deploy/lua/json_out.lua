-- JSON encoder for the Lua drivers in tests/deploy: stdlib-only Lua has none.
-- An empty table encodes as [], a table with positive integer keys 1..n as an
-- array, anything else as an object with sorted keys.

local escapes = {
	['"'] = '\\"',
	["\\"] = "\\\\",
	["\n"] = "\\n",
	["\r"] = "\\r",
	["\t"] = "\\t",
}

local function encode_string(s)
	return '"' .. s:gsub('[%c"\\]', function(c)
		return escapes[c] or string.format("\\u%04x", c:byte())
	end) .. '"'
end

local encode

local function is_array(t)
	local n = 0
	for _ in pairs(t) do
		n = n + 1
	end
	return n == #t
end

function encode(v)
	local kind = type(v)
	if v == nil then
		return "null"
	elseif kind == "boolean" then
		return tostring(v)
	elseif kind == "number" then
		if math.type(v) == "integer" then
			return string.format("%d", v)
		end
		return string.format("%.17g", v)
	elseif kind == "string" then
		return encode_string(v)
	elseif kind == "table" then
		if is_array(v) then
			local out = {}
			for i = 1, #v do
				out[i] = encode(v[i])
			end
			return "[" .. table.concat(out, ",") .. "]"
		end
		local keys = {}
		for k in pairs(v) do
			keys[#keys + 1] = tostring(k)
		end
		table.sort(keys)
		local out = {}
		for _, k in ipairs(keys) do
			out[#out + 1] = encode_string(k) .. ":" .. encode(v[k])
		end
		return "{" .. table.concat(out, ",") .. "}"
	end
	error("cannot encode " .. kind)
end

return encode
