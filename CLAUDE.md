# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ansible-based developer workstation setup tool that automates installation and configuration of development tools, dotfiles, and system preferences. Supports macOS (Darwin) and Ubuntu Linux.

**Key distinction**: `roles/devbox/files/dot_claude/` contains Claude-specific files deployed to `~/.claude/`; `dot_codex/` contains the portable Codex settings, global guidance, and native agents deployed under `~/.codex/`; and `dot_ai/` contains shared source material. The `USER_AUTHORITY_PROTOCOL.md` in `dot_ai/` is the Claude/Antigravity authority source, while Codex uses its adapted `dot_codex/AGENTS.md`; neither is this project's instruction file.

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
make lint                    # syntax-check + ansible-lint + semantics + typecheck
make lint-ansible-semantics  # static catch for set_fact intra-task self-references
make check-personal  # dry-run with personal profile
make check-work      # dry-run with work profile
make check-dev       # dry-run in dev_mode (override vars, no sudo/keychain)

# Fish shell upgrade + tide prompt sync
make fixfish          # upgrade fish, update plugins, apply tide config from defaults

# Secrets (macOS login keychain)
make secrets-init            # seed devbox-sudo + devbox-ssh-passphrase (idempotent)
make sudo-reseed             # after macOS login password rotation
make ssh-passphrase-reseed   # after SSH passphrase change or key regen

# otelbox edge (durable local OTLP collector, Task Flow step 12)
# scripts/otelbox-edge-{config,test,cert-check}.py are thin wrappers over the
# stdlib-only scripts/otelbox_edge/ package.
make otelbox-edge-config     # set remote endpoint (local overlay) + ingestion token (keychain); ONLY=endpoint|token|cert
make otelbox-edge-test       # liveness + delivery smoke: binary, launchd service, :13133, :8888, OTLP round-trip

# Weekly drive backup (packages/drive-backup — standalone uv project, own lock/tests)
make drive-backup-push       # (re)install project + LaunchAgent from the local overlay config
make drive-backup-now        # launchctl kickstart the agent; log in ~/Library/Logs/drive-backup.log
make test-drive-backup       # package pytest + ruff + pyrefly (strict) + example-config check

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

# Live engine tests (requires claude/codex/agy CLIs, run from regular terminal)
make test-live       # each engine binary honours the config this repo generates for it
make test-live ENGINES=claude,codex  # ...and a skip of a named engine is a failure (CI uses this)
make test-live-guard # hermetic: the throwaway-home and engine guards still fire (part of `make qa`)
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
7. `darwin/configure_pub_mode.yml` — pub mode: deploys the `pub-lease` controller to `~/.local/bin/` and installs the system-domain LaunchDaemon `local.pub-lease`, which reconciles the lease every 60 seconds. Gated on the profile actually installing the `cloudflare-warp` cask (personal only); the disabled path tears the whole thing down and restores any active lease. See `README.md` § Pub Mode.
8. `install_configs.yml` — deploy shared AI/client configs and dotfiles (see below)
9. `install_codex_configs.yml` — reconcile `dot_codex/config.toml.j2` into app-owned `~/.codex/config.toml` via `scripts/ai-config apply codex` (which renders the template itself — see Block 2 below), install `dot_codex/AGENTS.md` plus native TOML agents, and deploy the compatible `dot_ai` skill subset to `~/.agents/skills/`. The final task grants Codex hook trust via `scripts/codex-hook-trust.py` (thin wrapper over the stdlib-only `scripts/codex_hook_trust/` package): it drives `codex app-server`'s `hooks/list` + `config/batchWrite` to write `hooks.state."<key>".trusted_hash`, scoped to an allowlist derived from this repo's `[hooks]` block and `devbox_codex_plugins`. Without it Codex silently drops every provisioned hook. See `dot_codex/README.md` § Hook trust.
10. `apply_configs.yml` — post-deploy actions: fisher plugins, font cache, MCP server registration
11. `prepare_user.yml` — shell, user-level setup
12. `darwin/install_otelbox_edge.yml` — durable OpenTelemetry edge collector. It downloads the checksum-verified v2.1 release binary, deploys one self-contained `edge.yaml`, validates that exact pair and supervises it with `local.otelbox-edge`. The endpoint comes from the local overlay; the Keychain remains credential authority and the wrapper materialises v2.1's watched header in the private per-user temporary directory. Once v2.1 preflight passes, the task removes the legacy `otelcol-edge` binary, config, LaunchAgent and WAL. Homebrew remains a hard conflict. See `README.md` § OTLP Telemetry.
13. `darwin/configure_drive_backup.yml` — weekly drive backup. Switched on by the local-overlay config `~/.config/drive-backup/config.toml` (example: `files/.config/drive-backup/config.toml.example`): rsyncs the standalone uv project `packages/drive-backup/` to `~/.local/share/drive-backup/`, runs `uv sync --frozen --no-default-groups`, validates the config with `drive-backup check-config`, and (re)bootstraps the `local.drive-backup` LaunchAgent (`StartCalendarInterval` Saturday 03:00). Without the config it boots the agent out and removes it. See `README.md` § Drive Backup.

### Configuration Deployment (`install_configs.yml`)

Six deployment blocks, each using the most efficient method:

1. **symlinks** — `.claude/` subdirs (agents, skills, etc.) symlinked to repo for bidirectional editing.
2. **copy loop** — `.claude/` root file (config.md). `settings.json.j2` is not copied: it is reconciled field-by-field via `scripts/ai-config apply claude` against the ownership manifest `settings.ai-config.json`, so any key deployed from the repo — including `hooks` — must be declared there first. All three engine sources (`dot_claude/settings.json.j2`, `dot_agy/cli/settings.json.j2`, `dot_codex/config.toml.j2`) are Jinja templates, and **`scripts/ai-config` renders them, not Ansible** — `make claude-diff` / `claude-pull` invoke the reconciler directly, so rendering in Ansible would make those paths behave differently from the playbook. Variables come from `roles/devbox/defaults/main/*.yml` overlaid by `profiles/<profile>.yml` for the `--profile` given, under `StrictUndefined`. A leaf that a template expression produced is never written back from the live file: `ai-config diff` marks it `templated` and always re-applies the rendered value. Per-profile values therefore need no manifest binding; the only surviving binding providers are `keychain:` and `home:`, for values that must not be materialised into a rendered artefact.
3. **copy dir** — `kitty/`, `nvim/`, `fish/completions/`, `fish/functions/` as whole directories (no `--delete`, safe for local overlay). AeroSpace config is handled separately in **Block 3c**: `.config/aerospace/` (`aerospace.toml` + the `aerospace-layouts` dynamic-layout uv project) is one-way rsynced with `--delete` — repo is source of truth; the engine's runtime state lives under `~/.local/state/`, not here — excluding `.venv`/caches, then the project's `.venv` is materialised via `uv sync --frozen --no-dev` (mirroring Block 1b for `.claude/bin`) so the `aerospace.toml` layout keybindings can invoke the built console-script (`~/.config/aerospace/layouts/.venv/bin/aerospace-layouts`) by absolute path (`exec-and-forget` has no `uv` on PATH).
4. **copy loop** — individual files (fish/config.fish, conf.d/aliases.fish, README.md)
5. **template loop** — 6 `.j2` files rendered to their destinations (`.bashrc`, `.gemrc`, `.npmrc`, `.config/git/config`, 2 fish conf.d). `.config/git/config` is the XDG global git config, which git reads **in addition to** `~/.gitconfig` (the user's file is left untouched; where a key is set in both, `~/.gitconfig` wins). It carries behavioral settings only — branchless push/pull (`push.autoSetupRemote`, `pull.ff=only`), `rerere`, `core.hooksPath`, `jira.keyPosition`. Per-profile **identity** is layered on via `includeIf gitdir:` (`~/Projects` → personal, `~/Work` → work) pulling in `~/.config/git/identity-{personal,work}.gitconfig`, generated by `make git-identity` (`scripts/git-identity-gen.py`) into the gitignored local overlay and deployed via Block 6. `make git-identity` is standalone; `git-identity-ensure` is an idempotent prerequisite of `personal`/`work`. A user's existing `[user]` in `~/.gitconfig` loads last and shadows these includes — remove it when adopting per-profile identity. The `core.hooksPath` points at `~/.config/git/hooks/`, deployed by Block 3b; its `prepare-commit-msg` (Jira-key injection) is a self-contained stdlib Python script — tested via `make test-git-hooks` (`tests/git_hooks/`).
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

### AI Config (in `roles/devbox/files/dot_claude/`, `dot_codex/`, and `dot_ai/`)

| Path | Purpose | Deployed To |
|------|---------|-------------|
| `dot_ai/USER_AUTHORITY_PROTOCOL.md` | Claude/Antigravity User Authority Protocol | `~/.claude/CLAUDE.md`, `~/.gemini/config/rules/AGENTS.md` |
| `dot_codex/AGENTS.md` | Codex-adapted global working agreements | `~/.codex/AGENTS.md` |
| `settings.json.j2` | Default permissions (allow/deny); Jinja rendered by `scripts/ai-config` | `~/.claude/settings.json` |
| `settings.json.j2` → `hooks` | Pre/post tool-call hooks, session lifecycle, logging | `~/.claude/settings.json` |
| `dot_ai/agents/*.md` | Shared Markdown agent sources (28 agents) | `~/.claude/agents/`, `~/.gemini/config/agents/` |
| `dot_codex/agents/*.toml` | All 28 Codex-native agent adapters | `~/.codex/agents/` |
| `commands/techne-*.md` | Slash commands — 22, all `techne-` prefixed (`/techne-implement`, `/techne-test`, `/techne-plan`, etc.) | `~/.claude/commands/` |
| `dot_ai/skills/*/SKILL.md` | Reusable knowledge modules (40 skills); Codex receives the compatible allowlist | `~/.claude/skills/`, `~/.gemini/config/skills/`, `~/.agents/skills/` |
| `dot_ai/skills/fpf-thinking/references/` | Vendored FPF Core and companion NSTD specifications | Alongside each deployed `fpf-thinking` skill |
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

When working in `roles/devbox/files/dot_claude/` and `dot_ai/` you are editing files that get deployed to `~/.claude/` and `~/.gemini/config/`. This is a distinct activity from editing the Ansible playbook itself:

- **Deploy after editing**: managed subdirs are no longer symlinked. After changing agents/skills/commands/etc., run `make claude-push` to deploy via the slim `playbooks/claude.yml` (no sudo, no keychain lookup) — `~3-5s`. A full `make personal`/`make work` does the same work (Block 1 + Block 2 in `roles/devbox/tasks/install_configs.yml`) as part of the wider playbook.
- **Repo is the only source of truth**: Block 1 runs `ansible.posix.synchronize` with `--delete` per managed subdir, so any edits made directly under `~/.claude/agents/`, `skills/`, etc. are overwritten on next push. Host-only state (`projects/`, `plans/`, `memory/`, `plugins/`, ...) is never in scope of `--delete`.
- **`settings.json.j2` changes** affect sandbox permissions, network allowlists, and tool approvals globally. It is a Jinja template rendered by `scripts/ai-config`; keep every expression inside a quoted JSON value, because the *unrendered* document is what a captured live value is written back into.
- **`hooks` block in `settings.json.j2`** defines pre/post hooks for tool calls and session lifecycle (scripts in `bin/`). Claude Code reads user hooks only from the deployed `settings.json` / `settings.local.json` (and from a plugin's own `hooks/hooks.json`) — a standalone `~/.claude/hooks.json` is silently ignored, so never park hooks there.
- **`bin/` is a uv project** — `bin/pyproject.toml` + `bin/uv.lock` pin runtime deps (currently `bashlex` for `bash_decision_gate.py`). On deploy, `install_configs.yml` Block 1b runs `uv sync --frozen --no-dev` and materialises `~/.claude/bin/.venv/`. The `hooks` block launches each Python hook via the deployed venv's Python directly: `~/.claude/bin/.venv/bin/python ~/.claude/bin/<x>.py` — bypassing `uv run` to avoid its default sync of dev-group deps (`pytest`, `hypothesis`) into a `--no-dev` venv, which would fail hook execution on every Bash call. The same `bashlex` is mirrored in the root dev group so `make test`/Pyright also see it; **changes to `bin/pyproject.toml` require regenerating `bin/uv.lock` via `uv lock --project roles/devbox/files/dot_claude/bin`**.
- **Run `make test-claude-hooks`** to validate the bin/ test suite under the deployed-venv shape (same `uv sync --frozen` that Ansible runs). Complements `make test`/`make test-integration`, which use the root dev venv.
- **Run `make test-live`** after changing an engine's generated configuration. Every other suite asserts the *content* of generated files; `tests/live/` generates them through `scripts/ai-config apply` into a throwaway home and then points the real `claude` / `codex` / `agy` binary at it, asserting the engine observably honoured them (Codex: `hooks/list` discovery and trust, including the `modified` state a stale `trusted_hash` produces; Claude: which hook commands a model-free print session actually dispatched, and which matchers refused to fire; agy: the permission set and hook count its language-server log reports it loaded). `test_live_interpreters.py` additionally runs the playbook's own `uv sync --frozen --no-dev` in the throwaway home and resolves every declared hook command against it — no engine checks that its hooks are runnable, so nothing else would notice an interpreter that does not exist. Opt-in — never part of `make test` or `make qa` — and skips when a binary is missing, unless `ENGINES=` names it, in which case the skip is a failure. Needs no account and no reachable API. `tests/live/throwaway.py` refuses any path that is not under the temporary root and clear of the real home; it and the engine guard run with `make qa` via `make test-live-guard`, and in CI via the `test` job of `ci.yml`. The engine tests themselves run in `.github/workflows/live-engines.yml`, which installs `claude` and `codex` from npm and requires them; `agy` is installed best-effort there because the repository's own channel for it (the `antigravity-cli` cask) is macOS-only.
- **What each engine does with a configuration it cannot parse** is pinned by that suite, because two of the three say nothing. Claude Code drops an unparseable `settings.json` and runs a session indistinguishable from one with no `hooks` block: exit 0, empty stderr, nothing dispatched, `--debug` included. agy discards an unparseable `settings.json`, loads `permissions=<nil>` and records the reason only in its language-server log. Codex is the exception and the good case: `hooks/list` answers with a parse error naming file, line and column, and the CLI refuses to start. The generator must therefore never emit an invalid file for Claude or agy — no engine will tell you.
- **`templates/` changes** affect devcontainer scaffolding for new projects
- **Command naming — `techne-` prefix**: every file in `commands/` is named `techne-<name>.md` and invoked as `/techne-<name>`. The prefix is deliberate: bare names like `/focus`, `/plan`, `/status`, `/review`, `/verify` collide with Claude Code's built-in commands and bundled skills (the built-in/bundled one wins, shadowing the custom command). New commands MUST keep the `techne-` prefix, and any cross-reference to a command (in agents, skills, other commands, `bin/` hint text) MUST use the `/techne-<name>` form.
- Run `make validate-claude` to check cross-references between agents, skills, and commands
- The `USER_AUTHORITY_PROTOCOL.md` in `roles/devbox/files/dot_ai/` is deployed as `~/.claude/CLAUDE.md` and `~/.gemini/config/rules/AGENTS.md`; Codex uses the separately adapted `roles/devbox/files/dot_codex/AGENTS.md`

## Dependencies

Requires Ansible with `community.general` collection (>=10.1.0):
```bash
ansible-galaxy collection install -r requirements.yml
```
