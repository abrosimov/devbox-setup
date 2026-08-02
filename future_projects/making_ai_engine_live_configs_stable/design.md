# Stable live configuration for AI engines

> **Status: implementation complete; isolated automated acceptance passes.**
>
> The repository contains a common `ai-config` implementation for Claude, Antigravity, and Codex,
> profile-separated base state, JSON manifests, environment and Keychain binding providers,
> transactional writes, CLI operations, strict Python gates, and Ansible integration. Isolated
> tests apply the current repository documents for all three engines and prove second-run
> idempotence. No write-capable command has been run against the user's real `HOME`; rollout there
> remains a separate operator action after read-only review.

## 1. Decision

`devbox-setup` unifies the user's personal and work development environments. AI-engine settings
that describe that environment therefore belong in this repository alongside shell, editor, and
other developer-tool configuration.

Shared configuration is the default. Models, reasoning settings, permissions, sandbox policy,
plug-ins, marketplaces, hooks, and telemetry behaviour should not be duplicated between personal
and work profiles unless a concrete difference exists. The working “99% shared” statement is a
design heuristic, not a measured value.

There are three explicit exceptions:

1. An environment-dependent value is declared in the repository and, where necessary, resolved
   through a profile or environment binding.
2. A secret is declared as a Keychain binding. The declaration is versioned; the value is not.
3. Machine-local or runtime-owned state is classified and preserved outside portable
   reconciliation.

The user-facing interface is the repository-local `scripts/ai-config` command. Vendor formats and
paths remain engine-specific, while classification, planning, decisions, state, and transactional
writes use one contract.

## 2. Scope

The common writer currently owns these documents:

| Engine | Repository document | Live document | Format |
| --- | --- | --- | --- |
| Claude | `roles/devbox/files/dot_claude/settings.json` | `~/.claude/settings.json` | JSON |
| Antigravity | `roles/devbox/files/dot_agy/cli/settings.json.j2` | `~/.gemini/antigravity-cli/settings.json` | JSON |
| Codex | `roles/devbox/files/dot_codex/config.toml.j2` | `~/.codex/config.toml` | TOML |

Other engine assets, including hooks, guidance, skills, agents, and managed directories, retain
their existing one-way Ansible deployment where that is still the correct ownership model.

The implementation does not:

- synchronise caches, sessions, conversation history, or vendor migration markers;
- infer portability from a hostname or from the mere presence of a profile;
- guess the ownership of an unclassified vendor field;
- put secret values in Git, CLI diagnostics, decisions, journals, or base state;
- preserve comments or source key ordering when a changed JSON or TOML document is canonically
  re-rendered;
- make a real-user write part of automated acceptance.

## 3. Authority model

Every classified path has one scope:

| Scope | Meaning | Behaviour |
| --- | --- | --- |
| `shared` | Portable intent common to profiles | Three-way apply or capture |
| `environment` | Portable intent bound to a profile, environment variable, or Keychain item | Resolve the binding and apply repository authority |
| `local-state` | Durable state owned by this installation | Preserve the live value and exclude it from portable state |
| `runtime` | Ephemeral engine-owned state | Preserve the live value and exclude it from portable state |

There is no implicit shared fallback in code. A manifest rule must cover a repository field before
a write-capable operation can safely own it. An unclassified path is reported as `unknown`, and a
write-capable operation stops before changing configuration or advancing base state.

The portable convergence condition is:

```text
portable_projection(live) == resolved_portable_projection(repo)
```

Resolved secret values are fingerprinted before planning or persistence. The base contains the
fingerprint, not the resolved value. Local-state and runtime paths are absent from the portable
projection.

## 4. Three-way reconciliation

### 4.1 Inputs

For one engine and one profile the planner compares:

- `base`: the last successfully committed portable snapshot;
- `repo`: the current repository declaration after required bindings are resolved;
- `live`: the current engine document.

The default state path is profile-separated:

```text
${HOME}/.local/state/devbox-setup/ai-config/<engine>/<profile>/base.json
```

`--state-root PATH` replaces the prefix and produces:

```text
<state-root>/<engine>/<profile>/base.json
```

The current implementation does not automatically read `XDG_STATE_HOME`. A base file is JSON with
`schema_version`, `engine`, `profile`, `manifest_digest`, and `snapshot`. A manifest digest change
invalidates the old base for planning. State directories use mode `0700`; base, locks, journals,
backups, and live engine documents written by this tool use private modes.

### 4.2 Decisions

At each semantic field:

| Relationship | Classification | Resolution |
| --- | --- | --- |
| `repo == live` | `unchanged` | No content change |
| `repo == base`, `live != base` | `capture-live` | `reconcile` requires a live decision; `apply` refuses |
| `live == base`, `repo != base` | `apply-repo` | Apply repository intent |
| Both sides changed differently | `conflict` | Require an explicit repo/live decision |
| Scope is `local-state` or `runtime` | `preserve-local` | Retain live value |
| No manifest rule applies | `unknown` | Report it and block any document rewrite |

Addition, deletion, and absence are distinct inputs to the same table. A field with an explicit
binding is repository-owned after resolution and is classified as `apply-repo` when it differs.
Bound or secret fields cannot be captured from live configuration.

Without a base, equal repository and live projections can initialise state without rewriting the
engine document. A missing live file can be created from repository intent. Otherwise the planner
returns `initialisation-required`; the tool does not invent a direction.

### 4.3 Current semantic granularity

Nested objects are flattened to leaf paths and compared independently. Arrays are atomic by
default. A manifest can opt a field into `strategy: "ordered-set"`; independent additions and
deletions are then merged while retaining deterministic base/repository/live order. Claude uses
this for permission allow, deny, and additional-directory lists, and Antigravity uses it for its
permission allow list. Keyed-map and wildcard-selector syntax remain future extensions and must not
be assumed by adapters or documentation.

## 5. Manifests and bindings

Each engine has a versioned JSON manifest next to its repository document. The implemented schema
is deliberately small:

```json
{
  "schema_version": 1,
  "engine": "codex",
  "fields": [
    {
      "path": "model",
      "scope": "shared"
    },
    {
      "path": "otel.environment",
      "scope": "environment",
      "binding": "profile:devbox_active_profile"
    },
    {
      "path": "projects",
      "scope": "local-state"
    },
    {
      "path": "apiToken",
      "scope": "environment",
      "binding": "keychain:example-service/api-token",
      "secret": true
    }
  ]
}
```

Supported rule keys are `path`, `scope`, optional `binding`, optional `secret`, and optional
`strategy`. A path is a dotted string or an array of non-empty strings. A more specific prefix rule
wins over a broader one; duplicate exact paths are invalid. Every `environment` field requires a
binding, bindings are invalid for other scopes, and a secret field must have a binding. This avoids
silently capturing a personal environment value into the shared repository document. Portable
values are `shared` by default; a concrete environment exception must be explicit.

The implemented providers are:

- `profile:devbox_active_profile`, resolved from the explicit CLI profile;
- `env:NAME`, resolved from the process environment;
- `keychain:SERVICE/ACCOUNT`, resolved with macOS `security find-generic-password` using an argument
  vector rather than a shell.

Provider errors occur before writes. Keychain command output is used only as the resolved value;
error messages do not include it. No current engine manifest declares a Keychain-backed field, so
the provider is available for future environment configuration without forcing a secret into the
repository.

## 6. Implementation layout

The implemented package is:

```text
scripts/
  ai-config
  ai_config_cli.py
  ai_config/
    __init__.py
    __main__.py
    adapters.py
    bindings.py
    cli.py
    core.py
    decisions.py
    document.py
    manifest.py
    model.py
    resolution.py
    service.py
    state.py
    transaction.py
```

`adapters.py` defines immutable engine specifications for format and repository/live/manifest
paths. JSON and TOML parsing and rendering are shared format operations. `core.py` owns semantic
classification; `resolution.py` applies explicit decisions; `service.py` assembles inspection and
write operations; `state.py` owns profile-scoped base metadata; `transaction.py` owns locking,
staging, validation, replacement, read-back, rollback, and recovery.

This is a common behavioural path, not an attempt to erase vendor formats. A vendor-specific
semantic rule should be added only when backed by its manifest and focused tests.

## 7. CLI contract

All normal engine operations should pass an explicit repository root, home, and profile:

```console
scripts/ai-config status [ENGINE] \
  --repo-root "$PWD" --home "$HOME" --profile personal [--json]

scripts/ai-config diff [ENGINE] \
  --repo-root "$PWD" --home "$HOME" --profile personal [--json]

scripts/ai-config apply ENGINE \
  --repo-root "$PWD" --home "$HOME" --profile personal [--check] [--json]

scripts/ai-config reconcile ENGINE \
  --repo-root "$PWD" --home "$HOME" --profile personal \
  [--decisions FILE] [--check] [--json]
```

`status` and `diff` are read-only and do not establish base state. They return `0` only when the
plan is converged and state exists; drift returns `1`.

`apply` is the non-interactive deployment operation. It performs repository-originated changes,
safe initialisation, and deterministic ordered-set merges, but returns `1` when another
live-originated or conflicting path needs a decision.

`reconcile` accepts decisions interactively on a TTY or through `--decisions FILE`. A decision file
is JSON:

```json
{
  "decisions": [
    {"path": ["permissions", "allow"], "source": "repo"}
  ]
}
```

`--check` resolves the complete operation and reports `changed`, but writes neither repository,
live, nor base files. `--json` produces one structured result. Operation exit statuses are `0` for
a completed operation, `1` for a valid plan that still needs decisions or classification, and `2`
for invalid input, binding failure, or an operational error.

### 7.1 Make compatibility

The primary interface remains `scripts/ai-config`. Legacy Claude names are compatibility aliases:

- `make claude-diff` delegates to `scripts/ai-config diff claude`;
- `make claude-pull-review` delegates to `scripts/ai-config reconcile claude`;
- `make claude-pull` delegates to `claude-pull-review` and no longer copies files wholesale.

Each alias requires an active profile and passes explicit repository root, home, and profile.
`ARGS` is forwarded for options such as `--decisions`, `--check`, or `--json`.

`claude-push`, `agy-push`, and `codex-push` are deliberately blocked compatibility guards. Each
prints the engine-specific `diff`, `reconcile`, and checked `apply` workflow, exits non-zero, and
does not acquire the Ansible collections prerequisite or invoke Ansible. This protects habitual
use of the historical one-way names. The full profile playbooks retain the common `ai-config apply`
tasks with explicit context and structured JSON handling.

## 8. Transaction and recovery model

A write-capable operation:

1. inspects repository, live, manifest, bindings, and profile base;
2. resolves the plan and stops before writing on missing decisions or unsafe unknown fields;
3. renders and validates all candidates before creating transaction state;
4. acquires a per-engine/profile lock and checks that every source byte sequence used by the plan,
   including unchanged documents and the manifest, has not changed;
5. stages changed candidates on their destination filesystems;
6. records path and state metadata in a private, value-free transaction journal;
7. creates private recovery copies for replaced files;
8. installs candidates with atomic per-file replacement and validates the bytes read back;
9. rolls every installed target back, including its original mode, if installation or read-back
   validation fails;
10. commits the new base in the same multi-file transaction and removes the completed journal.

Several file replacements cannot be globally atomic. The journal under the profile state directory
is therefore the crash-recovery boundary: an unfinished installation is recovered before a new
transaction proceeds. Backups use stable per-target slots in the private state directory rather
than an unbounded history. Tests cover modes, candidate validation, concurrent modification,
locking, rollback, journal recovery, and absence of configuration values from the journal.

## 9. Ansible migration

The three settings writers now use the common apply command:

- Claude no longer includes `settings.json` in the blind root-file copy loop; hooks and `config.md`
  retain their existing deployment path.
- Antigravity no longer renders a managed intermediate settings file or invokes the recursive merge
  writer. `trustedWorkspaces` is classified as local state and is absent from repository intent.
- Codex settings deployment invokes the same common command; other portable Codex assets remain in
  their existing tasks.

The tasks pass the repository root, real or debug home, active profile, and `--json`. Ansible check
mode forwards `--check` while setting task-level `check_mode: false` so the read-only CLI plan still
runs. `changed_when` consumes the JSON `changed` field, and any non-zero return code fails the task.

Legacy helper files may remain on disk until a separate clean-up proves that nothing references
them. They are not the active settings writers in the migrated Ansible tasks.

## 10. Quality gates

Ruff and Pyrefly are mandatory for the implementation.

Ruff uses Python 3.12, `select = ["ALL"]`, formatting checks, and the repository line-length policy.
The project has a reviewed global exception list and test-only per-file exceptions; production
`ai_config` code has no blanket suppression. Lint failures must be corrected rather than hidden by
inline `noqa` directives.

Pyrefly applies explicit strict checks to `scripts/ai_config/**` and `scripts/ai_config_cli.py`,
including implicit `Any`, unannotated returns, invalid overrides, unbound names, missing override
decorators, and unused ignores. The normal gates include the package and its focused tests:

```console
make lint-py
make typecheck
make test-ai-config
make test-deploy
git diff --check
```

Passing these commands establishes only what their tests and analyses cover. It does not establish
that real user configuration has been safely applied.

## 11. Implemented test coverage

Repository tests currently cover:

- scalar three-way truth tables, additions, deletions, missing base, local/runtime preservation,
  bound fields, unknown fields, deterministic ordering, and ordered-set core properties;
- property-based determinism, repository-only changes, live-only changes, conflicts, preserved
  state, and unknown paths;
- JSON manifest parsing and current Claude, Antigravity, and Codex classifications;
- JSON and TOML path resolution, parsing, read-only engine plans, and Codex template parsing;
- initial live creation, base creation, idempotent second apply, repository apply, check mode,
  decision-file capture/conflict choices, local-state preservation, profile/environment/Keychain
  bindings, secret fingerprints, and redacted binding failure;
- transactional modes, backups, pre-validation, expected-content checks, lock contention, rollback,
  journal recovery, multi-file commit, and value-free journals;
- structural Ansible migration for all three engines, including explicit context, check mode,
  JSON-driven change reporting, and removal of the legacy settings writers from active tasks.

The tests use temporary roots and injected providers. They do not authorise or substitute for a
write against real engine files.

## 12. Phase status

| Phase | Repository status | Remaining gate |
| --- | --- | --- |
| 1. Read-only core | Implemented and covered by focused and property tests | Extend only when the public manifest contract grows |
| 2. Claude vertical slice | Apply/reconcile, transaction path, manifest, isolated apply, and Ansible migration implemented | Read-only real-home review, then an explicit operator rollout |
| 3. Antigravity | Common path, local workspace-state classification, isolated apply, and Ansible migration implemented | Same real-home gate; clean up the inactive legacy helper only after a separate reference audit |
| 4. Codex | Common TOML path, profile binding, isolated apply, and Ansible migration implemented | Same real-home gate; clean up the inactive legacy helper only after a separate reference audit |
| 5. Consolidation | CLI, Claude Make aliases, quality gates, recovery tests, and implementation documentation complete | Real-home rollout evidence only |

## 13. Acceptance checklist

The automated implementation acceptance covers the following in temporary repository, home, and
state roots:

1. Two consecutive applies produce changed then unchanged, with no second-run writes.
2. A repository-only portable edit reaches live configuration.
3. A live-only portable edit requires a decision and is not overwritten by `apply`.
4. A same-field concurrent edit reports a conflict and writes nothing without a decision.
5. Local and runtime paths survive every relevant operation.
6. An unknown field blocks a document rewrite until classified.
7. Invalid or unavailable profile, environment, and Keychain bindings fail before writes and do not
   leak values.
8. Injected failures across transaction boundaries recover prior files and do not incorrectly
   advance base state.
9. Structural Ansible tests verify `--check` forwarding and JSON-driven change/error expressions.
10. Ruff, Pyrefly, focused tests, deployment tests, and diff checks pass on the final tree.
11. Recovery is exercised against a deliberately interrupted transaction.

The remaining operator acceptance step is to run `status` or `diff` against the real engine files,
review the classification and decisions, and only then choose whether to run a real `apply` or
`reconcile`.

Running `apply` or `reconcile` against the user's real `HOME` is explicitly outside the current
implementation/test step. It requires a separate user decision after the read-only output has been
reviewed.

## 14. Evidence boundary

This document records the implemented architecture, current limits, and remaining acceptance work.
It does not itself prove runtime behaviour. Evidence comes from current code, passing static and
dynamic checks, isolated fault and engine-apply runs, and reviewed read-only output. Any claim
beyond that evidence remains pending.
