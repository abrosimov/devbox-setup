# devbox-setup

Ansible-based developer workstation setup. Automates installation of packages, dotfiles, shell config, and Claude Code agent infrastructure.

## Supported OS

- macOS (Darwin) — primary
- Ubuntu (Linux)

## Quick Start

```bash
make init       # Bootstrap (macOS: Homebrew, Ansible, collections)
make personal   # Full run with the personal profile (prompts for vault + sudo)
make work       # Full run with the work profile
```

A profile is mandatory: bare `make run` / `make dev` / `make check` fail with `PROFILE is required`. Use the per-profile wrappers below.

## Commands

| Command | Description |
|---------|-------------|
| `make personal` | Full setup with personal profile (prompts for vault + sudo) |
| `make work` | Full setup with work profile |
| `make dev-personal` | Deploy to `../debug/dotfiles` with personal profile |
| `make dev-work` | Deploy to `../debug/dotfiles` with work profile |
| `make check-personal` | Dry-run with personal profile |
| `make check-work` | Dry-run with work profile |
| `make check-dev` | Dry-run in dev_mode (test vault, no sudo) |
| `make upgrade-personal` | Upgrade all packages (personal profile) |
| `make upgrade-work` | Upgrade all packages (work profile) |
| `make lint` | Syntax-check + ansible-lint |
| `make validate-claude` | Validate agent/skill cross-references |

Add `V=1` through `V=4` for verbosity. Pass extra Ansible variables via `EXTRA_VARS='-e foo=bar'` (e.g. `--tags`: `make personal EXTRA_VARS='--tags packages'`).

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

Current per-profile differences:

| | `personal` | `work` |
|---|---|---|
| Projects dir | `$HOME/Projects` | `$HOME/Work` |
| Container runtime | `docker-desktop` | `orbstack` |
| Extra MCP servers | none | `atlassian` (HTTP) |

### System-Level macOS Tweaks

On Darwin, the playbook also codifies the manual steps previously kept in personal notes via `roles/devbox/tasks/darwin/configure_macos_basics.yml`:

- Touch ID for `sudo` (persisted in `/etc/pam.d/sudo_local` across system updates)
- `pmset -a disablesleep 1` — keeps the Mac awake when the lid is closed (clamshell workflow)
- `DevToolsSecurity --enable` — no password prompt when attaching a debugger

HiDPI for external displays is handled by installing [BetterDisplay](https://github.com/waydabber/BetterDisplay) as a Homebrew cask.

### Local Overlay

Laptop-only files that should not be committed go into `roles/devbox/local/`. This directory is gitignored and mirrors `roles/devbox/files/`. Files deploy **after** the main pass, so they override repo-managed ones.

```
roles/devbox/local/.config/fish/functions/kstg.fish
→ deployed to ~/.config/fish/functions/kstg.fish
```

## Tool Documentation

Keybindings and usage for each tool:

- [Neovim](roles/devbox/files/.config/nvim/README.md) — LSP, completion, navigation, testing, debugging
- [Kitty](roles/devbox/files/.config/kitty/README.md) — layout-independent bindings, readline-on-cyrillic, smart Cmd+Q, session save/restore
- [Fish](roles/devbox/files/.config/fish/README.md) — abbreviations, functions, plugins
- [Claude Code](roles/devbox/files/.claude/README.md) — agents, skills, commands, MCP servers

## Pub Mode

Optional tunnel for running Claude Code on untrusted wifi where a middlebox resets TCP on HTTP uploads larger than roughly 1.4 KB (`ECONNRESET`). At home or in the office, leave it off — `claude` goes direct (no proxy variables exist in the resting state).

Chain when enabled:

```
claude  ->  http://127.0.0.1:8080 (gost)  ->  socks5://127.0.0.1:40000 (WARP)  ->  Cloudflare  ->  Anthropic
```

WARP runs in proxy mode (no system DNS or route changes), with a local `gost` HTTP-to-SOCKS bridge fronting it because Claude Code honours `HTTP(S)_PROXY` only, not SOCKS. The bridge binds `127.0.0.1` explicitly so it is never exposed to the untrusted network.

### Usage

When `claude` breaks on bad wifi:

```fish
pub on       # Connect WARP + start the loopback-bound gost bridge
             # + export HTTPS_PROXY / HTTP_PROXY (and lowercase twins) as universal fish vars.
             # Restart your claude sessions to pick up the proxy.

pub off      # Erase the proxy vars + stop the bridge + disconnect WARP.
             # Restart your claude sessions to drop the proxy.

pub status   # warp-cli status, bridge up/down, current HTTPS_PROXY value.
```

`pub on` sets the proxy variables as **universal fish variables** (`set -Ux`), so every fish session and every child process inherits them in one shot. That's why already-running `claude` sessions need a manual restart — they read env once at startup.

### Caveat

WARP proxy mode uses MASQUE, which enforces a roughly 10-second per-request limit. Long-running Claude responses that drop mid-stream are the chain timing out, not the `pub` toggle itself. Disable `pub` for long-form work when you're on a trusted network.

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
