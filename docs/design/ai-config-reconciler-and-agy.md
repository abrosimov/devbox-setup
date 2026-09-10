# Reconciler and Antigravity CLI boundaries

Evidence inspected on 10 September 2026. This is analysis, not an accepted implementation design. No repository or live client configuration was changed. No client was launched, authenticated, or queried against a model. Local package paths were inspected without private settings. The full host failure frequency and the fields actually drifting on work/personal machines remain unmeasured.

## Reconciler architecture and operational boundaries

| Component | Current responsibility | Adaptation implication |
| --- | --- | --- |
| `scripts/ai-config:1–13`, `ai_config_cli.py:1`, `ai_config/__main__.py:1` | Bash chooses existing repository venv, otherwise `uv run --no-project --python >=3.12`; Python entry points call CLI | A composer can reuse the entry point; wrapper fallback can provision a runtime and should not be confused with an entirely offline validator |
| `ai_config/cli.py:53–158,215–338` | Status/diff, apply/reconcile, bootstrap; exit 1 for unresolved state/unknown fields, 2 for errors | Keep diagnostic and mutation contracts distinct; preflight must use `apply --check`, not convergence status as an applyability check |
| `ai_config/adapters.py:73–92,130–153` | Engine paths and JSON/TOML formats; Codex dynamically classifies recognised hook state | AGY `.j2` source is parsed as plain JSON, not rendered as Jinja; new templates need a real rendering stage |
| `ai_config/model.py:52–84,129–140` | Canonical typed semantic snapshots; recursively flattens non-empty objects, treats arrays/empty objects atomically | Composition needs explicit parent/child collision and deletion semantics; atomic strategy does not make a whole non-empty object indivisible |
| `ai_config/manifest.py:34–149`, `core.py:76–164` | Schema 1, longest-prefix field ownership, environment bindings and ordered-set strategy | Existing manifest is a good ownership catalogue but not a client value schema; broad object prefixes admit unknown descendant names |
| `ai_config/bindings.py:51–126` | Resolves profile/env/keychain/home values into repository projection | Profile currently resolves only `devbox_active_profile`; no arbitrary profile fragment composition. Injection-based providers already support isolated tests |
| `ai_config/core.py:208–255` | Three-way classification | Local/runtime survive automatically; shared user choices provoke manual decisions |
| `ai_config/resolution.py:35–144` | Copies chosen field values, merges ordered sets, requires explicit decisions | Deployment and capture currently share a resolver and can both change repository source |
| `ai_config/service.py:142–219,332–423` | Inspects inputs, resolves secrets for comparison, requires portable repo/live convergence, renders writes and baseline | One-way composition needs a different convergence invariant: effective managed output equals candidate, while local output need not equal repo |
| `ai_config/document.py:78–108,110–134,179–204,351–365` | Portable projection, sensitive fingerprints, formatting-conscious rendering, generic syntax/value validation | Keep projection and round-trip checks; add client schema/semantic validation and effective-loader proof where supported |
| `ai_config/state.py:43–63,75–76,101–134` | Baseline per engine/profile; raw manifest SHA | Preserve compatible baseline fields through semantic manifest migration rather than invalidating everything |
| `ai_config/decisions.py:18–24,51–100`, `cli.py:327–329,381–397` | Decisions contain path/source only; interactive retry re-inspects after prompting | Ordinary decisions are not bound to reviewed values. Add snapshot token if retaining reconciliation |
| `ai_config/transaction.py:320–435,597–633` | Engine lock, expectation checks, staging, backups/journal, per-file atomic replace, readback, rollback/recovery | Reuse but do not advertise isolation from client writers or all-client transactional deployment |
| `ai_config/__init__.py:1` | Re-exports public package API | Preserve compatibility deliberately if command semantics split |

### Concrete blockers and potentially surprising effects

1. `core.py:241–246` calls every live-only shared edit `capture-live`; `resolution.py:124–138` rejects it in apply. A both-sided edit is a conflict. A differing existing live file without valid baseline needs initialisation decisions. A completely missing live file can initialise from repo automatically.
2. `service.py:339–343` blocks every write for any unknown path, even an unrelated live-only vendor field. Unknown repo fields should still be rejected under a composition design; live-only fields can be preserved outside managed ownership boundaries.
3. `state.py:75–76,117–123` hashes raw manifest bytes and discards the entire baseline on mismatch. Even whitespace invalidates it. This is demonstrated by source, not a measured cause of this user's repeated interruptions.
4. `resolution.py:61–68,108–120` handles ordered-set MERGE before checking mode. Therefore apply can capture into repository source. A synthetic, in-memory probe with base `[common]`, repo `[common, repo-added]`, live `[common, live-added]` returned merged repository `[common, repo-added, live-added]` and no required decisions. No real files were used.
5. `service.py:246–254,286–328` binds bootstrap writes to a preview digest. Ordinary reconcile lacks that guarantee: the CLI re-inspects after questions but uses the old path/source choice. Transaction expectations only protect the newly inspected snapshot.
6. The internal transaction lock is scoped to engine/profile state (`state.py:43–63`). It serialises cooperating operations for that profile, not the applications, another profile targeting the same live path, or unrelated writers. Content expectations run before staging/install; a client writing afterwards can still race. Each replacement is atomic, the whole batch is journalled/recoverable but not atomically visible to external readers.
7. `document.py:351–365` verifies JSON/TOML parses into supported values, not that the client accepts field names, types, permission expressions, model names, hooks or installed dependencies. The root-object requirement is not a product schema. Known sensitive fields are redacted (`cli.py:437–445`), but unknown/local paths and values are not universally secret-safe; do not use raw diff as public research evidence.
8. Ansible invokes apply for each client inside the configuration deployment (`install_configs.yml:112–141,205–234`, `install_codex_configs.yml:39–64`). It is not a single global preflight. Earlier file copies can have occurred before a later engine blocks.

## AGY identity and native facilities

Repository installation declares Homebrew cask `antigravity-cli` (`roles/devbox/defaults/main/packages.yml:125`). `command -v agy` returned `/opt/homebrew/bin/agy`. A package binary exists at `/opt/homebrew/Caskroom/antigravity-cli/1.0.16,4893150192467968/antigravity`. Its archived cask JSON is empty (`{}`), so package-directory version is evidence of that installed artefact, not proof that the independent `/opt/homebrew/bin/agy` file has the same build. No `agy --version` was run. The current official documentation navigation identifies CLI v1.2.0; do not apply every new documented feature to the local binary without version verification.

The official AGY CLI documentation identifies `~/.gemini/antigravity-cli/settings.json` as its plain JSON preferences file and confirms that `/config` or `/settings` persists user selections. CLI flags can override certain settings for a session. This establishes that editing the file through the app is intended product behaviour, not inherently drift requiring repo capture. [Using AGY CLI](https://antigravity.google/docs/cli/using/).

Current documentation says preferences use sparse persistence: only values differing from defaults are written. Thus missing versus explicitly default-valued properties can be semantically equivalent for the client although the reconciler treats them as different. Version-specific default equivalence needs loader evidence before normalisation is introduced. [Settings documentation](https://antigravity.google/docs/cli/settings/).

The official changelog records project permission precedence over CLI global settings in 1.0.12, permission UI reload fixes in 1.0.15, preservation of unknown JSON fields in 1.0.7, and the hooks path correction to `~/.gemini/config/hooks.json` in 1.0.8. These support native permission separation and confirm that hooks have an interactive writer, but do not establish an arbitrary defaults/include layer for all settings. [AGY changelog](https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md).

Current permissions documentation specifies `deny`, `ask`, and `allow`, with deny before ask before allow. Command rules use literal word-prefix matching unless explicitly regex-prefixed. Therefore generic set union is not a complete permission-policy merge model. [AGY permissions](https://antigravity.google/docs/cli/permissions/).

Current reference documents persistent model selection, colour scheme and non-workspace-access options. It lists many additional fields beyond this repository's manifest. This is evidence that the six-rule manifest is a local ownership declaration, not an exhaustive current schema. [AGY CLI reference](https://antigravity.google/docs/cli/reference/).

No evidence was found in the inspected official CLI pages for a universal settings include directory, arbitrary settings-file flag, or config-only effective-settings validation command. This is a bounded search result, not a claim of non-existence. Gemini CLI and Antigravity IDE layering must not be substituted as AGY CLI proof.

## Complete AGY manifest ledger and candidate ownership

Manifest: `roles/devbox/files/dot_agy/cli/settings.ai-config.json`. Source values: `roles/devbox/files/dot_agy/cli/settings.json.j2:1–23`. This ledger covers all six rules, including the parent-prefix rule.

| Rule location | Path | Current declaration and value | Candidate ownership; decision needed |
| --- | --- | --- | --- |
| manifest:6 | `allowNonWorkspaceAccess` | shared atomic; true | Explicit static policy or profile policy. A local override that changes access semantics needs an admitted rule, not accidental last-writer priority |
| manifest:10 | `colorScheme` | shared atomic; `tokyo night` | Seed default, thereafter local preference; a theme change should not block deployment |
| manifest:14 | `model` | shared atomic; `Gemini 3.1 Pro (High)` | Seed default plus permitted profile/session/local choice; decide whether any model policy is actually mandatory |
| manifest:18 | `permissions` | shared atomic prefix, parent object | Replace blanket prefix ownership with explicit allow/ask/deny handling and preserve unowned names carefully; inherited rules classify unknown descendants as shared |
| manifest:22 | `permissions.allow` | shared ordered-set; 12 command expressions | Separate declared grants from interactive/local grants. Define membership provenance, removals/tombstones and interaction with ask/deny; never silently export local approvals |
| manifest:27 | `trustedWorkspaces` | local-state; excluded from repo source | Keep app-owned; do not template, export or cross-machine synchronise |

The 12 declared expressions are `command(uv)`, `command(go tool task docs:check)`, `command(grep)`, `command(agy)`, `command(python3 -c "import site; print(site.getsitepackages())")`, `command(pip3 show google-antigravity)`, `command(find)`, `command(git ls-remote)`, `command(git status)`, `command(git diff)`, `command(git log)`, `command(cat)`. These are source inventory, not newly endorsed approvals.

Additional AGY surfaces outside the manifest:

- `install_configs.yml:236–241` replaces the complete `~/.gemini/config/hooks.json` from `dot_agy/config/hooks.json.j2`, including every hook's `enabled: true`. Existing local hook entries or disabled states have no ownership protection here. The template contains 28 named hooks across PreToolUse, PostToolUse, Stop, PreCompact, Start and worktree events.
- `install_configs.yml:250–262` syncs the AGY hook bin tree with deletion, excluding caches/venv. This is a repo-owned directory deployment, not config reconciliation.
- Shared AI files sync into `~/.gemini/config/` without deletion (`install_configs.yml:168–181`), agent frontmatter is translated (`183–189`), and root AGENTS rules are copied (`198–203`). These are separate lifecycle/ownership contracts.
- `darwin/configure_gemini_telemetry.yml:48–59` contains another settings merge using `devbox_antigravity_settings`, but repository search found no include and no definition of that variable. Treat it as an apparently orphaned legacy writer, not an active recurrent-drift cause.

## Validation evidence and proposed scenario gates

Executed existing tests through the existing repository venv, with bytecode disabled, pytest cache disabled and Hypothesis storage under `/private/tmp`: core, service, transaction, CLI operations, property tests, AGY manifest and Claude/AGY deployment tests. Result: **165 passed in 5.60 seconds**. This validates current contracts using fixtures; it does not prove the proposed design or native AGY loading. Existing deployment tests inspect Ansible task data rather than running an application (`tests/deploy/test_ai_config_ansible_claude_agy.py:91–108,163–216`).

| Scenario | Existing evidence | Gate required for adaptation |
| --- | --- | --- |
| Clean first install and repeated apply | CLI tests:75–106; service creation/idempotence | Compile both profiles; second deployment changes nothing |
| Change theme/model via client | service:561–599 requires reconcile for live-only edit | Local preference survives routine apply without repo edit or prompt |
| Repo change and unrelated local edit | Current shared convergence can block | Apply managed change, preserve unrelated field and show provenance |
| New unknown vendor field | service:698–728 blocks all writes | Preserve live-only unknown; refuse repo typo and parent/path collisions |
| Local trust/runtime state | service:730 onwards; AGY manifest fixtures | Semantic preservation plus no export, including new trusted workspace |
| Manifest formatting/additive rule | Raw hash invalidates baseline | Formatting no-op; additive migration changes only newly owned fields |
| Concurrent permission additions | Core ordered-set tests; synthetic apply probe | No automatic repository writes; test allow/deny/ask semantics and removals |
| Client removes default-valued field | Not established by current tests | Version-bounded effective equivalence, no recurring false drift |
| Late client write during apply | Tests cover expectation mismatch and transaction failures | Fault inject after expectation check; preserve/update retry contract rather than claim universal locking |
| Invalid but parseable client value | Generic parsing permits it | Product schema/loader rejection before replacement |
| Partial multi-file failure | transaction:545–681 rollback/recovery tests | Preserve current guarantees; verify generated config and supporting hook files as one deployment plan |
| Existing disabled or local AGY hook | Whole-file template has no preservation | Hook identity ownership and local-state preservation fixture |
| Profile switch targeting one home | Baselines/locks profile-specific | Avoid concurrent cross-profile writes; define effective source and migration |
| Export after explicit review | Existing decision files unbound | Digest-bound reviewed export; reject stale sources and redact output |

Recommended implementation direction, subject to the user's ownership decisions: introduce composition as a one-way deploy contract and leave capture as a separate explicit operation. Native AGY project permissions can help where their exact precedence is verified; they do not replace the need to preserve global user preferences or resolve hook ownership. Keep the current parsing, provider injection and transaction tests, but change convergence from repo/live equality to effective-candidate correctness. Do not automate choosing repo for every conflict.

## Repository source navigation

Return to the [ownership and composition study](ai-config-ownership-and-composition.md). Source labels use repository-relative paths; `ai_config/` abbreviates `scripts/ai_config/`. Line numbers refer to commit `8553b576f060209a729e1062c0a7ce5fefb99f25`.

- [Reconciler modules](../../scripts/ai_config/) and [behavioural tests](../../tests/scripts/).
- [AGY manifest](../../roles/devbox/files/dot_agy/cli/settings.ai-config.json), [source](../../roles/devbox/files/dot_agy/cli/settings.json.j2), [assets](../../roles/devbox/files/dot_agy/) and [deployment](../../roles/devbox/tasks/install_configs.yml).
