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

# Install Ansible and tools
pipx install --include-deps ansible ansible-navigator ansible-builder
pipx install pipreqs

# Install required Ansible collections
ansible-galaxy collection install -r requirements.yml