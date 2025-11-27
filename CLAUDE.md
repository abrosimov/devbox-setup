# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ansible-based developer workstation setup tool that automates installation and configuration of development tools, dotfiles, and system preferences. It supports macOS (Darwin) and Ubuntu Linux.

## Commands

```bash
# Full setup run (prompts for vault password and sudo)
make run

# Development mode - uses debug/dotfiles as target instead of ~
make dev

# Increase verbosity (V=1 through V=4)
make run V=2

# Partial runs via tags
make packages       # package installation only
make configs        # configuration files only
make user           # user setup and shell config only

# Dev mode with specific phases
make dev-packages
make dev-configs
make dev-user

# Custom tag combinations
make run TAGS="packages,configs"
make dev TAGS="configs"
```

## Architecture

### Directory Structure
- `playbooks/main.yml` - Main playbook entry point, runs locally against 127.0.0.1
- `roles/devbox/` - Single role containing all setup logic
- `roles/devbox/tasks/` - Task files split by OS and phase
- `roles/devbox/files/` - Dotfiles and configs to be deployed to home directory
- `roles/devbox/defaults/main.yml` - Default variables (`devbox_user`, `devbox_paths`)
- `vault/` - Encrypted secrets (SSH passphrase)

### Task Flow
1. `main.yml` loads OS-specific tasks (`main_darwin.yml` or `main_linux.yml`)
2. Darwin flow: `install_from_brew_initial` → `install_configs` → `prepare_user` → `install_from_brew_secondary`
3. Linux flow: `install_from_apt_initial` → `install_configs` → `prepare_user` → `install_from_apt_secondary`

### Configuration Deployment
The `install_configs.yml` task uses `community.general.filetree` to mirror the entire `roles/devbox/files/` structure to the target dotfiles directory:
- Regular files are copied directly
- Files ending in `.j2` are rendered as Jinja2 templates (with `.j2` suffix stripped)
- Target directory is `~` in normal mode or `../debug/dotfiles` in dev_mode

### Key Variables
- `devbox_paths.dotfiles_root_dir` - Target for dotfile deployment (overridden in dev_mode)
- `devbox_user.login` - Username for user configuration
- `dev_mode` - When true, deploys to debug directory instead of home

## Dependencies

Requires Ansible with `community.general` collection (>=10.1.0). Install with:
```bash
ansible-galaxy collection install -r requirements.yml
```
