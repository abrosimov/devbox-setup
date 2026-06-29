---
tags: [claude-improvements, phase1, config-map, gaps]
phase: 1
created: 2026-06-27
status: ground-truth
---

# Current `dot_claude/` configuration map and gap analysis

Snapshot of `roles/devbox/files/dot_claude/` deployed as `~/.claude/`. Counts, anatomy, what targets which symptom, and where the defence has holes.

## 1. Inventory at a glance

- **Agents: 28** — agent_builder, api_designer, architect, build_resolver_go, code_reviewer, consistency_checker, content_reviewer, database_designer, database_reviewer, designer, doc_updater, domain_expert, domain_modeller, focus_coach, freshness_auditor, implementation_planner, integration_tests_writer_{go,python}, meta_reviewer, observability_engineer, refactor_cleaner, skill_builder, software_engineer_{frontend,go,python}, tdd_guide, technical_product_manager, unit_tests_writer.
- **Commands: 23** — all `techne-` prefixed (`techne-api-design`, `techne-audit`, `techne-build-{agent,skill}`, `techne-decision`, `techne-design`, `techne-devcontainer`, `techne-domain-analysis`, `techne-focus`, `techne-guide`, `techne-implement`, `techne-init-workflow`, `techne-learn`, `techne-log`, `techne-next`, `techne-options`, `techne-plan`, `techne-review`, `techne-schema`, `techne-test`, `techne-think`, `techne-validate-config`, `techne-verify`).
- **Skills: 40** — clusters: core agent protocols (5: agent-base-protocol, code-writing-protocols, agent-communication, shared-utils, config), engineering languages (12: go-engineer, go-testing, go-review-checklist, python-engineer, python-testing, python-tooling, python-monolith, frontend-engineer, frontend-testing, frontend-tooling, playwright-e2e, lint-discipline), navigation/search (3: lsp-navigation, lsp-tools, ast-grep), MCP (3: mcp-playwright, mcp-sequential-thinking, mcp-storybook), thinking/discipline (5: fpf-thinking, diverge-synthesize-select, iterative-retrieval, code-comments, self-contained-options), project (3: project-preferences, project-toolchain, sandbox-toolchain), builders/auditors (3: skill-builder, agent-builder, techne-fewer-permission-prompts), domain/UI (3: ui-design, structured-output, hooks-architecture), editing/workflow (3: editing-claude-config, workflow, docker-validation).
- **Hooks (`hooks.json:1-248`):**
  - `PreToolUse(Bash)` ×4: `pre_bash_toolchain_guard`, `pre_tmpdir_guard`, `pre_bash_safety_gate`, `pre_bash_boundary_wrap`.
  - `PreToolUse(Write)` ×5: `pre_tmpdir_guard`, `pre_edit_lint_guard`, `pre_write_completion_gate`, `pre_write_existing_guard`, `pre_plan_code_guard`.
  - `PreToolUse(Edit)` ×2: `pre_edit_lint_guard`, `pre_plan_code_guard`.
  - `PreToolUse(MultiEdit)`: `pre_plan_code_guard`.
  - `PermissionRequest` ×1: `permission_auto_approve`.
  - `PostToolUse(Edit|Write)`: `post_edit_lint`, `post_edit_typecheck` (async), `post_edit_cyrillic_guard`.
  - `PostToolUse(MultiEdit|NotebookEdit)`: `post_edit_cyrillic_guard`.
  - `PostToolUse` (default): `suggest_checkpoint` (async).
  - `UserPromptSubmit`: `proposal_discipline`.
  - `Stop`: `stop_format`, `stop_lint_gate`, `proposal_discipline`.
  - `PreCompact`: `session_save`, `pre_compact_mask`.
  - `SessionEnd`: `session_save`.
  - `WorktreeCreate`/`WorktreeRemove`: lifecycle scripts.
- **Bin scripts**: ~30 production + tests. Behaviour-relevant: `proposal_discipline.py`, `permission_auto_approve.py`, `pre_bash_safety_gate.py`, `pre_plan_code_guard.py`, `pre_write_existing_guard.py`, `pre_write_completion_gate.py`, `session_save.py`, `pre_compact_mask.py`, `stop_lint_gate.py`, `post_edit_cyrillic_guard.py`, `suggest_checkpoint.py`, `fpf_drift_check.py`.

## 2. USER_AUTHORITY_PROTOCOL.md (216 lines) — anatomy

Deployed as `~/.claude/CLAUDE.md`.

- **`§ Helpfulness Contract` (lines 9-13).** "You are not graded on speed of action … Acting on inferred intent — even producing technically correct output — is a failed outcome." Strict-reviewer framing. Encodes anti-S-016 (premature action).
- **`§ Discipline Protocol — Inquiry` (lines 17-51).** Forces reconnaissance ladder before action, mandates Disclosure block (Restated intent + Assumptions + Open questions) for non-trivial requests. Encodes anti-S-015 (random assumptions), anti-S-016. Lists batched-question rule `(line 46)`: "Present every unresolved doubt in a single `AskUserQuestion` call." — encodes anti-S-007 (asking too early).
- **`§ Voice — brevity` (lines 53-75).** Three modes: default (fact density), brainstorm (opt-in), iteration (delta-only). Lists explicit anti-patterns (restating user as conclusion, padding, hedging, full rewrites of numbered proposals). Encodes anti-S-005, S-006, S-009, S-011, S-014.
- **`§ Proposal ≠ Approval` (lines 77-94).** Approval-required trigger table. Encodes anti-S-012 (initiative creep), anti-S-016.
- **`§ What Counts as Approval` (lines 98-110).** Explicit allow-list of approval phrases. Tightens the gate.
- **`§ Enumerated Stop Conditions` (lines 112-124).** Categorical halt list (rm -rf, reset --hard, force-push, --no-verify, etc.). Pairs with `pre_bash_safety_gate.py`.
- **`§ Before Any Implementation` (lines 126-134).** Two-step self-check. Anti-S-016.
- **`§ Checkpoint Format` (lines 136-140).** Mandates `[Awaiting your decision]` token after proposals. Hook-detectable signal used by `proposal_discipline.py:41-44`.
- **`§ Git Commits` (lines 142-144).** "Never add Co-Authored-By trailers." Encodes anti-S-026.
- **`§ Language Policy` (lines 146-152).** British English for artefacts; Cyrillic guard PostToolUse hook.
- **`§ Code Projects — Go Formatting` (lines 160-162).** `goimports -local <module-name>` mandate.
- **`§ Agent Workflow opt-in` (lines 164-196).** Per-project `.claude/workflow.json` gates the mandatory-agent pipeline.
- **`§ Cross-Cutting Rules` (lines 198-212).** Immutability, comments policy, security at boundaries, model selection, agent delegation, LSP-first navigation, ast-grep, worktrees, shell discipline, Bash shape, tool choice for searches.

## 3. Behaviour-targeting assets per category

### 3.1 Context-window management (S-001, S-041)
- `settings.json:12` `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80` — pushes autocompact threshold to 80%.
- `pre_compact_mask.py` — masks content before compaction.
- `session_save.py` on PreCompact + SessionEnd — persists state.
- `iterative-retrieval` skill — progressive context refinement pattern.

### 3.2 Brevity / anti-graphomania (S-005, S-006, S-009, S-011, S-014, S-033)
- USER_AUTHORITY_PROTOCOL.md `§ Voice` (lines 53-75) — three modes, anti-patterns enumerated.
- `code-comments` skill — narration comments forbidden.
- `proposal_discipline.py` — nudges delta-only iteration via `additionalContext`.

### 3.3 Premature action / "jumps to implementation" (S-012, S-016, S-027, S-029)
- USER_AUTHORITY_PROTOCOL.md `§ Helpfulness Contract` + `§ Proposal ≠ Approval`.
- `code-writing-protocols` skill — MANDATORY Approval Validation step (Step 1: Scan, Step 2: Stop, Step 3: Proceed).
- `pre_plan_code_guard.py` PreToolUse on Write/Edit/MultiEdit.
- `pre_write_completion_gate.py` PreToolUse on Write.
- `proposal_discipline.py` UserPromptSubmit + Stop hook.

### 3.4 Inquiry discipline / clarification gating (S-007, S-008, S-015)
- USER_AUTHORITY_PROTOCOL.md `§ Discipline Protocol — Inquiry` (lines 17-51) — Disclosure block + Reconnaissance ladder + batched-question rule.
- `agent-base-protocol` skill `§ When to Ask` (lines 33-79) — Tier 1/2/3 + format template.
- `self-contained-options` skill — every option must include concrete identifier; descriptions restate context.

### 3.5 Engineering attitude (S-010, S-017, S-018, S-019, S-020, S-021, S-022, S-024)
- No dedicated skill exists. UAP does not encode Fisher's maxim or "no false dichotomy" rule.
- `fpf-thinking` skill exists but is opt-in (not always-applied) and targets problem-framing, not engineering posture.

### 3.6 Repetition / restating user words (S-006, S-009, S-014, S-034)
- USER_AUTHORITY_PROTOCOL.md `§ Voice` "Avoid: restating the user as your conclusion".
- `proposal_discipline.py` — only addresses one repetition class (rewrites instead of deltas).

### 3.7 Initiative creep / unsolicited reframing (S-012, S-013, S-029, S-037, S-038)
- USER_AUTHORITY_PROTOCOL.md `§ Proposal ≠ Approval`.
- `code-writing-protocols` skill Approval Validation.
- Agents have per-role `tools:` and scoped responsibilities (role boundary encoded in their frontmatter).

### 3.8 Reconnaissance before action (S-015, S-016)
- USER_AUTHORITY_PROTOCOL.md `§ Inquiry` Reconnaissance ladder (lines 39-44).
- `iterative-retrieval` skill — DISPATCH/EVALUATE/REFINE/LOOP pattern.
- `lsp-navigation` + `lsp-tools` skills — LSP-first navigation.
- `pre_write_existing_guard.py` — blocks writes to unread files (partially).

### 3.9 Bullshit detection / counter-evidence (S-023)
- `code-reviewer` agent has counter-evidence checks via go-review-checklist skill.
- No general-purpose bullshit detector. `fpf-thinking` is opt-in.

### 3.10 Git hygiene (S-025, S-026, S-031)
- USER_AUTHORITY_PROTOCOL.md `§ Git Commits` (S-026 ban on Co-Authored-By).
- `settings.json:140-226` `permissions.deny` blocks destructive git ops (force, reset --hard, --amend, --no-verify, etc.).
- `permission_auto_approve.py` reduces friction on safe git commands.
- `git_safe_commit.py`, `git_safe_merge.py` — exist as helpers.
- No hook detects/forces "pull master into branch" (S-025).

### 3.11 Out-of-order responses / interleaving (S-004)
- No dedicated mechanism.

### 3.12 Citations / file:line references (S-003, S-008)
- USER_AUTHORITY_PROTOCOL.md `§ Voice` "Cite verifiable claims: `path:line`, URL, doc anchor."
- `code-writing-protocols` skill — references citation discipline. No enforcement hook.

### 3.13 Permission allowlist hygiene (S-002, S-031)
- `settings.json:138-499` extensive permissions config.
- `permission_auto_approve.py` PermissionRequest hook with `SAFE_COMMAND_FAMILIES` whitelist.
- `techne-fewer-permission-prompts` skill — mines transcripts.
- `claude_fix_perms.py` bin script.

### 3.14 Sub-agent skill suppression (S-028)
- No mechanism enforces skill invocation. `Skill` tool is advisory.
- `validate_skill_evals.py` — evaluator exists but covers a subset.

### 3.15 Self-verification before reporting "done" (S-027)
- `stop_lint_gate.py` Stop hook — runs lint at session end.
- `stop_format.py` Stop hook — runs format.
- `post_edit_lint.py`/`post_edit_typecheck.py` PostToolUse hooks.
- No hook validates that build/test commands the agent reports as passing actually passed (the agent might never have run them).

## 4. Gaps and weaknesses

- **3.1 (context-mgmt):** No proactive `~/.claude` hook detects context fill ≥ 50% and emits a warning into `additionalContext`. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80` is too late — practitioner evidence puts the soft cliff at 50-60% ([[02-external-research#R4.5]]). `pre_compact_mask` runs only on compaction; no "rotate to fresh session" suggestion.
- **3.2 (brevity):** Anti-graphomania rules live in CLAUDE.md (advisory ~70% adherence). No PostStop hook flags output > N lines. Multi-screen agent reports go uncaught.
- **3.3 (premature action):** Hooks exist but operate on Write/Edit. No hook detects "agent emitted final answer without doing a single Read first" or "agent emitted code in a turn where the user asked a `?` question". `proposal_discipline.py` is nudge-only.
- **3.4 (inquiry):** `agent-base-protocol:35` says **"Ask ONE question at a time"** which **contradicts** USER_AUTHORITY_PROTOCOL.md `:46` **"Present every unresolved doubt in a single `AskUserQuestion` call"**. Direct conflict — see §5.
- **3.5 (engineering attitude):** No skill encodes Fisher's maxim, anti-false-dichotomy, shadow-mode/CBC patterns, kill-two-birds heuristic. User explicitly named these as missing in source feedback. Closest existing assets (`fpf-thinking`, `diverge-synthesize-select`) are opt-in and don't address attitude.
- **3.6 (repetition):** Only `proposal_discipline.py` covers the rewrite-instead-of-delta case. The broader "restate user message in your own words then act on the restatement" failure mode (reflection.md §3: helpfulness-as-artefact, §4: draft becomes source of truth) has no enforcement.
- **3.7 (initiative-creep):** Hooks gate Write/Edit but not "ran 6 Bash commands for an investigation when only 1 file Read was asked". No turn-level scope-creep detector.
- **3.8 (reconnaissance):** Reconnaissance ladder is advisory. `pre_write_existing_guard.py` partially enforces — only on Write — not on Edit. Agent can still emit a Bash command modifying a file it never Read.
- **3.9 (bullshit detection):** No dedicated mechanism. User explicit gap.
- **3.10 (git hygiene):** S-025 "pull master into branch" has zero coverage. S-026 (Co-Author leak): USER_AUTHORITY_PROTOCOL ban exists — but no `Bash(git commit *)` PreToolUse hook strips trailers. The ban relies on adherence.
- **3.11 (ordering):** Zero coverage.
- **3.12 (citations):** Advisory rule only. No PostStop hook detects bare references like "see d32" without a path.
- **3.13 (permission UX):** `permission_auto_approve.py` exists but the user is still being prompted on routine actions (this very session). Likely cause: SAFE_COMMAND_FAMILIES list does not cover Glob/Grep/Read/Task tool dispatch from subagents in some path. Worth instrumentation.
- **3.14 (skill suppression):** Only `validate_skill_evals.py` exists and is partial. No PreToolUse hook detects "user prompt matches skill trigger but agent attempts Edit instead".
- **3.15 (self-verification):** `stop_lint_gate.py` exists. No hook validates that agent-claimed test-pass actually corresponds to an executed test run. Agent can write "tests pass" without having called `pytest`/`go test`.

## 5. Inter-asset conflicts and orphans

### Conflict 5.1 — One question at a time vs batched
- `skills/agent-base-protocol/SKILL.md:35` "CRITICAL: Ask ONE question at a time. Do not overwhelm the user."
- `USER_AUTHORITY_PROTOCOL.md:46` "Batched questions. Present every unresolved doubt in a single AskUserQuestion call."

These collide. User feedback S-007 favours **batched**. The agent-base-protocol rule fights the global rule and is referenced by every agent → propagates the conflict.

### Conflict 5.2 — Workflow-opt-in detection bypasses user authority
- `USER_AUTHORITY_PROTOCOL.md:168-180` says "If no `workflow.json`, ASK before code edits." The asking itself violates the rule "don't ask one-by-one" and the brevity rule (long block of A/B/C explanation).

### Conflict 5.3 — Subagent vs main thread approval ownership
- `code-writing-protocols:15-49` mandates Approval Validation **inside the subagent**.
- USER_AUTHORITY_PROTOCOL.md treats approval as a main-thread concept (the user types "go ahead" to the main thread).
- Result: when main thread spawns a subagent via Task, the subagent re-asks for approval — duplicates the gate and burns context.

### Conflict 5.4 — Brevity rule vs disclosure block
- USER_AUTHORITY_PROTOCOL.md `§ Voice` "Lead with the answer; no preamble".
- USER_AUTHORITY_PROTOCOL.md `§ Discipline Protocol` "Disclosure block (first reply, always): Restated intent + Assumptions + Open questions".
- The disclosure block IS a preamble. The two rules collide on first-reply turns. Reflection.md §1 (helpfulness-as-artefact) is partly downstream of this collision.

### Orphan 5.5 — `lint-discipline` skill referenced as "alwaysApply" but skill `frontmatter` not verified
Multiple agents list `lint-discipline` as required reading but the agent-base-protocol does not enforce loading order.

### Duplication 5.6 — Approval validation logic
- `code-writing-protocols:15-49` (Approval Validation)
- `USER_AUTHORITY_PROTOCOL.md:98-110` (What Counts as Approval)
- `agent-base-protocol:33-79` (When to Ask)
All three say overlapping things slightly differently. Maintenance hazard.

## 6. CLAUDE.md size and bloat

| File | Lines |
|---|---|
| `USER_AUTHORITY_PROTOCOL.md` (deployed as `~/.claude/CLAUDE.md`) | **216** |
| Project `devbox-setup/CLAUDE.md` | **196** |
| Workspace `Projects/CLAUDE.md` | **97** |
| Combined effective CLAUDE.md when in this repo | **509** |

Anthropic guidance (per CHANGELOG `v2.1.169`): model attends ~150 instructions; system prompt eats ~50; net budget for CLAUDE.md ≈ 100-200 lines. The effective 509-line stack is **2.5×–5× over budget**. Practitioner evidence ([[02-external-research#R3.2]]) puts cliff at 200 lines.

Implications:
- The Voice rule (line 57-61) lives at line 57 of a 216-line file. Distant rules attended less reliably.
- Conflicts (§5) are made worse by bloat — model picks the rule it last attended.

## 7. Summary signal for downstream analysis

- **Hooks layer is mature** but skewed toward Write/Edit safety and post-edit linting. Behavioural gates (brevity, reconnaissance, initiative-creep, citation discipline) are largely absent.
- **CLAUDE.md is over budget by 2.5×–5×** depending on project — a structural cause of rule-drop.
- **At least 4 inter-asset conflicts** undermine consistency.
- **6 categories have zero hook coverage** (3.5, 3.9, 3.11, 3.12, 3.14, 3.15-partial).
- **Permission auto-approve exists but appears ineffective** in current session — instrumentation gap.

## See also

- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[04-reflection-evidence]]
- [[00-MoC]]
