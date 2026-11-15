# Tide prompt items — declarative config
# Overrides defaults set by `tide configure --auto`

# Left prompt: use proj_pwd instead of pwd for project-aware display
set -g tide_left_prompt_items vi_mode os proj_pwd git

# Right prompt: useful items only (removed rarely-used language indicators)
set -g tide_right_prompt_items status cmd_duration context jobs node python go kubectl time

# Treat orbstack as a "default" docker context (hides indicator when using orbstack)
set -g tide_docker_default_contexts default colima orbstack

# proj_pwd item styling (matches pwd styling)
set -g tide_proj_pwd_bg_color $tide_pwd_bg_color
set -g tide_proj_pwd_color_anchors $tide_pwd_color_anchors
set -g tide_proj_pwd_color_dirs $tide_pwd_color_dirs
set -g tide_proj_pwd_icon $tide_pwd_icon
