# Proposal: Unify the Live-Config Lifecycle, Not Vendor Schemas

## Status and decision use

This document proposes a target architecture for synchronizing mutable AI-client
configuration across machines. It is intended to guide a later implementation
decision; it is not an implementation plan or proof that the current deployment
is safe.

The system of interest is the `devbox-setup` workflow that observes, reviews,
promotes, and deploys live configuration for:

- Claude Code: `~/.claude/settings.json`;
- Antigravity CLI: `~/.gemini/antigravity-cli/settings.json`;
- Codex: `~/.codex/config.toml`.

Agents, skills, authority protocols, and rarely changing hook files are outside
this system unless a client demonstrably edits them at runtime. Authentication,
session history, caches, OAuth state, and credentials are always outside it.

## Problem pressure

Each client treats part of its user configuration as an application-owned state
store. Interactive actions can add approvals, trust decisions, MCP servers,
feature flags, UI preferences, or migration notices. At the same time,
`devbox-setup` needs a portable, reviewable baseline that can be reproduced on a
new machine.

Neither of the obvious ownership models is sufficient:

1. **Repository always wins.** A blind push destroys valid runtime state and can
   make a workstation less usable.
2. **Live file always wins.** A wholesale pull imports host paths, ephemeral
   state, credentials, and vendor noise into Git, while making intentional
   repository removals impossible.
3. **Recursive merge everything.** This preserves too much, cannot express
   deletion reliably, and gives list union semantics to values whose order or
   replacement semantics may matter.

The current repository contains all three failure modes in partial form:

- Claude root configuration is copied from the repository to the live location;
- Agy recursively merges the managed JSON into live JSON and unions every list;
- Codex preserves unowned top-level tables, but the managed fragment owns whole
  tables such as `[features]` and `[sandbox_workspace_write]`.

The desired outcome is not byte-for-byte equality between Git and live files.
It is a stable relation:

> The live configuration equals the validated application of portable repository
> policy to preserved runtime state, and every portable runtime-originated change
> is either promoted, explicitly rejected, or still visible for review.

## Proposed ownership model

Every supported config path must have an explicit ownership class. Ownership is
field-level; a whole table or object is owned only when the vendor contract makes
that safe.

| Class | Authority | Push behavior | Pull-review behavior |
|---|---|---|---|
| `managed` | Repository | Apply the repo value, including intentional deletion | Show live drift before replacement |
| `reviewable` | Neither until reviewed | Preserve live value | Offer promotion into the repo representation |
| `runtime` | Client | Preserve | Do not offer unless explicitly requested |
| `machine-local` | Current machine | Preserve | Never commit literal values; optionally translate to a portable template |
| `secret` | Credential store or environment | Preserve or reference indirectly | Never print or commit the value |
| `ephemeral` | Client | Preserve or let the client replace | Ignore in ordinary drift reports |

Absence also needs semantics. For a managed field, the manifest must distinguish:

- **unmanaged absence**: leave the live value alone;
- **managed deletion**: remove the live value;
- **default by omission**: remove the explicit value and rely on the client
  default.

This avoids retaining obsolete settings forever while preventing accidental
deletion of newly introduced vendor fields.

## Architecture

### 1. One protocol, three adapters

Unify the user workflow and result model, but retain vendor-specific parsers,
normalizers, ownership manifests, redactors, validators, and writers.

```text
Make targets
    -> common sync coordinator
        -> claude adapter (JSON and Claude permission semantics)
        -> agy adapter (JSON and Agy permission/workspace semantics)
        -> codex adapter (TOML and Codex config-layer semantics)
```

The common coordinator should understand only these operations:

- load and validate repository intent;
- load and validate live state;
- classify semantic drift by ownership class;
- produce a redacted report;
- produce a review candidate;
- reconcile to a temporary output;
- validate and atomically install that output;
- verify the postcondition.

It must not encode vendor field names or assume that arrays always use union
semantics. A generic recursive merge should not be the abstraction boundary.

### 2. Per-client ownership manifests

Each adapter should expose a small, reviewable manifest. Illustrative entries:

```yaml
codex:
  managed:
    - model
    - model_reasoning_effort
    - sandbox_mode
    - features.memories
    - sandbox_workspace_write.network_access
    - otel
  reviewable:
    - features.*
  runtime:
    - projects
    - plugins
    - marketplaces
    - desktop
    - tui
    - notice
    - tool_suggest
    - skills.config
    - mcp_servers
```

The real manifest must be derived from current vendor behavior and fixtures,
not copied from this example. In particular, `features.memories` can be managed
without claiming the entire `[features]` table. A one-time deletion such as
`features.js_repl` should be represented as an explicit tombstone or migration,
not as permanent ownership of all feature flags.

Claude and Agy need their own path classifications. Portable permission rules
may be reviewable, while absolute trusted-workspace paths are machine-local
representations that can only be promoted after translation to Jinja-backed
portable paths.

### 3. Semantic snapshots, not textual equality

JSON key reordering and TOML formatting are not drift. Each adapter should
normalize parsed data into a semantic snapshot containing:

- portable managed values;
- reviewable additions and removals;
- preserved runtime state;
- redacted machine-local and secret-state summaries;
- schema/version metadata where available.

Reports should contain field paths and safe summaries. Environment values,
headers, tokens, OAuth data, and command arguments classified as sensitive must
be redacted before reaching terminal output, logs, temporary review files, or
Git diffs.

### 4. Review decisions are first-class state

`pull-review` needs three decisions, not only keep/drop:

- **promote**: convert the live value into a portable repository representation;
- **local-only**: preserve it on this machine and stop reporting it as pending;
- **reset**: accept repository authority and remove or replace it on the next
  push.

Rejected or local-only values need a machine-local decision ledger keyed by a
redacted semantic fingerprint. Otherwise the same harmless runtime value is
presented on every invocation. The ledger must not contain raw secrets and must
not be required to bootstrap another machine.

Repository edits produced by `pull-review` remain candidates until reviewed in
`git diff`. The tool must not commit, push, or deploy them automatically.

### 5. Safe push transaction

For every client, push should follow the same observable transaction:

1. Render repository intent for the active profile into a private temporary
   file.
2. Parse and validate both desired and live configurations. Invalid live state
   fails closed without writing.
3. Classify drift and stop when unresolved reviewable drift would otherwise be
   destroyed.
4. Reconcile according to the client manifest.
5. Validate the complete candidate using both syntax checks and client-specific
   schema checks where available.
6. Write atomically with mode `0600` and retain a bounded private backup of the
   previous valid file.
7. Read the installed file back and verify the expected semantic postcondition.

Unowned runtime drift must not block deployment. Managed drift should be shown
before replacement. A force flag, if provided, should bypass only the review
gate; it must not bypass parsing, redaction, atomic-write, permissions, or
postcondition checks.

## User workflow

Expose consistent commands while keeping the adapters independent:

```text
make ai-config-status
make claude-diff
make claude-pull-review
make claude-push
make agy-diff
make agy-pull-review
make agy-push
make codex-diff
make codex-pull-review
make codex-push
```

`ai-config-status` is read-only and returns a compact matrix:

| Client | Managed drift | Reviewable drift | Local/runtime drift | Safe to push |
|---|---:|---:|---:|---:|
| Claude | count | count | count | yes/no |
| Agy | count | count | count | yes/no |
| Codex | count | count | count | yes/no |

There should be no `ai-config-pull` that blindly rewrites every repository
source, and no `ai-config-push` that silently deploys all clients. Cross-client
commands are useful for visibility; mutation remains explicit per client.

## Client-specific consequences

### Claude Code

- Replace the blind copy of `settings.json` with a reconciler.
- Retain the existing permission classifier as Claude-specific policy rather
  than moving its regexes into a generic sync engine.
- Expand drift reporting beyond `permissions.allow`, but require explicit
  ownership decisions before any new field is promoted automatically.
- Keep `hooks.json` and other static files on their existing push path unless
  evidence shows that Claude mutates them.

### Antigravity CLI

- Replace recursive list union with field-specific behavior.
- Make repository removal possible for managed permission entries.
- Treat literal `trustedWorkspaces` as machine-local; promote only a portable
  project identity that the template can render for each host.
- Add Agy-specific `diff` and `pull-review` commands before coupling it to a
  common status command.

### Codex

- Change `reconcile_config.py` from whole-table ownership to field-level
  ownership for mixed tables such as `[features]` and
  `[sandbox_workspace_write]`.
- Preserve Codex-owned tables such as projects, plugins, marketplaces, desktop,
  TUI, MCP servers, notices, tool suggestions, and skill enablement.
- Surface changes made by `codex features`, `/experimental`, `/memories`, and
  other persistent UI commands as managed or reviewable drift according to the
  manifest.
- Keep `[otel]` repository-managed unless a later requirement introduces a
  legitimate runtime writer for it.

## Delivery sequence

### Phase 1: Establish the contract without changing deployment

- Write ownership manifests for all current fields.
- Add redacted semantic snapshot fixtures from all three clients.
- Add read-only `{client}-diff` and `ai-config-status` commands.
- Record unsupported or unknown fields as runtime-owned by default.

### Phase 2: Make push non-destructive

- Introduce atomic writers, private backups, validation, and postcondition
  checks.
- Replace Claude's blind copy.
- Replace Agy's generic recursive merge.
- Narrow Codex ownership to field paths.

### Phase 3: Add back-propagation

- Add Agy and Codex pull-review adapters.
- Extend Claude pull-review to emit the shared result model.
- Add the local decision ledger and portable path translation.
- Gate destructive managed replacements on unresolved reviewable drift.

### Phase 4: Tighten assurance

- Run adapter tests against pinned real-world fixtures.
- Add idempotency and round-trip property tests.
- Add schema drift detection for newly observed vendor keys.
- Document recovery from an invalid live file and restoration from backup.

## Acceptance criteria

The architecture is ready for implementation only when tests can demonstrate:

1. A repo-managed change reaches the live file on every client.
2. A runtime-owned change survives repeated pushes.
3. A reviewable live addition appears in `pull-review` and is not silently
   committed.
4. A managed deletion actually removes the field or list entry.
5. An unknown vendor field is preserved by default and reported safely.
6. Machine-local absolute paths are never committed without translation.
7. Secret values never appear in output, logs, fixtures, or repository patches.
8. Invalid input causes no write.
9. A failed write leaves the previous valid file recoverable.
10. Repeated reconcile operations are semantically idempotent.
11. Installed files remain private (`0600`).
12. The three client adapters can evolve independently without changing the
    common workflow contract.

## Explicit non-goals

- A universal schema for Claude, Agy, and Codex settings.
- Cross-vendor translation of permission syntax.
- Synchronizing credentials, OAuth state, histories, sessions, caches, or
  telemetry queues.
- Treating every user-interface preference as portable policy.
- Automatically committing or pushing pulled changes.
- Requiring the repository and live files to be byte-identical.

## Open decisions

Before implementation, the owner should decide:

1. Whether unresolved reviewable drift blocks `push` by default or only produces
   a prominent warning.
2. Whether UI preferences such as themes and status lines are personal portable
   policy or runtime-only state.
3. Where to store the local review-decision ledger and how long entries remain
   valid after a client upgrade.
4. Whether private backups should be retained by count, by age, or both.
5. Which vendor-provided schema or validation command is authoritative for each
   pinned client version.

## Result boundary

The result of this proposal is an architecture candidate: a shared lifecycle
contract with vendor-specific adapters and field-level ownership. Its receiving
use is the later decision and implementation plan for stable multi-machine AI
configuration. It is valid for that use only after the ownership manifests are
checked against current Claude, Agy, and Codex behavior and the acceptance tests
are agreed; this document alone does not establish those facts.
