# Codex configuration

`dot_codex` is the portable, repo-owned part of `~/.codex`.

`config.toml.j2` is reconciled with the live `~/.codex/config.toml` through
`scripts/ai-config`. The manifest classifies portable, environment-bound,
machine-local, and runtime-owned fields; the repository becomes the source of
truth for the portable projection after initialisation.

Currently managed:

- service tier and sandbox mode (`personality` is no longer set: Codex ignores
  Friendly/Pragmatic overrides, so `ai-config apply codex` removes a live value
  that matches the last applied baseline);
- `[features]` (`memories` and hooks; `js_repl` is deliberately not enabled);
- `[sandbox_workspace_write]`;
- `[tui]` in inline rich-output mode: the alternate screen and raw-output
  startup are disabled so the terminal retains scrollback and native text
  selection, including Kitty's copy-on-select behaviour;
- `[otel]`, with the active devbox profile as the environment, semantic log
  export and metrics enabled, and noisy native Rust trace export disabled;
- selected plugin declarations captured during bootstrap;
- the vendored Langfuse tracing hook and its loopback-only runtime config;
- hook trust for the hooks declared here (see below);
- the blocking `Stop` hook `bin/stop_user_actions_guard.py`, a byte-identical
  copy of the Claude hook (a test enforces parity), which enforces the final
  "What I need from you" section;
- global working agreements in `AGENTS.md`;
- all 29 Codex-native custom-agent adapters under `agents/*.toml`;
- the allowlisted shared skills installed under `~/.agents/skills`, including
  the self-contained FPF/NSTD reference package and the inventory-first
  `diagnose-and-repair` workflow.

`model` and `model_reasoning_effort` have `preference` scope: existing local values
are preserved, and repository defaults (`gpt-5.6-sol` and `medium`) are applied only
when the respective field is absent. Switch to Astra locally when needed; later
apply or reconcile operations preserve that choice. Apply, reconcile, and live
bootstrap never capture these preferences
into the repository or portable baseline. Changing the repository default affects
only configurations without a local value. Validation requires a non-empty string;
supported values and model compatibility remain the Codex client's responsibility.
This concerns the user config file; native profile or session overrides can still
change the effective value.

Existing baselines migrate from every earlier Codex manifest the reconciler
recognises: the original shared model/reasoning version, the reasoning-preference
version, the model-and-reasoning-preference version, and the `apps` version. A
migration removes only newly demoted preference fields and keeps every other
baseline field; a field that joined as shared (`model_reasoning_summary`,
`hide_agent_reasoning`) is absent from the migrated baseline, so its repository
value applies as a repository change. Other manifest digest changes keep the
existing reinitialisation behaviour.

`model_reasoning_summary = "detailed"` makes Codex request reasoning summaries so
they are recorded in the session rollouts under `~/.codex/sessions/`;
`hide_agent_reasoning = true` keeps them out of the TUI and `codex exec` output.

`AGENTS.md` routes bounded implementation, planning, review, and test work to
the matching custom agents when delegation is useful. Go implementation uses
the shared `go-engineer` workflow and formats changed files with
`goimports -local <module-path>`.

Intentionally not copied from a workstation:

- authentication and session state;
- trusted project paths;
- plugin caches, marketplace timestamps, and ChatGPT app metadata;
- MCP entries containing app-version-specific or machine-local paths;
- history, logs, memories, state databases, and telemetry queues.

## Langfuse tracing hook

The `Stop` hook of `langfuse/codex-observability-plugin` is built from a pinned
upstream commit and committed as `bin/vendor/langfuse-codex/index.mjs`; it is not
installed as a Codex plugin. `config.toml.j2` declares it directly and runs it with
the keg-only Homebrew Node 22 (`/opt/homebrew/opt/node@22/bin/node`), and the
"Sync Codex bin directory" task deploys it to `~/.codex/bin/vendor/`. The pin, the
rebuild procedure and the update steps are in `bin/vendor/README.md`.

The hook reads `~/.codex/langfuse.json`, rendered from `langfuse.json.j2`, and sends
OTLP/HTTP traces to `http://127.0.0.1:14318` with non-secret sentinel credentials;
real Langfuse project credentials remain on the remote gateway.

Machines provisioned before the hook was vendored still carry the marketplace
install. `install_codex_configs.yml` removes `tracing@codex-observability-plugin`
and the `codex-observability-plugin` marketplace when it finds them, because the
plugin's own `Stop` hook would otherwise upload every turn a second time.

## Plugins

`devbox_codex_plugin_marketplaces` and `devbox_codex_plugins` in
`roles/devbox/defaults/main/codex.yml` list the Git marketplaces and the plugins
the playbook installs. `install_codex_configs.yml` adds a marketplace that is not
configured yet (`codex plugin marketplace add`), refreshes the marketplace of a
plugin that is not installed yet (`codex plugin marketplace upgrade`), installs
it (`codex plugin add`) and fails the run if a listed plugin is not installed and
enabled afterwards. A converged run only lists.

`codex plugin add` writes `[plugins."<name>@<marketplace>"] enabled = true` into
`config.toml`, and the reconcile owns the `[plugins]` table, so every listed
plugin is also declared in `config.toml.j2`. The `[marketplaces]` table it writes
is runtime state and is not reconciled.

Prefer a plugin's Git marketplace to OpenAI's remote catalog
(`openai-curated-remote`): the remote catalog refuses to install without a
ChatGPT login.

## Hook trust

Codex runs a hook only when it is enabled *and* its recorded `trusted_hash`
matches the hash Codex recomputes from the live definition. A mismatch resolves
to trust status `Modified` and the hook is dropped from the dispatch list — no
error, no log line. A fresh machine, or any edit to a hook command, therefore
disables every hook this repository provisions until a human grants trust in the
`/hooks` TUI. This is how Langfuse traces from Codex went missing.

`scripts/codex-hook-trust.py` (over the stdlib-only `scripts/codex_hook_trust/`
package) closes that gap as the last step of `install_codex_configs.yml`. It
drives `codex app-server` over JSON-RPC: `hooks/list` reports each discovered
hook's `currentHash` and `trustStatus`, and `config/batchWrite` upserts
`hooks.state."<key>".trusted_hash` into `~/.codex/config.toml`. The hash is read
back from the same binary that later verifies it rather than recomputed here, so
the scheme survives upstream changes to the hashing shape.

Only hooks this repository declares are eligible:

- command hooks whose event and command appear in `config.toml.j2`'s `[hooks]`
  block and whose `sourcePath` is the live `config.toml`;
- hooks belonging to a plugin passed via `--plugin`. Provisioning passes none: the
  only hooks it deploys are the ones in `config.toml.j2`.

Anything else is **refused** and fails the play — blanket-trusting whatever
`hooks/list` returns would auto-trust any hook that got injected. A hook the
repository declares but `hooks/list` never reports also fails the play: the
configuration that should carry it is not in effect. A trusted-but-disabled hook
is reported on stderr and left alone; disabling is a deliberate act in the TUI,
granting trust is not.

**A running Codex session caches its configuration.** Newly granted trust takes
effect for the *next* Codex process only — quit and relaunch (or start a new
`codex` invocation) before expecting the hooks to fire.

To audit without writing:

```sh
uv run --no-project --python '>=3.12' scripts/codex-hook-trust.py \
  --check --fail-on-drift
```

`--check` alone reports drift and exits `0`; `--fail-on-drift` turns pending
trust into a non-zero exit for a periodic gate. Exit codes follow `sysexits`:
`64` bad invocation, `69` no reachable app-server, `76` unrecognised protocol
shape, `78` a trust state the repository refuses to accept.

`hooks.state` stays out of ai-config's way: the Codex adapter classifies
`hooks.state.<key>.{enabled,trusted_hash}` as `runtime` scope and blocks every
other path under `hooks.state`, so `ai-config apply codex` preserves granted
trust verbatim while still owning the `[hooks]` definitions above it.

## First bootstrap

When Codex has already created `~/.codex/config.toml` but this profile has no
reconciliation base, preview the live-derived baseline:

```sh
scripts/ai-config bootstrap codex --from-live
```

The preview reports `capture`, `keep-repo`, `preserve-local`, and
`ignore-runtime` for every relevant field, emits a `preview-token`, and writes
nothing. After reviewing it, perform the same operation with that exact token:

```sh
scripts/ai-config bootstrap codex --from-live --write \
  --preview-token 'sha256:...'
```

The write is pull-only: it updates the repository and creates the first base,
but does not alter `~/.codex/config.toml`. It is rejected if any reviewed input
changed after the preview, or when a base already exists. Review the resulting
`diff`, then use `apply --check` and `apply` for repo-only settings such as
hooks. Subsequent conflicts use `reconcile`.

Portable skills continue to live in `dot_ai` and are selected for Codex by
`defaults/main/codex.yml`. Claude Markdown agents and the shared authority
protocol are not copied verbatim: Codex-native adapters live here and inherit
the parent session's model and permission settings unless an agent explicitly
narrows itself to read-only mode.
