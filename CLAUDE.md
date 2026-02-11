# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ansible-based developer workstation setup tool that automates installation and configuration of development tools, dotfiles, and system preferences. Supports macOS (Darwin) and Ubuntu Linux.

**Key distinction**: `roles/devbox/files/.claude/` contains files deployed to `~/.claude/` (user's global Claude Code config). The `CLAUDE.md` there is the **global authority protocol**, not this project's instructions.

## Commands

```bash
# Bootstrap (macOS only — installs Homebrew, Ansible, collections)
make init

# Full setup run (prompts for vault password and sudo)
make run

# Development mode — deploys to ../debug/dotfiles instead of ~
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

# Linting and dry-run
make lint            # syntax-check + ansible-lint
make check           # dry-run (check mode, prompts for vault+sudo)
make check-dev       # dry-run in dev_mode (uses test vault, no sudo)

# Vault management
make vault-init      # create and encrypt vault/devbox_ssh_config.yml
```

## Architecture

### Single role: `roles/devbox/`

Everything lives in one role. No multi-role orchestration.

### Task Flow

`main.yml` dispatches by OS. The Darwin flow (Linux is similar):

1. `darwin/install_from_brew_primary.yml` — core packages
2. `darwin/install_from_brew_secondary.yml` — packages that depend on core
3. `install_configs.yml` — deploy dotfiles (see below)
4. `apply_configs.yml` — post-deploy actions: fisher plugins, font cache, MCP server registration
5. `prepare_user.yml` — shell, user-level setup

### Configuration Deployment (`install_configs.yml`)

**Clean-before-deploy**: Before deploying, managed `.claude/` subdirectories (`agents`, `commands`, `skills`, `bin`, `docs`) and root files (`CLAUDE.md`, `settings.json`, `hooks.json`) are deleted. This ensures files removed from the repo are also removed from the user's config. `settings.local.json` is preserved (user permissions).

**Filetree mirroring**: Uses `community.general.filetree` to mirror `roles/devbox/files/` to the target directory:
- Regular files → copied directly
- `.j2` files → rendered as Jinja2 templates (suffix stripped)
- Protected files (listed in `files_that_should_not_be_overwritten`) are not overwritten if they already exist

**Local overlay**: After the main pass, `roles/devbox/local/` (gitignored) is deployed on top with identical logic. Laptop-only configs go here to stay out of VCS.

### MCP Server Registration (`apply_configs.yml`)

Three transport types configured in `defaults/main.yml`:
- **Docker** (`mcp_docker_servers`) — containers via `docker run --rm -i` (sequentialthinking, playwright)
- **Script** (`mcp_script_servers`) — wrapper scripts in `~/.claude/bin/` (memory-upstream, memory-downstream)
- **HTTP** (`mcp_http_servers`) — remote endpoints (figma)

Registered via `claude mcp add` with user scope.

### Key Variables (`defaults/main.yml`)

- `devbox_paths.dotfiles_root_dir` — target for deployment (`~` normally, `../debug/dotfiles` in dev_mode)
- `devbox_user.login` — username for user configuration
- `dev_mode` — when true, deploys to debug directory

### Claude Code Config (in `roles/devbox/files/.claude/`)

| Path | Purpose | Deployed To |
|------|---------|-------------|
| `CLAUDE.md` | User Authority Protocol | `~/.claude/CLAUDE.md` |
| `settings.json` | Default permissions (allow/deny) | `~/.claude/settings.json` |
| `agents/*.md` | Agent definitions | `~/.claude/agents/` |
| `commands/*.md` | Slash commands (/implement, /test, etc.) | `~/.claude/commands/` |
| `skills/*/SKILL.md` | Reusable knowledge modules | `~/.claude/skills/` |
| `bin/*` | Helper scripts (MCP wrappers, etc.) | `~/.claude/bin/` |
| `docs/` | Reference documentation | `~/.claude/docs/` |

## Dependencies

Requires Ansible with `community.general` collection (>=10.1.0):
```bash
ansible-galaxy collection install -r requirements.yml
```
