# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ansible-based developer workstation setup tool that automates installation and configuration of development tools, dotfiles, and system preferences. Supports macOS (Darwin) and Ubuntu Linux.

**Key distinction**: `roles/devbox/files/dot_claude/` contains files deployed to `~/.claude/` (user's global Claude Code config). The directory is named `dot_claude/` rather than `.claude/` so Claude Code does not treat edits to it as self-modifications. The `USER_AUTHORITY_PROTOCOL.md` there is the **global authority protocol** — it is deployed as `~/.claude/CLAUDE.md` and is not this project's instructions.

## Commands

A profile is mandatory for any playbook run. Bare `make run` / `make dev` / `make check` fail with `PROFILE is required` — use the per-profile wrappers below. `personal` targets a personal laptop (`AION_AUTOPOIESEON=~/Projects`); `work` targets a work laptop (`AION_AUTOPOIESEON=~/Work`). Slim targets (`make dotfiles-push` etc.) recover the active profile from the `MNEMOSYNE_PERISTASEOS` env var rendered into the user's shell rc by the previous full run, or fail with a hint if the var is unset. First-ever bootstrap: pass `PROFILE=personal|work` explicitly, or start a new shell after `make personal`/`make work` so the just-rendered rc is sourced.

Sudo and SSH passphrase live in the macOS login keychain (slots `devbox-sudo` and `devbox-ssh-passphrase`), seeded on first run by `scripts/ensure_secrets.sh` — chained as a Makefile prereq (`secrets-ready`) on `run`, `check`, and `macos-defaults`, so `make personal`/`make work` prompts once on a fresh machine and never again. Ansible reads sudo through `become_password_file = scripts/keychain-become-pass.sh` (see `ansible.cfg [privilege_escalation]`); `community.general.homebrew_cask.sudo_password:` reads it via the `devbox_sudo_password` variable defined in `roles/devbox/defaults/main/core.yml`. Any task consuming these values MUST set `no_log: true`. Rotation entrypoints: `make sudo-reseed`, `make ssh-passphrase-reseed`. First read from any subprocess pops a one-time Keychain ACL dialog — grant "Always Allow" once.

```bash
# Bootstrap (macOS only — installs Homebrew, Ansible, collections)
make init

# Full setup runs (first run: 2 keychain seed prompts; subsequent: 0 prompts)
make personal   # personal profile
make work       # work profile

# Increase verbosity (V=1 through V=4)
make personal V=2

# Development mode — deploys to ../debug/dotfiles instead of ~
make dev-personal
make dev-work

# Tag-scoped runs (no convenience targets — pass --tags via EXTRA_VARS)
make personal EXTRA_VARS='--tags packages'
make dev-personal EXTRA_VARS='--tags configs'

# Linting and dry-run
make lint            # syntax-check + ansible-lint
make check-personal  # dry-run with personal profile
make check-work      # dry-run with work profile
make check-dev       # dry-run in dev_mode (override vars, no sudo/keychain)

# Fish shell upgrade + tide prompt sync
make fixfish          # upgrade fish, update plugins, apply tide config from defaults

# Secrets (macOS login keychain)
make secrets-init            # seed devbox-sudo + devbox-ssh-passphrase (idempotent)
make sudo-reseed             # after macOS login password rotation
make ssh-passphrase-reseed   # after SSH passphrase change or key regen

# Claude config back-propagation (root files only — subdirs are symlinked)
make claude-diff     # show drift between deployed ~/.claude and repo
make claude-pull     # copy changed root files back from ~/.claude to repo

# Claude Code config validation
make validate-claude # validate agent/skill library cross-references
make validate-skills # structural validation of skill evals (fast, CI-safe)

# Skill trigger evaluation (requires claude CLI, run from regular terminal)
make eval-skills                          # all skills with trigger_evals.json
make eval-skills SKILL=lint-discipline    # single skill
make eval-skills MODEL=claude-sonnet-4-6  # override model (default: claude-opus-4-6)

# Skill description optimization (Anthropic's run_loop.py)
make improve-skills SKILL=lint-discipline # iterative description improvement (5 rounds)
```

## Architecture

### Single role: `roles/devbox/`

Everything lives in one role. No multi-role orchestration.

### Task Flow

`main.yml` dispatches by OS. The Darwin flow (Linux is similar):

1. `darwin/install_from_brew_primary.yml` — core packages
2. `darwin/install_from_brew_secondary.yml` — taps third-party repos (`devbox_brew_taps`), then installs packages that depend on core
3. `darwin/install_from_go.yml` — Go tools via `go install` (variable-driven)
4. `darwin/install_from_uv.yml` — Python tools via `uv tool` (variable-driven)
5. `darwin/install_kubectl.yml` — pinned kubectl binary download
6. `darwin/configure_macos_basics.yml` — codifies manual notes: Touch ID for sudo via `sudo_local`, `pmset disablesleep` for clamshell, `DevToolsSecurity --enable` for debugger access
7. `install_configs.yml` — deploy dotfiles (see below)
8. `apply_configs.yml` — post-deploy actions: fisher plugins, font cache, MCP server registration
9. `prepare_user.yml` — shell, user-level setup

### Configuration Deployment (`install_configs.yml`)

Six deployment blocks, each using the most efficient method:

1. **symlinks** — `.claude/` subdirs (agents, skills, etc.) symlinked to repo for bidirectional editing.
2. **copy loop** — `.claude/` root files (CLAUDE.md, settings.json, hooks.json, config.md)
3. **copy dir** — `kitty/`, `nvim/`, `fish/completions/`, `fish/functions/` as whole directories (no `--delete`, safe for local overlay). AeroSpace config is handled separately in **Block 3c**: `.config/aerospace/` (`aerospace.toml` + the `aerospace-layouts` dynamic-layout uv project) is one-way rsynced with `--delete` — repo is source of truth; the engine's runtime state lives under `~/.local/state/`, not here — excluding `.venv`/caches, then the project's `.venv` is materialised via `uv sync --frozen --no-dev` (mirroring Block 1b for `.claude/bin`) so the `aerospace.toml` layout keybindings can invoke the built console-script (`~/.config/aerospace/layouts/.venv/bin/aerospace-layouts`) by absolute path (`exec-and-forget` has no `uv` on PATH).
4. **copy loop** — individual files (fish/config.fish, conf.d/aliases.fish, README.md)
5. **template loop** — 6 `.j2` files rendered to their destinations (`.bashrc`, `.gemrc`, `.npmrc`, `.config/git/config`, 2 fish conf.d). `.config/git/config` is the XDG global git config, which git reads **in addition to** `~/.gitconfig` (the user's file is left untouched; where a key is set in both, `~/.gitconfig` wins). It carries behavioral settings only — branchless push/pull (`push.autoSetupRemote`, `pull.ff=only`), `rerere`, `core.hooksPath`, `jira.keyPosition`. Per-profile **identity** is layered on via `includeIf gitdir:` (`~/Projects` → personal, `~/Work` → work) pulling in `~/.config/git/identity-{personal,work}.gitconfig`, generated by `make git-identity` (`scripts/git-identity-gen.sh`) into the gitignored local overlay and deployed via Block 6. `make git-identity` is standalone; `git-identity-ensure` is an idempotent prerequisite of `personal`/`work`. A user's existing `[user]` in `~/.gitconfig` loads last and shadows these includes — remove it when adopting per-profile identity. The `core.hooksPath` points at `~/.config/git/hooks/`, deployed by Block 3b; its `prepare-commit-msg` (Jira-key injection) is a self-contained stdlib Python script — tested via `make test-git-hooks` (`tests/git_hooks/`).
6. **local overlay** — `roles/devbox/local/` (gitignored) deployed last via filetree. Laptop-only configs override repo files.

Protected files: `_init_env_confidential.fish` is copied only if absent (`force: false`).

### MCP Server Registration (`apply_configs.yml`)

Three transport types configured in `defaults/main/claude.yml`:
- **Docker** (`mcp_docker_servers`) — containers via `docker run --rm -i` (sequentialthinking, playwright)
- **Script** (`mcp_script_servers`) — wrapper scripts in `~/.claude/bin/` (memory-upstream, memory-downstream)
- **HTTP** (`mcp_http_servers + devbox_extra_mcp_http_servers`) — remote endpoints (figma + profile extras)

Registered via `claude mcp add` with user scope.

### Variables (`defaults/main/`)

Defaults are split into four files under `defaults/main/`:

| File | Contents |
|------|----------|
| `core.yml` | `devbox_user`, `devbox_paths`, `devbox_projects_dir`, `devbox_active_profile`, `upgrade_mode`, `devbox_extra_*` extension points |
| `packages.yml` | `devbox_brew_taps`, `devbox_brew_*` lists, `devbox_npm_packages`, `devbox_appstore_apps`, `devbox_packages` (go_tools, kubectl, uv_tools) |
| `shell.yml` | `devbox_shell` (env, PATH), `devbox_fish_plugins`, `devbox_tide_configure_auto` |
| `claude.yml` | `devbox_claude_managed_dirs`, `mcp_*_servers`, `claude_plugin*` |

**Important**: `defaults/main.yml` (file) must NOT coexist with `defaults/main/` (directory) — Ansible loads the file and ignores the directory if both are present.

Key variables:
- `devbox_paths.dotfiles_root_dir` — target for deployment (`~` normally, `../debug/dotfiles` in dev_mode)
- `devbox_shell.env` / `path_prepend` / `path_append` / `path_conditional` — single source of truth for shell environment. Templates for fish and bash iterate these lists. The Ancient Greek env vars (`MNEMOSYNE_PERISTASEOS` for the active profile, `AION_AUTOPOIESEON` for the workspace root) are intentional — see the comment block in `roles/devbox/defaults/main/shell.yml` for etymology and rationale. `PROJECTS_DIR` is kept as a transitional alias.
- `devbox_active_profile` — `personal` / `work`. Overridden in `profiles/{name}.yml`, rendered into `MNEMOSYNE_PERISTASEOS` via `devbox_shell.env`, and read by slim targets (`dotfiles-push`, `shell-push`, `mcp-sync`, etc.) via `Makefile:ACTIVE_PROFILE` so they recover the active profile without re-running the full personal/work playbook.
- `devbox_brew_secondary` + `devbox_extra_brew` — base packages + profile-specific additions (concatenated in task files)
- `devbox_extra_*` — extension points for profile overrides (default to `[]` in `core.yml`)
- `devbox_extra_brew_casks_no_binaries` — separate cask list installed with `--no-binaries` to skip brew's CLI shim + Spotlight metadata steps. Required for casks whose .pkg writes root-owned files inside /Applications/<App>.app (post-install `xattr -w` runs as the user and fails). Currently used for `docker-desktop`.
- `devbox_brew_taps` — third-party Homebrew repos tapped before `brew install` (currently: `nikitabobko/tap` for AeroSpace, `FelixKratz/formulae` for sketchybar + JankyBorders)

### Profiles (`profiles/`)

Profiles select non-sensitive per-machine configuration. Applied via `make personal` or `make work`:

| Layer | Source | Purpose |
|-------|--------|---------|
| 1. Role defaults | `defaults/main/*.yml` | Base package lists, shell env, MCP servers |
| 2. Profile | `profiles/{personal,work}.yml` | Machine-flavor overrides (extra packages, project dir) |
| 3. Keychain | macOS login keychain (`devbox-sudo`, `devbox-ssh-passphrase`) | Machine-local secrets (sudo password, SSH passphrase). Seeded by `scripts/ensure_secrets.sh`. |
| 4. Local overlay | `roles/devbox/local/` | Sensitive *files* — gitignored, for proprietary configs (k8s wrappers, internal hostnames) |

Current per-profile differences:

| | `personal` | `work` |
|---|---|---|
| `devbox_projects_dir` | `$HOME/Projects` | `$HOME/Work` |
| Container runtime cask | `docker-desktop` | `orbstack` |
| Extra MCP HTTP servers | none | `atlassian` |

### Claude Code Config (in `roles/devbox/files/dot_claude/`)

| Path | Purpose | Deployed To |
|------|---------|-------------|
| `USER_AUTHORITY_PROTOCOL.md` | User Authority Protocol (renamed on deploy) | `~/.claude/CLAUDE.md` |
| `settings.json` | Default permissions (allow/deny) | `~/.claude/settings.json` |
| `hooks.json` | Pre/post tool-call hooks | `~/.claude/hooks.json` |
| `agents/*.md` | Agent definitions (28 agents) | `~/.claude/agents/` |
| `commands/techne-*.md` | Slash commands — 22, all `techne-` prefixed (`/techne-implement`, `/techne-test`, `/techne-plan`, etc.) | `~/.claude/commands/` |
| `skills/*/SKILL.md` | Reusable knowledge modules (40 skills) | `~/.claude/skills/` |
| `schemas/*.json` | JSON Schema files (2: `se_output`, `dss_output`) for SE and DSS output validation | `~/.claude/schemas/` |
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

When working in `roles/devbox/files/dot_claude/` you are editing files that get deployed to `~/.claude/`. This is a distinct activity from editing the Ansible playbook itself:

- **Deploy after editing**: managed subdirs are no longer symlinked. After changing agents/skills/commands/etc., run `make claude-push` to deploy via the slim `playbooks/claude.yml` (no sudo, no keychain lookup) — `~3-5s`. A full `make personal`/`make work` does the same work (Block 1 + Block 2 in `roles/devbox/tasks/install_configs.yml`) as part of the wider playbook.
- **Repo is the only source of truth**: Block 1 runs `ansible.posix.synchronize` with `--delete` per managed subdir, so any edits made directly under `~/.claude/agents/`, `skills/`, etc. are overwritten on next push. Host-only state (`projects/`, `plans/`, `memory/`, `plugins/`, ...) is never in scope of `--delete`.
- **`settings.json` changes** affect sandbox permissions, network allowlists, and tool approvals globally
- **`hooks.json` changes** define pre/post hooks for tool calls (scripts in `bin/`)
- **`bin/` is a uv project** — `bin/pyproject.toml` + `bin/uv.lock` pin runtime deps (currently `bashlex` for `bash_decision_gate.py`). On deploy, `install_configs.yml` Block 1b runs `uv sync --frozen --no-dev` and materialises `~/.claude/bin/.venv/`. `hooks.json` launches each Python hook as `uv run --project ~/.claude/bin python ~/.claude/bin/<x>.py`, which resolves to that venv. The same `bashlex` is mirrored in the root dev group so `make test`/Pyright also see it; **changes to `bin/pyproject.toml` require regenerating `bin/uv.lock` via `uv lock --project roles/devbox/files/dot_claude/bin`**.
- **Run `make test-claude-hooks`** to validate the bin/ test suite under the deployed-venv shape (same `uv sync --frozen` that Ansible runs). Complements `make test`/`make test-integration`, which use the root dev venv.
- **`templates/` changes** affect devcontainer scaffolding for new projects
- **Command naming — `techne-` prefix**: every file in `commands/` is named `techne-<name>.md` and invoked as `/techne-<name>`. The prefix is deliberate: bare names like `/focus`, `/plan`, `/status`, `/review`, `/verify` collide with Claude Code's built-in commands and bundled skills (the built-in/bundled one wins, shadowing the custom command). New commands MUST keep the `techne-` prefix, and any cross-reference to a command (in agents, skills, other commands, `bin/` hint text) MUST use the `/techne-<name>` form.
- Run `make validate-claude` to check cross-references between agents, skills, and commands
- The `USER_AUTHORITY_PROTOCOL.md` in `roles/devbox/files/dot_claude/` is deployed as `~/.claude/CLAUDE.md` and is the **User Authority Protocol** — it governs all Claude Code sessions globally, not just this project

## Dependencies

Requires Ansible with `community.general` collection (>=10.1.0):
```bash
ansible-galaxy collection install -r requirements.yml
```
