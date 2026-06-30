---
tags: [claude-improvements, consolidation, action-plan, phase4]
phase: 4
created: 2026-06-30
status: draft
inputs:
  - 00-MoC.md
  - 10-root-causes-overview.md
  - rc-01..rc-31 (31 atomic RC files)
  - roles/devbox/files/dot_claude/future_projects/knowledge_restoration_plan.md
  - roles/devbox/files/dot_claude/future_projects/comprehensive_analysis/README.md
  - roles/devbox/files/dot_claude/future_projects/test-strategy/README.md
  - roles/devbox/files/dot_claude/future_projects/unit-decomposition/README.md
  - roles/devbox/files/dot_claude/future_projects/prompt_for_making_standard_work_better.md
---

# Consolidation plan — from RC catalogue to prioritised action

This file consolidates the 31-RC catalogue and the relevant `future_projects/` streams into a single prioritised action plan. Reading order: [[00-MoC]] → [[10-root-causes-overview]] → this file.

The plan answers two questions in this order:

1. **Topology question (Q1):** do we keep 3-per-stack SE agents (`software_engineer_{go,python,frontend}`) or collapse to one `software-engineer` agent with stack-conditional skills? Test-writer and reviewer consolidation status is already partially settled (see Inventory) — this question is real only for SE.
2. **Sequencing question (Q2):** what to do first / second / third — grouped by cluster, not by RC ID.

## Inventory — what we have right now

### Agent topology (current)

| Role | Agents | Stack split? | Pattern |
|---|---|---|---|
| Software engineer | `software_engineer_{go,python,frontend}` | **Yes (3)** | Heavy per-stack mandates (uv-run vs goimports vs pnpm), per-stack security scans, per-stack skill loadouts. |
| Unit test writer | `unit_tests_writer` | **No (1)** | Universal; detects language(s) in diff and loads matching `{lang}-engineer` + `{lang}-testing` skill. |
| Integration test writer | `integration_tests_writer_{go,python}` | **Yes (2)** | No frontend integration writer. Testcontainers / DB / HTTP setup diverges per stack. |
| Code reviewer | `code_reviewer` | **No (1)** | Universal; loads `{lang}-engineer` + `{lang}-testing` skill based on diff. Already proves the "1 agent + stack skill" pattern. |
| Meta reviewer | `meta_reviewer` | **No (1)** | Universal; reviews agent/skill definitions. Scope-specific not stack-specific. |
| Content reviewer | `content_reviewer` | **No (1)** | Universal; reviews skill content quality. Scope-specific. |
| Database reviewer | `database_reviewer` | **No (1)** | Universal; reviews schema migrations. Scope-specific. |

**Net:** the "3 per stack" pattern is real for SE, partial for integration-tests, and absent for reviewers. The user's framing "нужны ли 3 SE / 3 test-writer / 3 reviewer" overstates the split — reviewers are already universal, unit-test is already universal. The actual open question is SE (3) and integration-tests (2 → 1?).

### Skills with engineer scope (current)

- `go-engineer`, `python-engineer`, `frontend-engineer` — 130/167/151 lines. Significant overlap with their owning agent's body (complexity check, workflow, pre-flight, "what this agent does/doesn't do"). Mostly **duplicate** content already present in agent files. Candidates for trim or merger.
- `code-writing-protocols` — cross-cutting; referenced by all 3 SE agents. Owns Approval Validation, Decision Classification, Anti-Satisficing, Anti-Helpfulness, Routine Task Mode, Pre-Implementation Verification, Pre-Handoff Self-Review, After Completion.
- `go-testing`, `python-testing`, `frontend-testing` — stack-specific test patterns; consumed by both SE agents (read-only) and test writer / reviewer (deterministic loading).
- `go-review-checklist` — already proves the "scope-specific skill on a universal agent" pattern.

### Future-projects streams (active / relevant)

| Stream | Status | Bearing |
|---|---|---|
| [[../roles/devbox/files/dot_claude/future_projects/knowledge_restoration_plan]] | In progress (2026-06-09) | 5 phases. Phase 0 (measurement-first) is the prerequisite gate for any major topology change. Phase 1 enforcement-via-tooling reduces agent-prompt size. Phase 2 restores deleted reference content as lazy-loaded skills. Phase 3 hardens reviewers (blind protocol + forced justification on PASS). Phase 4 self-reflection enables data-driven dark-skill removal. |
| [[../roles/devbox/files/dot_claude/future_projects/comprehensive_analysis/README]] | Completed audit (2026-06-24) | 7 root-cause classes around permissions / allow-list / sandbox / sub-agent isolation. Direct fix surface is `settings.json` + hook layer, not agent topology. Orthogonal but high-priority backlog. |
| [[../roles/devbox/files/dot_claude/future_projects/test-strategy/README]] | Proposal (2026-06-09) | 9 proposals (A-I) for test-writer / reviewer skill content. Explicitly defers agent topology. Confirms direction: agnostic concept skills (test-strategy, isolation, distributed-patterns) loaded by signal; idioms in `{lang}-testing` skills. |
| [[../roles/devbox/files/dot_claude/future_projects/unit-decomposition/README]] | Blocked on RAG agent (2026-02-22) | Atomic work-unit decomposition for planner. Independent of SE consolidation; resumes when RAG project lands. |
| [[../roles/devbox/files/dot_claude/future_projects/prompt_for_making_standard_work_better]] | Template (74 lines) | Per-project `var/` convention for caches/tmp/state/log. Orthogonal to agents; folds into Tranche 1 (foundation) as a settings change. |

### Cross-stream convergence

All three active streams (knowledge restoration, comprehensive analysis, test-strategy) converge on the same principle: **measurement before structural change** and **deterministic tooling over advisory prompts**. None recommends collapsing to 1×SE. None blocks it either. Knowledge restoration Phase 0 + Phase 4 (skill adherence tracking, dark-skill identification) is the natural data source for evidence-based SE-topology decision.

---

## Q1 — agent topology DSS

### Scope

Limited to `software_engineer_{go,python,frontend}`. The `integration_tests_writer_{go,python}` merge is a derivative question; reviewers/unit-test-writer are already settled.

### Diverge — six options

**Option A — Status quo: 3×SE (go, python, frontend)**

Keep three agents as authored today. Each carries its own mandatory pre-flight (`uv run` mandate for python, `goimports -local` for Go, package-manager detection + zero-tolerance `any` for frontend), security scans (Python pickle/SSTI vs Go timing-unsafe/SQL-fmt vs JS XSS/localStorage), skill loadout, and quick-reference command tables. Drift between the three files is unavoidable manual labour.

**Option B — 1×SE with stack-conditional skill auto-load**

Single `software-engineer` agent. At workflow step 1, detect stack from `git diff --name-only` + lock files (`uv.lock|poetry.lock|go.mod|pnpm-lock.yaml`). Load matching `{lang}-engineer` skill which carries all stack-specific mandates, security scans, pre-flight. Mixed-stack diffs load multiple skills.

**Option C — 1×SE with stack pre-injection by `/techne-implement`**

Single `software-engineer` agent definition. `/techne-implement` command does the stack detection and injects the stack context as the first user message (or as `additionalContext`). Agent itself stays stack-agnostic; the dispatching command carries the routing intelligence.

**Option D — Hybrid: keep 3×SE; consolidate `integration_tests_writer` to 1**

Keep 3 SE agents (per-stack divergence is genuine — see trade-off matrix). Merge `integration_tests_writer_go` + `integration_tests_writer_python` into a single `integration_tests_writer` that loads `{lang}-testing` skill the same way `code_reviewer` already does. Net change: -1 agent.

**Option E1 — Single Jinja2 source for SE; Ansible renders 3 outputs at deploy**

One authoring source `roles/devbox/files/dot_claude/agents/software_engineer.md.j2` with stack-conditional Jinja2 blocks (`{% if stack == 'go' %} ... {% endif %}`). The Ansible deploy step (`install_configs.yml` Block 2) loops over `[go, python, frontend]` and renders three concrete `software_engineer_{stack}.md` files into `~/.claude/agents/`. At runtime the three deployed files are statically identical to today — same prompt shape, hard-mandates still in first lines of each — but the source of truth is a single template. Drift across the three becomes physically impossible: a change to a shared section edits one block in one file. Implementation cost: ~3-4h (Jinja2 refactor + Block 2 from copy loop to template loop). Combines with the integration-test merge from Option D.

**Option E2 — Single agent file with inline per-stack conditionals in the prompt**

Single `software_engineer.md` containing literal "IF Go: use goimports / IF Python: uv run / IF Frontend: pnpm + no any" branches that the model reads at runtime. One physical file in `.claude/agents/`. Rejected up-front: all three stack branches consume context budget on every invocation (rc-13 returns at agent scope), mandate attention dilutes across irrelevant branches, no advantage over E1 on maintenance.

### Synthesize — trade-off matrix

| Dimension | A: Status quo | B: 1×SE + skill | C: 1×SE + pre-inject | D: Hybrid | **E1: Jinja2 source** |
|---|---|---|---|---|---|
| Total agent files at runtime (SE + integration-test) | 5 | 2-3 | 2-3 | 4 | **4 (3 SE + 1 int-test, all rendered)** |
| Source files to author | 5 | 2-3 | 2-3 | 4 | **2 (1 SE template + 1 int-test)** |
| Maintenance burden (drift across files) | High | Low | Low | Medium | **Zero (single source)** |
| Stack-specific enforcement strength | High | Medium (skill-load risk) | High | High | **High (mandates still in first lines of each rendered file)** |
| Cross-stack rule consistency | Low (drift) | High | High | Medium | **High (shared blocks live in one place)** |
| Entry-point flexibility (direct `Task`, slash, sub-agent dispatch) | High | Medium | Low (command-bound) | High | **High (same as A/D at runtime)** |
| Risk of misfire on mono-repo / polyglot diff | Low | Medium-high | Low (explicit flag) | Low | **Low (stack-pinned at deploy)** |
| Failure isolation (broken Python guard doesn't break Go work) | High | Low | Low | High | **High (separate rendered files)** |
| Skill-activation dependency on [[rc-19-skill-invocation-advisory]] | None | Critical (deal-breaker) | None | None | **None** |
| Aligns with current direction (reviewer, unit-test already universal) | Partial | No (over-rotates) | No (over-rotates) | Yes | **Yes + addresses drift** |
| Required prerequisites | — | Fix RC-19 first | `/techne-implement` rewrite | Refactor 2 test-writer files | **Jinja2 refactor of SE; Block 2 copy→template** |
| Implementation cost | None | High | High | Low | **Low-medium (~3-4h)** |
| Restartability if wrong | High | Low (big rewrite) | Low | High | **High (revert template, files unchanged)** |

### Select — recommendation: **Option E1 (Jinja2 source + Ansible render) plus integration-test merge from D**

**Reasoning.**

- **E1 preserves the runtime properties of D while killing the only weakness D had** — drift between 3 separately-authored SE files. Rendered output is statically identical to today's hand-authored files; the model reads the same hard-mandate blocks in the same first lines. Nothing changes at invocation time.
- **SE divergence is mandatory, not advisory.** Each SE agent's top section is a hard-mandate block (`MANDATORY: All Commands via uv run`, `ZERO TOLERANCE: any Types`, `ALWAYS use goimports -local`). These are the **first** instructions the model reads; they shape every Bash/Edit choice that follows. Both D and E1 preserve this. B fails because it moves the mandates behind skill activation ([[rc-19-skill-invocation-advisory]] is the deal-breaker). C fails the entry-point flexibility test — direct `Task` invocation skips the command-level pre-injection.
- **Per-stack security scans are genuinely different.** `pickle.load` (Python) vs timing-unsafe `==` on tokens (Go) vs `dangerouslySetInnerHTML` (frontend) are three different scan vocabularies. In E1 they live in a single `{% if stack == 'X' %}` block each — readable, version-controlled, and impossible to silently drift.
- **Reviewer is the proof case for runtime universality, not a counter-example.** `code_reviewer` works as 1-agent-universal because review fires **after** changes exist, so the diff is the trigger and skill loading is deterministic. SE fires **before** changes exist — the agent's mandate must be loaded the moment the user invokes it, not after the first Bash call. E1 keeps this invariant.
- **Integration-test writers are the right additional consolidation.** Testcontainers, HTTP setup, DB fixtures share enough across Go and Python that one agent + `{lang}-testing` skill matches `code_reviewer`'s working pattern. Independent of E1 — ship together.
- **Stay reversible.** E1 is a Jinja2 refactor of one source file plus a one-line change in the Ansible Block 2 task. If it goes wrong, revert the template and the rendered output reverts to today's files.

**What E1 + integration-test merge entails.**

1. **SE source consolidation.** Convert the 3 existing SE agent files into one Jinja2 template `roles/devbox/files/dot_claude/agents/software_engineer.md.j2`. Shared content (Approval Validation pointer, Anti-Satisficing pointer, LSP Navigation Protocol, Workflow steps 1-3 and 7-8, Handoff Protocol) appears once. Stack-specific content (top-of-file mandates, security scan vocabulary, language quick-reference, skill loadout, pre-flight commands, language-specific quality checklist) sits in `{% if stack == 'go' %} ... {% elif stack == 'python' %} ... {% elif stack == 'frontend' %} ... {% endif %}` blocks. The rendered output target name (`software_engineer_{stack}.md`) is derived from the loop variable.
2. **Ansible task change.** `roles/devbox/tasks/install_configs.yml` Block 2 (Claude root files copy loop) gains a sibling task: `ansible.builtin.template` with `loop: ['go', 'python', 'frontend']`, `vars: { stack: "{{ item }}" }`, source `agents/software_engineer.md.j2`, dest `~/.claude/agents/software_engineer_{{ item }}.md`. The pre-existing copy-loop entry for these 3 files is removed.
3. **Integration-test merge.** Generalise `integration_tests_writer_go.md` → `integration_tests_writer.md` following the `code_reviewer` pattern: detect language(s) in diff, load `{lang}-engineer` + `{lang}-testing`. Migrate Python-only content from `integration_tests_writer_python.md` into `python-testing` skill. Delete `integration_tests_writer_python.md`.
4. **Skill duplication trim.** The 3 `*-engineer` skills (130/167/151 lines) significantly duplicate content from their owning SE agent. Move agent-only content out of the skills; keep only patterns the skill can carry on its own. Done as part of the E1 template refactor.
5. **Validation.** `make validate-claude` confirms cross-references; `make claude-push` re-renders and deploys; smoke test by invoking each SE agent in turn and verifying the top-of-file mandate is present in the deployed file.

**What E1 explicitly does not solve.**

- Polyglot projects (Go service + Python tool + frontend dashboard) still require three sequential SE invocations. Same as today. Out of scope for this consolidation.
- Cross-stack rule additions (e.g. a new security-scan family that applies to all 3) still require editing 3 Jinja2 blocks — but in the same template file, in adjacent sections. Net authoring cost lower than today.

---

## Q2 — prioritised tranches

Five tranches, each independently shippable. The order encodes dependency, not strict sequence — Tranche 2 and Tranche 5 can run in parallel after Tranche 1 lands.

### Tranche 1 — Foundation: budget, trim, measurement

**Goal:** clear the attention budget and install measurement infrastructure before adding any new always-on rule. The UAP trim is an aggressive "delete + re-home", not bare deletion — load-bearing rules move to deterministic mechanisms before their UAP line disappears.

| Action | Source | Surface |
|---|---|---|
| **UAP triage** — section-by-section audit of `USER_AUTHORITY_PROTOCOL.md`. Each section gets a target: keep in UAP (load-bearing, no better home), move to alwaysApply skill, move to hook, move to `settings.json`, move to per-agent frontmatter (loaded only when agent fires), or delete (dead / advisory-only / already covered). | [[rc-13-claude-md-bloat]] F1 + [[rc-11-claude-md-attention-budget]] + user authority on aggressive trim | Multi-file: UAP + target destinations |
| **UAP aggressive trim** execution — apply triage outcomes. Target: ~150-200 effective lines removed (509 → ~300-350), bringing UAP near the ~200-line attention budget for the first time. Every removed section either has a deterministic backstop (hook / settings) or has been re-homed to a more narrowly-loaded location. | [[rc-13-claude-md-bloat]] F1 | Edit UAP + skills + hooks |
| Pin model versions in all agent frontmatter | knowledge restoration Phase 1 | Multi-file edit (~33 agents) |
| Baseline-task seed + budget audit script (count effective instructions per agent invocation) | knowledge restoration Phase 0 | New `bin/` script |
| Adopt `var/` convention for tool caches | future_projects/prompt_for_making_standard_work_better | `settings.json` env |
| Expand permission allow-list (git -C *, go env/list/doc, common read-only tools); rewrite `pre-tmpdir-guard` to whitelist `/tmp/claude/` and `$TMPDIR` | comprehensive_analysis Class A + C | `settings.json`, hooks |
| Move rc-31 F3a (diff-first debugging discipline) into `code-writing-protocols` skill, **not** UAP — UAP is shrinking in this same tranche, so the destination is the SE-loaded skill instead. | [[rc-31-agent-satisficing]] F3a (revised destination) | Edit one skill |

**Acceptance:** UAP effective-line count in `[300, 350]` range; every section that left UAP has a documented destination (hook ID, skill ID, settings.json path, or "deleted as advisory-only"); baseline tasks runnable; permission-prompt rate drops measurably; one model version per agent; diff-first debugging rule present in `code-writing-protocols`.

### Tranche 2 — Verification harness

**Goal:** close the "agent claims X without proof" structural gap. RCs 24-28 are a coherent cluster.

| Action | RC | Surface |
|---|---|---|
| Build the deterministic verification harness — Stop hook scanning final-message claims against tool-call history | [[rc-24-done-without-verification]] F1 | New `bin/stop_verify_claims.py`, hooks.json |
| Truncate lint/test stdout above threshold; inject `--quiet` flags pre-tool-use | [[rc-28-lint-test-output-flood]] F1, F2 | Pre/Post Bash hook |
| Citation audit — Stop hook scanning bare identifiers without `path:line` anchors | [[rc-25-citation-not-enforced]] F1 | Extend Stop hook from RC-24 |
| Counter-evidence audit checklist in `meta_reviewer` | [[rc-26-no-bullshit-detector]] F3 | Edit one agent |
| Definition-of-Done block + workaround-pattern PostToolUse hook | [[rc-31-agent-satisficing]] F1, F2 | Skill edit + new hook |

**Acceptance:** false-done rate measurable and trending down; output-flood reduced by ≥60%; bare identifiers caught at Stop time ≥80% of cases; workaround patterns flagged before commit.

### Tranche 3 — Pipeline re-entry and roadmap

**Goal:** dissolve the waterfall topology. RCs 20-23 are a coherent cluster around pipeline shape.

| Action | RC | Surface |
|---|---|---|
| `/techne-re-enter <stage>` command + `workflow.json` re-entry flag | [[rc-20-waterfall-pipeline]] F1, F2 | New command + state file |
| Split monolithic stage outputs into atomic section files (`assumptions.md`, `evidence.md`, etc.) | [[rc-21-monolithic-and-duplicate-outputs]] F3 | Template refactor |
| `roadmap.md` template + `pipeline-roadmap` skill + statusline integration | [[rc-22-manual-dispatch-no-roadmap]] F2, F4 | New skill + template |
| Per-agent `tools:` tightening + PreToolUse role-boundary hook | [[rc-23-role-boundary-violations]] F1, F2 | Multi-file frontmatter + new hook |

**Acceptance:** any stage re-entrable without re-running upstream; TPM/designer agents cannot Edit `.go|.py|.ts` files; roadmap milestone state visible in statusline.

### Tranche 4 — Knowledge restoration and engineering posture

**Goal:** restore lazy-loaded reference content and encode the Fisher's-maxim posture. Pure additive skill work; requires Tranche 1 budget headroom first.

| Action | Source | Surface |
|---|---|---|
| New `engineering-attitude` skill (alwaysApply) — Fisher's maxim, anti-false-dichotomy, shadow-mode + CBC, overlap scan, internal locus | [[rc-15-engineering-attitude-skill-missing]] F1 | New skill |
| Restore "Prefer X over Y" reference content as lazy-loaded skills (go/python/frontend corrective-patterns) | knowledge restoration Phase 2 | 3 new on-demand skills |
| Security and reliability reference skills (on-demand) | knowledge restoration Phase 2 | 2 new skills |
| Reviewer hardening — blind review protocol + forced justification on PASS | knowledge restoration Phase 3 | 3 reviewer agent edits |
| New `verification-discipline` and `counter-evidence-audit` skills | [[rc-24-done-without-verification]] F5 + [[rc-26-no-bullshit-detector]] F6 | 2 new skills |

**Acceptance:** corrective-pattern references discoverable on-demand; `engineering-attitude` skill loaded on all 3 SE + reviewer agents; reviewer forced-explanation rate ≥90% on PASS verdicts.

### Tranche 5 — Topology refactor (executes Option E1 + integration-test merge)

**Goal:** ship Option E1 (single Jinja2 source for SE, rendered to 3 deployed files) plus the D-style integration-test merge. Independent of Tranches 2-4; can run in parallel once Tranche 1 lands.

| Action | Surface |
|---|---|
| **Jinja2 SE source.** Convert `software_engineer_{go,python,frontend}.md` into a single `agents/software_engineer.md.j2`. Shared sections (Approval Validation pointer, Anti-Satisficing pointer, LSP Navigation Protocol, Workflow steps 1-3 and 7-8, Handoff Protocol, After Completion) appear once. Stack-specific sections (top-of-file mandates, security scan vocabulary, language quick-reference table, skill loadout, pre-flight commands, language-specific quality checklist) live in `{% if stack == 'X' %}` blocks. Deleted: the 3 separate hand-authored files. | New `.md.j2` source; delete 3 old files |
| **Ansible Block 2 template loop.** In `roles/devbox/tasks/install_configs.yml` Block 2, remove the 3 SE files from the copy loop. Add an `ansible.builtin.template` task with `loop: ['go', 'python', 'frontend']`, `vars: { stack: "{{ item }}" }`, source `agents/software_engineer.md.j2`, dest `~/.claude/agents/software_engineer_{{ item }}.md`. | One Ansible task edit |
| **Render parity check.** After first deploy: diff each rendered `~/.claude/agents/software_engineer_{stack}.md` against the pre-refactor hand-authored version. Differences should be either intentional consolidations (one shared line replacing three near-duplicates) or formatting from Jinja2 (whitespace). Anything semantically new is a refactor bug to fix before merging. | Manual diff verification |
| Generalise `integration_tests_writer_go.md` → `integration_tests_writer.md`; mirror `code_reviewer`'s stack-skill loading pattern | One file edit |
| Migrate Python-only sections from `integration_tests_writer_python.md` into `python-testing` skill | Skill extension |
| Delete `integration_tests_writer_python.md` (replaced) and `integration_tests_writer_go.md` (renamed to universal) | File removal |
| Trim duplication between SE Jinja2 template and `{go,python,frontend}-engineer` skills — keep template-only content in the template, skill-only patterns in the skills | Multi-file trim |
| Update all references (commands, MoC, doc, `make validate-claude` checks) | Cross-cutting search-and-replace |

**Acceptance:** Deployed agent file count drops from 5 (3 SE + 2 integration-test) to 4 (3 SE rendered from 1 template + 1 integration-test); **authored source file count drops from 5 to 2** (1 Jinja2 SE template + 1 integration-test); render-parity check shows no semantic regression vs pre-refactor; duplication audit shows zero shared sections between the SE template's stack-specific blocks and the `*-engineer` skills; all references updated; `make validate-claude` passes; `make claude-push` re-renders cleanly.

---

## Cross-cutting infrastructure (build once, used by multiple tranches)

These are shared dependencies surfaced by [[00-MoC#Fix surface frequency]]. Build early.

1. **Output-style harness with composition.** Tranche 2 needs `cite-strict`, `assertion-tagged`; Tranche 1 needs `delta-discipline`; Tranche 4 needs `engineer-posture`; rc-31 needs `layer-tagged`. Today output-styles are single-choice. A composition mechanism (`[engineer-posture, cite-strict, delta-discipline]`) unlocks half the catalogue.
2. **Hook composition / shared pattern library.** Tranches 2, 3, and rc-31 propose Stop / PostToolUse hooks with overlapping pattern libraries (claim-detection, workaround-detection, citation-detection). One shared `bin/pattern_library.py` consumed by N hook scripts beats N copies of the same regex set.
3. **Skill-activation enforcement.** [[rc-19-skill-invocation-advisory]] is the silent dependency under Tranche 4 (engineering-attitude must actually load) and Option B above (deal-breaker). Build a PreToolUse hook that detects skill-trigger match and exit-2 if `Skill` was not invoked, BEFORE the alwaysApply tail bloats further.

---

## Decisions taken (resolved)

Captured here so the rationale is not lost when this file is revisited:

1. **UAP trim target:** aggressive, 150-200 effective lines removed (509 → ~300-350). Executed as section-by-section triage in Tranche 1, with each removed section explicitly re-homed to a deterministic mechanism (hook / settings.json / per-agent frontmatter / alwaysApply skill) or deleted as advisory-only with prior documentation.
2. **rc-31 F3 delivery:** both F3a and F3b. F3a content moves into `code-writing-protocols` skill (not UAP — UAP is shrinking in Tranche 1). F3b (`root-cause-discipline` skill + UserPromptSubmit hook) lands in Tranche 4. Two layers — advisory-in-skill plus deterministic-in-hook.
3. **SE topology:** Option E1 — single `software_engineer.md.j2` Jinja2 source rendered by Ansible into 3 deployed files. Drift across SE files becomes physically impossible. Runtime behaviour identical to current 3 hand-authored files. Combines with the integration-test-writer merge.
4. **Tranche 4 ordering:** `engineering-attitude` (alwaysApply) ships first inside Tranche 4 — covers 8 symptoms (S-010, S-017-S-022, S-024) with one skill, but only viable after Tranche 1 frees the attention budget. Corrective-patterns and reviewer-hardening follow.

## Open questions

The four decisions above are settled. New questions surface as the plan moves toward execution:

1. **Tranche 1 ordering — UAP triage before or after baseline-task scripts?** Triage benefits from the budget audit script (we can measure attention spend per section objectively). But waiting risks losing the agreed-upon trim direction. Default: triage first using qualitative judgement, then the audit script validates retroactively.
2. **E1 Jinja2 source layout — flat file or split into includes?** A single 600-line `.md.j2` with `{% if %}` blocks works for 3 stacks. If a 4th stack lands (Rust? OCaml?), split into `_shared.md.j2` + `_stack_go.md.j2` etc. via Jinja2 `{% include %}`. Defer until the 4th stack is real.
3. **Render parity check — automated or manual?** Tranche 5 acceptance asks for a diff against pre-refactor files. A `make verify-se-render` target could automate: cache the pre-refactor copies, render the template, diff, fail CI on unexpected semantic delta. Worth the harness investment? Probably yes for the initial migration only, then delete the cache.
4. **Reviewer-hardening (Tranche 4) — which reviewer first?** `code_reviewer` is the high-volume gate; `meta_reviewer` is the agent-and-skill review gate. Default: `code_reviewer` first to maximise blast radius coverage.

## See also

- [[00-MoC]] — catalogue hub
- [[10-root-causes-overview]] — cluster map and cross-cutting observations
- [[rc-31-agent-satisficing]] — Fix 8 captured as its own RC
- [[rc-13-claude-md-bloat]] · [[rc-15-engineering-attitude-skill-missing]] · [[rc-24-done-without-verification]] · [[rc-19-skill-invocation-advisory]] — gating RCs for tranche dependency
- `roles/devbox/files/dot_claude/future_projects/` — full source for streams listed in Inventory
