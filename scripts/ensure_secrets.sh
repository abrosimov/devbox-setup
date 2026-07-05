#!/usr/bin/env bash
# Seed macOS login keychain with the secrets consumed by the devbox playbook.
#
# Two slots (account = $USER, keychain = login):
#   devbox-sudo             — the user's macOS login/sudo password. Read by
#                             scripts/with_sudo_keepalive.sh (piped into
#                             `sudo -S -v`) and by ansible-playbook via
#                             `become_password_file = scripts/keychain-become-pass.sh`
#                             in ansible.cfg. Also referenced from Homebrew
#                             cask tasks via the `devbox_sudo_password` var.
#   devbox-ssh-passphrase   — the SSH private-key passphrase. Read by Ansible
#                             (lookup pipe in roles/devbox/defaults/main/core.yml)
#                             to (a) generate the key in prepare_user.yml and
#                             (b) write the `SSH: <path>` slot the LaunchAgent
#                             loads from in configure_ssh_keychain.yml.
#
# Both slots are added with `-T /usr/bin/security` so any subprocess invoking
# `security find-generic-password` reads them silently after the first
# "Always Allow" grant (mirrors the pattern in
# roles/devbox/tasks/darwin/configure_ssh_keychain.yml:57-85, which grants
# `ssh-agent`/`ssh-add` silent access to the `SSH: <path>` slot).
#
# Invocation:
#   scripts/ensure_secrets.sh             — seed both slots if missing
#   scripts/ensure_secrets.sh --only sudo — only devbox-sudo
#   scripts/ensure_secrets.sh --only ssh  — only devbox-ssh-passphrase
#
# Called automatically as a Makefile prerequisite of `run`/`check`/`macos-defaults`
# (target: `secrets-ready`). Standalone entrypoints: `make secrets-init`,
# `make sudo-reseed`, `make ssh-passphrase-reseed`.
#
# Non-Darwin: exits 0 silently (Linux path never reads these slots).
# Non-TTY: refuses to prompt, exits 1 with pointer to run interactively.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    exit 0
fi

readonly SUDO_SVC="devbox-sudo"
readonly SUDO_LABEL="devbox: sudo/login password"
readonly SSH_SVC="devbox-ssh-passphrase"
readonly SSH_LABEL="devbox: SSH key passphrase"

_only=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --only)
            _only="${2:-}"
            shift 2
            ;;
        --only=*)
            _only="${1#--only=}"
            shift
            ;;
        -h|--help)
            sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "ensure_secrets: unknown argument: $1" >&2
            exit 64
            ;;
    esac
done

case "${_only}" in
    ""|sudo|ssh) ;;
    *)
        echo "ensure_secrets: --only takes 'sudo' or 'ssh', got '${_only}'" >&2
        exit 64
        ;;
esac

_slot_exists() {
    /usr/bin/security find-generic-password -a "$USER" -s "$1" >/dev/null 2>&1
}

_prompt_and_store() {
    local svc="$1" label="$2" pass=""
    # Empty entries silently poison Ansible lookups downstream. Loop until we
    # get something non-empty, capped at 3 attempts to fail loudly on a
    # confused operator (e.g. Ctrl-D producing an empty read).
    local attempt
    for attempt in 1 2 3; do
        printf '%s: ' "$label" >&2
        IFS= read -rs pass || true
        printf '\n' >&2
        if [[ -n "$pass" ]]; then
            break
        fi
        echo "ensure_secrets: empty input, try again ($attempt/3)" >&2
    done
    if [[ -z "$pass" ]]; then
        echo "ensure_secrets: giving up after 3 empty attempts" >&2
        exit 1
    fi
    /usr/bin/security add-generic-password \
        -U \
        -a "$USER" \
        -s "$svc" \
        -w "$pass" \
        -T /usr/bin/security \
        "$HOME/Library/Keychains/login.keychain-db" >/dev/null
    echo "ensure_secrets: stored '$svc' in login keychain" >&2
}

_maybe_seed() {
    local svc="$1" label="$2"
    if _slot_exists "$svc"; then
        return 0
    fi
    if [[ ! -t 0 ]]; then
        echo "ensure_secrets: keychain slot '$svc' missing and stdin is not a TTY." >&2
        echo "  Run 'make secrets-init' interactively before invoking this target." >&2
        exit 1
    fi
    _prompt_and_store "$svc" "$label"
}

if [[ -z "${_only}" || "${_only}" == "sudo" ]]; then
    _maybe_seed "$SUDO_SVC" "$SUDO_LABEL"
fi
if [[ -z "${_only}" || "${_only}" == "ssh" ]]; then
    _maybe_seed "$SSH_SVC" "$SSH_LABEL"
fi
