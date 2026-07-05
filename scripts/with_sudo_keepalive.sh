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
# correctly), and keep the timestamp warm via `sudo -n true` on a fast loop
# (well under the default 300s sudo timestamp_timeout). While the timestamp
# is valid, ansible's `become: true` reuses it without ever invoking pam_tid
# again, sidestepping the race entirely.
#
# Verified for macOS Tahoe 26.x (pam_tid mechanics unchanged from Sonoma).
# Usage: with_sudo_keepalive.sh <command> [args...]
#
# Config (env vars, all optional):
#   SUDO_KEEPALIVE_LOG          log file (default: /tmp/sudo-keepalive.log; truncated on start)
#   SUDO_KEEPALIVE_INTERVAL     refresh interval in seconds (default: 30)
#   SUDO_KEEPALIVE_RETRIES      retries on transient `sudo -n` failure (default: 3)
#   SUDO_KEEPALIVE_RETRY_DELAY  seconds between retries (default: 5)

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <command> [args...]" >&2
    exit 64
fi

readonly KEEPALIVE_LOG="${SUDO_KEEPALIVE_LOG:-/tmp/sudo-keepalive.log}"
readonly KEEPALIVE_INTERVAL="${SUDO_KEEPALIVE_INTERVAL:-30}"
readonly KEEPALIVE_RETRIES="${SUDO_KEEPALIVE_RETRIES:-3}"
readonly KEEPALIVE_RETRY_DELAY="${SUDO_KEEPALIVE_RETRY_DELAY:-5}"

_ts()  { date '+%Y-%m-%dT%H:%M:%S%z'; }
_log() { printf '%s [pid=%d] %s\n' "$(_ts)" "$$" "$*" >>"${KEEPALIVE_LOG}"; }

# Truncate log at start — history between runs is not preserved on purpose
# (per-run signal only; if you need multi-run history, redirect via env var).
: >"${KEEPALIVE_LOG}"
_log "wrapper: start, argv0='$1', interval=${KEEPALIVE_INTERVAL}s, retries=${KEEPALIVE_RETRIES}, retry_delay=${KEEPALIVE_RETRY_DELAY}s"

# Prime the sudo timestamp interactively. pam_tid (Touch ID) or password
# prompt — both fine here, because the terminal owns stdin and the user
# can respond. Failure aborts before we touch the actual workload.
if ! sudo -v; then
    _log "wrapper: sudo -v failed — aborting"
    echo "with_sudo_keepalive: sudo -v failed (see ${KEEPALIVE_LOG})" >&2
    exit 1
fi
_log "wrapper: sudo -v ok"

# Background keep-alive: refresh the sudo timestamp every
# ${KEEPALIVE_INTERVAL}s. On a `sudo -n true` failure, retry up to
# ${KEEPALIVE_RETRIES} times with a ${KEEPALIVE_RETRY_DELAY}s pause before
# giving up — a single transient failure (system load, PAM check race, brief
# `sudo -k` from another script) should not silently kill the keepalive.
# Once we do exit, the timestamp expires ~5 min later and subsequent ansible
# become tasks fail loudly with the real reason instead of masking it.
(
    while true; do
        _ok=0
        for _attempt in $(seq 1 "${KEEPALIVE_RETRIES}"); do
            if sudo -n true 2>/dev/null; then
                _log "keepalive: refresh ok (attempt ${_attempt})"
                _ok=1
                break
            fi
            _log "keepalive: refresh failed (attempt ${_attempt}/${KEEPALIVE_RETRIES})"
            if [[ ${_attempt} -lt ${KEEPALIVE_RETRIES} ]]; then
                sleep "${KEEPALIVE_RETRY_DELAY}"
            fi
        done
        if [[ ${_ok} -eq 0 ]]; then
            _log "keepalive: giving up after ${KEEPALIVE_RETRIES} attempts — exiting"
            exit 0
        fi
        sleep "${KEEPALIVE_INTERVAL}"
        # $$ in a bash subshell is the PARENT shell's PID, which after
        # `exec "$@"` below is the ansible-playbook process. When that
        # exits, this check trips on the next iteration and we self-exit.
        if ! kill -0 "$$" 2>/dev/null; then
            _log "keepalive: parent (pid=$$) gone — exiting"
            exit 0
        fi
    done
) &
readonly KEEPALIVE_PID=$!
_log "wrapper: keepalive spawned, pid=${KEEPALIVE_PID}"

# Trap covers only the pre-exec window (Ctrl-C during `sudo -v` etc.); once
# `exec` replaces the shell process image, all traps are lost with it and
# keepalive relies solely on the `kill -0 $$` check above to self-terminate.
trap 'kill "${KEEPALIVE_PID}" 2>/dev/null || true' EXIT INT TERM

_log "wrapper: exec $*"
exec "$@"
