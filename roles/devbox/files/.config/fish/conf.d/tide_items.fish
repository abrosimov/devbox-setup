# Tide prompt items — declarative config
# Overrides defaults set by `tide configure --auto`

# One item per line, in display order; each comment says when the item shows.

# Left prompt
set -g tide_left_prompt_items
set -a tide_left_prompt_items vi_mode # vi key bindings only: the current mode
set -a tide_left_prompt_items os # always: OS icon
set -a tide_left_prompt_items proj_pwd # always: directory, project-aware (replaces tide's pwd)
set -a tide_left_prompt_items git # inside a git repository: branch and state

# Right prompt
# venv_python replaces tide's python item, which appends the venv's directory
# name that proj_pwd already shows; it keeps tide's tide_python_* styling. It
# needs its own name because `fisher update` rewrites tide's _tide_item_python.
set -g tide_right_prompt_items
set -a tide_right_prompt_items status # the last command failed: its exit status
set -a tide_right_prompt_items cmd_duration # the last command ran longer than 3 s
set -a tide_right_prompt_items context # over SSH or as root: user@host
set -a tide_right_prompt_items private_mode # `fish --private`: history is not saved
set -a tide_right_prompt_items shlvl # nested shell (SHLVL above 1): nesting depth
set -a tide_right_prompt_items jobs # background jobs are running
set -a tide_right_prompt_items node # package.json above: Node version
set -a tide_right_prompt_items venv_python # active venv or Python project marker: Python version
set -a tide_right_prompt_items go # go.mod or go.work above: Go version
set -a tide_right_prompt_items rustc # Cargo.toml above: Rust version
set -a tide_right_prompt_items time # always: clock

# tide renders each prompt in a background `fish -c` from _tide_left_items and
# _tide_right_items, which it caches as universal variables. Whichever shell
# last re-sourced tide's fish_prompt.fish wrote them, and a long-lived shell
# re-sources it after every `fisher update` with the item lists it read at its
# own start, so the cache can name items whose functions are gone. Globals
# derived from the lists above shadow that cache in every fish process,
# including the background renderer. Items are kept when their function exists
# and, for items backed by a CLI, when that CLI is on PATH.
set -l tide_cli_items git node go rustc
for side in left right
    set -l prompt_items tide_{$side}_prompt_items
    set -g _tide_{$side}_items (for item in $$prompt_items
        functions -q _tide_item_$item; or continue
        contains $item $tide_cli_items; and not type -q $item; and continue
        echo $item
    end)
end

# Treat orbstack as a "default" docker context (hides indicator when using orbstack)
set -g tide_docker_default_contexts default colima orbstack

# proj_pwd item styling (matches pwd styling)
set -g tide_proj_pwd_bg_color $tide_pwd_bg_color
set -g tide_proj_pwd_color_anchors $tide_pwd_color_anchors
set -g tide_proj_pwd_color_dirs $tide_pwd_color_dirs
set -g tide_proj_pwd_icon $tide_pwd_icon
