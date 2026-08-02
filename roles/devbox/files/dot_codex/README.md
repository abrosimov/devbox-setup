# Codex configuration

`dot_codex` is the portable, repo-owned part of `~/.codex`.

`config.toml.j2` is intentionally a TOML fragment. The deploy task renders it
for the active profile and `bin/reconcile_config.py` merges it into the live
`~/.codex/config.toml`. Keys and complete tables present in the fragment are
repo-owned. Other keys and tables remain app-owned and survive every deploy.

Currently managed:

- model, reasoning, service tier, personality, and sandbox mode;
- `[features]` (`memories` only; `js_repl` is deliberately not enabled);
- `[sandbox_workspace_write]`;
- `[otel]`, with the active devbox profile as the environment.
- global working agreements in `AGENTS.md`;
- all 28 Codex-native custom-agent adapters under `agents/*.toml`;
- the allowlisted shared skills installed under `~/.agents/skills`, including
  the self-contained FPF/NSTD reference package.

Intentionally not copied from a workstation:

- authentication and session state;
- trusted project paths;
- plugin caches, marketplace timestamps, and ChatGPT app metadata;
- MCP entries containing app-version-specific or machine-local paths;
- history, logs, memories, state databases, and telemetry queues.

Portable skills continue to live in `dot_ai` and are selected for Codex by
`defaults/main/codex.yml`. Claude Markdown agents and the shared authority
protocol are not copied verbatim: Codex-native adapters live here and inherit
the parent session's model and permission settings unless an agent explicitly
narrows itself to read-only mode.
