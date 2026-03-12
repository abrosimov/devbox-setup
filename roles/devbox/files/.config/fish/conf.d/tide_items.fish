# Tide prompt items — declarative config
# Overrides defaults set by `tide configure --auto`

# Left prompt: no docker indicator
set -g tide_left_prompt_items vi_mode os pwd git

# Right prompt: useful items only (removed rarely-used language indicators)
set -g tide_right_prompt_items status cmd_duration context jobs node python go kubectl time

# Treat orbstack as a "default" docker context (hides indicator when using orbstack)
set -g tide_docker_default_contexts default colima orbstack
