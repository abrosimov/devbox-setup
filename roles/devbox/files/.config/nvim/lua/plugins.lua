return {
    -- "folke/neoconf.nvim"
    {
	    'tpope/vim-sleuth', -- Detect tabstop and shiftwidth automatically
    },
    {
            'numToStr/Comment.nvim',
    },
    {
	    "folke/tokyonight.nvim",
	    lazy = false, -- make sure we load this during startup if it is your main colorscheme
	    priority = 1000, -- make sure to load this before all the other start plugins
	    config = function()
	      -- load the colorscheme here
	      vim.cmd([[colorscheme tokyonight]])
	    end,
    },
    {
	    "nvim-treesitter/nvim-treesitter",
	    branch = 'master',
	    lazy = false,
	    build = ":TSUpdate",
            opts = {
                ensure_installed = { 'bash', 'python', 'go', 'c', 'diff', 'html', 'lua', 'luadoc', 'markdown', 'vim', 'vimdoc' },
                -- Autoinstall languages that are not installed
                auto_install = true,
                highlight = {
                    enable = true,
                    -- Some languages depend on vim's regex highlighting system (such as Ruby) for indent rules.
                    --  If you are experiencing weird indenting issues, add the language to
                    --  the list of additional_vim_regex_highlighting and disabled languages for indent.
                    additional_vim_regex_highlighting = { 'ruby' },
                },
                indent = { enable = true, disable = { 'ruby' } },
	    },
            config = function(_, opts)
                -- [[ Configure Treesitter ]] See `:help nvim-treesitter`
                -- Prefer git instead of curl in order to improve connectivity in some environments
                require('nvim-treesitter.install').prefer_git = true
                ---@diagnostic disable-next-line: missing-fields
                require('nvim-treesitter.configs').setup(opts)
                -- There are additional nvim-treesitter modules that you can use to interact
                -- with nvim-treesitter. You should go explore a few and see what interests you:
                --
                --    - Incremental selection: Included, see `:help nvim-treesitter-incremental-selection-mod`
                --    - Show your current context: https://github.com/nvim-treesitter/nvim-treesitter-context
                --    - Treesitter + textobjects: https://github.com/nvim-treesitter/nvim-treesitter-textobjects
            end,
    },
    {
        'MeanderingProgrammer/render-markdown.nvim',
        dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-mini/mini.nvim' },            -- if you use the mini.nvim suite
        -- dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-mini/mini.icons' },        -- if you use standalone mini plugins
        -- dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-tree/nvim-web-devicons' }, -- if you prefer nvim-web-devicons
        ---@module 'render-markdown'
        ---@type render.md.UserConfig
        opts = {},
    },
    {
        "iamcco/markdown-preview.nvim",
        cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
        ft = { "markdown" },
        build = function() vim.fn["mkdp#util#install"]() end,
    },

    -- =====================================================================
    -- LSP, completion, and Go IDE plugins
    -- =====================================================================

    -- 1. Mason — LSP installer
    {
        "mason-org/mason.nvim",
        opts = {},
    },
    {
        "mason-org/mason-lspconfig.nvim",
        dependencies = { "mason-org/mason.nvim" },
        opts = {
            ensure_installed = { "gopls" },
        },
    },

    -- 2. LSP config
    {
        "neovim/nvim-lspconfig",
        dependencies = {
            "mason-org/mason-lspconfig.nvim",
            "saghen/blink.cmp",
        },
        config = function()
            local lspconfig = require("lspconfig")
            local capabilities = require("blink.cmp").get_lsp_capabilities()

            lspconfig.gopls.setup({
                capabilities = capabilities,
                settings = {
                    gopls = {
                        analyses = {
                            unusedparams = true,
                        },
                        staticcheck = true,
                    },
                },
            })

            vim.api.nvim_create_autocmd("LspAttach", {
                callback = function(ev)
                    local opts = { buffer = ev.buf }
                    vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)
                    vim.keymap.set("n", "gi", vim.lsp.buf.implementation, opts)
                    vim.keymap.set("n", "gr", vim.lsp.buf.references, opts)
                    vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
                    vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, opts)
                    vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, opts)
                    vim.keymap.set("n", "<leader>ds", vim.lsp.buf.document_symbol, opts)
                    vim.keymap.set("n", "<leader>ws", vim.lsp.buf.workspace_symbol, opts)
                end,
            })
        end,
    },

    -- 3. Completion — blink.cmp
    {
        "saghen/blink.cmp",
        version = "1.*",
        opts = {
            keymap = { preset = "default" },
            appearance = { nerd_font_variant = "mono" },
            completion = { documentation = { auto_show = true } },
            signature = { enabled = true },
            sources = {
                default = { "lsp", "path", "snippets", "buffer" },
            },
        },
    },

    -- 4. Telescope — fuzzy finder
    {
        "nvim-telescope/telescope.nvim",
        branch = "0.1.x",
        dependencies = {
            "nvim-lua/plenary.nvim",
            { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
        },
        config = function()
            local telescope = require("telescope")
            telescope.setup({
                defaults = {
                    layout_strategy = "vertical",
                    file_ignore_patterns = { "vendor/", "node_modules/" },
                },
            })
            telescope.load_extension("fzf")

            local builtin = require("telescope.builtin")
            vim.keymap.set("n", "<leader>ff", builtin.find_files, { desc = "Find files" })
            vim.keymap.set("n", "<leader>fg", builtin.live_grep, { desc = "Live grep" })
            vim.keymap.set("n", "<leader>fb", builtin.buffers, { desc = "List buffers" })
            vim.keymap.set("n", "<leader>fo", builtin.oldfiles, { desc = "Recent files" })
        end,
    },

    -- 5. File explorer
    {
        "nvim-tree/nvim-tree.lua",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        opts = {
            view = { width = 35 },
        },
        keys = {
            { "<leader>t", "<cmd>NvimTreeToggle<CR>", desc = "Toggle file explorer" },
        },
    },

    -- 6. Format on save — goimports -local
    {
        "stevearc/conform.nvim",
        event = "BufWritePre",
        config = function()
            require("conform").setup({
                formatters_by_ft = {
                    go = { "goimports" },
                },
                format_on_save = {
                    timeout_ms = 3000,
                    lsp_format = "fallback",
                },
                formatters = {
                    goimports = {
                        prepend_args = function()
                            -- Read module name from go.mod for -local flag
                            local gomod = vim.fn.findfile("go.mod", ".;")
                            if gomod ~= "" then
                                for line in io.lines(gomod) do
                                    local mod = line:match("^module%s+(%S+)")
                                    if mod then
                                        return { "-local", mod }
                                    end
                                end
                            end
                            return {}
                        end,
                    },
                },
            })
        end,
    },

    -- 7. Diagnostics list
    {
        "folke/trouble.nvim",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        opts = {},
        keys = {
            { "<leader>xx", "<cmd>Trouble diagnostics toggle<CR>", desc = "Toggle diagnostics" },
        },
    },

    -- 8. Debugging — DAP
    {
        "mfussenegger/nvim-dap",
        dependencies = {
            "leoluz/nvim-dap-go",
            "rcarriga/nvim-dap-ui",
            "nvim-neotest/nvim-nio",
        },
        config = function()
            local dap = require("dap")
            local dapui = require("dapui")

            require("dap-go").setup()
            dapui.setup()

            dap.listeners.after.event_initialized["dapui_config"] = function()
                dapui.open()
            end
            dap.listeners.before.event_terminated["dapui_config"] = function()
                dapui.close()
            end
            dap.listeners.before.event_exited["dapui_config"] = function()
                dapui.close()
            end

            vim.keymap.set("n", "<leader>db", dap.toggle_breakpoint, { desc = "Toggle breakpoint" })
            vim.keymap.set("n", "<leader>dc", dap.continue, { desc = "Continue debug" })
            vim.keymap.set("n", "<leader>dt", function()
                require("dap-go").debug_test()
            end, { desc = "Debug nearest test" })
        end,
    },

    -- 9. Test runner — neotest
    {
        "nvim-neotest/neotest",
        dependencies = {
            "nvim-neotest/nvim-nio",
            "nvim-lua/plenary.nvim",
            "nvim-treesitter/nvim-treesitter",
            "fredrikaverpil/neotest-golang",
        },
        config = function()
            local neotest = require("neotest")
            neotest.setup({
                adapters = {
                    require("neotest-golang"),
                },
            })

            vim.keymap.set("n", "<leader>tr", function() neotest.run.run() end, { desc = "Run nearest test" })
            vim.keymap.set("n", "<leader>tf", function() neotest.run.run(vim.fn.expand("%")) end, { desc = "Run file tests" })
            vim.keymap.set("n", "<leader>ts", function() neotest.summary.toggle() end, { desc = "Test summary" })
        end,
    },

    -- 10. Git signs
    {
        "lewis6991/gitsigns.nvim",
        opts = {
            signs = {
                add = { text = "+" },
                change = { text = "~" },
                delete = { text = "_" },
            },
        },
    },

    -- 11. Status bar
    {
        "nvim-lualine/lualine.nvim",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        opts = {
            options = {
                theme = "tokyonight",
            },
            sections = {
                lualine_b = { "branch", "diagnostics" },
            },
        },
    },

    -- 12. Buffer tabs
    {
        "akinsho/bufferline.nvim",
        version = "*",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        opts = {
            options = {
                diagnostics = "nvim_lsp",
                offsets = {
                    { filetype = "NvimTree", text = "Explorer", highlight = "Directory", separator = true },
                },
            },
        },
        keys = {
            { "<Tab>", "<cmd>BufferLineCycleNext<CR>", desc = "Next buffer" },
            { "<S-Tab>", "<cmd>BufferLineCyclePrev<CR>", desc = "Prev buffer" },
        },
    },

    -- 13. Key discovery
    {
        "folke/which-key.nvim",
        event = "VeryLazy",
        opts = {},
    },

    -- 14. Auto-close brackets
    {
        "windwp/nvim-autopairs",
        event = "InsertEnter",
        opts = {},
    },

    -- 15. Git worktree switching
    {
        "polarmutex/git-worktree.nvim",
        version = "2.*",
        dependencies = {
            "nvim-lua/plenary.nvim",
            "nvim-telescope/telescope.nvim",
        },
        config = function()
            require("git-worktree").setup()
            require("telescope").load_extension("git_worktree")

            vim.keymap.set("n", "<leader>gw", function()
                require("telescope").extensions.git_worktree.git_worktree()
            end, { desc = "Switch worktree" })
        end,
    },
}
