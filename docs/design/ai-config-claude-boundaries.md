# Claude Code configuration boundary

Repository evidence: `8553b57`, inspected 10 September 2026. The installed executable reported `2.1.247 (Claude Code)` through `claude --version`. No user configuration, credentials, session files or application-owned stores were read. Current documentation describes some releases newer than the installed executable; documentation is not installed-runtime proof.

## Delta, 21 September 2026 — rendering replaced the profile binding

The conclusions below stand. Three of the facts they rest on no longer hold, and the section that records the invariant now describes a different mechanism.

1. **The repository source is a Jinja template named `settings.json.j2`.** `scripts/ai-config` renders it against `roles/devbox/defaults/main/*.yml` overlaid by `profiles/<profile>.yml`, using `StrictUndefined`, in the playbook path and the standalone `make claude-diff` / `claude-pull` path alike. Rendering deliberately did not move into Ansible: those two paths invoke the reconciler directly and would otherwise diverge from the playbook.
2. **The `profile:` and `env:` binding providers are gone; the Claude manifest declares no binding at all.** Rows 30 and the former `env.LANGFUSE_USER_ID` rule were deleted — their values are now ordinary Jinja. The Keychain and home providers remain, because a secret or a machine path must never be materialised into a rendered artefact. `scope: "environment"` therefore now means "resolved from a machine-local store at apply time", and no current rule uses it.
3. **The invariant of row 30 — "Live resolved value must not become the portable source declaration" — is no longer enforced per field.** It holds automatically for every leaf that a template expression produced. Provenance is decided by rendering the source twice, once against the real variables and once against type-preserving probe values, and taking every leaf whose value differs (including a leaf only one render produces). Such a leaf is classified `apply-repo` ahead of the base-state, capture and ordered-set branches, and is reported as `templated` in `diff` output. Coverage: `tests/scripts/test_ai_config_templating.py`.
4. **A consequence to keep in view:** the *unrendered* source is the write-back base for a capture, so it has to stay parseable. That confines Jinja to value positions in both the JSON and the TOML sources.

The manifest now holds **15 rules**. The inventory below lists 14 of them: the two Langfuse rows are gone, and `hooks` was added after this document and never listed.

## Conclusion

The existing reconciler already composes repository settings, profile bindings and preserved application fields into one user settings file. Its `shared` scope is a synchronisation contract, not an authoritative defaults layer. Native Claude scopes do not supply a documented second, lower-priority personal defaults file below user settings. `--settings` is an override, and managed fragments enforce organisational policy. A useful split therefore needs an explicit ownership and deletion contract, not merely several source files.

The strongest repository-specific concern is that ownership is broad: every descendant of `env`, `enabledPlugins`, `extraKnownMarketplaces`, `permissions`, `sandbox` and `tui` inherits shared scope unless a more specific rule overrides it. Native UI or CLI writes within those families can become changes requiring capture decisions. Conversely, genuinely new top-level application settings remain unknown and block the entire settings transaction.

## Current repository composition

- `scripts/ai_config/adapters.py` maps the Claude repository source `roles/devbox/files/dot_claude/settings.json.j2`, user destination `.claude/settings.json`, and `settings.ai-config.json`. This is one source document and one destination, not a fragments loader. `load_repository_document` parses it twice — unrendered, which is the write-back base, and rendered, which is what reconciliation compares.
- `scripts/ai_config/model.py:129` flattens non-empty objects into leaf paths. Arrays and empty objects remain leaf values. `scripts/ai_config/core.py:131` applies the longest matching path rule.
- `scripts/ai_config/core.py:207` classifies missing rules as unknown, local/runtime paths as preserved, and divergent shared paths by a three-way base/repository/live comparison. A live-only edit becomes `capture-live`; a divergent two-sided edit becomes conflict.
- `scripts/ai_config/resolution.py:124` does not let `apply` choose a side for capture/conflict/existing-file initialisation. `scripts/ai_config/service.py:338` blocks all writes for unknown paths before resolution; `service.py:355` blocks when decisions remain required.
- `scripts/ai_config/bindings.py` resolves Keychain and home bindings only. The Claude manifest declares neither, so binding resolution is a no-op for this engine; per-profile values come from the render instead.
- `roles/devbox/tasks/install_configs.yml:112` invokes `ai-config apply claude` with home/profile/check arguments and treats any non-zero result as failure. `roles/devbox/tasks/main_darwin.yml:70` performs this installation before `apply_configs.yml`.
- Later tasks add marketplaces, install plugins and enable plugins through native CLI commands: `roles/devbox/tasks/apply_configs.yml:127`, `:206`, `:248`. They are additional writers, separate from the reconciler. A successful native addition outside the previously reconciled shared projection can therefore create subsequent drift; whether it has done so on this host was not inspected.

## Complete manifest inventory and ownership candidates

All references in the first column are to `roles/devbox/files/dot_claude/settings.ai-config.json`. “Candidate” is a proposed boundary, not a change to accepted ownership. Repo presence refers only to the current tracked settings source.

| Rule and line | Current contract / repo presence | Candidate ownership and mutable writer |
| --- | --- | --- |
| `autoMemoryEnabled`, 6 | Shared; present | Personal preference, optionally a portable default. Keep an explicit user override route. Repository/manual edits are evidenced; exact installed UI write behaviour was not tested. |
| `enabledPlugins`, 10 | Shared subtree; present | Separate the required plugin set from discretionary personal choices. Native plugin installation/enable/disable and Ansible are writers. Removing a required plugin from the manifest does not inherently uninstall it. |
| `env`, 14 | Shared subtree; present | Manage named portable toolchain/cache/telemetry variables; leave unrelated application/private variables outside repository ownership. The current blanket rule admits every added descendant as shared. `LANGFUSE_TRACING_ENVIRONMENT` and `LANGFUSE_USER_ID` are covered by it: they are Jinja in the source, so provenance — not a rule of their own — keeps a live value out of the declaration. |
| `extraKnownMarketplaces`, 18 | Shared subtree; present | Manage declared marketplace identities; distinguish optional user additions and CLI registry/cache state. Ansible marketplace registration and explicit user edits are distinct operations. |
| `model`, 26 | Shared; absent | Personal model choice or explicit portable default, depending on authority decision. Native `/model` is a documented writer; absence from source does not imply application state. |
| `permissions`, 30 | Shared subtree; present | Explicitly separate durable permission policy/defaults from user decisions. Currently all unlisted descendant keys inherit shared ownership; `defaultMode` is present. |
| `permissions.allow`, 34 | Shared ordered-set; present | Portable approved rules plus deliberately retained user additions, with an explicit revocation model. Saved standing approvals are normally project-local in current documentation, not evidence that every user allow entry is application-generated. |
| `permissions.deny`, 39 | Shared ordered-set; present | Durable restrictions; define who may remove a rule. Native cross-scope deny semantics differ from this reconciler's set reconciliation. |
| `permissions.additionalDirectories`, 44 | Shared ordered-set; absent | Machine/workspace grants are candidates for local ownership or named bindings. Do not classify all future entries as portable simply because this rule exists. |
| `sandbox`, 49 | Shared subtree; present | Separate selected sandbox choices from host paths and network exceptions. Domain/excluded-command arrays are presently atomic in reconciliation, unlike permission arrays. |
| `skipAutoPermissionPrompt`, 53 | Shared; present | Unknown product contract from the consulted current primary pages. Do not rename, remove or reclassify based only on its name. |
| `skipWorkflowUsageWarning`, 57 | Runtime; absent | Existing runtime exception. Exact product semantics and writer remain unverified; preserve under current contract until established. |
| `statusLine`, 61 | Shared subtree; present | Portable helper definition with machine installation binding where necessary; explicit manual edits are another possible writer. |
| `tui`, 65 | Shared; present, scalar `fullscreen` | Personal UI preference or portable default. The source is scalar, so there is no current subtree granularity to split. Exact installed persistence behaviour was not exercised. |

The table above covers **14 of the 15 manifest rules** — `hooks`, added later, is the omission — against **9 top-level keys in the current settings source**. The next inventory accounts for every source key independently of manifest declarations.

| Repository top-level key | Source location | Current material / split implication |
| --- | --- | --- |
| `env` | `settings.json.j2:2` | Toolchain choices, cache paths, OTLP configuration, local Langfuse bridge parameters and two profile-dependent Jinja expressions. Values are repository-recorded; this does not establish that future similarly named values are non-secret. |
| `permissions` | `settings.json.j2:33` | `allow`, `deny`, `defaultMode`. `additionalDirectories` is not present. |
| `statusLine` | `settings.json.j2:399` | Command helper at `~/.claude/bin/statusline.py`. Installation of the helper and configuration of its path must remain coherent. |
| `enabledPlugins` | `settings.json.j2:403` | Five entries: three official LSP plugins and two Anthropic skills plugins. Native installation/enabling also occurs outside ai-config. |
| `extraKnownMarketplaces` | `settings.json.j2:410` | `anthropic-agent-skills` points to the `anthropics/skills` GitHub source. |
| `sandbox` | `settings.json.j2:418` | Enablement, automatic sandbox permission choice, unsandboxed allowance, network domains/local binding, weaker network isolation and excluded commands. |
| `autoMemoryEnabled` | `settings.json.j2:535` | Explicit false. |
| `skipAutoPermissionPrompt` | `settings.json.j2:536` | Explicit true; consulted documentation did not establish its contract. |
| `tui` | `settings.json.j2:537` | Explicit `fullscreen`. |

## Native sources, precedence and mutability

**Settings documentation facts.** User settings cover all projects on one machine; shared project settings belong to a project; project-local settings are personal to that project; managed settings are organisational. Precedence is managed, command-line settings, project-local, project, user. Lists generally combine rather than replace lower lists. `/config` writes selected preferences; `/model` normally saves a default. Settings-file changes, including permissions and hooks, are generally watched; model/effort edits require the corresponding command or a new session. The application also owns `.claude.json` for authentication, MCP and local/global state. `/status` confirms loaded sources, not every key's provenance. These are current documentation facts; installed 2.1.247 was not exercised against them. [Settings files and precedence](https://code.claude.com/docs/en/settings#settings-precedence), [reload section](https://code.claude.com/docs/en/settings#when-edits-take-effect).

**CLI documentation facts.** `--settings` accepts one JSON file or inline JSON; supplied values override file settings for that session and omissions retain lower values. The referenced file must be regular and at most 2 MiB. `--setting-sources` selects `user`, `project`, and `local`; it is not an ordered fragment list. `--strict-mcp-config` limits MCP input to explicit configuration, subject to managed controls. No documented arbitrary ordered chain of user-default fragments was found in these CLI options. A wrapper carrying `--settings` therefore changes precedence and covers only launches routed through it. [CLI reference](https://code.claude.com/docs/en/cli-reference).

**Managed fragment facts.** `managed-settings.d/*.json` is a system policy facility. The main file loads first, then non-hidden JSON fragments alphabetically. Scalars use later values, arrays deduplicate, and objects merge recursively; named marketplace and managed-MCP entries replace whole entries. On macOS the directory is below `/Library/Application Support/ClaudeCode/`. These settings rank above personal and command-line choices. That makes the mechanism inappropriate as a substitute for overridable personal defaults without an explicit change in authority. [Deploy managed settings](https://code.claude.com/docs/en/managed-settings#split-a-file-based-policy-across-teams).

**Permission facts.** Deny is evaluated before ask, then allow; a narrower allow cannot bypass a matching deny. A deny from one settings scope still constrains allowances elsewhere. Project allow rules and extra directories have workspace-trust requirements. Consequently, putting an empty list or an allow exception in a higher source cannot be treated as revocation of a lower deny. [Configure permissions](https://code.claude.com/docs/en/permissions#manage-permissions).

## Hooks, plugins and MCP are different ownership units

**Hooks documentation facts.** Supported locations include user/project/local settings and plugin `hooks/hooks.json`; plugin hooks combine with settings hooks. Matching handlers run concurrently. Identical handlers in settings files deduplicate, while plugin/skill copies remain separate. Removing a hook requires removing its source entry; a global disable switch is different from per-hook removal. Direct settings hooks normally reload through file watching. `/hooks` is a read-only source browser. [Hooks reference](https://code.claude.com/docs/en/hooks#configuration).

**Repository hook gap.** `roles/devbox/files/dot_claude/hooks.json:1` contains a standalone root `hooks` document; `install_configs.yml:100` copies it to `~/.claude/hooks.json`. Current `settings.json.j2` has no `hooks` entry and its manifest has no hooks rule. No reference loading this file through `--settings`, a plugin manifest or a settings include was found in the inspected fish/tasks paths. The repository validates its JSON and invokes individual hook scripts in tests, but that is not proof that Claude loads the root file. Treat this as an unverified runtime integration boundary, not a proven claim that all deployed hooks are inactive. A future hook plugin is one possible native component boundary; it would require explicit installation and runtime activation proof.

**Plugin documentation facts.** Plugin install scope selects the settings file whose `enabledPlugins` is changed. Plugin configuration prompts can write non-sensitive `pluginConfigs` options into user settings; sensitive options use secure storage. Plugin settings do not provide arbitrary personal defaults: plugin `settings.json` currently supports only `agent` and `subagentStatusLine`. Skills-directory plugin component changes other than `SKILL.md` require `/reload-plugins` or restart. These restrictions prevent treating a general plugin as a transparent replacement for this repository's complete settings source. [Plugins reference](https://code.claude.com/docs/en/plugins-reference#installation-scopes).

`pluginConfigs` has no Claude manifest rule. A newly written top-level `pluginConfigs` field would therefore be unknown to the current reconciler, irrespective of whether its product use is legitimate. This is a code-derived conditional result, not an observation of the user's settings. The same applies to newly introduced product keys outside current prefixes. Tests explicitly expect unknown application data to remain unknown (`tests/scripts/test_ai_config_claude_manifest.py:132`).

**MCP documentation facts.** User and local server definitions live in `.claude.json`; project definitions live in `.mcp.json`. Duplicate server names use the highest-priority complete definition, not field merging: local, project, user, then plugin and connector sources, with separately documented managed rules. Current documentation also notes a Desktop exception. `.mcp.json` supports environment substitution in commands, arguments, environment, URLs and headers. These facts do not justify copying the entire app-owned `.claude.json` into source control. [MCP reference](https://code.claude.com/docs/en/mcp#mcp-installation-scopes).

The repository already registers named user MCP servers with `claude mcp add --scope user` (`roles/devbox/tasks/apply_configs.yml:319`, `:339`, `:354`). It also actively prunes registrations: `apply_configs.yml:378` runs `claude mcp list`; `:390` subtracts the declared Docker/script/HTTP/extra-HTTP server names and excludes names beginning `claude.ai `; `:407` runs `claude mcp remove <name> --scope user`. The listing command itself has no scope filter. Removal failures are tolerated, so this is a deletion attempt, not proof that every selected registration disappears. A manually added user-scope server can be selected even when its settings are otherwise considered private. This adjacent authority must be explicitly retained or narrowed in a future split. Keep desired server definitions and registration separate from authentication and trust state. No private server configuration was read.

## Merge and deletion contracts that must survive any split

1. **Objects versus arrays:** the existing reconciler operates on leaf paths, so separate `env` entries can already have different owners. Permission arrays have explicit ordered-set rules; sandbox arrays, hook arrays if introduced, and unspecified arrays do not.
2. **Ordered-set deletion is not native layer union:** `scripts/ai_config/core.py:258` preserves base/repository/live order and performs per-member three-way reconciliation. Tests cover independent deletion plus a live addition (`tests/scripts/test_ai_config_core.py:345`). A compositor that simply unions fragments would silently lose this deletion behaviour.
3. **Native omission is not a tombstone:** leaving a key out of `--settings` preserves the lower value; layered lists retain lower entries. A future defaults compositor needs a separate, explicit removal representation if local overrides may remove defaults. This is a design consequence, not an already available Claude delete operator.
4. **Required versus discretionary plugins:** removing one repository `enabledPlugins` entry, disabling that plugin, uninstalling its files, and removing its marketplace are different operations. The current Ansible tasks install/enable named entries; they do not form a general removal workflow.
5. **Source and live ownership:** moving defaults to fragments while continuing to rewrite native user settings requires preserving UI/CLI-written fields and comparing against a generation baseline. Moving them to `--settings` avoids that write collision only by making those values session overrides and requiring launch-path coverage.

## Bounded options and unanswered questions

**Candidate A — retain native user settings, narrow repository ownership.** Use named leaf rules for durable defaults, explicit local/runtime exceptions, and an agreed required-plugin set. Keep existing three-way state and transactional protections. This is the smallest architectural delta, but broad failure on unknown top-level fields remains a separately chosen policy.

**Candidate B — generate a native settings overlay from distinct source fragments.** The generation contract must state merge order, deletion semantics, which values users can override, and how CLI versus editor/Desktop launches receive it. Do not describe this as native low-priority defaults: `--settings` has different authority. No product execution validation was performed.

**Candidate C — package executable customisations as a plugin.** Hooks, skills and related resources can become a native component. General env/sandbox/permissions/UI preferences still need their own owner and loading mechanism. Avoid duplicate hook registrations during migration.

Unresolved evidence:

- Current primary `settings-reference` page returned an access/internal error through the research tool; searches did not establish `skipAutoPermissionPrompt` or `skipWorkflowUsageWarning`. Their absence from search is not proof of invalidity.
- No installed-runtime merge, reload, `--settings`, plugin writer or hook-source experiment was run. Versioned documentation newer than 2.1.247 must not be asserted as that executable's behaviour.
- No reviewed native user-scope drop-in directory or general settings include was established. Managed drop-ins and plugin settings are not equivalent substitutes.
- Marketplace source replacement semantics were established for managed fragments; exact replacement/removal semantics across ordinary user/project scopes should be confirmed before a compositor relies on them.
- Which currently shared choices should become local is an authority decision. Mutability alone does not establish ownership, and machine specificity does not establish that a value is safe to publish.

## Suggested acceptance evidence for a later implementation

Use isolated fixtures and a version-recorded native client to check scalar precedence; nested-key preservation; permission addition and revocation; plugin true/false and uninstall distinction; unknown UI-key preservation; templated-leaf and secret non-capture; hook source visibility and duplicate execution; hot reload versus new-session changes; and launch coverage outside the shell wrapper. Keep existing tests for transaction rollback and concurrent source changes. These are proposed future checks, not completed validation.

## Repository source navigation

Return to the [ownership and composition study](ai-config-ownership-and-composition.md).

- [Claude manifest](../../roles/devbox/files/dot_claude/settings.ai-config.json), [source](../../roles/devbox/files/dot_claude/settings.json.j2), [templating](../../scripts/ai_config/templating.py) and [assets](../../roles/devbox/files/dot_claude/).
- [Settings installation](../../roles/devbox/tasks/install_configs.yml), [native plugin/MCP operations](../../roles/devbox/tasks/apply_configs.yml) and [reconciler](../../scripts/ai_config/).
