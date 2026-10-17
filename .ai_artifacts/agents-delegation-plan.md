# Plan: agents that carry work through to a PR

Status: plan only, no changes to the project. Branch `claude/agents-delegation-models-1i1s22`. All paths are relative to `roles/devbox/files/` unless stated otherwise. `file:line` checks were made against the current tree; differences from the earlier draft are marked **Corrected**.

## Goal

Rebuild the agent system so that a work contract (goal, done criteria, authority) replaces questions during the work. Developer, test writer and reviewer work in pairs and in parallel. Contested decisions are recorded with their options in `.ai_artifacts/` inside the repository. Commit, push, PR and CI watching are pre-authorised. Merge into the default branch happens automatically when CI is green. The Jira key is propagated automatically and is never asked for.

## Non-goals

Do not change the dialogue agents `tdd_guide` and `focus_coach`. Do not touch `fpf-thinking`, or the hook architecture beyond the two hooks named below (`bash_decision_gate.py` and `pre_edit_repo_boundary.py`). Do not back-fill `docs/implementation_plans/`. Do not allow force-push, `--no-verify` or other destructive git operations. Do not invent threshold examples; they come from raw logs (see "Threshold examples").

## Target pipeline

```
contract.md (goal, criteria, authority, KEY)
   ├── domain_modeller ──► entities.md ──┐
   ├── api_designer ─────► api_spec ─────┤
   │                                     ▼
   │        ┌── software_engineer_* (implementation, no tests)
   │        │                 ∥ in parallel, from the contract
   │        └── unit/integration test writer (does not see the implementation)
   │                          ▼
   │              code_reviewer: finding ⇒ refute_*_test (default)
   │                           or a task for unit-test-writer
   │                          │  fix loop until "no open findings"
   │                          ▼
   │      commit → push → PR → CI until green → gate 4.3 → merge into default branch
   │                          ▼
   └────────────────► report.md + reply to the user
```

Differences from today's `/techne-implement` (`techne-implement.md:116-197`): tests are written in parallel rather than after (`Next: Run /techne-test`); the reviewer is assigned automatically rather than through `/techne-review`; the agent makes commit, push and PR itself; merge is automatic under the gate in 4.3.

## Preconditions and checks before starting

| # | Fact | How to check | Result now |
|---|---|---|---|
| P1 | Claude Code accepts `model: fable` in subagent frontmatter | `code.claude.com/docs/en/sub-agents`, frontmatter table | **Confirmed**: `sonnet`, `opus`, `haiku`, `fable`, full model ID, `inherit`. Fable 5.1 requires Claude Code ≥ 2.1.257 (`docs/en/model-config`). Check `claude --version` on the target machine |
| P2 | Repository validators accept `fable` | `dot_claude/bin/validate_config.py:242-244` (list is `sonnet/opus/haiku`), `dot_agy/bin/translate_agents.py:8` (`MODEL_MAP` has only opus/sonnet), `dot_ai/skills/agent-builder/SKILL.md:63`, `dot_ai/agents/agent_builder.md:294` | **Do not accept it.** Fixed in step 6.1 |
| P3 | `pre_edit_repo_boundary.py` treats a worktree as part of the project | `dot_claude/bin/pre_edit_repo_boundary.py:33-37`: boundary is the git root of `CLAUDE_PROJECT_DIR`; `_claude_lib/paths.py:51` looks for `.git` with `exists()`, so a worktree's `.git` file is also found | **Partly**: if the session *started inside* the worktree, fine. If it started in the main checkout and the worktree sits beside it (`$AION_AUTOPOIESEON/<project>/<branch>/`, `CLAUDE_ADAPTER.md:64-65`), the hook returns `ask`. There is no worktree test in `test_pre_edit_repo_boundary.py`. Fixed in step 7.2 |
| P4 | Temporary directory is excluded from the boundary | `pre_edit_repo_boundary.py:40-45` → `paths.temp_roots()` (`TMPDIR`, `tempfile.gettempdir()`) | **Corrected** from the draft: the exclusion exists, in `_claude_lib/paths.py:15-17` |
| P5 | `bash_decision_gate.py` does not block commit and push | `dot_claude/bin/bash_decision_gate.py:436-455`: `rule_git_commit` and `rule_git_push` **deny unconditionally**, with the comment "stands even when a project-level CLAUDE.md tells the agent to commit" | **Blocks.** The draft missed this. Without step 4.1, no policy written in Markdown will take effect |
| P6 | Default branch and branch protection | `.github/workflows/ci.yml:14-20`: default branch is **`master`** (not `main`); CI runs on push to `master` and `claude/**` and on PRs to `master`; jobs `lint`, `validate`, `test`, `hook-projects` | Branch protection / rulesets **not checked**: `gh auth status` reports an invalid token, and the GitHub MCP has no protection tool. Check with `gh api repos/abrosimov/devbox-setup/branches/master/protection` and `.../rulesets` using a working token |
| P7 | GitHub integration available to the agent | `mcp__github__get_me` → `abrosimov` | **Available** via MCP. `gh` is installed (`/usr/local/bin/gh`), but its token is invalid in this session. Re-check `gh auth status` on the working machine |
| P8 | Codex budget | `cat USER_AUTHORITY_PROTOCOL.md dot_codex/AGENTS.md \| wc -c` = 21,882 of 32,768 (`tests/deploy/test_codex_assets.py:124-126`) | About 10.9 KB left; new rules go into skills, not into the core |
| P9 | Git Jira hook | `.config/git/hooks/prepare-commit-msg:17,56,67`: the key is taken from the branch name matching `[A-Z]{2,}-[0-9]+`, position from `jira.keyPosition` | Commit footer/prefix is already automatic if the key is in the branch name. Only "never ask" remains |

## Steps

### Phase 0 — artifacts and threshold (foundation)

**0.1 Layout of `.ai_artifacts/` and the "no `$TMPDIR`" rule.**
Files: `dot_ai/skills/agent-base-protocol/SKILL.md` (new section "Artefacts"), `dot_ai/USER_AUTHORITY_PROTOCOL.md:143` (**Corrected**: the reference to `$TMPDIR/ledger-<topic>.md` is in §5, not §4), `dot_ai/skills/workflow/SKILL.md:134` (`$TMPDIR/<job>-decision-log.md`), `dot_ai/skills/config/SKILL.md` (`PLANS_DIR`).
Change: the layout in "Decisions and report" below becomes the only place for plans, decisions, ledgers and reports. Mentions of `$TMPDIR` are replaced with `.ai_artifacts/<task>/…`. `ai_written_scripts/` (core §4:127) stays as is: it holds code, not artefacts.
Check: `make validate-claude`, `make rules-budget`, `pytest tests/deploy/test_codex_assets.py`. Rollback: one commit. Dependencies: none.

**0.2 Threshold for option deliberation: extend `diverge-synthesize-select`, do not create `option-deliberation`.**
**Corrected**: a skill with the procedure for 3–7 candidates, a "Combine" step (synergy) and a persisted `dss_output.json` already exists (`dot_ai/skills/diverge-synthesize-select/SKILL.md:16-40,86-92,135-141`). It is attached to architect, api_designer, designer, domain_modeller, implementation_planner, TPM and all three SE agents. A new skill would duplicate it.
Files: in `diverge-synthesize-select/SKILL.md`, the "When to use it" section (lines 16-40) gets the owner's threshold. *Design decisions* (code structure, algorithm, API shape, data structure, module boundaries) → 5–7 candidates + synergy + an entry in `decisions.md`. Variable names, argument order, choosing between equivalent helpers → below the threshold, one line in `decisions.md`. The lower bound of "3" stays for cards shown to the user; "5–7" becomes the norm for entries written to an artefact. Add a placeholder subsection "Threshold examples (pending raw logs)" that links to the "Threshold examples" section of this plan.
`dot_ai/agents/architect.md:49-50` ("usually meet the threshold") → replace with a reference to the threshold, without "usually".
Check: `make validate-claude`, `make validate-skills`. Rollback: commit. Dependencies: 0.1.

### Phase 1 — result contract

**1.1 "Work contract" section in `agent-base-protocol/SKILL.md`** (included by all 28 agents; currently 4.5 KB, so there is room).
Content: goal; done criteria with evidence (command, file, output) — the wording "user approved" is forbidden; three authority levels (decide and record / decide and raise in the report / BLOCKED); pre-authorised actions (commit on the working branch, push the branch, create PR, watch CI, merge on green CI — see Phase 4); return format `Status | Result | Decisions | Blockers | Evidence | Paths`.
Check: `make validate-claude`; `make rules-budget` (must not grow by more than the gates removed below). Rollback: commit. Dependencies: 0.1, 0.2.

**1.2 Replace the phrase-based approval check with a contract check.**
Files: `dot_ai/skills/code-writing-protocols/SKILL.md:17-44` ("Approval Validation", the "⚠️ Approval Required" template), `dot_ai/skills/agent-communication/SKILL.md:148-166` (same check) and `:200` ("Implementing without approval → stop").
Change: a subagent checks that a contract from the orchestrator exists (goal + criteria), not a phrase from the user. User approval stays the orchestrator's job (core §0-§1, `CLAUDE_ADAPTER.md:20-23`).
Check: `make validate-claude`. Rollback: commit. Dependencies: 1.1.

### Phase 2 — agent bodies

**2.1 Developers** (`software_engineer_go/python/frontend.md`, mirrors `dot_codex/agents/software-engineer-*.toml`): do not write tests; inputs are the contract + entities (`domain_modeller`) + API (`api_designer`) + the stream file from the plan; threshold from 0.2; mention automatic review. Check: `make validate-claude`, `pytest tests/deploy/test_codex_assets.py`. Dependencies: 1.1.

**2.2 Test writers** (`unit_tests_writer.md`, `integration_tests_writer_go/python.md`, `dot_codex/agents/unit-test-writer.toml`, `integration-tests-writer-*.toml`): inputs are the contract and public interface (signatures, OpenAPI/proto, entities), **not the diff** (`unit_tests_writer.md:3,18`: "Detects the language(s) in the diff"). Do not read implementation files beyond public headers (`contract-boundary`). Tests that fail before the implementation exists are expected; their status in the report is `RED-by-design`. Remove the self-stop "re-run with Opus" (`:52-60`); the dispatcher assigns the model (step 6.2). Check: `make validate-claude`. Dependencies: 1.1.

**2.2a Developer ∥ test writer handshake** (new subsection in `dot_ai/skills/contract-boundary/SKILL.md`): both start from the same `contract.md` + `entities.md` + `api_spec`. The test writer imports only public names from the contract. If the implementation departs from the contract, the developer must update the contract first and record `D<n>`; the test writer does not adapt tests to the implementation. The orchestrator launches both in one message (`CLAUDE_ADAPTER.md:38`, "Launch independent agents in one message") and waits for both before review. Check: `make validate-claude`. Dependencies: 2.1, 2.2.

**2.3 Reviewer** (`code_reviewer.md`, `dot_codex/agents/code-reviewer.toml`):
- Refutation tests: **default path** — the reviewer writes a failing test in a separate file `<tests_dir>/refute_<slug>_test.<ext>` (Go: `refute_<slug>_test.go`; Python: `tests/refute_<slug>_test.py`; TS: `__tests__/refute_<slug>.test.ts`). `refute_*` files live until the fix. After green CI, the developer (or `unit-test-writer`) moves their content into the main test file and deletes `refute_*`. A `refute_*` file left in the branch blocks merge (gate 4.3). **Alternative path** — delegate to `unit-test-writer` with a description of the bug; used when the bug needs fixtures or infrastructure the reviewer does not have (integration tests, frontend with MSW). The choice of path is one line in `decisions.md`.
- Permissions: the frontmatter already has `Edit` (`code_reviewer.md:4`); add `Write`, restricted in the body to test paths. In the TOML, `sandbox_mode = "read-only"` (`code-reviewer.toml:3,26`) → `workspace-write`; replace "Stay read-only and never implement fixes" with "never edit non-test files".
- Style comments do not block.
Check: `make validate-claude`, `pytest tests/deploy/test_codex_assets.py`. Rollback: commit. Dependencies: 1.1, 2.2.

**2.4 Designers** — remove gates and "user approved":
`domain_modeller.md:113` ("Present the glossary to the user for validation"); `api_designer.md:55` ("user approved"), `:154` ("Present error strategy for approval"), `:160` ("Ask user if offset-based needed"); `designer.md:55`, `:120`, `:168`, `:196`; `database_designer.md:56`; `database_designer.md:109` — `gen_random_uuid()` produces v4; on PG 18+ write `uuidv7()`. Done criterion → "spec passes linting and consumers (developer, test writer) can build from it". Check: `make validate-claude`. Dependencies: 1.1.

**2.5 TPM** (`technical_product_manager.md:173-181,283,413,561`): the interview loop becomes "questions that pass the core §1 stop list, batched into the report"; `user approval obtained` → a checkable criterion. Dependencies: 1.1.

**2.6 Planner** (`implementation_planner.md:144,186,631,662`): instead of one `plan.md`, a `plan.md` index (goal, criteria, order, dependencies) plus `streams/WS-<n>-<slug>.md` per stream; a developer receives only the path of its own stream. The hook `pre-plan-code-guard` (`:26`) must cover `streams/*.md`: check `pre_plan_code_guard.py` and extend its test. Check: `make validate-claude`, `make test-claude-hooks`. Dependencies: 0.1.

**2.7 Utility agents**: `refactor_cleaner.md:60` ("Ask the user before removing >20 lines" → decision in the report); `observability_engineer.md:24-36` (self-stop → dispatcher), `:216,441-454` vs `:650` (deploy to sandbox — remove the deploy commands, keep generation; matches `:650` "humans deploy"); `build_resolver_go` — `go clean -modcache` and `goimports -w .` only with an entry in `decisions.md`. Dependencies: 1.1.

**2.8 `skill-builder.toml:5`** refers to `skill-creator`, which does not exist in `dot_ai/skills/` (the skill is `skill-builder`). Replace the reference. Check: `make validate-claude`.

### Phase 3 — Jira without questions

**3.1 One rule for context resolution.** Files: `techne-test.md:34-36`, `techne-review.md:25-27`, `techne-design.md:17-19`, `techne-api-design.md:17-19`, `techne-domain-analysis.md:17-19`, `techne-schema.md:36-38` (all six call `AskUserQuestion` on exit 2). Replace with the block already used by `techne-plan.md:17-20` / `techne-implement.md:68-72` ("do not ask"): the key comes from the branch (`resolve_context.py:16`), else from the task text, else `_adhoc`. If the user gave a key and no branch exists yet, create the branch as `<KEY>_<slug>`; then `prepare-commit-msg` (P9) adds the key to commits automatically; PR title `<type>(<KEY>): …`; folder `.ai_artifacts/<KEY>_<slug>/`. Switch the default `PROJECT_DIR` in `resolve_context.py:15` to `.ai_artifacts` (new `DEFAULT_PLANS_DIR`); update `test_resolve_context.py` and `config/SKILL.md`.
Check: `make test-claude-hooks` (`test_resolve_context.py`), `make validate-claude`, `make test-git-hooks`. Rollback: commit. Dependencies: 0.1.

### Phase 4 — git, PR, CI, merge

**4.1 Hook `bash_decision_gate.py`** (`:436-455`): `rule_git_commit` / `rule_git_push` → allow `git commit` and `git push` **without** `--force*`, `--no-verify`, `--amend`, and not on `main|master` (rule `rule_commit_on_main:458` stays; force-push and `--no-verify` stay denied). Update `test_pre_bash_safety_gate.py:52-260` (the `*_denied_via_generic` tests for plain push/commit are inverted). Check: `make test-claude-hooks`, `make test-agy-hooks` (the copy in `dot_agy/bin/` must be edited separately). Rollback: commit. Dependencies: none, but ship only together with 4.2.

**4.2 Policy in adapters and skills**: `CLAUDE_ADAPTER.md:17` (commit/push/PR from "Always confirm" → "pre-authorised inside a work contract; merge — only through the 4.3 gate"), `:44-45` and `:62-63` (models → reference the frontmatter); `dot_codex/AGENTS.md:56-57,97`; `dot_agy/GEMINI_ADAPTER.md:11`; `agent-communication/SKILL.md:208` (the line "Push commits, open PRs" moves from Human-Only into the contract; approve/merge stay human-only **except** the automatic merge under 4.3); `techne-implement.md:177-197` ("The user will commit manually", "Next: Run /techne-test"); `techne-review.md:85-110` (the `'pr'` menu). Check: `make rules-budget`, `pytest tests/deploy/test_codex_assets.py`, `make test-live` (content changes but settings generation does not — `test-live-guard` is enough). Dependencies: 1.1, 4.1.

**4.3 Automatic merge into the default branch** — new section in `workflow/SKILL.md` and a "Land" step in `techne-implement.md`. All conditions are mandatory:
1. The PR is not a draft; `mergeable_state` is `clean` (`mcp__github__pull_request_read`).
2. All required checks are green (`get_check_run` / `actions_get`). The required set comes from branch protection (P6); until that is confirmed, hardcode `lint, validate, test, hook-projects` from `ci.yml`.
3. No unresolved review threads (`pull_request_read` → threads; `resolve_review_thread` only for threads opened by the agents themselves and closed by a fix with green CI).
4. The reviewer returned `no open findings`, and the branch has no `refute_*` files.
5. `.ai_artifacts/<task>/report.md` is written and committed.
Mechanics: `mcp__github__enable_pr_auto_merge` (squash) after items 1–5; if auto-merge is disabled on the repository, `merge_pull_request` manually after re-checking item 2. **CI red** → read logs (`get_job_logs`), fix, push, repeat; a failure outside the task → BLOCKED in the report, no merge. **CI unavailable** (no runs for 10 min, API 5xx) → the PR stays open, status `CI unavailable` in the report, no merge. **Branch protection requires a human review** → merge is impossible; this is recorded and the PR stays open; whether to lift that requirement is an owner question (Q2).
Check: end-to-end run (step 8.2). Rollback: commit; in an emergency, `disable_pr_auto_merge`. Dependencies: 4.1, 4.2, P6.

**4.4 CI watching**: `subscribe_pr_activity` after the PR is created; if unavailable, poll `actions_list` every 2 minutes, for at most 30 minutes. File: `workflow/SKILL.md`. Dependencies: 4.3.

### Phase 5 — commands and pipeline

**5.1 `techne-implement.md`**: steps 6–8 (`:116-197`) → the chain "contract → (domain_modeller, api_designer if needed) → [developer ∥ test writer] → reviewer → fix loop → push → CI → land → report". `:91` "Unclear → backend" and `:97,122` (implicit launch of `/techne-api-design`) → a decision recorded in `decisions.md`. `:99-110` model table → reference to the frontmatter. Check: `make validate-claude`. Dependencies: phases 1–4.

**5.2 `workflow/SKILL.md:96,104,160`**: autonomous mode is the default; step-by-step mode runs only with `--step`. Remove "Next: Run …" from the 5 commands (`grep "Next\*\*: Run"`). `lint-discipline/SKILL.md:28,85-90` — WAIT → an item in the report for the orchestrator. Dependencies: 5.1.

### Phase 6 — models

**6.1 Validators**: `validate_config.py:242-244` — add `fable` and `inherit`; `test_validate_config.py` — cases; `translate_agents.py:8` — `fable` → **open** (Antigravity has the tiers `pro`/`flash`; I found no documentation mapping `fable` to them; until verified, keep an explicit fallback to `pro` with a comment and a test in `test_agy_hooks.py`); `agent-builder/SKILL.md:63`, `agent_builder.md:184-189,294`. Check: `make validate-claude`, `make test-claude-hooks`, `make test-agy-hooks`. Dependencies: P1.

**6.2 Frontmatter** in `dot_ai/agents/*.md` per the table below. Single source of truth — `model:`. Delete the prose in `agent-communication/SKILL.md:122-129`, `techne-implement.md:101`, `CLAUDE_ADAPTER.md:62-63`. Codex TOML files do not contain `model` — correct, they inherit (`dot_codex/README.md:155`). Check: `make validate-claude`. Dependencies: 6.1.

### Phase 7 — hooks

**7.1 `stop_user_actions_guard.py`** R3 (`:191-196`): add a test in `test_stop_user_actions_guard.py` for a Russian imperative next to a slash command. Check: `make test-claude-hooks`.

**7.2 `pre_edit_repo_boundary.py:33-37`**: treat as in-project any path whose `git rev-parse --git-common-dir` matches the project's shared `.git` (a worktree of the same repository). Add `test_worktree_of_the_session_repository_is_allowed`. Mirror in `dot_agy/bin/`. Check: `make test-claude-hooks`, `make test-agy-hooks`. Dependencies: P3.

**7.3 Subagent isolation**: Claude Code supports `isolation: worktree` in frontmatter (docs/sub-agents), but `CLAUDE_ADAPTER.md:64` prefers `proj wt add` over `EnterWorktree`. Decide on one rule (Q3) and record it in `workflow/SKILL.md`.

### Phase 8 — verification

**8.1** `make qa`, `make validate-claude`, `make validate-skills`, `make rules-budget`, `make test-live-guard`; deploy with `make "$MNEMOSYNE_PERISTASEOS" EXTRA_VARS='--tags ai,claude,codex,agy'`.
**8.2** End-to-end run on a practice task in a separate worktree of this repository: contract → developer ∥ test writer → reviewer with `refute_*` → fix → push → CI → auto-merge into a test branch called `landing-test` (a temporary branch, so the real `master` is untouched) → report. Criteria: no `AskUserQuestion` calls; `decisions.md` is filled in; no `refute_*` left after the fix; parallel worktrees do not interfere with each other.

### Commit order and rollback

Each step is one commit, with the task's Jira key in the title (the key is added by `prepare-commit-msg` if the branch is named `<KEY>_<slug>`). Phase order follows the dependencies: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Within phase 2 the steps are independent and can run in parallel in separate worktrees. Steps 4.1 (hook) and 4.2 (policy) must not be deployed separately: otherwise Markdown either permits what the hook denies, or the reverse. Rolling back any step means `git revert` of its commit. Rolling back 4.1 restores the old deny, and it is the only step after which the rest of the tree stays consistent only if 4.2 and 4.3 are rolled back at the same time. Deploy to the machine (`make "$MNEMOSYNE_PERISTASEOS" EXTRA_VARS='--tags ai,claude,codex,agy'`) after each phase, not after each step: Block 1 rsync with `--delete` overwrites `~/.claude/` entirely, and an intermediate state of a phase (for example 4.1 without 4.2) must not live in the running engine.

## Models by role (verify against the docs before 6.2)

| Role | Model | Why | Status |
|---|---|---|---|
| architect, technical_product_manager | `fable` | first decisions that everything else depends on; docs: "hardest and longest-running tasks" | alias confirmed; CLI version ≥ 2.1.257 to check |
| option evaluators for architecture decisions (advocates in DSS) | `fable` | independent check of high-stakes choices | same |
| domain_modeller, api_designer, designer, database_designer, implementation_planner | `opus` | contracts for two consumers | unchanged |
| software_engineer_* | `opus` (`sonnet` with an explicit flag) | accuracy of implementation; the reviewer catches the rest | unchanged |
| unit/integration test writers | `sonnet`, `opus` for a complex contract (the dispatcher decides by interface size, not the agent) | specification → tests | remove the self-stop |
| code_reviewer | `opus` | correctness review + failing tests | unchanged |
| build_resolver_go, doc_updater, refactor_cleaner, consistency_checker, freshness_auditor, observability_engineer | `sonnet` | bounded tasks | unchanged |
| tdd_guide, focus_coach | `sonnet` | dialogue | do not touch |
| `haiku` | do not assign | no role is purely mechanical | — |
| Antigravity tier for `fable` | `pro` (fallback) | no documentation for the mapping | open |

## Decisions and report: `.ai_artifacts/` layout

```
.ai_artifacts/
  <KEY>_<slug>/            # or _adhoc/<sanitised_branch>/
    contract.md            # goal, criteria, authority, pre-authorised actions
    plan.md                # plan index (implementation_planner)
    streams/WS-<n>-<slug>.md
    entities.md, api_spec.yaml | *.proto   # domain_modeller, api_designer
    decisions.md           # decision log (format below)
    dss_output.json        # machine-readable DSS record, when requested
    review.md              # reviewer findings with links to refute_*
    ci.md                  # push → run id → status → what was fixed
    report.md              # final report to the user
```

Entry format in `decisions.md`: `## D<n> — <question>` → level (routine / stated / escalated) → for design decisions, 5–7 options with pros/cons and the synergy found → choice and reason → rejected options → how to undo → status (`decided`, `raised`). Below the threshold, a single line `D<n>: <choice> — <reason>`.

`report.md` and the reply to the user: link to the PR and merge status; criteria PASS/FAIL with evidence; `Decisions I made` (only stated/escalated, with D<n> numbers); blockers; CI status; `What I need from you` — only for BLOCKED items (core §4:116-120, hook R1-R3). The folder is committed to the branch along with the work; `.gitignore` does not exclude it (checked).

## Risks

| Risk | Mitigation |
|---|---|
| 4.1 opens commit/push, and the agent commits junk | deny on `main|master`, `--amend`, `--force*`, `--no-verify` stay; mandatory `git_safe_commit.py`; PR is always created before merge |
| Auto-merge with an incomplete set of required checks | until P6 is confirmed, hardcode the four CI jobs and refuse merge if any of them has not reported |
| Tests written in parallel do not compile against the implementation | the test writer works only from contract signatures; a mismatch is a contract gap recorded in `decisions.md`; the developer fixes the implementation, not the tests |
| A reviewer with write access starts fixing code | allowlist of test paths in the agent body + check in 8.2; the TOML is `workspace-write` only for `refute_*` |
| `refute_*` files stay in the branch | condition 4 in 4.3 blocks merge |
| The 5–7 option process eats the budget on small things | threshold 0.2 + placeholder for examples; below the threshold, one line |
| Codex budget of 32 KiB | new rules go into skills; `test_codex_assets.py` runs in CI |
| `dot_agy/bin` drifts from `dot_claude/bin` | every hook step touches both copies and both make targets |
| `fable` unavailable on a machine (CLI version, gateway) | docs: fallback to the session model is silent — step 8.2 checks the actual model through the hook log (`universal_logger`) |

## Open questions for the owner

1. **Merge strategy**: squash (recommended — one commit per task, Jira key in the title) or merge commit?
2. **Branch protection on `master`**: if it requires an approving human review, auto-merge is impossible. Recommendation: required checks = the four CI jobs, no human review required, auto-merge enabled in the repository settings.
3. **Worktree mechanism for subagents**: Claude Code's `isolation: worktree` (temporary, removed without changes) or the existing `proj wt add` (`CLAUDE_ADAPTER.md:64`)? Recommendation: keep `proj wt add`, because `pre_edit_repo_boundary` and the `$AION_AUTOPOIESEON` layout already depend on it; step 7.2 makes it safe.
4. **Antigravity and `fable`**: fall back to `pro`, or exclude agents on `fable` from the `agy` deployment? Recommendation: `pro` with a comment until documentation exists.

## Threshold examples (to be added from raw logs)

> Placeholder. This section will hold real cases where the user explicitly asked for a discussion of options: the request quoted, the type of decision (structure / algorithm / API shape / data structure / module boundaries), what was chosen, and counter-examples below the threshold. Examples are not invented; the source is raw session logs. Once added, they move into `diverge-synthesize-select/SKILL.md` (step 0.2).

## What was checked and what was not

Checked against files: every `file:line` in the steps above was opened and confirmed, including `unit_tests_writer.md:52-60`, `domain_modeller.md:113`, `api_designer.md:55,154,160`, `designer.md:55,120,168,196`, `database_designer.md:56,109`, `technical_product_manager.md:175-179,283,413,561`, `refactor_cleaner.md:60`, `observability_engineer.md:24-36,216,441-454,650`, `architect.md:49-50`, `agent_builder.md:184-189,294`, the six commands that call `AskUserQuestion`, `techne-implement.md:68-72,91,97,101,122,177-197`, `techne-review.md:25-27,85-110`, `workflow/SKILL.md:96,104,134,160`, `code-writing-protocols:17-44`, `agent-communication:122-129,148-166,200,208`, `lint-discipline:28,85-90`, `agent-builder/SKILL.md:63`, `translate_agents.py:8`, `validate_config.py:242-244`, `code-reviewer.toml:3,26`, `skill-builder.toml:5`, `CLAUDE_ADAPTER.md:17-18,44-45,62-65`, `dot_codex/AGENTS.md:52-57,97`, `GEMINI_ADAPTER.md:11-12`, `ci.yml:14-20`, `prepare-commit-msg:17,56,67`, and the Codex budget of 21,882 bytes. Against documentation: `model: fable` for subagents and the `fable` alias in Claude Code (code.claude.com, sub-agents and model-config). The GitHub MCP works (`get_me`).

Corrected from the draft: `$TMPDIR` in the core is at §5:143, not §4; the temporary-directory exclusion in `pre_edit_repo_boundary` does exist (`paths.temp_roots`); `bash_decision_gate.py` denies commit/push unconditionally — a critical omission; the DSS skill already contains the option procedure, so a new `option-deliberation` is not needed; the default branch is `master`, not `main`; `techne-implement.md:68-72` and `techne-plan.md` no longer ask about Jira.

Not checked: branch protection / rulesets and the auto-merge setting on `abrosimov/devbox-setup` (the `gh` token is invalid and MCP has no tool for it); the `claude` version on the target machine (≥ 2.1.257 for Fable 5.1); the mapping of `fable` to Antigravity tiers; the behaviour of `pre_plan_code_guard.py` for `streams/*.md`; `workspace-write` support in the current Codex version for TOML agents (`dot_codex/README.md:41` leaves this to the Codex client).
