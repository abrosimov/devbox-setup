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
    }
}
