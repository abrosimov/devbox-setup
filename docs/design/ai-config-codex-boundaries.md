# Codex configuration boundaries

Read-only assessment, 10 September 2026. No configuration changes, installations, client sessions, or remote application writes were performed. `codex --version` reported `codex-cli 0.153.4` from `/opt/homebrew/bin/codex`; it also warned that PATH aliases could not be created because the operation was not permitted. This is CLI version evidence, not a check of the desktop app's or IDE's bundled runtime.

## Verified native boundaries

**Layer precedence.** Highest first: command-line overrides; trusted project layers from root towards current directory; selected profile file; user config; cloud-managed defaults; Unix `/etc/codex/config.toml`; built-in defaults. User configuration remains `~/.codex/config.toml`. Project trust gates project config, hooks and rules, not user/system layers. Defaults and enforced requirements are different mechanisms. [Config basics](https://learn.chatgpt.com/docs/config-file/config-basic), retrieved lines 823–850.

**Profiles and locations.** Current profiles are `$CODEX_HOME/<name>.config.toml` selected with `--profile <name>`. Since 0.134.0, the old `[profiles.<name>]` tables and top-level `profile` selector are no longer supported. Project configuration ignores `otel`, `notify`, provider/auth-routing keys and profile selectors. `CODEX_HOME` also contains authentication, history and other user state, so replacing it to select portable settings changes more than configuration. [Advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced), retrieved lines 826–884. Installed CLI 0.153.4 is newer than that documented migration boundary; no repository legacy profile table was found in the inspected Codex source.

**Hooks.** `hooks.json` and inline `[hooks]` are supported beside active layers. Hooks from different sources accumulate; higher-precedence hooks do not replace lower ones. Both representations in one layer load together and generate a warning. User/plugin hooks require review of their current definition hash; changed definitions are skipped until trusted. `/hooks` manages that trust and enablement. Managed hooks have a different policy/trust status. This is a behavioural difference, not just a different storage location. [Hooks](https://learn.chatgpt.com/docs/hooks), retrieved lines 846–871, 1097–1112.

**Native writers and reload.** App-server `config/value/write` and `config/batchWrite` write user `config.toml`; the latter is atomic. `config/read` resolves on-disk layers. The API separately provides `skills/config/write` and `config/mcpServer/reload`; MCP reload queues refreshes for loaded threads. `mergeStrategy` examples show `replace`/`upsert` for writes, but they do not establish general file-layer array or deletion semantics. [App Server](https://learn.chatgpt.com/docs/app-server), retrieved lines 1084–1100, 2106–2164.

**Client compatibility.** App agents share configuration with CLI and IDE. IDE `chatgpt.*` editor settings remain outside `config.toml`. TUI controls expose model/reasoning, permissions, personality, features and appearance; some settings can be saved while others are session-only. `/debug-config` exposes layer provenance, and `--strict-config` rejects unknown keys. A supported CLI profile flag does not prove that every app/IDE launch route selects the same profile. [Developer settings](https://learn.chatgpt.com/docs/developer-settings?surface=ide), retrieved lines 843–928.

**MCP.** User/project MCP definitions are shared by desktop app, CLI and IDE. Native add/login flows may persist configuration, including OAuth callback information. App and IDE documentation explicitly instructs restarting the relevant client component after saving a server. Plugin-provided transport definitions belong to the plugin; user config may still control plugin-server enablement and tool policy. [MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), retrieved lines 840–887, 921–937, 1003–1012.

**Agents.** Standalone `~/.codex/agents/*.toml` and project `.codex/agents/*.toml` are native discovery locations. Required fields are `name`, `description`, `developer_instructions`; other supported config settings can override inherited session settings. Custom-file model/effort values override resolved defaults; omitted settings inherit. Parent live permission overrides are reapplied to spawned children. Subagent activity is supported across app, CLI and IDE, though UI details differ. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), retrieved lines 815–825, 932–985.

**Reference limits.** `skills.config` is a path-based array of enablement overrides; `mcp_servers.<id>.enabled=false` disables without deleting the server definition. Hook matcher groups and handlers are arrays. No `hooks.state` entry or `otel.resource_attributes` entry was found in the fetched reference. Absence from this page alone does not prove runtime rejection. [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), retrieved lines 939–944, 961–963, 1103–1105.

## Complete manifest ledger

M = `roles/devbox/files/dot_codex/config.ai-config.json`; T = `roles/devbox/files/dot_codex/config.toml.j2`. All 22 manifest rules are enumerated below. Present means the current template supplies a value. Proposed ownership is a design candidate, not an accepted user decision; in particular, model and reasoning may remain fixed if the user wants them fixed.

| Rule | Recorded scope / M line | Present / T line | Existing or native writer boundary | Ownership candidate, requiring acceptance |
| --- | --- | --- | --- | --- |
| `personality` | shared / 6 | pragmatic / 5 | ai-config plus native personality controls | repository default or native preference; choose one persistent owner |
| `model` | shared / 10 | gpt-6-astra / 6 | ai-config plus model picker/run overrides | may remain repository-fixed; do not presume runtime-only |
| `model_reasoning_effort` | shared / 14 | medium / 7 | ai-config plus model/reasoning controls | same explicit decision as model |
| `service_tier` | shared / 18 | default / 8 | ai-config; session/client tier selection can differ | fixed default or user-controlled preference |
| `sandbox_mode` | shared / 22 | workspace-write / 9 | ai-config plus native permission controls/requirements | repository default; enforcement is separate |
| `features` | shared / 26 | hooks, js_repl, memories / 28–31 | broad subtree also admits native feature controls | explicit owned feature allowlist preferable to accidental ownership of future features |
| `hooks` | shared / 30 | six event arrays / 33–39 | repository definitions; native trust lives below same table | separate definition artefact is possible, with one-time migration and trust review |
| `sandbox_workspace_write` | shared / 34 | network_access=true / 12–13 | broad subtree can include machine paths and session permissions | split portable flags from local writable roots if those appear |
| `shell_environment_policy` | local-state / 38 | absent | host environment/security configuration | leave native/local; never infer values from another host |
| `otel` | shared / 42 | six fields / 15–22 | ai-config; user-level host integration | repository-owned integration, with parameterised host/environment values |
| `otel.environment` | environment / 46–48 | devbox_active_profile / 16 | Ansible profile binding | retain explicit environment binding |
| `plugins` | shared / 51 | eleven enabled declarations / 41–74 | ai-config declarations plus native plugin commands/UI | portable desired plugin list and native enablement can collide; choose writer per plugin/field |
| `marketplaces` | runtime / 55 | absent | native marketplace commands invoked by provisioning | native materialisation; desired pins belong to Ansible data |
| `desktop` | local-state / 59 | absent | desktop preference controls | native/local |
| `tui` | shared / 63 | absent | native appearance controls can save preferences | classify desired portable appearance separately if needed |
| `tui.model_availability_nux` | runtime / 67 | absent | native onboarding state | native/runtime |
| `tool_suggest` | shared / 71 | disabled_tools array / 25–26 | ai-config; UI writer not established in this inspection | repository desired suppression list or native preference; explicit decision |
| `skills.config` | shared / 75 | absent | native skills/config/write and path enablement | native path state unless a portable identifier/path binding is defined |
| `mcp_servers` | runtime / 79 | absent | native MCP/app setup; may contain local executable and callback paths | native/runtime for current setup; portable named servers could be separately owned if requested |
| `projects` | local-state / 83 | absent | native project trust and machine paths | native/local |
| `notify` | local-state / 87 | absent | machine notification commands; exact local writer unverified | native/local |
| `notice` | runtime / 91 | absent | native notices/onboarding | native/runtime |

Manifest scope is actual repository policy, not proof of the vendor's sole writer. Longest matching prefix wins (`scripts/ai_config/core.py:127–147`), so broad shared tables cover future descendants unless an explicit exception applies. Unclassified fields stay unclassified rather than automatically portable (tests: `tests/scripts/test_ai_config_codex_manifest.py:286–294`).

### `hooks.state` exception

`scripts/ai_config/adapters.py:51–62` derives runtime rules only for four-component paths `hooks.state.<identifier>.enabled` and `.trusted_hash` seen in base/live snapshots. The Codex adapter blocks the entire `hooks.state` prefix from inherited broad rules (`:81–88`); unknown descendants therefore do not silently inherit `hooks=shared`. This is more precise than labelling the whole hooks table portable. Tests explicitly preserve these leaves and demonstrate source-path/event/index identifiers (`tests/scripts/test_ai_config_codex_manifest.py:100–128,169–188`). Moving definitions from config.toml to hooks.json must not copy or manufacture trust records. New source identities/hashes need native review; exact migration behaviour has not been run.

## Complete current source inventory

The template has exactly 11 top-level keys: the five scalar rows `personality`, `model`, `model_reasoning_effort`, `service_tier`, `sandbox_mode`, and six tables `sandbox_workspace_write`, `otel`, `tool_suggest`, `features`, `hooks`, `plugins`.

All current child fields:

- `sandbox_workspace_write.network_access=true` (T12–13).
- `otel.environment`, `log_user_prompt=true`, `exporter.otlp-grpc.endpoint=http://127.0.0.1:4317`, `trace_exporter=none`, `metrics_exporter.otlp-grpc.endpoint` at the same loopback endpoint, and `resource_attributes[otelbox.telemetry.class]=llm` (T15–22). T21 records an unresolved upstream dependency for resource attributes; do not present that attribute as proven effective.
- `tool_suggest.disabled_tools`: one `{id=github@openai-curated-remote,type=plugin}` item (T25–26).
- `features.hooks=true`, `features.js_repl=false`, `features.memories=true` (T28–31).
- Hook events: `PostToolUse`, `PreCompact`, `PreToolUse`, `SessionEnd`, `SessionStart`, `Stop`. Each calls `~/.codex/bin/.venv/bin/python ~/.codex/bin/universal_logger.py <event>`; all handlers are command hooks, PostToolUse is asynchronous, and Pre/PostToolUse have `.*` matchers (T33–39).
- Eleven `plugins.<id>.enabled=true`: browser@openai-bundled; codex-app-tools@openai-bundled; documents@openai-primary-runtime; pdf@openai-primary-runtime; presentations@openai-primary-runtime; sites@openai-bundled; spreadsheets@openai-primary-runtime; superpowers@openai-curated; template-creator@openai-primary-runtime; tracing@codex-observability-plugin; visualize@openai-bundled (T43–74).

All 28 standalone agent files parse as TOML. Each has exactly `name`, `description`, `developer_instructions`; eight additionally set `sandbox_mode=read-only`. None sets model or reasoning. Example implementation adapter: `roles/devbox/files/dot_codex/agents/software-engineer-python.toml:1–20`; example restrictive adapter: `agents/code-reviewer.toml:1–5`. Inventory authority is `roles/devbox/defaults/main/codex.yml:26–54`. These are separate owned files, not entries in the 22-rule config manifest.

## Provisioning and runtime artefact boundary

`roles/devbox/tasks/install_codex_configs.yml` resolves destination `.codex` and `.agents/skills` from the dotfiles root/HOME (:4–24), applies config through `scripts/ai-config apply codex --profile <devbox-profile>` (:39–62), then deploys Langfuse configuration (:64–69), global AGENTS.md (:71–76), agents (:78–87), selected skill directories (:89–123), bin scripts (:125–145), and the pinned hooks venv (:147–168). The Ansible `--profile` argument belongs to **ai-config**, not to Codex's native profile selector. No native `<name>.config.toml` deployment is present here.

Native Codex marketplace/plugin commands perform discovery/add/install/verification (:170–350). `roles/devbox/defaults/main/codex.yml:56–66` records the desired tracing marketplace commit and plugin version. The broad plugins table is nevertheless shared in the manifest, so replacing ai-config with whole-file ownership would still collide with a native writer.

`roles/devbox/files/dot_codex/bin/reconcile_config.py:1–6,101–119` is an older top-level replacement merger still present in the deployed bin tree. It is **not** the current configuration task: `tests/deploy/test_ai_config_ansible_codex.py:110` asserts that the active task does not call it. Do not use its whole-table semantics to describe current ai-config behaviour.

Keep `.codex/config.toml` native writable state separate from repo assets in `.codex/agents`, `.codex/bin`, `.codex/AGENTS.md`, and `.agents/skills`. Authentication/keychain, sessions/history, logs, caches, memories, state databases, plugin runtime paths, marketplace timestamps and local MCP paths remain non-portable by current repository documentation (`roles/devbox/files/dot_codex/README.md:30–36`). Hook trust is deliberately not automated (:47–50). Langfuse runtime JSON is independently templated and should not be confused with native Codex config.

## Decision implications and unresolved verification

1. A default layer under `/etc/codex/config.toml` can separate files but has lower precedence than native user state. It cannot implement “repository always wins” without a different policy mechanism. Moving personal hooks there also changes their trust classification; this is not a mechanical file relocation.
2. A dedicated native profile can separate selected CLI defaults from the mutable user file, but requires explicit selection and does not establish app/IDE selection parity. Project layers cannot carry this repository's OTel block. Therefore neither is yet a universal replacement for all current shared fields.
3. Separating hooks into one `hooks.json` and retaining agent/skill/script artefacts outside config is a plausible narrower simplification. Existing inline hooks must be removed in a controlled migration to avoid duplicates; trust must remain user-owned. This is a proposal, not an authorised migration.
4. The unresolved user choice is which preferences are fixed desired configuration: model, reasoning, tier, personality, appearance, feature flags and plugin enablement. Their native editability does not prove they should become runtime-only.
5. Generic cross-layer array replacement/concatenation, deletion/tombstones, and whole-config hot reload were not established by the fetched official pages. Hook accumulation and MCP refresh are established exceptions. Before relying on layer splitting, verify exact installed-version behaviour with isolated, authorised fixtures covering `skills.config`, `tool_suggest.disabled_tools`, hooks, plugin enablement, nested tables, absent keys and deletions. No such client-starting experiment was run in this read-only subtask.
6. CLI 0.153.4 does not establish desktop or IDE runtime version parity. No native writer, in-session reload, profile-selection, hook trust migration or current `resource_attributes` effectiveness was tested live.

## Repository source navigation

Return to the [ownership and composition study](ai-config-ownership-and-composition.md). Source labels use repository-relative paths; `ai_config/` abbreviates `scripts/ai_config/`. Line numbers refer to commit `8553b576f060209a729e1062c0a7ce5fefb99f25`.

- [Reconciler modules](../../scripts/ai_config/) and [behavioural tests](../../tests/scripts/).
- [Codex manifest](../../roles/devbox/files/dot_codex/config.ai-config.json), [source](../../roles/devbox/files/dot_codex/config.toml.j2), [assets](../../roles/devbox/files/dot_codex/) and [deployment](../../roles/devbox/tasks/install_codex_configs.yml).
