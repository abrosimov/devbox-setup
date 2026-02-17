# devbox-setup

Ansible-based developer workstation setup. Automates installation of packages, dotfiles, shell config, and Claude Code agent infrastructure.

## Supported OS

- macOS (Darwin) — primary target
- Ubuntu (Linux) — Ubuntu-only

## Quick Start

```bash
# Bootstrap (macOS only — installs Homebrew, Ansible, collections)
make init

# Full run (prompts for vault password and sudo)
make run

# Development mode — deploys to ../debug/dotfiles instead of ~
make dev

# Increase verbosity (V=1 through V=4)
make run V=2
```

## Partial Runs via Tags

```bash
make packages                  # package installation only
make configs                   # configuration files only
make user                      # user setup and shell config only

make dev-packages              # packages phase in dev_mode
make dev-configs               # configs phase in dev_mode
make dev-user                  # user phase in dev_mode

make run TAGS="packages,configs"  # custom tag combination
make dev TAGS="configs"           # custom tags in dev_mode
```

## Linting and Dry-Run

```bash
make lint       # syntax-check + ansible-lint
make check      # dry-run (check mode, prompts for vault+sudo)
make check-dev  # dry-run in dev_mode (uses test vault, no sudo)
```

## Vault

```bash
make vault-init  # create and encrypt vault/devbox_ssh_config.yml
```

## Local Overlay

Laptop-only files that should not be committed go into `roles/devbox/local/`. This directory is gitignored and mirrors the structure of `roles/devbox/files/`. Files are deployed **after** the main pass, so they can add new files or override repo-managed ones.

```
roles/devbox/local/.config/fish/functions/kstg.fish
→ deployed to ~/.config/fish/functions/kstg.fish
```

## Claude Code Config

This repo also manages the global Claude Code configuration deployed to `~/.claude/`:

- **33 agents** — specialised subagents (software engineers, reviewers, planners, etc.)
- **79 skills** — reusable knowledge modules (Go, Python, frontend, DDD, security, etc.)
- **19 commands** — slash commands (`/implement`, `/test`, `/review`, `/devcontainer`, `/guide`, etc.)
- **Hooks** — pre/post tool-call guards (sandbox, formatting, linting)
- **MCP servers** — sequential thinking, playwright, memory graph, figma
- **Devcontainer template** — Docker sandbox with iptables egress firewall for isolated agent runs

```bash
make validate-claude  # validate agent/skill library cross-references
```

## TODO

- [ ] Move `prepare_user` and `install_configs` tasks to common directory
- [ ] Write tests
- [ ] Write CI for GitHub Actions
- [ ] Install Rosetta automatically (`sudo softwareupdate --install-rosetta`)
