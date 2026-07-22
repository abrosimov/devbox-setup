# Route RI2 — Always-on load audit (deep-dive)

**Status:** analysis complete 2026-07-21. Ready for user decision on demotions before implementation.
**Wave:** W1 (measure first).
**FPF position:** for W1, `selectedRoute = RI2`. `routeRationale`: *"RI1 established that always-on carries 119 rules (~60% of budget). RI2 asks: are those rules actually earning their always-on seat? If any fire for <80% of sessions, they should be demoted to trigger-loaded to free budget for W2 additions and reduce attention dilution."*
**Serves PCs:** PC8 (always-on load asymmetry) — primary; PC7 (instruction budget) — secondary (demotions free budget headroom for W2).
**Cost:** Low (static analysis of 5 skills + UAP; frontmatter reads, no code).

## Purpose

For each artefact currently loaded into every Claude Code session (as identified by RI1's `rules_budget_baseline.md`), decide:

- **Keep always-on** — the artefact is genuinely universal.
- **Demote to trigger-loaded** — the artefact is domain-scoped; a `description` + `triggers:` frontmatter is enough for it to fire when relevant.
- **Split** — the artefact mixes universal and scoped content; universal part stays, scoped part moves to a sibling skill.

## Method

Anthropic Skills progressive-disclosure guidance (`research_pattern_language.md` [26]) mandates that only level-1 (frontmatter) is universally loaded. `alwaysApply: true` overrides that discipline; each override needs an explicit rationale.

For each always-on artefact:

1. Read frontmatter (`description`, existing `triggers:`, `alwaysApply`).
2. Read first section of body (what the skill actually mandates).
3. Estimate scope of applicability: **universal** (every session) / **code-writing** / **config-editing** / **narrow**.
4. Classify: keep / demote / split, with rationale.
5. If demote: propose trigger keywords (or note "existing `triggers:` block is sufficient").

The 80% threshold from `routed_cue_set.md` is a design heuristic; without session-log mining we approximate it by asking *"is the artefact meaningful on the current session type?"* across the observed session shapes: (a) code writing, (b) config/config-editing, (c) architecture/design discussion, (d) planning/PM.

## Inventory (from `rules_budget_baseline.md`)

Six always-on artefacts:

| Artefact | Kind | Flat rules | Hard | Soft |
|---|---|---:|---:|---:|
| `USER_AUTHORITY_PROTOCOL.md` | uap | 56 | 12 | 44 |
| `skills/code-comments/SKILL.md` | skill | 21 | 5 | 16 |
| `skills/lint-discipline/SKILL.md` | skill | 21 | 5 | 16 |
| `skills/lsp-navigation/SKILL.md` | skill | 4 | 1 | 3 |
| `skills/project-preferences/SKILL.md` | skill | 11 | 3 | 8 |
| `skills/project-toolchain/SKILL.md` | skill | 6 | 2 | 4 |
| **Total** | | **119** | **28** | **91** |

## Per-artefact findings

### UAP (`USER_AUTHORITY_PROTOCOL.md`) — 56 rules

- **Scope:** universal. Governs approval flow, discipline, voice, git safety, language policy. Every session touches at least one of these axes.
- **Verdict: KEEP always-on.**
- **Note.** Largest single contributor at 47% of always-on budget. Splitting it (RS3, W4) is the main lever for budget reduction, not demotion. RI2 does not touch UAP.

### `code-comments` — 21 rules

- **Frontmatter description:** *"Rules for code comments and documentation. Covers narration comments (forbidden), acceptable WHY comments, and docstring policies."*
- **Scope:** code-writing only. On config sessions (like this one, editing markdown + Python scripts), Python-comment rules apply for ~10% of edits; markdown edits pull nothing from this skill.
- **Estimated fire rate:** ~40-50% of sessions (all code-writing + partial config); below 80%.
- **Verdict: DEMOTE to trigger-loaded.**
- **Proposed triggers:** `comment`, `docstring`, `narration`, `//`, `#`, `"""`, `/* */`. Description already discoverable via keyword match on "comments"/"documentation".

### `lint-discipline` — 21 rules

- **Frontmatter description:** *"Lint discipline rules — agents must fix lint issues, never suppress them with directives like noqa, nolint, or eslint-disable."*
- **Existing `triggers:` block:** `lint, linter, noqa, nolint, eslint-disable, ts-ignore, type: ignore, suppress, silence`. Already well-defined for trigger-loading.
- **Scope:** fires when lint output appears or suppression is considered. On non-code sessions (planning, architecture, design docs): zero relevance.
- **Estimated fire rate:** ~30-40% of sessions.
- **Verdict: DEMOTE.** Zero-cost change: flip `alwaysApply: true` → remove line. Existing triggers array does the loading.

### `lsp-navigation` — 4 rules

- **Frontmatter description:** *"Enforces LSP-first code navigation. Grep discovers files and text. LSP understands code."*
- **Scope:** code refactoring, symbol lookup, definition-following. On markdown/config sessions: not applicable (LSP does not understand these).
- **Estimated fire rate:** ~30% of sessions (code-writing subset that involves navigation).
- **Verdict: DEMOTE.**
- **Proposed triggers:** `symbol`, `definition`, `references`, `refactor`, `rename`, `implementation`, `call hierarchy`, `LSP`, `goToDefinition`, `workspaceSymbol`.

### `project-preferences` — 11 rules

- **Frontmatter description:** *"Project-specific conventions and opinionated choices. Library selections, tooling mandates, coding rules that differ from community defaults. Single source of truth — never duplicate these in other skills."*
- **Content mix:** British English rule (universal, applies to all persisted artefacts), Go library preferences (code-specific), Python tooling (code-specific), other stack-specific choices.
- **Scope:** the British English clause is genuinely universal — every persisted artefact (docs, plans, code, commits) is affected. The library-preference sections are code-specific.
- **Verdict: SPLIT.** Suggested breakdown:
  - `project-preferences` — keep always-on, contains ONLY the British English clause + any other truly universal choices.
  - `project-preferences-{go,python,frontend}` — new trigger-loaded skills for stack-specific library / tooling mandates. Fire via file-extension triggers (`.go`, `.py`, `.ts`).
- **Deferred to W3 or W4.** RI2 flags the split; execution belongs with the RC family / RS4.
- **Interim verdict: KEEP always-on.** Do not demote wholesale — the British English rule is load-bearing and must remain universal.

### `project-toolchain` — 6 rules

- **Frontmatter description:** *"Project toolchain detection and correct command prefixes per language. Prevents failures from bare tool invocations outside virtual environments."*
- **Scope:** any session running Bash tool commands (which is almost every session — reads, greps, tests, git ops, builds). Broadly applicable.
- **Estimated fire rate:** ~85% of sessions.
- **Verdict: KEEP always-on.** Cost (6 rules) is well matched to the failure-prevention value.

## Recommendations summary

| Artefact | Action | Rules freed |
|---|---|---:|
| UAP | Keep | 0 |
| `code-comments` | Demote | 21 |
| `lint-discipline` | Demote | 21 |
| `lsp-navigation` | Demote | 4 |
| `project-preferences` | Keep (split flagged for W3/W4) | 0 |
| `project-toolchain` | Keep | 0 |
| **Total demotion saving** | | **46 rules** |

**Post-demotion always-on budget:** 119 - 46 = **73 rules** (~37% of the 200-rule budget). Comfortable headroom for W2 (`problem:` + `related:` frontmatter additions do not add rules) and future universal-scope additions.

## Risks

- **False demotion.** If `code-comments` / `lint-discipline` / `lsp-navigation` fire less reliably than their descriptions suggest, agents may skip lint fixes / write narration comments / grep for symbols. Mitigation: strong descriptions and comprehensive `triggers:` blocks; monitor via `make eval-skills` after change.
- **Discoverability.** Demoted skills need explicit reference from downstream agents. `code-comments` is already declared in `skills:` frontmatter of every SE agent (`software_engineer_go/python/frontend.md` — verified in `agents/*.md` skills field). `lint-discipline` and `lsp-navigation` — verify presence before demotion.
- **British English enforcement gap.** Splitting `project-preferences` (W3/W4) risks losing the always-on British English rule if the split is done carelessly. The split must retain a universal-scope shell.

## Implementation plan

Not implemented in W1 — RI2 produces the audit only. Actual demotion edits belong to W2 or W3 (they are trivial frontmatter changes, natural to batch with W2's `related:` / `problem:` additions or W3's content edits).

### Prerequisites before demotion

- Verify each demotion candidate is referenced in the `skills:` frontmatter of every relevant SE / test-writer / code-reviewer agent.
- If not referenced, add the reference (so triggering happens even if description keywords miss).

### Change shape per demotion candidate

- `code-comments`: remove `alwaysApply: true`; add `triggers: [comment, docstring, narration, ...]`.
- `lint-discipline`: remove `alwaysApply: true` only — existing `triggers:` block is sufficient.
- `lsp-navigation`: remove `alwaysApply: true`; add `triggers: [symbol, definition, references, refactor, rename, LSP, ...]`.

### Validation

- Re-run `make rules-budget` — always-on flat should drop to 73.
- Re-run `make validate-claude` — no dangling references.
- Optional: `make eval-skills SKILL=code-comments` etc. to sanity-check trigger firing.

## Open questions (resolved 2026-07-21)

- **Q-RI2-1 — Timing.** → **W2** (fold demotions into the RS1/RS2/RS5 pass). All frontmatter changes in one deploy; single `make rules-budget` re-run after the wave gives the post-W2 metric cleanly.
- **Q-RI2-2 — `project-preferences` split.** → **W3, incrementally.** Universal shell (British English + persist-artefact rules) stays; language-specific spinoffs (`project-preferences-{go,python,frontend}`) created on demand as real need surfaces, not batch-front-loaded.
- **Q-RI2-3 — Reference verification tool.** → **Yes, add in W2.** New check inside `bin/validate_config.py`: for every skill declaring `triggers:` and referenced from an agent's `skills:`, the skill must appear in that agent's `skills:` list (guards against a demoted skill silently failing to load in agents that need it). Belongs with RS5's `related:` validator work.

## Next actions (after user decision on Q-RI2-1..3)

1. Move to W2 (`routed_cue_set.md`): `RS1` (`problem:` + `related:` frontmatter) → `RS2` (SKILLS-INDEX) → `RS5` (validate links).
2. Batch the RI2 demotions into the W2 frontmatter pass (per recommendation above).
3. After W2 completes, re-run `make rules-budget --baseline` — capture "post-W2" numbers for comparison.

## FPF anti-patterns to avoid (`CC-B.4.1-5`)

- **Optimising for a lower always-on count** at the cost of skill fireability. The number is a proxy for attention dilution — not a target to hit blindly.
- **Silent re-scoping.** Every demotion must record the *rationale* + *trigger set* so a future auditor can trace why the skill left always-on.
- **Scope creep into split work.** RI2 recommends splits but does not execute them — that is W3/W4 territory.
