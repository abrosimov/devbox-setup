#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE="$PROJECT_ROOT/vault/devbox_ssh_config.yml.tpl"
OUTPUT="$PROJECT_ROOT/vault/devbox_ssh_config.yml"

if [[ ! -f "$TEMPLATE" ]]; then
    echo "Error: Template file not found: $TEMPLATE" >&2
    exit 1
fi

read -sp "Enter SSH key passphrase: " PASSPHRASE
echo

awk -v pass="$PASSPHRASE" '{gsub(/<your-ssh-keyfile-password-is-here>/, pass); print}' \
    "$TEMPLATE" > "$OUTPUT"

ansible-vault encrypt "$OUTPUT"

echo "Vault file created and encrypted successfully."
