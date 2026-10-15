-- TLA+ support: SANY diagnostics for nvim-lint and the jar location shared with the runners.
local M = {}

function M.jar()
	local jar = vim.env.TLA2TOOLS_JAR
	if jar == nil or jar == "" then
		jar = vim.fn.expand("~/.local/share/tlaplus/tla2tools/tla2tools.jar")
	end
	return jar
end

-- SANY reports problems in several shapes; only those located in the linted module are kept:
--   line 5, col 9 to line 5, col 11 of module Foo   (semantic, message on the next non-empty line)
--   Encountered "x" at line 6, column 1 and token "y"   (parse, under "Parsing file <path>")
--   Lexical error at line 4, column 7.  Encountered: ...
function M.parse_sany(output, bufnr)
	local severity = vim.diagnostic.severity
	local path = vim.api.nvim_buf_get_name(bufnr)
	local module = vim.fn.fnamemodify(path, ":t:r")
	local diagnostics = {}
	local current = severity.ERROR
	local parsing_this = true
	local expecting
	local pending

	for line in vim.gsplit(output, "\n", { plain = true }) do
		local parsing = line:match("^Parsing file (.+)$")
		if parsing then
			parsing_this = vim.fn.fnamemodify(parsing, ":t:r") == module
		elseif line:match("^%*%*%* Errors:") then
			current = severity.ERROR
		elseif line:match("^%*%*%* Warnings:") then
			current = severity.WARN
		elseif pending ~= nil and line:match("%S") then
			if pending then
				pending.message = vim.trim(line)
				table.insert(diagnostics, pending)
			end
			pending = nil
		else
			local l1, c1, l2, c2, mod = line:match("^%s*line (%d+), col (%d+) to line (%d+), col (%d+) of module (%S+)")
			if l1 then
				pending = mod == module
						and {
							lnum = tonumber(l1) - 1,
							col = tonumber(c1) - 1,
							end_lnum = tonumber(l2) - 1,
							end_col = tonumber(c2),
							severity = current,
							source = "sany",
						}
					or false
			elseif line:match("^Was expecting") then
				expecting = vim.trim(line)
			else
				local l, c = line:match("at line (%d+), column (%d+)")
				if l and parsing_this and (line:match("^Encountered") or line:match("^Lexical error")) then
					local message = vim.trim(line)
					if expecting then
						message = message .. " (" .. expecting .. ")"
					end
					table.insert(diagnostics, {
						lnum = tonumber(l) - 1,
						col = tonumber(c) - 1,
						severity = severity.ERROR,
						source = "sany",
						message = message,
					})
					expecting = nil
				end
			end
		end
	end
	return diagnostics
end

-- Shell command running a tla2tools.jar entry point on the file substituted for `%`.
function M.tla2tools_command(main)
	return "java -XX:+UseParallelGC -cp " .. vim.fn.shellescape(M.jar()) .. " " .. main .. " %"
end

local function translate_pluscal()
	vim.cmd("write")
	local file = vim.api.nvim_buf_get_name(0)
	local result = vim.system({ "java", "-cp", M.jar(), "pcal.trans", "-nocfg", file }, { text = true }):wait()
	if result.code ~= 0 then
		vim.notify("PlusCal translation failed:\n" .. result.stdout .. result.stderr, vim.log.levels.ERROR)
		return
	end
	vim.cmd("checktime")
	vim.notify("PlusCal translated", vim.log.levels.INFO)
end

function M.setup()
	vim.api.nvim_create_autocmd("FileType", {
		group = vim.api.nvim_create_augroup("tlaplus_keymaps", { clear = true }),
		pattern = "tla",
		callback = function(ev)
			vim.keymap.set("n", "<leader>rp", translate_pluscal, { buffer = ev.buf, desc = "Translate PlusCal" })
			vim.keymap.set("n", "<leader>ra", function()
				vim.cmd("write")
				vim.cmd("vsplit | terminal apalache-mc check " .. vim.fn.shellescape(vim.fn.expand("%")))
			end, { buffer = ev.buf, desc = "Apalache check" })
		end,
	})
end

function M.sany_linter()
	return {
		cmd = "java",
		args = {
			"-cp",
			M.jar,
			"tla2sany.SANY",
		},
		stdin = false,
		append_fname = true,
		stream = "stdout",
		ignore_exitcode = true,
		parser = M.parse_sany,
	}
end

return M
