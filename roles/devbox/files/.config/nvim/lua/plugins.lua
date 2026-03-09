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
	      vim.cmd([[colorscheme tokyonight-storm]])
	    end,
    },
    {
	    "nvim-treesitter/nvim-treesitter",
	    branch = 'main',
	    lazy = false,
	    build = ":TSUpdate",
            dependencies = {
                {
                    "nvim-treesitter/nvim-treesitter-textobjects",
                    branch = "main",
                    config = function()
                        require("nvim-treesitter-textobjects").setup({
                            move = { set_jumps = true },
                        })
                        local move = require("nvim-treesitter-textobjects.move")
                        vim.keymap.set({ "n", "x", "o" }, "]f", function() move.goto_next_start("@function.outer", "textobjects") end, { desc = "Next function" })
                        vim.keymap.set({ "n", "x", "o" }, "[f", function() move.goto_previous_start("@function.outer", "textobjects") end, { desc = "Prev function" })
                        vim.keymap.set({ "n", "x", "o" }, "]c", function() move.goto_next_start("@class.outer", "textobjects") end, { desc = "Next class" })
                        vim.keymap.set({ "n", "x", "o" }, "[c", function() move.goto_previous_start("@class.outer", "textobjects") end, { desc = "Prev class" })
                    end,
                },
            },
            config = function()
                local ts = require("nvim-treesitter")
                ts.setup()

                local langs = { 'bash', 'python', 'go', 'c', 'cpp', 'diff', 'html', 'lua', 'luadoc', 'markdown', 'vim', 'vimdoc', 'typescript', 'tsx', 'javascript', 'json', 'css', 'rust', 'ocaml', 'prolog', 'dart', 'swift', 'yaml', 'toml', 'dockerfile', 'fish', 'proto', 'hcl' }
                ts.install(langs, { summary = false })

                vim.api.nvim_create_autocmd("FileType", {
                    pattern = "*",
                    callback = function(ev)
                        pcall(vim.treesitter.start, ev.buf)
                        vim.bo[ev.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
                    end,
                })
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
    -- LSP, completion, and IDE plugins (Go + Python + TypeScript + Rust + OCaml + Prolog)
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
            ensure_installed = {
                "gopls", "pyright", "ts_ls", "rust_analyzer", "clangd",
                "yamlls", "jsonls", "lua_ls", "bashls", "dockerls",
                "marksman", "taplo", "terraformls",
            },
        },
    },

    -- 2. LSP config (Neovim 0.11+ native API)
    {
        "neovim/nvim-lspconfig",
        dependencies = {
            "mason-org/mason-lspconfig.nvim",
            "saghen/blink.cmp",
        },
        config = function()
            -- Go
            vim.lsp.config("gopls", {
                settings = {
                    gopls = {
                        semanticTokens = true,
                        analyses = {
                            unusedparams = true,
                        },
                        staticcheck = true,
                    },
                },
            })
            vim.lsp.enable("gopls")

            -- Python — pyright for types/completion, ruff for linting/formatting
            vim.lsp.config("pyright", {
                before_init = function(_, config)
                    local venv_python = config.root_dir .. "/.venv/bin/python"
                    if vim.uv.fs_stat(venv_python) then
                        config.settings.python.pythonPath = venv_python
                    end
                end,
                settings = {
                    python = {
                        analysis = {},
                    },
                },
            })
            vim.lsp.enable("pyright")

            vim.lsp.config("ruff", {})
            vim.lsp.enable("ruff")

            -- TypeScript/JavaScript
            vim.lsp.config("ts_ls", {})
            vim.lsp.enable("ts_ls")

            -- Rust
            vim.lsp.config("rust_analyzer", {
                settings = {
                    ["rust-analyzer"] = {
                        checkOnSave = { command = "clippy" },
                    },
                },
            })
            vim.lsp.enable("rust_analyzer")

            -- OCaml (installed via opam, not Mason)
            vim.lsp.config("ocamllsp", {})
            vim.lsp.enable("ocamllsp")

            -- Prolog (SWI-Prolog lsp_server pack)
            vim.lsp.config("prolog_lsp", {
                cmd = {
                    "swipl",
                    "-g", "use_module(library(lsp_server)).",
                    "-g", "lsp_server:main",
                    "-t", "halt",
                    "--", "stdio",
                },
                filetypes = { "prolog" },
            })
            vim.lsp.enable("prolog_lsp")

            -- C/C++ (clangd via Mason)
            vim.lsp.config("clangd", {})
            vim.lsp.enable("clangd")

            -- Swift (sourcekit-lsp ships with Xcode)
            vim.lsp.config("sourcekit", {})
            vim.lsp.enable("sourcekit")

            -- YAML (Ansible, k8s, CI configs)
            vim.lsp.config("yamlls", {
                settings = {
                    yaml = {
                        validate = true,
                        schemaStore = { enable = true },
                    },
                },
            })
            vim.lsp.enable("yamlls")

            -- JSON/JSONC (package.json, tsconfig, etc.)
            vim.lsp.config("jsonls", {
                settings = {
                    json = {
                        validate = { enable = true },
                    },
                },
            })
            vim.lsp.enable("jsonls")

            -- Lua (nvim config)
            vim.lsp.config("lua_ls", {
                settings = {
                    Lua = {
                        runtime = { version = "LuaJIT" },
                        workspace = {
                            library = { vim.env.VIMRUNTIME },
                            checkThirdParty = false,
                        },
                        diagnostics = { globals = { "vim" } },
                    },
                },
            })
            vim.lsp.enable("lua_ls")

            -- Bash/Shell
            vim.lsp.config("bashls", {})
            vim.lsp.enable("bashls")

            -- Dockerfile
            vim.lsp.config("dockerls", {})
            vim.lsp.enable("dockerls")

            -- Markdown
            vim.lsp.config("marksman", {})
            vim.lsp.enable("marksman")

            -- TOML (pyproject.toml, Cargo.toml)
            vim.lsp.config("taplo", {})
            vim.lsp.enable("taplo")

            -- Terraform/HCL
            vim.lsp.config("terraformls", {})
            vim.lsp.enable("terraformls")

            -- Protobuf (buf CLI)
            vim.lsp.config("buf_ls", {})
            vim.lsp.enable("buf_ls")

            -- Dart LSP is handled by flutter-tools.nvim — do NOT configure dartls here

            -- Disable hover from ruff so pyright handles it
            vim.api.nvim_create_autocmd("LspAttach", {
                group = vim.api.nvim_create_augroup("lsp_disable_ruff_hover", { clear = true }),
                callback = function(args)
                    local client = vim.lsp.get_client_by_id(args.data.client_id)
                    if client and client.name == "ruff" then
                        client.server_capabilities.hoverProvider = false
                    end
                end,
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

    -- 5. File explorer (filesystem right, open buffers left)
    {
        "nvim-neo-tree/neo-tree.nvim",
        branch = "v3.x",
        dependencies = {
            "nvim-lua/plenary.nvim",
            "MunifTanjim/nui.nvim",
            "nvim-tree/nvim-web-devicons",
        },
        opts = {
            filesystem = {
                follow_current_file = { enabled = true },
                window = {
                    position = "right",
                    width = 35,
                },
            },
            buffers = {
                follow_current_file = { enabled = true },
                group_empty_dirs = true,
                show_unloaded = true,
                window = {
                    position = "left",
                    width = 30,
                },
            },
        },
        keys = {
            { "<leader>t", "<cmd>Neotree toggle filesystem<CR>", desc = "Toggle file explorer" },
            { "<leader>b", "<cmd>Neotree toggle buffers<CR>", desc = "Toggle open buffers" },
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
                    python = { "ruff_organize_imports", "ruff_format" },
                    typescript = { "prettier" },
                    typescriptreact = { "prettier" },
                    javascript = { "prettier" },
                    javascriptreact = { "prettier" },
                    json = { "prettier" },
                    css = { "prettier" },
                    html = { "prettier" },
                    yaml = { "prettier" },
                    markdown = { "prettier" },
                    rust = { "rustfmt" },
                    ocaml = { "ocamlformat" },
                    dart = { "dart_format" },
                    swift = { "swift_format" },
                    c = { "clang_format" },
                    cpp = { "clang_format" },
                    lua = { "stylua" },
                    sh = { "shfmt" },
                    bash = { "shfmt" },
                    fish = { "fish_indent" },
                    proto = { "buf" },
                    terraform = { "terraform_fmt" },
                    toml = { "taplo" },
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
            "mfussenegger/nvim-dap-python",
            "mxsdev/nvim-dap-vscode-js",
            {
                "microsoft/vscode-js-debug",
                build = "npm install --legacy-peer-deps && npx gulp vsDebugServerBundle && mv dist out",
            },
            "rcarriga/nvim-dap-ui",
            "nvim-neotest/nvim-nio",
        },
        config = function()
            local dap = require("dap")
            local dapui = require("dapui")

            require("dap-go").setup()
            require("dap-python").setup("python3")

            -- Rust — codelldb
            local codelldb_path = vim.fn.stdpath("data") .. "/mason/bin/codelldb"
            if vim.fn.executable(codelldb_path) == 1 then
                dap.adapters.codelldb = {
                    type = "server",
                    port = "${port}",
                    executable = {
                        command = codelldb_path,
                        args = { "--port", "${port}" },
                    },
                }
                dap.configurations.rust = {
                    {
                        type = "codelldb",
                        request = "launch",
                        name = "Launch (cargo build)",
                        program = function()
                            return vim.fn.input("Path to executable: ", vim.fn.getcwd() .. "/target/debug/", "file")
                        end,
                        cwd = "${workspaceFolder}",
                        stopOnEntry = false,
                    },
                }

                local c_cpp_config = {
                    {
                        type = "codelldb",
                        request = "launch",
                        name = "Launch executable",
                        program = function()
                            return vim.fn.input("Path to executable: ", vim.fn.getcwd() .. "/", "file")
                        end,
                        cwd = "${workspaceFolder}",
                        stopOnEntry = false,
                    },
                }
                dap.configurations.c = c_cpp_config
                dap.configurations.cpp = c_cpp_config
            end

            -- TypeScript/JavaScript — vscode-js-debug
            require("dap-vscode-js").setup({
                debugger_path = vim.fn.stdpath("data") .. "/lazy/vscode-js-debug",
                adapters = { "pwa-node", "pwa-chrome" },
            })
            for _, lang in ipairs({ "typescript", "javascript", "typescriptreact", "javascriptreact" }) do
                dap.configurations[lang] = {
                    {
                        type = "pwa-node",
                        request = "launch",
                        name = "Launch file",
                        program = "${file}",
                        cwd = "${workspaceFolder}",
                    },
                    {
                        type = "pwa-node",
                        request = "attach",
                        name = "Attach",
                        processId = require("dap.utils").pick_process,
                        cwd = "${workspaceFolder}",
                    },
                    {
                        type = "pwa-chrome",
                        request = "launch",
                        name = "Launch Chrome",
                        url = "http://localhost:3000",
                        webRoot = "${workspaceFolder}",
                    },
                }
            end

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
            "antoinemadec/FixCursorHold.nvim",
            "nvim-treesitter/nvim-treesitter",
            "fredrikaverpil/neotest-golang",
            "nvim-neotest/neotest-python",
            "marilari88/neotest-vitest",
            "rouge8/neotest-rust",
        },
        config = function()
            local neotest = require("neotest")
            neotest.setup({
                adapters = {
                    require("neotest-golang")({}),
                    require("neotest-python")({ runner = "pytest" }),
                    require("neotest-vitest"),
                    require("neotest-rust"),
                },
            })
        end,
        keys = {
            { "<leader>tr", function() require("neotest").run.run() end, desc = "Run nearest test" },
            { "<leader>tf", function() require("neotest").run.run(vim.fn.expand("%")) end, desc = "Run file tests" },
            { "<leader>ts", function() require("neotest").summary.toggle() end, desc = "Test summary" },
            { "<leader>to", function() require("neotest").output_panel.toggle() end, desc = "Test output panel" },
        },
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

    -- 12. Buffer navigation (Tab/S-Tab cycle buffers)
    {
        "nvim-tree/nvim-web-devicons",
        lazy = true,
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
            -- v2 has no setup() — configure hooks and load telescope extension
            local Hooks = require("git-worktree.hooks")
            local config = require("git-worktree.config")

            Hooks.register(Hooks.type.SWITCH, Hooks.builtins.update_current_buffer_on_switch)
            Hooks.register(Hooks.type.DELETE, function()
                vim.cmd(config.update_on_change_command)
            end)

            require("telescope").load_extension("git_worktree")

            vim.keymap.set("n", "<leader>gw", function()
                require("telescope").extensions.git_worktree.git_worktree()
            end, { desc = "Switch worktree" })
        end,
    },

    -- 16. Flutter/Dart (handles LSP + DAP + hot reload + device selection)
    {
        "nvim-flutter/flutter-tools.nvim",
        lazy = false,
        dependencies = {
            "nvim-lua/plenary.nvim",
            "stevearc/dressing.nvim",
        },
        opts = {
            debugger = {
                enabled = true,
                run_via_dap = true,
            },
        },
    },
}
