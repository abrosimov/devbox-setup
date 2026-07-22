# Route W2 — Structural quick wins (deep-dive)

**Status:** planning; open questions Q-W2-1..3 must be resolved before implementation.
**Wave:** W2 (structural — the Alexander insight the current config genuinely lacks).
**FPF position:** `selectedRoute = {RS1, RS2, RS5} + RI2-demotions + Q-RI2-3-validator`. `routeRationale`: *"W1 confirmed budget headroom (73/200 after demotions). W2 spends part of that headroom on the one durable structural gain: typed cross-links between skills/agents/commands. Batched with RI2 demotions and the trigger-consistency validator because all three are frontmatter-level changes over the same file set."*
**Serves PCs:** PC6 (cross-link discoverability) primary; PC7/PC8 secondary via folded-in RI2 demotions.
**Cost:** Med (touches 40 skills + 28 agents; each edit is small but there are many).
**Depends on:** W1 complete (RI1 baseline + RI2 audit).

## Scope (5 sub-routes, one wave)

| Sub-route | Origin | What it does |
|---|---|---|
| **RS1** | routed_cue_set | Add `problem:` + `related:` optional fields to skill/agent frontmatter |
| ~~**RS2**~~ | routed_cue_set | ~~Generate `SKILLS-INDEX.md` cross-index from the `related:` graph~~ (dropped 2026-07-22 — see Q-W2-2 reversal) |
| **RS5** | routed_cue_set | Extend `make validate-claude` to validate `related:` links |
| **RI2-demotions** | Q-RI2-1 = W2 | Flip `alwaysApply: true` on 3 skills; add `triggers:` where needed |
| **Trigger-consistency validator** | Q-RI2-3 = W2 | New check in `bin/validate_config.py` (see below) |

Q-RI2-2 (project-preferences split) is deliberately **not** in W2 — deferred to W3 per user decision.

## Concrete change list

### RI2 demotions (3 skills)

Edits confined to frontmatter of:

- `skills/code-comments/SKILL.md` — remove `alwaysApply: true`; add `triggers: [comment, docstring, narration, "//", "#", "\"\"\"", "/* */", "# type:"]`.
- `skills/lint-discipline/SKILL.md` — remove `alwaysApply: true` **only** (existing `triggers:` array already covers lint/noqa/etc).
- `skills/lsp-navigation/SKILL.md` — remove `alwaysApply: true`; add `triggers: [symbol, definition, references, refactor, rename, implementation, "call hierarchy", LSP, goToDefinition, workspaceSymbol, findReferences]`.

**Preconditions:**

- Verify `code-comments` is in `skills:` list of every agent that writes code (`software_engineer_*`, `unit_tests_writer`, `integration_tests_writer_*`, `tdd_guide`, `refactor_cleaner`). Add where missing.
- Same for `lint-discipline` (same set of agents).
- Same for `lsp-navigation` (SE + reviewer agents).

### RS1 — `problem:` + `related:` frontmatter

For every skill and every agent:

- **`problem:`** — one-line statement of the problem the artefact solves. Optional; skip when trivial. Discovery aid.
- **`related:`** — list of skill/agent names logically adjacent. Optional; empty list allowed.

Existing frontmatter fields are preserved; new fields added below existing keys.

Discovery pass (before edits): grep for existing prose "see also" / "related" / "companion" mentions across skills and agents to seed the `related:` graph from what is already documented informally.

### RS2 — `SKILLS-INDEX.md`

New script: `bin/build_skills_index.py`. Reads `related:` from every skill/agent frontmatter and emits `~/.claude/SKILLS-INDEX.md`:

- Alphabetical skill list with one-line `description` + `related:` links.
- Per-family cluster view (grouping via a new `family:` field or inferred from directory).

Makefile target: `make skills-index` (regenerates on demand). Regeneration is deterministic and idempotent.

### RS5 — validator extension

Extend `bin/validate_config.py` with two new checks:

1. **`related-links`** — every name in a `related:` list resolves to an existing skill or agent.
2. **`trigger-consistency`** (Q-RI2-3) — for every agent listing a skill in `skills:`, if that skill declares `triggers:`, the agent's presence in the skill's use-context is coherent (skill referenced from every agent that plausibly needs its triggers; conservative — warn, don't fail).

Reflect both in `make validate-claude` output.

## Sequencing inside W2

Waterfall inside the wave, because each step consumes the previous step's output:

1. **Preflight** — grep-based scan to seed `related:` graph and verify precondition references (agents `skills:` fields).
2. **RI2 demotion preconditions** — add missing `skills:` entries to agents that need `code-comments` / `lint-discipline` / `lsp-navigation`.
3. **RI2 demotions** — flip `alwaysApply` on the 3 skills, add `triggers:`.
4. **RS1 edits** — add `problem:` + `related:` frontmatter across skills and agents. Batch by directory to keep review-able.
5. **RS5 validator extension** — write new checks; must pass on current tree.
6. **RS2 index generation** — script + Makefile target; first run produces `SKILLS-INDEX.md`.
7. **Validation** — `make validate-claude` + `make rules-budget --baseline` (write post-W2 baseline for comparison).
8. **Report** — record post-W2 numbers here; append to state log in `README.md`.

## Deliverables

1. Edits to `skills/*/SKILL.md` (frontmatter).
2. Edits to `agents/*.md` (frontmatter).
3. `bin/build_skills_index.py` + tests.
4. `bin/validate_config.py` extensions + tests.
5. `SKILLS-INDEX.md` at config root (generated).
6. `rules_budget_post_w2.md` (comparison baseline).
7. `make skills-index` Makefile target.

## Success criteria

- `make validate-claude` — PASS with 0 errors, warnings acceptable and explained.
- `make rules-budget` — always-on flat count drops from 119 to ~73 (±5 for accidental changes).
- `SKILLS-INDEX.md` regenerates identically on repeated runs (deterministic).
- Every existing skill/agent still validates; no accidental breakage.

## Anti-patterns to avoid (`CC-B.4.1-5`)

- **Over-linking.** `related:` is not "everything vaguely adjacent" — a link is a promise that following it is useful. If in doubt, omit.
- **Frontmatter bloat.** `problem:` must fit on one line. Description ≠ problem; do not repeat the description.
- **Silent semantic drift on `triggers:`.** When adding `triggers:` to a demoted skill, verify against Anthropic's Skills documentation shape — do not invent a variant.
- **Coupling RS2 to specific rendering.** `SKILLS-INDEX.md` is markdown for humans; do not use it as machine input (that is what the frontmatter itself is for).

## Open questions (resolved 2026-07-21)

### Q-W2-1 — Batch size per iteration

- **A.** All-in-one: edit all 40 skills + 28 agents in one session. Fastest, but review-heavy.
- **B. (Recommended)** Two-phase: (i) all skills, then (ii) all agents. Each phase ends with `make validate-claude`; blast radius contained.
- **C.** Per-family batches (SE agents, then test writers, then reviewers, then designers, then meta). Slowest, most review-able.

**→ Decision: B.** Skills first (Phase 1: 40 SKILL.md + RI2 demotions on 3 of them). Checkpoint via `make validate-claude` + `make rules-budget` — always-on flat count must drop 119 → ~73. Then agents (Phase 2: 28 agent .md + `skills:` list updates for demoted-skill preconditions). Second checkpoint. Deploy via `make claude-push` once, at the end.

### Q-W2-2 — Where should `SKILLS-INDEX.md` live?

- **A. (Recommended)** `~/.claude/SKILLS-INDEX.md` (config root — colocated with `USER_AUTHORITY_PROTOCOL.md`). Discoverable at the same level as the authority protocol.
- **B.** `~/.claude/skills/INDEX.md` (inside skills tree). More localised; but agents currently do not enter that directory in normal use.
- **C.** `~/.claude/docs/SKILLS-INDEX.md` (docs directory). Consistent with other reference docs; loses colocation with the artefacts it indexes.

**→ Decision: A.** Source: `roles/devbox/files/dot_claude/SKILLS-INDEX.md` → deployed to `~/.claude/SKILLS-INDEX.md`. Colocated with `USER_AUTHORITY_PROTOCOL.md`. `make skills-index` regenerates it. **File must be listed in `install_configs.yml` Block 2** (copy loop for `.claude/` root files) so `make claude-push` deploys it. Add to `.gitignore`? No — commit the generated file so drift is visible in review; the source-of-truth is the frontmatter graph, but the rendered index goes with the repo.

**Reversal (2026-07-22).** Q-W2-2 rescinded — the rendered index adds no signal Claude actually uses (skill `description:` is already visible via the Skill tool; the related graph lives in frontmatter and is validated by `related-links`). Deleted `bin/build_skills_index.py`, `bin/test_build_skills_index.py`, `SKILLS-INDEX.md`, the `make skills-index` target, and the `install_configs.yml` Block 2 deploy hook. RS2 dropped from W2 scope. The `related:` graph remains authoritative in frontmatter; humans can `grep related:` or run a bespoke query when they need cluster views.

### Q-W2-3 — Seeding the `related:` graph

- **A. (Recommended)** Grep-first: extract existing "see also" / "companion skill" prose mentions across skills+agents, hydrate `related:` from those. Then iteratively add more where obviously missing.
- **B.** Manual curation only — read each skill top-to-bottom and decide `related:` from scratch. Highest quality, highest cost.
- **C.** Automatic keyword-cluster inference — cluster skills by shared vocabulary. Cheap but noisy; risks the "everything vaguely adjacent" anti-pattern.

**→ Decision: A.** Preflight step scans for the patterns: `see also`, `companion`, `related`, `see the .* skill`, backtick-quoted skill/agent names inside prose. Hydrate `related:` from that harvest. Iterative refinement is welcome but not part of the initial seed — an obvious gap is a note in the deep-dive, not a session-blocker.

## Preflight findings (2026-07-21)

Ran grep-based scan per Q-W2-3 = A. Two substantive findings surfaced beyond seed-graph harvesting; both changed the plan.

### Finding 1 — LSP skill duplication

`lsp-navigation` (always-on, 4 rules, 0 agents reference it in `skills:`) and `lsp-tools` (trigger-loaded, referenced by every SE / test / reviewer agent) cover overlapping ground. Not two skills — one skill's content spread across two files.

### Finding 2 — Demotion precondition gaps

| Skill | Missing from `skills:` of |
|---|---|
| `code-comments` | tdd_guide, refactor_cleaner, build_resolver_go |
| `lint-discipline` | unit_tests_writer, integration_tests_writer_{go,python}, tdd_guide, refactor_cleaner, build_resolver_go |

### Finding 3 — Related graph seed is thin

Grep harvested ~15 explicit see-also edges. Enough to seed but not to populate. Consistent with Q-W2-6 = A choice (minimal graph, grow organically).

## Additional open questions surfaced by Preflight (resolved 2026-07-21)

### Q-W2-4 — LSP duplication

- **A. (Recommended)** Merge `lsp-navigation` → `lsp-tools`; delete `lsp-navigation` directory.
- B. Demote `lsp-navigation` and add to 10 agents.
- C. Show side-by-side diff first.

**→ Decision: A.** Rationale: no agent references `lsp-navigation` in `skills:`, so deletion is safe under `validate-claude`. Merging pulls its 4 rules into `lsp-tools` (already trigger-loaded on every code agent). Net effect: 4 rules leave always-on budget, no new agent frontmatter edits needed for the LSP demotion. RI2's "demote lsp-navigation" step simplifies to "merge and delete".

### Q-W2-5 — Precondition fixes

- **A. (Recommended)** Add `code-comments` to tdd_guide, refactor_cleaner, build_resolver_go. Add `lint-discipline` to all 6 missing agents.
- B. Only critical (test-writers + refactor_cleaner).
- C. None — rely on triggers.

**→ Decision: A.** All 6 gaps closed before demotion so post-demote behaviour matches pre-demote for those agents. Cost: ~9 skill-list line edits across 6 agents.

### Q-W2-6 — Related-graph seeding depth

- **A. (Recommended)** Minimal (~15 grep-seeded edges); grow organically as artefacts are touched.
- B. Full adjacency (~60 edges) inferred now.
- C. Skip `related:` in W2; do `problem:` only.

**→ Decision: A.** `related:` gets populated for the 15 grep-known edges; empty for the rest. `problem:` gets a real one-line value derived from each artefact's existing `description:`. Growth is organic; PC6 (discoverability) is served by the presence of the field + the mechanism (validator + index), not by graph density on day 1.

## Revised sequencing (post-Preflight)

1. **Phase 1a — LSP merge (Q-W2-4).** Read `lsp-navigation/SKILL.md` + `lsp-tools/SKILL.md`; merge non-duplicate content into `lsp-tools`; delete `skills/lsp-navigation/`.
2. **Phase 1b — RI2 demotions.** Flip `alwaysApply` on `code-comments` + `lint-discipline`; add `triggers:` to `code-comments`.
3. **Phase 1c — Skills frontmatter batch.** Add `problem:` + `related:` to remaining 39 SKILL.md files (after merge; excludes agent-base-protocol changes to structure). Grep-seeded edges populated; others empty `[]`.
4. **Phase 1 checkpoint.** `make validate-claude` + `make rules-budget` — expect always-on drop 119 → ~73.
5. **Phase 2a — Precondition fixes (Q-W2-5).** Add `code-comments` and `lint-discipline` to `skills:` lists of the 6 named agents.
6. **Phase 2b — Agents frontmatter batch.** Add `problem:` + `related:` to all 28 agent .md files.
7. **Phase 2 checkpoint.** `make validate-claude`.
8. **Phase 3a — Validator extensions.** Extend `bin/validate_config.py` with `related-links` + `trigger-consistency` checks. Tests.
9. **Phase 3b — Index generator.** Write `bin/build_skills_index.py` + tests + `make skills-index` target.
10. **Phase 3c — Deploy hook.** Add `SKILLS-INDEX.md` to `install_configs.yml` Block 2 (copy loop for root `.claude/` files).
11. **Final checkpoint.** `make validate-claude` + `make rules-budget --baseline` → `rules_budget_post_w2.md`. `make claude-push` (user runs).

## Execution strategy — Q-W2-7 (resolved 2026-07-21)

- **A. (Recommended)** Script-driven bulk: `scripts/apply_w2_frontmatter.py` + data-table.
- B. Subagent per phase.
- C. Split into next session(s).

**→ Decision: A.** Concrete plan:

- **Data table** — `future_projects/claude_tuning/w2_frontmatter_data.yaml`. Shape: `{skills|agents}[name] = {problem: str, related: [str, ...]}`. Sparse — omitting `related` means `[]`. Authored via subagent (reads all 67 artefacts once, drafts entries, returns YAML) to preserve main context. User reviews before apply.
- **Script** — `scripts/apply_w2_frontmatter.py` (repo-root; developer tool, not deployed). Reads YAML, patches frontmatter in-place. `--dry-run` prints unified diff. Idempotent (running twice = no diff on second run). Refuses to overwrite existing `problem:` / `related:` unless `--force`.
- **Authoring rule for `problem:`.** One line, 12-20 words, framed as *"the problem this artefact addresses"* — not a paraphrase of `description:`. Discovery aid, not another summary.

## Once Q-W2-7 answered, next actions

1. Execute the revised sequencing per chosen strategy (Phase 1a manual → apply script + data table → precondition fixes → validator + index).
2. Update `README.md` state log; record post-W2 baseline for comparison; move to W3 (content edits — RC1-RC6 + `project-preferences` split).

## Infrastructure session (2026-07-21, late)

Everything except the frontmatter batch is now ready. Tomorrow's single decision: **approve `w2_frontmatter_data.yaml`**, then run the pre-baked commands.

Delivered:

- `future_projects/claude_tuning/w2_frontmatter_data.yaml` — 67 entries (39 skills + 28 agents). 100% `problem:` filled. 163 `related:` edges seeded from grep of prose (backticked names, disambiguation notes, pipeline handoffs).
- `scripts/apply_w2_frontmatter.py` — dev tool. `--dry-run` prints unified diff. Idempotent. Refuses overwrite without `--force`. 11 tests in `tests/scripts/test_apply_w2_frontmatter.py`.
- `bin/validate_config.py` — extended with `related-links` (error on dangling ref) and `trigger-consistency` (warn on unreachable trigger-loaded skill). 14 new tests. Registered in `ALL_CHECKS`.
- ~~`bin/build_skills_index.py` + tests + `make skills-index` target + `install_configs.yml` Block 2 hook~~ — deleted 2026-07-22 (see Q-W2-2 reversal). RS2 dropped; related-graph stays in frontmatter, `related-links` validator enforces integrity.
- **Phase 2a preconditions applied** — `code-comments` + `lint-discipline` added to `skills:` of `tdd_guide`, `refactor_cleaner`, `build_resolver_go`, `unit_tests_writer`, `integration_tests_writer_go`, `integration_tests_writer_python`.
- **Phase 2a extension (2026-07-22)** — trigger-consistency warning surfaced `self-contained-options` as unreachable via the agent trigger-path. Added to `skills:` of 9 planning/design agents that call `AskUserQuestion`: `technical_product_manager`, `implementation_planner`, `architect`, `api_designer`, `database_designer`, `designer`, `domain_expert`, `domain_modeller`, `focus_coach`. Warning cleared. Always-on count unchanged (skill was never always-on).

Verified:

- `make validate-claude` → 0 errors, 0 warnings (after the Phase 2a extension on 2026-07-22 closed the `self-contained-options` trigger-path).
- `make rules-budget` → **always-on flat count = 73** (target hit; matches plan's 119 → ~73 projection).
- Full test suite: 1142 passed (was 1151 pre-reversal; 9 index tests removed).
- Ruff clean on all new files; pre-existing `rules_budget.py` lint noise unchanged (W1 baggage, not in scope).

Tomorrow's flow:

1. Review `future_projects/claude_tuning/w2_frontmatter_data.yaml` — the single decision.
2. `.venv/bin/python scripts/apply_w2_frontmatter.py --dry-run | less` — inspect diff.
3. `.venv/bin/python scripts/apply_w2_frontmatter.py` — apply frontmatter to 67 files.
4. `make validate-claude` — expect 0 errors, 0 warnings.
5. `make rules-budget` — expect ~73 (frontmatter additions are not rule-shaped, so no drift).
6. Commit and `make claude-push`.
