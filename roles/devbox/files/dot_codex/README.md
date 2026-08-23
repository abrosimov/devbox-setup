# Codex configuration

`dot_codex` is the portable, repo-owned part of `~/.codex`.

`config.toml.j2` is reconciled with the live `~/.codex/config.toml` through
`scripts/ai-config`. The manifest classifies portable, environment-bound,
machine-local, and runtime-owned fields; the repository becomes the source of
truth for the portable projection after initialisation.

Currently managed:

- model, reasoning, service tier, personality, and sandbox mode;
- `[features]` (`memories` and hooks; `js_repl` is deliberately not enabled);
- `[sandbox_workspace_write]`;
- `[otel]`, with the active devbox profile as the environment;
- selected plugin declarations captured during bootstrap;
- global working agreements in `AGENTS.md`;
- all 28 Codex-native custom-agent adapters under `agents/*.toml`;
- the allowlisted shared skills installed under `~/.agents/skills`, including
  the self-contained FPF/NSTD reference package and the inventory-first
  `diagnose-and-repair` workflow.

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
