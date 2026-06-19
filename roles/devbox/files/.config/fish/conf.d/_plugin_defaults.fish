# Plugin tunables. Underscore prefix sorts before plugin conf.d files
# (done.fish, sponge.fish, ...), so plugins see our values and skip their
# built-in defaults. Universal scope is required because sponge gates on
# `set -q --universal`; setting --global would leak the plugin's default
# (e.g. sponge_delay=2) into fish_variables alongside our override.
# No guard: repo is single source of truth — manual `set -U` is overwritten
# on next shell start, matching the previous Ansible-task behaviour.

# done — desktop notification for commands longer than 300s
set --universal __done_min_cmd_duration 300000
set --universal __done_kitty_remote_control 1
set --universal __done_notification_duration 5000

# sponge — keep N most-recent commands in the failure buffer (default 2)
set --universal sponge_delay 5
