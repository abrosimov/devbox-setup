# devbox-setup

Ansible-based developer workstation setup. Automates installation of packages, dotfiles, shell config, and Claude Code agent infrastructure.

## Supported OS

- macOS (Darwin) — primary
- Ubuntu (Linux)

## Quick Start

```bash
make init       # Bootstrap (macOS: Homebrew, Ansible, collections)
make personal   # Full run with the personal profile
make work       # Full run with the work profile
```

On the very first run, `make personal`/`make work` prompts once for the sudo/login password and once for the SSH key passphrase (both stored in the macOS login Keychain as `devbox-sudo` and `devbox-ssh-passphrase`). Subsequent runs are non-interactive.

A profile is mandatory: bare `make run` / `make dev` / `make check` fail with `PROFILE is required`. Use the per-profile wrappers below.

## Commands

| Command | Description |
|---------|-------------|
| `make personal` | Full setup with personal profile |
| `make work` | Full setup with work profile |
| `make dev-personal` | Deploy to `../debug/dotfiles` with personal profile |
| `make dev-work` | Deploy to `../debug/dotfiles` with work profile |
| `make check-personal` | Dry-run with personal profile |
| `make check-work` | Dry-run with work profile |
| `make check-dev` | Dry-run in dev_mode (override vars, no sudo/keychain) |
| `make upgrade-personal` | Upgrade all packages (personal profile) |
| `make upgrade-work` | Upgrade all packages (work profile) |
| `make codex-push` | Deploy portable Codex settings, global guidance, custom agents, and compatible shared skills |
| `make lint` | Syntax-check + ansible-lint + semantics + typecheck |
| `make lint-ansible-semantics` | Static catch for set_fact intra-task self-references |
| `make validate-claude` | Validate agent/skill cross-references |
| `make otelbox-edge-config` | Set the edge collector's remote endpoint + ingestion token (`ONLY=endpoint\|token`) |
| `make otelbox-edge-test` | Liveness + delivery smoke for the edge collector (also runs after `make personal`/`work`) |

Add `V=1` through `V=4` for verbosity. Pass extra Ansible variables via `EXTRA_VARS='-e foo=bar'` (e.g. `--tags`: `make personal EXTRA_VARS='--tags packages'`).

## Configuration

### Secrets (macOS Keychain)

Two login-keychain slots are used, seeded automatically on first `make personal`/`make work`:

| Slot | Contents | Consumers |
|---|---|---|
| `devbox-sudo` | Login/sudo password | `scripts/with_sudo_keepalive.sh` (primes `sudo -v`); `ansible.cfg` `become_password_file`; Homebrew cask `sudo_password:` (via `devbox_sudo_password` var) |
| `devbox-ssh-passphrase` | SSH key passphrase | `roles/devbox/tasks/prepare_user.yml` (key generation); `configure_ssh_keychain.yml` (writes `SSH: <path>` slot for `ssh-add --apple-load-keychain`) |

Rotation:

```bash
make sudo-reseed              # after changing macOS login password
make ssh-passphrase-reseed    # after changing/regenerating SSH passphrase
make secrets-init             # reseed both (idempotent -U)
```

Inspect existing slots via `security find-generic-password -s devbox-sudo` (or `-s devbox-ssh-passphrase`). The first read from any subprocess triggers a one-time Keychain ACL dialog — click "Always Allow" to grant `security` silent access thereafter.

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
- [AeroSpace](roles/devbox/files/.config/aerospace/README.md) — i3-style tiling WM, ijlm bindings, workspace→monitor auto-assignment
- [Fish](roles/devbox/files/.config/fish/README.md) — abbreviations, functions, plugins
- [Claude Config](roles/devbox/files/dot_claude/README.md) — Claude runtime, hooks, schemas, and templates
- [Codex Config](roles/devbox/files/dot_codex/README.md) — portable settings, global guidance, native agents, FPF references, and ownership boundaries

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

## OTLP Telemetry (otelbox edge)

A durable local OpenTelemetry collector — Ansible-deployed, `launchd`-supervised, no brew — sinks agent telemetry at `127.0.0.1:4317` (gRPC) / `:4318` (HTTP), buffers it on disk across outages, and forwards to one remote gateway with `deployment.environment.name={profile}` stamped on every record. Langfuse transcript plugins use the separate traces-only listener at `127.0.0.1:14318/api/public/otel/v1/traces`; only that pipeline adds `otelbox.telemetry.class=llm`.

Wired: Claude Code CLI (`OTEL_*` env in `~/.claude/settings.json`), Codex CLI/app (`[otel]` managed from `dot_codex`), and Antigravity through the `agy` wrapper's standard OpenTelemetry environment variables.

### Where the collector comes from

Nothing is built here. The binary is the published [`abrosimov/otelcol-otelbox`](https://github.com/abrosimov/otelcol-otelbox) artefact — one collector serving the workstation `edge` and the server roles deployed by `remote_server_setup`. That repository owns the component set, release pipeline and reference profiles; this one owns the deployed edge profile, secrets, supervisor and machine-local values.

Version 2.x loads one self-contained `edge.yaml`. The binary and profile are upgraded together; v1 `base.yaml` layering is deliberately unsupported. The pin lives in `devbox_packages.otelbox_edge.version` and nowhere else — `otelbox-edge-test.sh` reads it from there rather than repeating the literal.

| Path | Role |
|------|------|
| `~/.local/bin/otelcol-otelbox` | the pinned release asset, checksum-verified on download |
| `roles/devbox/files/.config/otelbox/edge/edge.yaml` | self-contained v2.3 edge profile adapted from the published profile |
| `~/.config/otelbox/edge/` | profile + wrapper + `endpoint.env`, as deployed |
| `~/.config/otelbox/edge/client/` | optional client-certificate pair (mode 0700), deployed from the gitignored overlay |
| `~/.local/state/otelbox/edge/` | the on-disk WAL (bbolt) |
| `~/Library/Logs/otelbox-edge.log` | service log, owned by the LaunchAgent `local.otelbox-edge` |

**Bumping the collector:** raise `devbox_packages.otelbox_edge.version`, reconcile `edge.yaml` with that release and run the playbook. The release already exists — there is nothing to build, tag or publish here.

Homebrew is not an installation path on a machine this playbook manages. The artefact publishes a formula for machines it does not, and installing both puts two copies on disk with `launchd` running the one Homebrew did not install — so the playbook fails outright if it finds a keg.

### Machine-local setup (once per machine)

Three values are not tracked in the repository. All are set by `make otelbox-edge-config` (add `ONLY=endpoint` / `ONLY=token` / `ONLY=cert` for just one; it needs a TTY):

- **Endpoint** (non-secret) — written to the gitignored overlay `roles/devbox/local/.config/otelbox/edge/endpoint.env` and live to `~/.config/otelbox/edge/endpoint.env`. Format: `OTELBOX_UPSTREAM_ENDPOINT=otel.example.com:443` — `host:port`, no scheme. The name is matched exactly by both the wrapper and the playbook's preflight; the v1 `OTELBOX_EDGE_ENDPOINT` is rejected.
- **Ingestion key** (secret) — stored in the login Keychain slot `otelbox-edge-token`. The wrapper materialises the complete `Bearer <token>` header as a mode-0600 file below macOS's per-user temporary directory because the collector watches a credential file for live rotation; the Keychain remains authoritative.
- **Client certificate** (optional, secret half) — an EC P-256 self-signed leaf generated *on this machine* by `ONLY=cert`, valid 825 days (`OTELBOX_CERT_DAYS` overrides). Both halves land in the gitignored overlay `roles/devbox/local/.config/otelbox/edge/client/` and live in `~/.config/otelbox/edge/client/`; Ansible's overlay copy preserves modes, so the key stays 0600 inside a 0700 directory. The private key is never sent anywhere — only `client.crt` is meant to travel to whoever configures the gateway front end, the same shape as an SSH public key.

None is required for the playbook to succeed: without `endpoint.env` the service is not started and the run reports why, and without a certificate the bearer token simply remains the only credential. Exactly *one* half of a certificate pair is a hard error — `configtls` rejects a lone `cert_file` or `key_file`, so both the playbook and the wrapper refuse it rather than letting the collector fail at start.

```bash
make otelbox-edge-config           # remote endpoint (local overlay) + ingestion token (keychain)
make otelbox-edge-config ONLY=cert # generate the client-certificate pair into the overlay
make otelbox-edge-test             # binary, launchd service, :13133, :8888, OTLP round-trip, gateway delivery
```

Restart after changing the endpoint: `launchctl kickstart -k gui/$(id -u)/local.otelbox-edge`. Token changes update the watched header file and do not require a restart. A certificate needs one restart the first time — a collector that started without a pair holds empty paths for its lifetime — after which regenerations are re-read within `OTELBOX_UPSTREAM_TLS_RELOAD_INTERVAL` (1h) by polling, not instantly.

The client-certificate fields arrived with upstream 2.2.0, together with the gateway leg moving from gzip to **zstd**. That codec is safe only because both ends of the leg are the same binary — a gRPC codec has to be registered in the peer's build, not merely named in its configuration — so a gateway still on 2.1.x will not accept it. Override it with `devbox_packages.otelbox_edge.upstream_compression` (`gzip` / `none`), which renders into the LaunchAgent — not in `endpoint.env`, which is a strict one-line contract that both the wrapper and the preflight check reject a second line in.

`make otelbox-edge-test` also runs non-fatally at the end of `make personal`/`make work`. It requires the pinned version, probes `/status`, sends a local OTLP marker and fails on exporter send/enqueue failures, receiver refusals or any signal queue at 80% capacity.

The v2 apply is a one-way cleanup: after the exact pinned binary, endpoint and Keychain credential pass preflight, Ansible stops `local.otelcol-edge` and removes its binary, configuration, LaunchAgent and WAL. No v1 backlog or rollback bundle is retained.

## Telemetry Tunnel (`otelbox`)

For viewing the SigNoz/ClickStack dashboards only — not part of the OTLP ingestion path above. The observability host keeps both browser UIs on loopback — only authenticated OTLP ingestion is published through the public edge. `otelbox` opens an SSH control master with the two forwards and launches the UIs:

```fish
otelbox              # tunnel up + open SigNoz and ClickStack in the browser
otelbox up --no-open # tunnel up, no browser
otelbox status       # the same table on its own
otelbox down         # ssh -O exit through the control socket
otelbox signoz       # ensure the tunnel, open one UI only
otelbox clickstack
```

Every invocation ends with the same summary, so the ports never have to be remembered:

```
  tunnel      user@telemetry.example.com up             ~/.ssh/otelbox.sock
  SigNoz      http://127.0.0.1:18080     listening      traces / metrics / logs
  ClickStack  http://127.0.0.1:28080     listening      HyperDX: logs / sessions
```

The state column is a live `nc -z` probe of each forwarded port, not an assumption from the tunnel being up.

The tunnel is a control master at `~/.ssh/otelbox.sock`, so `down` is an explicit `ssh -O exit` rather than a `pkill` pattern, and a second `otelbox up` reuses the existing session instead of stacking processes. `ExitOnForwardFailure=yes` makes a busy local port a hard failure instead of a tunnel with no working forwards.

### Configuration

The SSH destination is machine-local — this repository is public:

```
roles/devbox/files/.config/otelbox/tunnel.env.example  # committed template
roles/devbox/local/.config/otelbox/tunnel.env          # real values, gitignored
→ deployed to ~/.config/otelbox/tunnel.env by `make local-push`
```

```
OTELBOX_TUNNEL_HOST=user@telemetry.example.com
#OTELBOX_SIGNOZ_PORT=18080
#OTELBOX_CLICKSTACK_PORT=28080
```

Ports default to `18080` (SigNoz) and `28080` (ClickStack) and only need overriding if the server-side loopback publications change.

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
