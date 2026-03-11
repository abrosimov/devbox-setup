# devbox-setup

Ansible-based developer workstation setup. Automates installation of packages, dotfiles, shell config, and Claude Code agent infrastructure.

## Supported OS

- macOS (Darwin) — primary
- Ubuntu (Linux)

## Quick Start

```bash
make init   # Bootstrap (macOS: Homebrew, Ansible, collections)
make run    # Full run (prompts for vault password and sudo)
make dev    # Development mode — deploys to ../debug/dotfiles
```

## Commands

| Command | Description |
|---------|-------------|
| `make run` | Full setup (prompts for vault + sudo) |
| `make dev` | Deploy to `../debug/dotfiles` instead of `~` |
| `make packages` | Package installation only |
| `make configs` | Configuration files only |
| `make user` | User setup and shell config only |
| `make run TAGS="..."` | Custom tag combination |
| `make upgrade-personal` | Upgrade all packages (personal profile) |
| `make upgrade-work` | Upgrade all packages (work profile) |
| `make lint` | Syntax-check + ansible-lint |
| `make check` | Dry-run (check mode) |
| `make check-dev` | Dry-run in dev_mode |
| `make validate-claude` | Validate agent/skill cross-references |

Add `V=1` through `V=4` for verbosity.

## Configuration

### Vault

```bash
make vault-init  # Create and encrypt vault/devbox_ssh_config.yml
```

### Profiles

Profiles select per-machine configuration:

```bash
make personal   # Personal laptop
make work       # Work laptop
```

### Local Overlay

Laptop-only files that should not be committed go into `roles/devbox/local/`. This directory is gitignored and mirrors `roles/devbox/files/`. Files deploy **after** the main pass, so they override repo-managed ones.

```
roles/devbox/local/.config/fish/functions/kstg.fish
→ deployed to ~/.config/fish/functions/kstg.fish
```

## Tool Documentation

Keybindings and usage for each tool:

- [Neovim](roles/devbox/files/.config/nvim/README.md) — LSP, completion, navigation, testing, debugging
- [Kitty](roles/devbox/files/.config/kitty/README.md) — splits, tabs, hints, scrollback
- [Fish](roles/devbox/files/.config/fish/README.md) — abbreviations, functions, plugins
- [Claude Code](roles/devbox/files/.claude/README.md) — agents, skills, commands, MCP servers

## Testing

```bash
make test       # Run all validation tests
make test-json  # Validate JSON configs and schemas
make test-fish  # Fish shell syntax check
make test-bash  # Bash script syntax check
make test-nvim  # Headless neovim config smoke test
```

### Interactive Neovim Testing

```bash
# Symlink repo config to /tmp, launch isolated nvim
ln -sfn ~/Projects/devbox-setup/roles/devbox/files/.config/nvim /tmp/nvim-test
XDG_CONFIG_HOME=/tmp NVIM_APPNAME=nvim-test nvim
```

## TODO

- [ ] Move `prepare_user` and `install_configs` tasks to common directory
- [ ] Write tests
- [ ] Write CI for GitHub Actions
- [ ] Install Rosetta automatically (`sudo softwareupdate --install-rosetta`)
