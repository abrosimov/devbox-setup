# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ansible-based developer workstation setup tool that automates installation and configuration of development tools, dotfiles, and system preferences. Supports macOS (Darwin) and Ubuntu Linux.

**Key distinction**: `roles/devbox/files/dot_claude/` contains files deployed to `~/.claude/` (user's global Claude Code config). The directory is named `dot_claude/` rather than `.claude/` so Claude Code does not treat edits to it as self-modifications. The `USER_AUTHORITY_PROTOCOL.md` there is the **global authority protocol** — it is deployed as `~/.claude/CLAUDE.md` and is not this project's instructions.

## Commands

A profile is mandatory for any playbook run. Bare `make run` / `make dev` / `make check` fail with `PROFILE is required` — use the per-profile wrappers below. `personal` targets a personal laptop (`AION_AUTOPOIESEON=~/Projects`); `work` targets a work laptop (`AION_AUTOPOIESEON=~/Work`). Slim targets (`make dotfiles-push` etc.) recover the active profile from the `.devbox-profile` stamp written by the previous full run, or fail with a hint if no stamp exists.

The sudo password is captured once at playbook start via `vars_prompt: ansible_become_password` (defined in `playbooks/main.yml`). Ansible uses it transparently for any `become: true` task and forwards it to `community.general.homebrew_cask` via the `sudo_password:` parameter, so pkg-based casks (karabiner-elements, etc.) install non-interactively. This is why the Makefile does NOT pass `-K` to `ansible-playbook` — that flag would trigger a redundant second prompt and its captured value is not exposed for templating. Tasks that consume `ansible_become_password` MUST set `no_log: true` to avoid leakage in verbose output.

```bash
# Bootstrap (macOS only — installs Homebrew, Ansible, collections)
make init

# Full setup runs (prompt for vault password and sudo)
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
make check-personal  # dry-run with personal profile (prompts for vault + sudo)
make check-work      # dry-run with work profile
make check-dev       # dry-run in dev_mode (uses test vault, no sudo)

# Fish shell upgrade + tide prompt sync
make fixfish          # upgrade fish, update plugins, apply tide config from defaults

# Vault management
make vault-init      # create and encrypt vault/devbox_ssh_config.yml

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
3. **copy dir** — `kitty/`, `nvim/`, `fish/completions/`, `fish/functions/` as whole directories (no `--delete`, safe for local overlay)
4. **copy loop** — individual files (fish/config.fish, conf.d/aliases.fish, README.md)
5. **template loop** — 5 `.j2` files rendered to their destinations (`.bashrc`, `.gemrc`, `.npmrc`, 2 fish conf.d)
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
- `devbox_active_profile` — `personal` / `work`. Overridden in `profiles/{name}.yml`, stamped to `.devbox-profile` at repo root by `playbooks/main.yml` post_tasks, and read by slim targets (`dotfiles-push`, `shell-push`, `mcp-sync`, etc.) so they recover the active profile without re-running the full personal/work playbook.
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
| 3. Vault | `vault/devbox_ssh_config.yml` | Encrypted secrets (SSH passphrase) |
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
| `commands/*.md` | Slash commands — 23 (/implement, /test, /status, /focus, etc.) | `~/.claude/commands/` |
| `skills/*/SKILL.md` | Reusable knowledge modules (85 skills) | `~/.claude/skills/` |
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

When working in `roles/devbox/files/dot_claude/` you are editing files that get deployed to `~/.claude/`. This is a distinct activity from editing the Ansible playbook itself:

- **Deploy after editing**: managed subdirs are no longer symlinked. After changing agents/skills/commands/etc., run `make claude-push` to deploy via the slim `playbooks/claude.yml` (no sudo, no vault) — `~3-5s`. A full `make personal`/`make work` does the same work (Block 1 + Block 2 in `roles/devbox/tasks/install_configs.yml`) as part of the wider playbook.
- **Repo is the only source of truth**: Block 1 runs `ansible.posix.synchronize` with `--delete` per managed subdir, so any edits made directly under `~/.claude/agents/`, `skills/`, etc. are overwritten on next push. Host-only state (`projects/`, `plans/`, `memory/`, `plugins/`, ...) is never in scope of `--delete`.
- **`settings.json` changes** affect sandbox permissions, network allowlists, and tool approvals globally
- **`hooks.json` changes** define pre/post hooks for tool calls (scripts in `bin/`)
- **`templates/` changes** affect devcontainer scaffolding for new projects
- Run `make validate-claude` to check cross-references between agents, skills, and commands
- Run `bin/validate-pipeline-output --help` to test the pipeline validation script locally
- Run `bin/validate-pipeline-output --progress-check --project-dir <path>` to validate progress spine files
- **`schemas/` changes** define JSON Schema contracts for pipeline execution (stream completion, execution DAG, pipeline state, progress plan, progress agent) — validated by `bin/validate-pipeline-output`
- **`bin/progress`** is the serializer for the progress spine system — manages milestone DAG and per-agent status files in `{PROJECT_DIR}/progress/`
- The `USER_AUTHORITY_PROTOCOL.md` in `roles/devbox/files/dot_claude/` is deployed as `~/.claude/CLAUDE.md` and is the **User Authority Protocol** — it governs all Claude Code sessions globally, not just this project

## Dependencies

Requires Ansible with `community.general` collection (>=10.1.0):
```bash
ansible-galaxy collection install -r requirements.yml
```
