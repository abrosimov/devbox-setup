# Tide prompt items — declarative config
# Overrides defaults set by `tide configure --auto`

# Left prompt: use proj_pwd instead of pwd for project-aware display
set -g tide_left_prompt_items vi_mode os proj_pwd git

# Right prompt: useful items only (removed rarely-used language indicators).
# venv_python replaces tide's python item, which appends the venv's directory
# name that proj_pwd already shows; it keeps tide's tide_python_* styling. It
# needs its own name because `fisher update` rewrites tide's _tide_item_python.
set -g tide_right_prompt_items status cmd_duration context jobs node venv_python go kubectl time

# tide renders each prompt in a background `fish -c` from _tide_left_items and
# _tide_right_items, which it caches as universal variables. Whichever shell
# last re-sourced tide's fish_prompt.fish wrote them, and a long-lived shell
# re-sources it after every `fisher update` with the item lists it read at its
# own start, so the cache can name items whose functions are gone. Globals
# derived from the lists above shadow that cache in every fish process,
# including the background renderer. Items are kept when their function exists
# and, for items backed by a CLI, when that CLI is on PATH.
set -l tide_cli_items git node go kubectl
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
