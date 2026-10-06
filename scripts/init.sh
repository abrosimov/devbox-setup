#!/bin/bash
set -euo pipefail

# Only macOS is supported for now
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Error: This script only supports macOS. Linux support is not yet available." >&2
    exit 1
fi

# Install Homebrew if not present
if ! command -v brew &> /dev/null; then
    curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash
    # Setup brew path for Apple Silicon
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# Install pipx via brew
brew install pipx
pipx ensurepath

# uv has to exist before the playbook, not after it. `make personal` depends on
# `test`, which materialises the dev venv, which refuses to run without uv —
# while uv itself is declared in devbox_brew_secondary and would only be
# installed by the very playbook that cannot start. This breaks that cycle;
# the playbook then finds it already present and moves on.
brew install uv

# Install Ansible and tools
pipx install --include-deps ansible ansible-navigator ansible-builder
pipx install pipreqs

# Install required Ansible collections
ansible-galaxy collection install -r requirements.yml

# Claude Code is NOT installed here. It is declared as the `claude-code@latest`
# cask in devbox_brew_secondary_casks and installed by the playbook, alongside
# the `codex` and `antigravity-cli` casks — one mechanism for all three engines,
# a checksum-verified download, and `make upgrade-*` to keep it current. The
# playbook installs it at step 2, well before the step that needs the binary to
# register MCP servers.