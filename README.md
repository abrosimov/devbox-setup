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
| `make sync-upstream-docs` | Refresh the [FPF, Narrative and Engineering DPF bundle](roles/devbox/files/dot_ai/skills/fpf-thinking/references/bundle-index.md) from one upstream commit; use `ARGS='--check'` for a read-only comparison |
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

### Why pub exists

Pub was created to work around Claude Code connectivity failures on a particular wifi network. The original network fault was not established; interference by a middlebox is a hypothesis, not a confirmed diagnosis. The requirement is a temporary alternative network path, with automatic restoration after leaving that network or reaching the time limit, so the workaround does not become a permanent VPN setting.

Pub controls Cloudflare WARP; it does not implement a VPN. The tunnel affects the machine, not just Claude. Claude is the original use case and the current connectivity probe target, but pub does not need Claude credentials or install Claude. It cannot guarantee that every application or existing connection survives a network change.

The current `warp+doh` mode sends IP traffic through WARP and lets WARP handle DNS over HTTPS. This addresses a subsequently observed fault: `tunnel_only` left the original network's DNS servers configured, but they stopped answering through the tunnel. IP connectivity and an HTTPS request with an explicit destination IP still worked. Docker's kernel UDP networking then exposed a separate local DNS-port conflict; its fix is described below.

For the source map, preserved contracts and release checks needed to distribute pub independently, see [Pub: purpose and package extraction](docs/design/pub-package-extraction.md). Extraction is planned after validation of the current change; no standalone package is available yet.

### Connectivity and verification

`pub on` verifies system DNS resolution and an HTTPS response from `api.anthropic.com` before reporting success. A failed check triggers restoration of the captured WARP state. Existing `tunnel_only` leases remain restorable; an explicit `pub on` upgrades them to `warp+doh` while preserving their original restoration intent and twelve-hour ceiling.

`Port53Bound` means WARP cannot start its local DNS proxy because another service owns port 53. On macOS, Docker's kernel networking for UDP can make `mDNSResponder` occupy that port. Disable that Docker option and apply its restart at a suitable time; pub does not stop Docker or system DNS services. See [Cloudflare's DNS proxy troubleshooting](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/troubleshooting/client-errors/#cf_dns_proxy_failure).

In Docker Desktop, open **Settings → Resources → Network**, clear **Use kernel networking for UDP**, then apply and restart. The personal playbook also merges `KernelForUDP: false` into the existing `settings-store.json` before deploying pub. It stops a running Desktop before the merge and restarts it afterwards, interrupting its containers; an already compliant configuration causes no restart. Other preferences are preserved. The work profile uses OrbStack and does not run this task. If Docker has never been launched, initialise it once and rerun the playbook; no partial first-run configuration is created.

Before deploying changes with `make personal` or `make work`, run these checks on the Mac that uses WARP:

```sh
make pub-preflight
make pub-e2e
```

`pub-preflight` leaves network settings unchanged and checks Docker's UDP setting when present, local port 53, WARP policy/state and DNS/HTTPS reachability. `pub-e2e` temporarily runs the repository's candidate controller against real WARP, checks connectivity with pub enabled, then verifies that `off` restores the original mode, connection state and connectivity. It refuses an existing lease and requires a loaded supervisor whose installed controller can recover `warp+doh` leases; this compatibility update is a one-time prerequisite for testing the first migration. Failures return a non-zero exit code. These commands are explicit rather than automatic deployment prerequisites because the live test switches the machine's network. They do not apply to a work machine without WARP.

Mocked controller tests and isolated Ansible deployment tests run through `make test-scripts test-deploy`; the live gate catches host DNS conflicts that those tests cannot reproduce. Its HTTPS probe checks transport availability, not an authenticated Claude conversation, and results apply to the current network and host configuration.

Pub mode does not set application proxy variables or run a `gost` bridge. Local services such as the OTLP collector at `127.0.0.1:4317` therefore remain direct rather than being sent through a loopback HTTP proxy.

### Usage

When `claude` breaks on bad wifi:

```fish
pub on       # Start a WARP lease, or re-home an existing one onto this network.
pub off      # End the lease early and restore the previous WARP state.
pub status   # Show WARP state and the remaining lease time.
```

The lease is machine-wide rather than tied to one fish session. A LaunchDaemon registered in the system domain runs the controller as the owning user and reconciles it every minute, including after the terminal which enabled it exits and after GUI logout. Sleep time counts towards both the renewal window and the twelve-hour ceiling below — `launchd` misses a `StartInterval` firing while the system sleeps, so a lease that outlived its window closes on the first reconcile after the lid opens. A reboot ends the lease and restores the captured WARP mode and connection state when the daemon next runs.

The lease only renews while the machine stays on the network it was taken out on. Each reconcile derives a network signature — a SHA-256 over the default route's router address and the gateway's ARP hardware address, read locally through `/usr/sbin/scutil` and `/usr/sbin/arp` with no root, no Location Services and no network request. macOS redacts the SSID from unprivileged callers, so the gateway is what identifies the network; the primary interface only locates the route and its ARP entry, so moving between wifi and a dock behind the same router stays the same network. A matching signature extends the lease to thirty minutes from that moment and never past a twelve-hour ceiling fixed at activation. A different signature is tolerated once and closes the lease on the second consecutive reconcile, roughly two minutes after leaving. A signature that cannot be read at all — asleep, link down, mid-DHCP — neither renews the lease nor counts against it, so the lease ages out on its own expiry rather than being dropped during a wifi roam. `pub on` re-homes an existing lease onto the current network without moving the ceiling; once the ceiling is reached the lease closes, and a deliberate `pub on` starts a new one.

Transitions nobody typed are announced. When the reconciler closes a lease itself — expiry, the twelve-hour ceiling, a network change or a reboot — completes an interrupted restoration, or loses ownership to a manual mode change or to WARP policy, it posts a macOS notification through `launchctl asuser`, the documented bridge from the system-domain job into the GUI session that owns Notification Centre. Delivery is best effort: a notification that cannot be posted is a silent no-op and never changes the outcome of a lease operation. An operation whose stderr is a terminal posts nothing, because the same line is already on screen; an uneventful reconcile posts nothing at all.

Every new interactive fish shell prints one line whenever `~/.local/state/pub-lease/lease.json` exists, naming the phase the file actually records: active with the time remaining, activating, restoring, expired and awaiting the reconciler, or present but unreadable. The file's mere existence is not read as "the tunnel is on". The line parses the lease directly and never runs `pub-lease status` or `warp-cli`, whose two WARP daemon probes are far too expensive for every shell.

The controller is a self-contained Python 3.9+ standard-library program. The playbook verifies the macOS Command Line Tools interpreter before deploying or reloading the LaunchDaemon; no project virtual environment or third-party Python package is required at runtime.

A normal Ansible run for a profile that no longer manages Cloudflare WARP blocks new activations, boots out both the current LaunchDaemon and any legacy GUI LaunchAgent, restores any active lease, then removes their plist and the controller executable. The supervisor stops before the restoration so the sixty-second reconciler cannot re-enter halfway through it. If restoration fails, the supervisor, controller, and recovery metadata are retained for retry. Re-enabling the managed profile removes the block before deployment. Dev mode only reconciles its isolated debug tree and never changes the live supervisor or WARP state.

The controller keeps an immutable recovery snapshot beside its working lease metadata. If only the working file is damaged, `pub off` and the LaunchDaemon restore from that snapshot. If both files are unreadable, `pub off --force` disconnects a recognised pub tunnel and quarantines the metadata, but deliberately does not guess the lost previous WARP mode.

Changing the WARP mode manually ends controller ownership and leaves the selected mode unchanged. A manual disconnect in the lease mode pauses the tunnel without discarding the restoration snapshot; `pub on` reconnects it and `pub off` still restores the original state.

`pub on` captures the pre-lease connection state as the restoration intent. A `Connecting` status is given ten seconds to settle first. `Connected` and `Disconnected` are restored exactly; a degraded state (`Unable to connect`, or still `Connecting` after that budget) is reported on activation and later restored best-effort — the controller aims to reconnect but ends the lease even if the network still refuses, the reconnection is rejected outright, or the resulting status cannot be read, rather than holding the pub tunnel open forever. Restoring the mode itself, and confirming it afterwards, stays strict for every intent. `Registration Missing` and any status the controller does not recognise are refused outright.

`pub on` refuses to start while WARP forbids mode switching — the controller asks `warp-cli settings mode-switch-allowed` and reads a bare `true` as unlocked and a bare `false` as locked — because it could not guarantee restoration. Any other answer is an unreadable probe rather than a locked policy: the lease is retained, WARP is left alone and the operation fails, because a probe that cannot be classified must never be allowed to discard the only record of the mode to restore. If the policy really is locked during an active lease, the controller treats the policy as the new owner, leaves WARP unchanged, and removes its lease metadata instead of retrying forever. It leaves an advisory note behind, so a later `pub off` or `pub status` reports the mode that preceded the dropped lease and the mode WARP was actually left in — both read at the moment the lease was dropped, since an administrator may already have moved it — instead of claiming the mode is already off; nothing restores from that note. WARP's derived `always_on` setting reflects the current connection toggle and does not transfer ownership.

Interactive `pub on` and `pub off` operations wait up to ten seconds for another pub operation to release the controller lock, then report `another pub operation is already running` and exit 75 (`EX_TEMPFAIL`); the background reconciler does not wait. Activation makes up to twenty-five status probes and interactive restoration up to twenty, printing progress on stderr only when it is a terminal — stdout carries the result alone, so scripted callers can match it. Background restoration makes up to sixty probes in silence and retries on the next one-minute reconcile. Every `warp-cli` invocation has its own five-second timeout, so a stalled client cannot hold the controller lock indefinitely. The controller rotates `~/Library/Logs/pub-lease.log` after it grows beyond 1 MiB, retaining one `.1` copy. Quarantined metadata is retained for at least seven days and removed by a later locked operation.

The first interactive shell after this upgrade removes every universal proxy variable still pointing to the legacy `127.0.0.1:8080` endpoint, then disables that migration permanently. Unrelated proxy settings are preserved. A `gost` process left by an already-running old shell is no longer used; close that shell or restart the machine to retire it.

## OTLP Telemetry (otelbox edge)

A durable local OpenTelemetry collector — Ansible-deployed, `launchd`-supervised, no brew — sinks agent telemetry at `127.0.0.1:4317` (gRPC) / `:4318` (HTTP), buffers it on disk across outages, and forwards to one remote gateway with `deployment.environment.name={profile}` stamped on every record. Langfuse transcript plugins use the separate traces-only listener at `127.0.0.1:14318/api/public/otel/v1/traces`; only that pipeline adds `otelbox.telemetry.class=llm`.

Wired: Claude Code CLI (`OTEL_*` env in `~/.claude/settings.json`), Codex CLI/app (`[otel]` managed from `dot_codex`), and Antigravity through the `agy` wrapper's standard OpenTelemetry environment variables.

### Where the collector comes from

Nothing is built here. The binary is the published [`abrosimov/otelcol-otelbox`](https://github.com/abrosimov/otelcol-otelbox) artefact — one collector serving the workstation `edge` and the server roles deployed by `remote_server_setup`. That repository owns the component set, release pipeline and reference profiles; this one owns the deployed edge profile, secrets, supervisor and machine-local values.

Version 2.x loads one self-contained `edge.yaml`. The binary and profile are upgraded together; v1 `base.yaml` layering is deliberately unsupported. The pin lives in `devbox_packages.otelbox_edge.version` and nowhere else — `otelbox-edge-test.py` reads it from there rather than repeating the literal.

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

The three repository utilities are self-contained Python 3.9+ programs and use
only the standard library. They run with the system interpreter; the project
virtual environment is not a runtime dependency. External macOS commands are
still used only at their operating-system boundaries (`security`, `scutil`,
`launchctl`, and `openssl`).

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

## Drive Backup

A weekly LaunchAgent (`local.drive-backup`, Friday→Saturday night at 03:00) archives a set of directories — `~/.claude`, `~/.codex`, `~/.gemini`, plus any under `$AION_AUTOPOIESEON` — into the `drive` repository at `$AION_AUTOPOIESEON/drive/base`, then commits and pushes. The tool is the standalone uv project [`packages/drive-backup`](packages/drive-backup/README.md) (stdlib-only, Python 3.14), kept self-contained so it can move to its own repository.

**Switch it on per machine** by putting the list of directories in the local overlay; the playbook installs the agent only when this file exists, and removes it when it does not:

```sh
cp roles/devbox/files/.config/drive-backup/config.toml.example \
   roles/devbox/local/.config/drive-backup/config.toml
$EDITOR roles/devbox/local/.config/drive-backup/config.toml
make drive-backup-push     # or a full make personal / make work
make drive-backup-now      # optional: run once now; tail -f ~/Library/Logs/drive-backup.log
```

Layout in the repository: `<YYYY-MM>/<profile>_<name>_<YYYY-MM-DD>.tar.zst`, with the profile from `$MNEMOSYNE_PERISTASEOS`. Each run also commits `<YYYY-MM>/<profile>_backup_<YYYY-MM-DD>.log`, including runs that fail, so failures are visible from any clone. Only a failure that leaves no usable repository (missing, dirty, detached) stays local, in `~/Library/Logs/drive-backup.log`, with a desktop notification. Old archives are never deleted by the tool.

A directory with `busy` processes configured (e.g. a live `claude` session) is deferred and re-checked every 15 minutes for up to 3 hours, then archived anyway. The files are copied as they are at that moment, and the log records this as a warning.

Prerequisites in the drive repository: `*.tar.zst` must be LFS-tracked (`*.tar.zst filter=lfs diff=lfs merge=lfs -text` in `.gitattributes`), and the LFS filters must be configured (`git lfs install`). The tool refuses to commit an archive that would bypass LFS. It runs git with `core.hooksPath=/dev/null` and uploads LFS objects itself with `git lfs push`, so the global hooks path set up by this repository doesn't block uploads.

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
