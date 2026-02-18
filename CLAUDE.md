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

# Claude Code config validation
make validate-claude # validate agent/skill library cross-references
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

**Clean-before-deploy**: Before deploying, managed `.claude/` subdirectories (`agents`, `commands`, `skills`, `schemas`, `bin`, `docs`, `templates`) and root files (`CLAUDE.md`, `settings.json`, `hooks.json`, `config.md`) are deleted. This ensures files removed from the repo are also removed from the user's config. `settings.local.json` is preserved (user permissions).

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
- `devbox_shell.env` / `path_prepend` / `path_append` / `path_conditional` — single source of truth for shell environment. Templates for fish (`_init_env.fish.j2`, `_init_path.fish.j2`) and bash (`.bashrc.j2`) iterate these lists, so adding a path here updates both shells.

### Claude Code Config (in `roles/devbox/files/.claude/`)

| Path | Purpose | Deployed To |
|------|---------|-------------|
| `CLAUDE.md` | User Authority Protocol | `~/.claude/CLAUDE.md` |
| `settings.json` | Default permissions (allow/deny) | `~/.claude/settings.json` |
| `hooks.json` | Pre/post tool-call hooks | `~/.claude/hooks.json` |
| `agents/*.md` | Agent definitions (33 agents) | `~/.claude/agents/` |
| `commands/*.md` | Slash commands — 19 (/implement, /test, /guide, etc.) | `~/.claude/commands/` |
| `skills/*/SKILL.md` | Reusable knowledge modules (80 skills) | `~/.claude/skills/` |
| `schemas/*.json` | JSON Schema files for pipeline validation | `~/.claude/schemas/` |
| `bin/*` | Helper scripts (MCP wrappers, hooks, validation) | `~/.claude/bin/` |
| `templates/` | Reusable project templates (devcontainer) | `~/.claude/templates/` |
| `docs/` | Reference documentation | `~/.claude/docs/` |

### Devcontainer Template (`templates/devcontainer/`)

A reusable Docker sandbox for Claude Code with network-level isolation:

- `domains.conf` — domain allowlist for the egress firewall (aligned with `settings.json` sandbox domains)
- `init-firewall.sh` — iptables + ipset default-deny firewall, runs as `postStartCommand`
- `Dockerfile` — `node:20-bookworm` base with conditional language install via `INSTALL_GO`, `INSTALL_PYTHON`, `INSTALL_RUST`, `INSTALL_OCAML` build args
- `devcontainer.json` — `NET_ADMIN`/`NET_RAW` caps, host `settings.json` bind-mounted read-only, named volume for shell history

Use via `/devcontainer init` (Claude Code command) or `claude-devcontainer init` (CLI).

## Editing Claude Code Config

When working in `roles/devbox/files/.claude/` you are editing files that get deployed to `~/.claude/`. This is a distinct activity from editing the Ansible playbook itself:

- **Agent/skill/command changes** don't need `make run` — test by copying files directly to `~/.claude/` or symlinking
- **`settings.json` changes** affect sandbox permissions, network allowlists, and tool approvals globally
- **`hooks.json` changes** define pre/post hooks for tool calls (scripts in `bin/`)
- **`templates/` changes** affect devcontainer scaffolding for new projects
- Run `make validate-claude` to check cross-references between agents, skills, and commands
- Run `bin/validate-pipeline-output --help` to test the pipeline validation script locally
- **`schemas/` changes** define JSON Schema contracts for pipeline execution (stream completion, execution DAG, pipeline state) — validated by `bin/validate-pipeline-output`
- The `CLAUDE.md` in `roles/devbox/files/.claude/` is the **User Authority Protocol** — it governs all Claude Code sessions globally, not just this project

## Dependencies

Requires Ansible with `community.general` collection (>=10.1.0):
```bash
ansible-galaxy collection install -r requirements.yml
```
