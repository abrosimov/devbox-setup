#!/usr/bin/env bash
# Run a command with a live sudo timestamp held in the background.
#
# Why: ansible's `become: true` calls `sudo -S` with the password on stdin.
# On macOS with `pam_tid.so` enabled in /etc/pam.d/sudo_local (Touch ID for
# sudo), pam_tid races with sudo's stdin reader — when the laptop is in
# clamshell (TouchID disabled), the dialog times out and sudo's
# pam_opendirectory step reads a corrupted stdin buffer, returning "Sorry,
# try again". Ansible then sees a duplicate password prompt and bails.
#
# Fix: pre-cache sudo interactively (in the terminal, where pam_tid behaves
# correctly), and keep the timestamp warm via `sudo -n true` every 60s
# (under the default 300s sudo timestamp_timeout). While the timestamp is
# valid, ansible's `become: true` reuses it without ever invoking pam_tid
# again, sidestepping the race entirely.
#
# Verified for macOS Tahoe 26.x (pam_tid mechanics unchanged from Sonoma).
# Usage: with_sudo_keepalive.sh <command> [args...]

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <command> [args...]" >&2
    exit 64
fi

# Prime the sudo timestamp interactively. pam_tid (Touch ID) or password
# prompt — both fine here, because the terminal owns stdin and the user
# can respond. Failure aborts before we touch the actual workload.
sudo -v

# Background keep-alive: refresh the sudo timestamp every 60s for as long
# as this wrapper script is alive. `sudo -n` is non-interactive — if the
# timestamp ever expires (e.g. user revoked it via `sudo -k`), the keep-
# alive loop exits silently and subsequent ansible become tasks will fail
# loudly with the real reason instead of masking it.
while true; do
    sudo -n true 2>/dev/null || exit 0
    sleep 60
    kill -0 "$$" 2>/dev/null || exit 0
done &
KEEPALIVE_PID=$!

# Make sure the keep-alive dies with us, even on Ctrl-C or playbook fail.
trap 'kill "${KEEPALIVE_PID}" 2>/dev/null || true' EXIT INT TERM

exec "$@"
