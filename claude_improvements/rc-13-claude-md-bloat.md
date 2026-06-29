---
tags: [claude-improvements, phase3, root-cause, layer-C]
phase: 3
rc-id: RC-13
layer: C
created: 2026-06-27
symptoms: [S-003, S-005, S-006, S-007, S-008, S-011, S-012, S-013, S-014, S-015, S-016, S-026]
---

# RC-13 — Effective CLAUDE.md stack is 2.5x-5x over Anthropic's attention budget

## Mechanism

CLAUDE.md content is loaded as a system-level instruction block. Anthropic's own warning threshold (CHANGELOG `v2.1.169`) and the underlying attention-budget research ([[02-external-research#R3.2]]) put the practical ceiling at ~150 attended instructions, of which the harness system prompt already consumes ~50. The user's deployed stack — `USER_AUTHORITY_PROTOCOL.md` (216 lines) + project `devbox-setup/CLAUDE.md` (196 lines) + workspace `Projects/CLAUDE.md` (97 lines) = 509 effective lines ([[03-current-config-map#6. CLAUDE.md size and bloat]]) — exceeds budget by 2.5x-5x. Rule-drop is structural, not motivational: the model literally cannot maintain attention across 509 lines while also serving a turn. Distant rules (Voice at line 57 of a 216-line file; Co-Authored-By ban at line 142) are statistically dropped more often than rules at the top. Bloat is the upstream cause of nearly every adherence-class symptom in [[01-symptoms-inventory]].

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-005]], [[01-symptoms-inventory#S-006]], [[01-symptoms-inventory#S-007]], [[01-symptoms-inventory#S-008]], [[01-symptoms-inventory#S-011]], [[01-symptoms-inventory#S-012]], [[01-symptoms-inventory#S-013]], [[01-symptoms-inventory#S-014]], [[01-symptoms-inventory#S-015]], [[01-symptoms-inventory#S-016]], [[01-symptoms-inventory#S-026]] — all instruction-adherence-class.
- External: [[02-external-research#R1.5]] Anthropic `v2.1.169` "CLAUDE.md is too long" warning now scales with context window; [[02-external-research#R3.2]] practitioner consensus ≤200 lines; [[02-external-research#R2.3]] GH #53459 — "CLAUDE.md rules are silently dropped".
- Config gaps: [[03-current-config-map#6. CLAUDE.md size and bloat]] (509-line total), [[03-current-config-map#2. USER_AUTHORITY_PROTOCOL.md (216 lines) — anatomy]].
- Reflection: not direct, but compounds with [[04-reflection-evidence#RC-ref-1]] — when rules are dropped, helpfulness gradient dominates.

## Fix proposals

### F1 — Surgical trim of `USER_AUTHORITY_PROTOCOL.md` to ≤150 lines

- **Surface:** CLAUDE.md
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — losing recall on rules moved out; mitigated by skill back-references.
- **Approach:** Cut UAP from 216 to ≤150 lines by moving the entire "Code Projects Only" block (lines 156-212, ~57 lines) into a new `alwaysApply: true` skill `coding-context-rules`, keeping only a one-line pointer in UAP. Collapse "What Counts as Approval" enumeration into the trigger table that precedes it.
- **Steps:**
  1. Extract `roles/devbox/files/dot_claude/USER_AUTHORITY_PROTOCOL.md:156-212` into `roles/devbox/files/dot_claude/skills/coding-context-rules/SKILL.md` (alwaysApply true).
  2. Replace lines 156-212 with a single pointer line: `*See* `coding-context-rules` *skill for Go formatting, agent workflow opt-in, and cross-cutting rules.*`
  3. Merge `§ What Counts as Approval` (lines 96-110) into a third column of the trigger table at lines 79-94.
  4. Re-deploy via `make claude-push`.
- **Touches/replaces:** `roles/devbox/files/dot_claude/USER_AUTHORITY_PROTOCOL.md`; new `roles/devbox/files/dot_claude/skills/coding-context-rules/SKILL.md`.

### F2 — Audit and dedupe project-level CLAUDE.md against global

- **Surface:** CLAUDE.md (project + workspace)
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** No-code audit. `Projects/CLAUDE.md` (97 lines) describes workspace layout — keep. `devbox-setup/CLAUDE.md` (196 lines) duplicates much of UAP-context: it re-states Go formatting policy, agent workflow opt-in, and language policy that already live in UAP. Cut redundant sections; keep only project-specific content (commands, architecture, devbox-specific deployment notes).
- **Steps:**
  1. Read both files, identify duplicate sections against UAP §Code Projects.
  2. Remove dupes from project CLAUDE.md (target ≤120 lines).
  3. Workspace CLAUDE.md: keep as-is — it describes `proj`/`wt` tooling unique to the workspace.
- **Touches/replaces:** `/Users/kirillabrosimov/Projects/devbox-setup/CLAUDE.md`.

### F3 — Post-edit hook warning when CLAUDE.md exceeds line budget

- **Surface:** hook (new bin script + `hooks.json`)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low
- **Approach:** Deterministic guard. New PostToolUse hook on `Write|Edit|MultiEdit` matching paths `**/CLAUDE.md`, `**/USER_AUTHORITY_PROTOCOL.md`, `**/.claude/CLAUDE.md`. Counts lines, emits `additionalContext` warning when over budget (UAP ≤150, project ≤120, workspace ≤100). Non-blocking — informational only, so authoring CLAUDE.md content does not require approval gymnastics.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/bin/post_edit_claude_md_size.py` — read final line count, compare to per-path budget, emit `additionalContext` with line count and suggested cuts.
  2. Register in `hooks.json` under `PostToolUse` matcher `Edit|Write|MultiEdit` with path filter.
  3. Cover with unit test in `bin/tests/test_post_edit_claude_md_size.py`.
- **Touches/replaces:** new `bin/post_edit_claude_md_size.py`; `roles/devbox/files/dot_claude/hooks.json`.

### F4 — Convert "Code Projects Only" block to conditional alwaysApply skill

- **Surface:** new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low — skill activates only on code-project signals.
- **Approach:** Reuses the extraction from F1 but goes further — the new `coding-context-rules` skill uses an `alwaysApply: false` posture with a clear trigger description ("Use when the working directory is a Go/Python/TS code project (presence of `go.mod`, `pyproject.toml`, `package.json`, or `.claude/workflow.json`)"). Saves attention budget on non-code sessions (Obsidian notes, devbox-setup config edits).
- **Steps:**
  1. Define skill frontmatter with explicit trigger description per `skill-builder` template.
  2. Body: Go formatting, agent workflow opt-in, cross-cutting code rules.
  3. Update `agents/software_engineer_*.md` frontmatter to reference the skill explicitly.
- **Touches/replaces:** new `roles/devbox/files/dot_claude/skills/coding-context-rules/SKILL.md`; `software_engineer_{go,python,frontend}.md`.

### F5 — `make validate-claude` line-budget check

- **Surface:** validation script (existing `bin/validate-pipeline-output` or new)
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Deterministic CI-style guard. Extend `make validate-claude` target to fail when any deployed CLAUDE.md file exceeds its budget. Output table of file + line count + budget + delta. Block `make claude-push` if check fails (or warn-only initially).
- **Steps:**
  1. Add `bin/validate_claude_md_budget.py` (single-purpose) returning non-zero on violation.
  2. Wire into `Makefile:validate-claude` target.
  3. Initial mode: warn-only for 7 days; flip to blocking afterwards.
- **Touches/replaces:** `Makefile`; new `bin/validate_claude_md_budget.py`.

## Acceptance signal

- `wc -l` on UAP returns ≤150 lines; project CLAUDE.md ≤120; workspace ≤100; combined effective stack ≤370 (down from 509).
- Re-test on 5 prior failure cases (S-005, S-007, S-008, S-014, S-026) shows ≥1 of them no longer reproducing in a fresh session.
- `make validate-claude` flags any future overshoot before merge.
- Anthropic's own "CLAUDE.md too long" warning (per `v2.1.169`) stops firing in the harness.
- Hook `post_edit_claude_md_size.py` emits zero warnings for ≥7 days of normal editing.

## Trade-offs and counter-evidence

- **Counter-evidence — moving rules to skills lowers attention further.** Skills are loaded on-demand; an `alwaysApply: true` skill still costs attention per turn but is colocated with skill index, not the system prompt. Moving content out of CLAUDE.md may relocate the adherence problem rather than solve it.
- **Aggressive cuts risk losing protection.** UAP §Enumerated Stop Conditions (lines 112-124) is partially backstopped by `pre_bash_safety_gate.py` — those can move safely. UAP §Voice (lines 53-75) has no hook backstop — cuts there immediately drop brevity adherence.
- **Anthropic reverted the ≤25/≤100 word brevity cap after a 3% eval drop** ([[02-external-research#R2.1]]). Trimming Voice section too far may produce the same regression. Keep Voice rules verbatim; trim Approval/Code-Projects/Cross-Cutting.
- **Compounding bloat with project CLAUDE.md.** Per-project CLAUDE.md files in `agentic-rag-mcp`, `ai-assistant-playground`, etc. each add their own lines. Fix surface here addresses only the workspace+global stack; per-project cleanup is per-project work.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-11-claude-md-attention-budget]] — same mechanism, Anthropic-side
- [[rc-14-inter-asset-conflicts]] — conflicts amplify bloat penalty
- [[rc-17-advisory-only-rules]] — bloat undermines advisory rules first
