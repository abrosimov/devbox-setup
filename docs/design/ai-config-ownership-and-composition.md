# AI configuration: ownership and composition

Research date: 10 September 2026. Repository evidence: `8553b576f060209a729e1062c0a7ce5fefb99f25`. Status: research and proposed design, not an accepted migration or an implemented contract. No application settings were changed for this study.

Implementation follow-up, 12 September 2026: the [Codex configuration guide](../../roles/devbox/files/dot_codex/README.md) describes the first bounded preference migration for reasoning effort. The inventory and proposals below remain the September 10 research snapshot; the full composition architecture and ownership of other fields have not been implemented by that pilot.

## Finding and recommendation

The recurring reconciliation is partly a consequence of the current contract. `shared` means a value can travel in either direction through a three-way merge. It does not mean that the repository owns the value. An application changing a shared preference therefore creates legitimate capture work, and deployment refuses to choose on the user's behalf. More templates alone would leave that behaviour intact.

Use an explicit ownership contract per tool and field, then compose the deployable document from repository policy, profile bindings, permitted local preferences and preserved application state. Ordinary deployment should only write deployment outputs and private deployment metadata. Importing a live preference into the repository should remain a separate, deliberate operation.

Retain the existing parsers, adapters, transaction machinery and behavioural tests where their contracts fit. Introduce ownership and composition incrementally; replacing the whole reconciler or adopting another dotfile manager is not justified by the evidence.

The detailed inventories are part of this study:

- [Claude Code: fields, files and native layers](ai-config-claude-boundaries.md).
- [Codex: fields, files and native layers](ai-config-codex-boundaries.md).
- [Reconciler and Antigravity CLI: mechanisms, coverage and limits](ai-config-reconciler-and-agy.md).

## What “constant” can mean

Three guarantees must be distinguished:

| Guarantee | Meaning | Feasibility here |
| --- | --- | --- |
| Source remains constant | Ordinary deployment and native preference persistence never import live values into repository declarations. | Enforceable by a deployment API that cannot write source files; deliberate edits by an agent or user with repository access remain possible. |
| Installed managed values converge | After successful deployment, the owned semantic fields equal the resolved source. | Enforceable at deployment time, subject to concurrent-writer limitations below. |
| Effective application behaviour remains constant | No project setting, profile, CLI option, UI action or running process can override the value. | Not implied by either guarantee above; needs tool-specific precedence and, where appropriate, actual managed policy. |

The recommended default is the first two guarantees. A writable user configuration file cannot provide continuous enforcement against the application that owns the same user account. Repeated background repair or read-only permissions would create a different operational system and can interfere with normal settings/state writes. This research does not recommend either.

Constancy is semantic: a telemetry destination, permission rule or hook command retains its declared meaning. JSON indentation, TOML table order and resolved home-directory strings need not be identical on two machines. The renderer should avoid unnecessary textual changes, but byte identity is not the ownership contract.

## Evidence: why the current workflow asks for attention

| Finding | Evidence | Consequence |
| --- | --- | --- |
| Shared fields support capture from live. | [core.py](../../scripts/ai_config/core.py), `_plan_field`; [resolution.py](../../scripts/ai_config/resolution.py), apply resolution. | An unchanged source plus changed live value is not an ordinary successful apply. |
| Unknown fields block writes for the engine. | [service.py](../../scripts/ai_config/service.py), unknown-field guard. | A vendor-added field outside the intended managed set can obstruct unrelated deployment. |
| The baseline depends on raw manifest bytes. | [state.py](../../scripts/ai_config/state.py), manifest fingerprint and baseline loading. | A formatting change or unrelated rule change can invalidate the comparison baseline. |
| Ordered-set merges can update both repository and live documents during apply. | [resolution.py](../../scripts/ai_config/resolution.py), `_apply_merged_change`; [service.py](../../scripts/ai_config/service.py), file write construction. | `apply` is not currently a strict one-way deployment interface. |
| Decisions identify a path and source, without binding to the reviewed values. | [decisions.py](../../scripts/ai_config/decisions.py), `FieldDecision` and parser. | Reusing an old decision file can select a newer value that was never reviewed. |
| Syntax/read-back validation is not native settings validation. | [service.py](../../scripts/ai_config/service.py), `_FormatValidator`; [document.py](../../scripts/ai_config/document.py), `validate_document`. | Valid JSON/TOML can still be ignored, misinterpreted or rejected by the client. |
| Settings are only part of deployment. | [install_configs.yml](../../roles/devbox/tasks/install_configs.yml), [install_codex_configs.yml](../../roles/devbox/tasks/install_codex_configs.yml), [apply_configs.yml](../../roles/devbox/tasks/apply_configs.yml). | Hooks, executable helpers, agents, skills, plugins and MCP registration need ownership too. |
| Claude MCP cleanup targets undeclared names, with an exception for `claude.ai ` registrations. | [apply_configs.yml](../../roles/devbox/tasks/apply_configs.yml), MCP diff and removal tasks. | A manually added user-scope server can be selected for removal even if settings composition preserves all local fields. |
| Some helper/skill directories use synchronisation with deletion. | [install_codex_configs.yml](../../roles/devbox/tasks/install_codex_configs.yml), bin and named skill synchronisation; [install_configs.yml](../../roles/devbox/tasks/install_configs.yml), agy helpers. | Local files inside those managed destinations are not protected by the settings manifest. |

These are observed code behaviours, not claims that every branch has caused a user incident. The earlier intent of the reconciler was to prevent silent overwrites; its caution is valuable for ambiguous ownership. The mismatch is using the same bilateral mechanism for values now intended to be fixed.

A read-only inspection of the personal machine during this investigation found one Codex `capture-live` field, `model_reasoning_effort`; the remaining reported Codex and Claude changes were source-to-live updates. Antigravity had no reported changes. This illustrates the mechanism, but does not establish the frequency or causes of interruptions on the work machine. Values and local paths are intentionally omitted.

## Ownership model

Declare ownership separately from storage format, merge behaviour, sensitivity and the actor that can write the file. An application may technically rewrite a repository-owned value; that does not automatically make the value local policy.

| Class | Source of the intended value | Ordinary deployment | Import to repository |
| --- | --- | --- | --- |
| Repository-owned | Reviewed source for this tool | Restore its resolved value; report meaningful drift without asking for a merge decision | Never automatic |
| Environment-bound | Reviewed recipe plus selected `personal`/`work` profile, home path or secret provider | Resolve and validate on this machine | Recipe only; never resolved secrets or machine paths |
| User preference | Explicit local overlay, with optional repository default | Preserve a valid local choice; fill a default only when absent | Explicit selected-field export |
| Application state | Application, project trust flow or session | Preserve; initialise only through the application's supported mechanism | Excluded |
| Unclassified live data | Unknown until investigated | Preserve only when structurally disjoint from owned fields; report | Excluded pending classification |

“Dynamic” does not mean arbitrary. Each locally overridable setting needs a type, allowed scope, fallback and deletion/reset behaviour. For example, a local model preference may be permitted while a local telemetry endpoint override is prohibited. There is no implicit priority rule allowing the local overlay to replace every field.

Permissions, sandbox restrictions, command execution, trust decisions and credential references require individual classification. A broad `permissions` or `plugins` ownership rule is often too coarse: repository-installed entries and user-installed entries can coexist under that object. Application state includes trust approvals even when they happen to be stored in the main config.

The per-tool appendices propose candidates. They do not authorise changing the current ownership of model, reasoning effort, plugin enablement or permission additions. Those choices have visible user consequences and must be settled before migration.

## Composition contract

Conceptually, compose `C = compose(tool, policy, profile, local, live, ownership)`:

1. Parse and validate the source and ownership declarations. Reject unknown source keys, unsupported declarations and overlapping rules with ambiguous ownership.
2. Resolve profile/home/secret bindings from declared providers. Missing required bindings stop the plan; they must not silently select another environment.
3. Read local preferences and the live document. Validate local choices against their allowed fields. Preserve application state and unrelated live data.
4. Assign repository-owned and environment-bound values. Apply local overrides only to explicitly overridable preferences. Apply defaults only to absent preferences.
5. Validate the complete candidate, its ownership projections and cross-file references. Produce a redacted plan with reasons and restart/reload requirements.
6. Commit using the existing transaction foundation, then verify the installed candidate. A second identical apply should do no work.

Required invariants:

```text
owned_projection(candidate) == resolved_owned_source
preserved_projection(candidate) == preserved_projection(live)
repository_after_apply == repository_before_apply
compose(same_inputs) == same_candidate
apply(apply(inputs)) == no_change
```

The preservation invariant concerns fields outside the deliberately changed ownership set. It must cover absent values, explicit nulls where supported, unknown nested objects and list order. A parent object changing into a scalar can destroy descendants; that is a structural conflict, even if a superficial path matcher calls them unrelated.

### What to template

Keep each tool's source document in its native vocabulary. Share the composition machinery and ownership concepts, not a fictional common schema translating all permissions, models or hooks between vendors. Parameterise known environment differences such as the active profile and home path. Keep portable commands and policy declarations as reviewed source. Do not template application-generated trust, history or cache state.

For example, if the user chooses to make Codex reasoning effort a local preference, its source value becomes a default and the local choice survives deployment. If the user chooses to keep it fixed, deployment restores the source value and reports that restoration. Both outcomes are deterministic; a template cannot choose between them. Meanwhile `otel.environment` resolves from the selected profile, and project trust remains application state regardless of the reasoning-effort choice.

Split source files only where the split expresses a useful responsibility: tool base, profile bindings, local preferences and ownership declaration. Assemble a candidate in a temporary location during deployment and validate it before installation. These are composer inputs, not a claim that any client automatically reads an arbitrary `config.d` directory. A single native source file plus a small binding map may be sufficient for a tool with few differences.

### Lists, removal and identity

Every collection needs an explicit operation: atomic replacement, ordered set, or keyed entries with stable identity. Do not default to recursive dictionary merge plus list concatenation.

JSON Merge Patch replaces arrays as a whole and treats `null` as deletion; it does not supply field ownership or item identity. It is useful as a reference for precise operations, not a sufficient composition contract. [RFC 7396](https://www.rfc-editor.org/rfc/rfc7396.html)

JSON Patch supplies explicit remove/replace operations and value tests, which can express a reviewed change more precisely. Its array addresses are positional, so a concurrent insertion can change their meaning. Use stable entry identity and input fingerprints in our plan; choosing a patch format alone supplies neither ownership nor a filesystem transaction. [RFC 6902](https://www.rfc-editor.org/rfc/rfc6902.html)

For repository-owned collections, absence in the declared desired collection removes previously owned entries. For mixed collections, remove only entries with recorded repository ownership. Hooks need stable identity and deliberate ordering; permission removal must not be undone by set union. Local preference reset needs an explicit operation distinct from “overlay omitted this field”.

Object paths should be arrays of segments internally. A dotted marketplace or plugin identifier is one literal key, not a hierarchy. Existing manifest support for segment arrays should be retained.

### Unknown data and newly claimed fields

Preserving unknown live data is not permission to let it override a fixed setting through another native layer. File composition and effective-configuration checking are separate responsibilities.

Unknown source fields should fail as likely mistakes. Unknown live fields outside the ownership boundary should normally produce a non-blocking diagnostic. Unknown children inside a closed owned object, parent/type collisions, duplicate entry identities and unsupported schema versions require a scoped error. A vendor upgrade should not automatically extend our ownership to newly introduced descendants.

Changing ownership is a migration. Record the old and new ownership contract and show which existing local values would be displaced. Do not infer ownership from a field appearing in the source for the first time. Losing ownership should normally preserve the last installed value until a separately declared removal is chosen.

## Native layers: useful, but tool-specific

Native layering can reduce how often devbox touches an application-written file. It must first pass an adapter-specific test for precedence, array semantics, discovery paths, UI writes and supported client versions. The appendices hold the detailed primary documentation and version evidence.

| Tool | Promising native mechanism | Boundary that prevents a universal solution |
| --- | --- | --- |
| Claude Code | User/project/local settings and explicit session settings | Project local settings are not a general home-local overlay. Session settings have high precedence. Additive lists and hook loading need explicit tests. Enterprise policy is a different authority. |
| Codex | Separate named profile files on the verified current CLI; user/project configuration | Host settings are not all accepted at project scope. Hooks can accumulate. The app can also write user configuration. Profile selection must match CLI, IDE and app behaviour. |
| Antigravity CLI | Documented global/project settings | Installed-version evidence and detailed merge/reload semantics are narrower; Gemini CLI behaviour cannot be assumed to apply. |

Native layers do not necessarily implement “fixed base plus local exceptions” in the desired direction. If an effective restriction must survive project/CLI overrides, choose and verify the actual policy facility supported by that tool. A generated user config should not be advertised as enforcement.

## Architecture options

| Option | Benefit | Cost or failure mode | Assessment |
| --- | --- | --- | --- |
| Run current reconcile automatically before Make | Minimal wiring | Automates source capture and unresolved ownership; can still conflict | Reject as the default fix |
| Render and overwrite whole user files | Deterministic source output | Displaces preferences, trust and vendor state | Suitable only for exclusively owned files |
| Native layers only | Less shared-file writing | Different coverage and merge rules per client; does not manage adjacent assets | Use selectively after capability checks |
| Ownership-aware composition with tool adapters | Explicit preservation and deterministic managed fields; builds on existing code | Requires migration and collection semantics | Recommended common mechanism |
| Replace with a dotfile manager | Existing templating and deployment ecosystem | Ownership policy and application-specific validation still needed | No evidence of sufficient benefit for migration now |

Chezmoi supports machine-specific rendering and a merge workflow when destination and target differ. That addresses generation and user-mediated differences; it does not by itself decide which AI-tool fields must remain fixed. [Machine differences](https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/), [merge workflow](https://www.chezmoi.io/user-guide/tools/merge/)

Kubernetes Server-Side Apply is a useful analogy for field ownership and collection identity. Its API server tracks managers and conflicts; local files do not have that coordinating authority. Borrow explicit ownership concepts, not claims of equivalent concurrency guarantees or the Kubernetes infrastructure. [Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/)

## Deployment and concurrency boundaries

Compose during `make work`/`make personal`, with a reusable read-only planning operation for preflight. Avoid adding a prerequisite manual reconcile for routine drift. Avoid composing on every application launch until there is a demonstrated need: startup wrappers introduce another writer and can miss IDE/GUI entry points.

The settings phase should first plan and validate all selected AI engines and owned assets, then install. Today an engine-level transaction does not make the whole Ansible playbook atomic. A failure after earlier hooks or assets have been copied can leave a partial deployment. The implementation plan must either introduce a single bounded AI configuration installation phase or explicitly report partial application with recovery instructions.

The existing transaction implementation provides an advisory lock in engine/profile state, expected-source checks, staged files, a journal, backups, read-back verification and rollback. Preserve those mechanisms. Its lock coordinates participating reconciler processes using that state directory; it does not lock out a client or a different profile targeting the same file. A composition transaction should coordinate by actual destination identity as well. Expected-byte checks occur before installation and cannot close every interval between a check and a rename. [Transaction implementation](../../scripts/ai_config/transaction.py), [state paths](../../scripts/ai_config/state.py)

Therefore do not promise zero lost writes while arbitrary clients concurrently edit a shared file. Prefer native separation where proven; otherwise use bounded detection/replanning, refuse known active writes, and surface the residual race. Re-check before rollback and preserve detected third-party changes; that check still leaves a check-to-rename race. A strict guarantee may require a quiescent application or a supported client API. Atomic rename prevents partial-file reads, not logical lost updates or atomic visibility across files.

A capability record per tool should state supported versions, accepted files, validation method, reload method and whether a new session is needed. There is no established generic `SIGUSR` reload contract for these tools. Do not signal applications speculatively. A successfully installed file is not proof that an existing session adopted it.

### Adjacent assets

Track ownership for hook definitions and helpers, custom agents, skills, plugin declarations/installations and MCP registrations. Use named entries or an installation inventory for shared directories. Never infer that every file in a tool's home belongs to devbox. Credentials, sessions, caches, histories and trust records remain outside portable source.

Private backups of a mixed live file may contain sensitive data even when the portable projection does not. Keep them outside Git with restrictive permissions and a defined retention policy. Redaction must cover plans, errors, exported patches and test artefacts, not only the final source document.

A hook file's existence is not proof of registration; a configured plugin is not proof of installation; an MCP declaration is not proof of authentication or successful connection. Validate these as separate stages and avoid running real hooks or remote MCP services in the cheap deployment preflight.

## Migration without a new daily ritual

1. Agree ownership for the ambiguous preference and mixed-collection fields listed below. Version the manifest semantics independently from its textual formatting.
2. Add a composition plan operating on fixtures and temporary homes. Keep current deployment unchanged while comparing old and proposed classifications.
3. Make deployment source-read-only. Move any repository updates behind selected-field export with a preview bound to source/live/manifest inputs. Preserve the explicit import path for intentional edits.
4. Implement semantic manifest migration: unchanged rules retain their state; newly claimed fields get an explicit adoption plan. Treat disappearance, changed type and changed collection identity separately.
5. Introduce the candidate validation and installation phase into AI deployment. Retain old state and a recoverable migration record; do not bootstrap every existing live value into source.
6. Rehearse on synthetic personal/work homes, then separately on each real machine. Check both install results and a fresh client session. A successful personal run does not establish work compatibility.

The desired routine is one Make command. Explicit reconciliation remains for changing ownership or promoting a local preference, not for accepting every ordinary application write. Previously unclassified dangerous collisions may still require attention; removing all errors would weaken the contract.

## Verification plan

These are proposed acceptance tests, not claims of existing coverage. The inspected current core/service/transaction/CLI/property, AGY manifest and Claude/AGY deployment suite passed **165 tests in 5.60 seconds** using the existing environment and temporary fixtures. This is a scoped baseline, not a full CI rerun or proof of the proposed behaviour. The reconciler appendix records its limits.

| Level | Scenario | Required observation |
| --- | --- | --- |
| Pure composition | Application changes a fixed field | Apply restores owned value, leaves source and unrelated state unchanged |
| Pure composition | Application changes an allowed preference | Choice survives repeated apply without a reconciliation prompt |
| Pure composition | New unknown sibling vs conflicting parent | Sibling survives with a diagnostic; destructive structural collision fails before writes |
| Pure composition | Remove permission/hook/plugin entry | Owned removal takes effect; unrelated local entry survives; no accidental union resurrection |
| Pure composition | Null, absent, empty list, dotted key, reordered object | Correct distinct semantics and deterministic result |
| Profile fixtures | Personal/work and different home roots | Correct bound values; no cross-profile leakage or captured absolute paths |
| Failure fixtures | Missing secret or invalid local override | No target write and no secret value in output, journal metadata or exported source |
| Migration fixtures | Formatting-only manifest change; claim/release field | No broad reset for formatting; explicit and bounded ownership transition |
| Transaction subprocess | Competing deployers, app write during preparation/installation/rollback | Proven handling at instrumented boundaries; residual non-cooperating race documented |
| Failure injection | Invalid candidate, disk/rename/read-back failure, interruption | Recoverable state; no silent partial success or destruction of newer external data |
| Deployment fixtures | First and second complete AI install | First produces valid owned assets; second changes nothing; repository remains byte-identical |
| Native loader fixture | Project/profile/CLI override and duplicate hooks | Effective precedence matches capability record; hooks do not execute twice |
| Version fixture | Supported minimum/current client and unknown future field | Supported configurations load; incompatible behaviour fails with a specific capability error |
| Real machine | New session after deployment | Client loads intended configuration; trust/auth remain usable; per-engine reload limits recorded |

Run offline syntax, manifest, composition and deployment-fixture tests before any write to real homes. Use repository test targets and pinned environments. Native probes must use isolated homes, known-safe hooks and inert MCP definitions; if an isolation method is not established, keep the probe out of automatic preflight. Authenticated requests, plugin downloads and remote telemetry checks are a separate explicit integration step.

Measure improvement with a small replay corpus: fixture count requiring manual decisions before/after, unrelated state changes, source writes during apply, idempotence and validation latency. The target is zero decisions for agreed routine fixed-field drift and local preference changes, zero source writes during apply, and zero unrelated state loss. No measured reduction percentage is available yet.

## Decisions needed before implementation

| Choice | Proposed starting position | Why it needs an explicit decision |
| --- | --- | --- |
| Model, reasoning effort, service tier, UI preferences | Repository default with an allowed local override where desired | Keeping these fixed means a UI change will be reverted at the next deployment |
| Permission additions and extra directories | Repository baseline plus explicitly declared local entries only if semantics are proven | Extra permissions change effective access; collection union complicates revocation |
| Plugin and marketplace entries | Own devbox entries by identity; preserve unrelated installations | Whole-object ownership can remove user choices; additive loading can duplicate hooks |
| Fixed-file values vs enforced effective behaviour | Convergence of installed fields by default | Enforcement against project/CLI layers is a separate policy requirement |
| Deployment while clients are writing | Native separation where verified; otherwise explicit race handling and limits | A local advisory lock cannot make an uncooperative writer transactional |

These choices do not prevent defining the architecture or building fixture coverage. They prevent honestly claiming a completed migration before the user's intended policy has been expressed.

## Evidence limits and source use

The repository audit covers the current three manifests, reconciler modules, deployment wiring and relevant tests. Tool appendices distinguish official documentation from local version evidence, unverified native behaviour and proposed ownership. This is not an enumeration of every setting each vendor has ever supported, nor proof of the effective configuration in every project/session.

External documentation was checked on the research date. The linked primary sources establish vendor and format behaviour; the ownership model, migration and acceptance criteria are this study's proposals. Re-check version-sensitive capabilities before implementing native layering. Real work-machine state, concurrent client behaviour and all native loading paths have not been exercised by this research.
