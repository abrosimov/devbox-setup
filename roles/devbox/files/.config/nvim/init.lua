-- Set dot (.) as the leader key
-- See `:help mapleader`
--  NOTE: Must happen before plugins are loaded (otherwise wrong leader will be used)
vim.g.mapleader = '.'
vim.g.maplocalleader = '.'

vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1
vim.opt.termguicolors = true

-- Ensure vim.lsp.config['*'] exists before blink.cmp loads (workaround for saghen/blink.cmp#2379)
if vim.fn.has('nvim-0.11') == 1 and vim.lsp.config and not vim.lsp.config['*'] then
    vim.lsp.config('*', {})
end

-- Map space to half-page down in normal mode
vim.keymap.set('n', '<Space>', '<C-d>', { desc = 'Half page down' })

vim.opt.number = true
-- Enable break indent
vim.opt.breakindent = true

-- Sync clipboard between OS and Neovim.
--  See `:help 'clipboard'`
vim.opt.clipboard = 'unnamedplus'

-- Delete/change/x go to black hole register — don't pollute OS clipboard.
-- Yank (y) and paste (p) still sync with OS clipboard via unnamedplus.
-- Use <leader>X when you need "cut" (delete + copy to clipboard).
vim.keymap.set({ 'n', 'v' }, 'd', '"_d')
vim.keymap.set({ 'n', 'v' }, 'D', '"_D')
vim.keymap.set({ 'n', 'v' }, 'c', '"_c')
vim.keymap.set({ 'n', 'v' }, 'C', '"_C')
vim.keymap.set('n', 'x', '"_x')
vim.keymap.set({ 'n', 'v' }, '<leader>X', 'd', { desc = 'Cut (delete + yank to clipboard)' })

-- Save undo history
vim.opt.undofile = true

-- Case-insensitive searching UNLESS \C or one or more capital letters in the search term
vim.opt.ignorecase = true
vim.opt.smartcase = true

-- Keep signcolumn on by default
vim.opt.signcolumn = 'yes'

-- Decrease update time
vim.opt.updatetime = 250

-- Decrease mapped sequence wait time
-- Displays which-key popup sooner
vim.opt.timeoutlen = 300

-- Configure how new splits should be opened
vim.opt.splitright = true
vim.opt.splitbelow = true

-- Cursor must always be like "block"
vim.opt.guicursor = "n-v-c-i:block"

vim.opt.cursorline = true
vim.opt.scrolloff = 10

vim.opt.foldmethod = "expr"
vim.opt.foldexpr = "v:lua.vim.treesitter.foldexpr()"
vim.opt.foldlevelstart = 99

-- [[ Basic Keymaps ]]
--  See `:help vim.keymap.set()`

-- Esc: close floating windows + clear search highlight
vim.opt.hlsearch = true
vim.keymap.set("n", "<Esc>", function()
    for _, win in ipairs(vim.api.nvim_list_wins()) do
        if vim.api.nvim_win_get_config(win).relative ~= "" then
            pcall(vim.api.nvim_win_close, win, true)
        end
    end
    vim.cmd("nohlsearch")
end)

-- Diagnostic keymaps
vim.keymap.set('n', '[d', vim.diagnostic.goto_prev, { desc = 'Go to previous [D]iagnostic message' })
vim.keymap.set('n', ']d', vim.diagnostic.goto_next, { desc = 'Go to next [D]iagnostic message' })
vim.keymap.set('n', '<leader>q', vim.diagnostic.setloclist, { desc = 'Open diagnostic [Q]uickfix list' })

-- Git conflict marker navigation (treesitter owns [c/]c for classes)
vim.keymap.set('n', '[C', '[c', { desc = 'Previous git [C]onflict marker' })
vim.keymap.set('n', ']C', ']c', { desc = 'Next git [C]onflict marker' })

-- Keybinds to make split navigation easier.
--  Use CTRL+<hjkl> to switch between windows
--
--  See `:help wincmd` for a list of all window commands
vim.keymap.set('n', '<C-h>', '<C-w><C-h>', { desc = 'Move focus to the left window' })
vim.keymap.set('n', '<C-l>', '<C-w><C-l>', { desc = 'Move focus to the right window' })
vim.keymap.set('n', '<C-j>', '<C-w><C-j>', { desc = 'Move focus to the lower window' })
vim.keymap.set('n', '<C-k>', '<C-w><C-k>', { desc = 'Move focus to the upper window' })

-- Buffer cycling
vim.keymap.set('n', '<Tab>', '<cmd>bnext<CR>', { desc = 'Next buffer' })
vim.keymap.set('n', '<S-Tab>', '<cmd>bprevious<CR>', { desc = 'Prev buffer' })

-- Run main in split
vim.keymap.set("n", "<leader>rm", function()
    local runners = {
        go = "go run .",
        c = "cc -o /tmp/a.out % && /tmp/a.out",
        cpp = "c++ -o /tmp/a.out % && /tmp/a.out",
        rust = "cargo run",
        python = "python3 %",
        typescript = "npx tsx %",
        javascript = "node %",
        dart = "dart run",
        swift = "swift run",
        ocaml = "dune exec .",
    }
    local cmd = runners[vim.bo.filetype]
    if cmd then
        cmd = cmd:gsub("%%", vim.fn.expand("%"))
        vim.cmd("vsplit | terminal " .. cmd)
    else
        vim.notify("No runner for filetype: " .. vim.bo.filetype, vim.log.levels.WARN)
    end
end, { desc = "Run main in split" })

-- Enable LSP semantic tokens for all servers
vim.api.nvim_create_autocmd("LspAttach", {
    group = vim.api.nvim_create_augroup("lsp_semantic_tokens", { clear = true }),
    callback = function(args)
        local client = vim.lsp.get_client_by_id(args.data.client_id)
        if not client then return end
        if not client.server_capabilities.semanticTokensProvider then
            local semantic = client.config.capabilities.textDocument.semanticTokens
            if semantic and type(semantic) == "table" then
                client.server_capabilities.semanticTokensProvider = {
                    full = true,
                    legend = { tokenTypes = semantic.tokenTypes, tokenModifiers = semantic.tokenModifiers },
                    range = true,
                }
            end
        end
    end,
})

require("config.lazy")
