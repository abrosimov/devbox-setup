#!/bin/bash
curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh
brew install pipx
pipx ensurepath
pipx install --include-deps ansible ansible-navigator ansible-builder
pipx install pipreqs # usage: pipreqs <path/to/project>
# TODO: install valid version of python?