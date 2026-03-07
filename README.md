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

make test       # run all config validation tests (runs automatically before deploy)
make test-json  # validate JSON configs and schemas
make test-fish  # fish shell syntax check
make test-bash  # bash script syntax check
make test-nvim  # headless neovim config smoke test
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

## Keybinding Cheatsheet

### Kitty Terminal

**Splits**

| Key | Action |
|-----|--------|
| `cmd+d` | Split vertically (side by side) |
| `cmd+shift+d` | Split horizontally (top/bottom) |
| `cmd+opt+arrows` | Navigate between panes |
| `cmd+shift+enter` | Toggle maximize current pane |

**Tabs**

| Key | Action |
|-----|--------|
| `cmd+t` | New tab (inherits cwd) |
| `cmd+w` | Close pane (or tab if last pane) |
| `cmd+1` — `cmd+9` | Jump to tab N |

**Hints** (select text patterns from terminal output)

| Key | Action |
|-----|--------|
| `ctrl+shift+e` | Select URL → open in browser |
| `cmd+shift+p` | Select file path → insert in terminal |
| `cmd+shift+g` | Select file:line → open in editor |
| `cmd+shift+h` | Select git hash → copy to clipboard |

**Scrollback & Shell Integration**

| Key | Action |
|-----|--------|
| `ctrl+shift+h` | Full scrollback in bat pager |
| `ctrl+shift+g` | Last command output in pager |
| `ctrl+shift+z` | Jump to previous shell prompt |
| `ctrl+shift+x` | Jump to next shell prompt |

**Other**

| Key | Action |
|-----|--------|
| `cmd+shift+o` | File picker (choose-files kitten) |
| `cmd+equal` / `cmd+minus` | Font size up/down |
| `cmd+0` | Reset font size |
| `ctrl+shift+f5` | Reload config |

### Neovim

Leader key: `.` (dot)

**Navigation**

| Key | Mode | Action |
|-----|------|--------|
| `Space` | Normal | Half page down |
| `Tab` | Normal | Next buffer |
| `Shift+Tab` | Normal | Previous buffer |
| `Ctrl+h/j/k/l` | Normal | Move focus between splits |
| `]f` / `[f` | Normal | Next / previous function |
| `]c` / `[c` | Normal | Next / previous class |

**Folding**

| Key | Mode | Action |
|-----|------|--------|
| `za` | Normal | Toggle fold |
| `zc` | Normal | Close fold |
| `zo` | Normal | Open fold |
| `zM` | Normal | Close all folds |
| `zR` | Normal | Open all folds |

**Editing**

| Key | Mode | Action |
|-----|------|--------|
| `d` / `D` | Normal, Visual | Delete (no yank — black hole register) |
| `c` / `C` | Normal, Visual | Change (no yank — black hole register) |
| `x` | Normal | Delete char (no yank) |
| `.d` | Normal, Visual | Cut (delete AND yank to clipboard) |

**LSP** (active when language server is attached)

| Key | Mode | Action |
|-----|------|--------|
| `gd` | Normal | Go to definition |
| `gi` | Normal | Go to implementation |
| `gr` | Normal | Go to references |
| `K` | Normal | Hover documentation |
| `.rn` | Normal | Rename symbol |
| `.ca` | Normal | Code action |
| `.ds` | Normal | Document symbols |
| `.ws` | Normal | Workspace symbols |

**Diagnostics**

| Key | Mode | Action |
|-----|------|--------|
| `[d` / `]d` | Normal | Previous / next diagnostic |
| `.e` | Normal | Show diagnostic float |
| `.q` | Normal | Diagnostic quickfix list |
| `.xx` | Normal | Toggle Trouble diagnostics panel |

**Telescope** (fuzzy finder)

| Key | Mode | Action |
|-----|------|--------|
| `.ff` | Normal | Find files |
| `.fg` | Normal | Live grep |
| `.fb` | Normal | List open buffers |
| `.fo` | Normal | Recent files |

**File Explorer** (Neo-tree)

| Key | Mode | Action |
|-----|------|--------|
| `.t` | Normal | Toggle file tree (right side) |
| `.b` | Normal | Toggle buffers panel (left side) |

**Run**

| Key | Mode | Action |
|-----|------|--------|
| `.rm` | Normal | Run main in vertical split |

**Testing** (Neotest)

| Key | Mode | Action |
|-----|------|--------|
| `.tr` | Normal | Run nearest test |
| `.tf` | Normal | Run all tests in file |
| `.ts` | Normal | Toggle test summary |
| `.to` | Normal | Toggle test output panel (bottom) |

**Debugging** (DAP)

| Key | Mode | Action |
|-----|------|--------|
| `.db` | Normal | Toggle breakpoint |
| `.dc` | Normal | Continue / start debug |
| `.dt` | Normal | Debug nearest Go test |

**Git**

| Key | Mode | Action |
|-----|------|--------|
| `.gw` | Normal | Switch git worktree |

**Comments** (Comment.nvim defaults)

| Key | Mode | Action |
|-----|------|--------|
| `gcc` | Normal | Toggle line comment |
| `gc` | Visual | Toggle comment on selection |

## Testing Neovim Config Changes

```bash
# Headless smoke test — validates config loads without errors
make test-nvim

# Interactive testing — symlinks repo config to /tmp, launches isolated nvim
ln -sfn ~/Projects/devbox-setup/roles/devbox/files/.config/nvim /tmp/nvim-test
XDG_CONFIG_HOME=/tmp NVIM_APPNAME=nvim-test nvim
```

`NVIM_APPNAME` + `XDG_CONFIG_HOME=/tmp` makes nvim use `/tmp/nvim-test/` for config and `/tmp/nvim-test-data/` for data — fully isolated from your live setup. Plugins install fresh on first launch.

## TODO

- [ ] Move `prepare_user` and `install_configs` tasks to common directory
- [ ] Write tests
- [ ] Write CI for GitHub Actions
- [ ] Install Rosetta automatically (`sudo softwareupdate --install-rosetta`)
