#!/usr/bin/env bash
# Ansible `become_password_file` reader — prints the devbox-sudo keychain slot
# to stdout. Referenced from ansible.cfg [privilege_escalation]. Slot is seeded
# by scripts/ensure_secrets.sh (invoked as a Makefile prereq of run/check/macos-defaults).
#
# Exits non-zero if the slot is absent — Ansible surfaces the failure with the
# stderr line, and the user is directed to the seed step.

set -euo pipefail

# Capture then re-emit without a trailing newline. Ansible strips a trailing
# `\n` from become_password_file stdout, but macOS Keychain values could
# legitimately contain a `\n` mid-password (unlikely for sudo, defensive).
if ! pw="$(/usr/bin/security find-generic-password -w -a "$USER" -s devbox-sudo 2>/dev/null)"; then
    echo "keychain-become-pass: devbox-sudo slot missing from login keychain." >&2
    echo "  Run 'make secrets-init' (or re-run make personal/work from a TTY)." >&2
    exit 1
fi
printf '%s' "$pw"
