---
tags: [claude-improvements, phase3, root-cause, layer-C]
phase: 3
rc-id: RC-14
layer: C
created: 2026-06-27
symptoms: [S-007, S-008, S-009, S-011, S-014, S-026, S-029]
---

# RC-14 — Inter-asset rule conflicts force the model to drop one rule on every turn

## Mechanism

Four documented direct conflicts exist between `USER_AUTHORITY_PROTOCOL.md`, `agent-base-protocol/SKILL.md`, and `code-writing-protocols/SKILL.md` ([[03-current-config-map#5. Inter-asset conflicts and orphans]]). When two rules contradict and both are in-context, the model picks the rule it last attended — typically the one nearer the bottom of the system prompt or the most-recently-mentioned skill. This makes adherence stochastic: any single conflict produces ~50% drift on rules whose phrasing differs across assets. Compounding with [[rc-13-claude-md-bloat]] (509 lines), even non-conflicting rules degrade in attention; the conflicting ones degrade catastrophically. Symptom S-007 (asks too early) is the textbook example: `agent-base-protocol:35` says "Ask ONE question at a time", `UAP:46` says "Present every unresolved doubt in a single AskUserQuestion call". User feedback explicitly favours batched. The agent follows whichever rule it attended last.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-007]] (one-vs-batched questions), [[01-symptoms-inventory#S-008]] (questions without context), [[01-symptoms-inventory#S-009]] (re-confirming user statements), [[01-symptoms-inventory#S-011]] (pub-talk vs dry facts), [[01-symptoms-inventory#S-014]] (paraphrase), [[01-symptoms-inventory#S-026]] (Co-Authored-By leak), [[01-symptoms-inventory#S-029]] (no proactive option-listing).
- External: [[02-external-research#R2.3]] GH #53459 — "CLAUDE.md rules silently dropped, violated across multi-paragraph outputs"; [[02-external-research#R3.2]] CLAUDE.md is advisory (~70% adherence).
- Config gaps: [[03-current-config-map#5. Inter-asset conflicts and orphans]] (4 documented conflicts + 1 duplication).
- Reflection: [[04-reflection-evidence#RC-ref-3]] — asking-vs-guessing asymmetry exacerbated when "ask" rule is contradicted across assets.

## Fix proposals

### F1 — Harmonise `agent-base-protocol` to defer to UAP on batching

- **Surface:** skill
- **Effort:** low
- **Impact:** high
- **Risk:** low
- **Approach:** Direct fix to Conflict 5.1. Replace `agent-base-protocol/SKILL.md:35` "Ask ONE question at a time" with "Batch all open doubts into a single AskUserQuestion call — see UAP §Discipline Protocol — Inquiry for the binding rule." Removes the contradiction; preserves UAP as single source of truth.
- **Steps:**
  1. Edit `roles/devbox/files/dot_claude/skills/agent-base-protocol/SKILL.md` line 35 region.
  2. Audit all 28 agents for direct `Ask ONE question` quotes (they may have copy-pasted the agent-base text); replace with batched language.
  3. Re-deploy via `make claude-push`.
- **Touches/replaces:** `skills/agent-base-protocol/SKILL.md`; possibly some `agents/*.md` files.

### F2 — Declare main-thread-owned approval state in a single skill

- **Surface:** skill (extend existing `code-writing-protocols`)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — subagents must learn to read approval state, not re-ask.
- **Approach:** Fix Conflict 5.3 (subagent vs main-thread approval ownership). Amend `code-writing-protocols` to state: "Approval is owned by the main thread. Subagents inherit approval from the dispatching `Task` call's prompt — they MUST NOT re-ask for approval on the same scope. If a subagent encounters new ambiguity outside the dispatched scope, it returns to main thread with a clarification request, it does not interactively re-prompt the user." Then remove the standalone Approval Validation step from agent-base-protocol.
- **Steps:**
  1. Edit `skills/code-writing-protocols/SKILL.md` — add `§ Approval Ownership` section.
  2. Remove duplicated approval logic from `skills/agent-base-protocol/SKILL.md:33-79`; leave a one-line pointer.
  3. Update software-engineer agents to reference the single source.
- **Touches/replaces:** `skills/code-writing-protocols/SKILL.md`; `skills/agent-base-protocol/SKILL.md`; `agents/software_engineer_*.md`.

### F3 — Replace disclosure block with `<reconnaissance>` XML tag separate from `<answer>`

- **Surface:** CLAUDE.md (UAP) + output-style
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — changing output format affects every turn.
- **Approach:** Fix Conflict 5.4 (Voice "Lead with the answer; no preamble" vs Discipline "Disclosure block, first reply, always"). Disclosure block IS preamble; the conflict cannot be resolved by either side winning. Use Anthropic's XML tag convention ([[02-external-research#R3.5]]): wrap the disclosure in `<reconnaissance>...</reconnaissance>` followed by `<answer>...</answer>`. The harness can hide or collapse `<reconnaissance>` in UI; the model writes both. Both rules become satisfiable simultaneously: answer is led, reconnaissance is captured separately.
- **Steps:**
  1. Edit UAP `§ Discipline Protocol — Inquiry` "Disclosure block" subsection to mandate `<reconnaissance>` wrapping.
  2. Edit UAP `§ Voice` to clarify: "Lead with the answer inside `<answer>` tag; reconnaissance preamble is permitted only inside `<reconnaissance>` tag and does not count as preamble."
  3. Add output-style `dual-tag` in `output-styles/` showing the contract.
- **Touches/replaces:** `USER_AUTHORITY_PROTOCOL.md`; new `output-styles/dual-tag.md`.

### F4 — Consolidate approval logic into one skill referenced everywhere

- **Surface:** skill consolidation (no-code restructure)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low
- **Approach:** Fix Duplication 5.6. Three assets carry overlapping approval logic: `code-writing-protocols:15-49`, `UAP:96-110`, `agent-base-protocol:33-79`. Make `code-writing-protocols` (or a new `approval-protocol` skill) authoritative; UAP carries the gate table only; agent-base-protocol carries a one-line pointer. Single source of truth — any future amendment touches one file.
- **Steps:**
  1. Decide canonical home (recommend extending `code-writing-protocols` to avoid yet another skill).
  2. Strip overlapping prose from UAP `§ What Counts as Approval` — keep the IS/NOT enumerated lists; remove paragraph commentary.
  3. Strip from `agent-base-protocol:33-79`.
  4. All agents listing approval validation reference the single canonical skill.
- **Touches/replaces:** `skills/code-writing-protocols/SKILL.md`; `skills/agent-base-protocol/SKILL.md`; `USER_AUTHORITY_PROTOCOL.md`.

### F5 — `techne-validate-config` rule detecting cross-asset string conflicts

- **Surface:** validation script (extend `bin/validate-pipeline-output` or new)
- **Effort:** high
- **Impact:** medium
- **Risk:** low
- **Approach:** Deterministic guard. New validator scans all CLAUDE.md + skill SKILL.md files for documented anti-pattern phrase pairs (e.g. "ONE question at a time" vs "single AskUserQuestion call"; "no preamble" vs "always include"). Pairs come from a maintained `bin/conflict_pairs.toml` catalogue. Reports conflicts at `make validate-claude` time. Catches re-introduction of resolved conflicts during future edits.
- **Steps:**
  1. Create `bin/conflict_pairs.toml` with the 4 documented conflicts + room for growth.
  2. Create `bin/validate_asset_conflicts.py` — for each pair, grep across `dot_claude/` for both sides; report cross-file matches.
  3. Wire into `Makefile:validate-claude`.
  4. Run as part of `commands/techne-validate-config.md`.
- **Touches/replaces:** new `bin/validate_asset_conflicts.py`, new `bin/conflict_pairs.toml`; `Makefile`; `commands/techne-validate-config.md`.

## Acceptance signal

- `agent-base-protocol/SKILL.md` no longer contains the string "ONE question at a time".
- `bin/validate_asset_conflicts.py` reports 0 conflicts after F1+F2+F4.
- Re-test S-007 (asks too early): in 10 fresh sessions on non-trivial tasks, ≥8 use a single batched `AskUserQuestion` call.
- Subagents dispatched via Task do not re-issue approval prompts on scope already approved in the dispatch prompt.
- `<reconnaissance>` and `<answer>` tags appear separated in first-reply turns; Voice anti-preamble rule reads as honoured.

## Trade-offs and counter-evidence

- **F3 (XML tag separation) is a format change.** Anthropic reverted ≤25/≤100 word brevity caps after a 3% eval drop ([[02-external-research#R2.1]]) — output-format mandates have nonzero cost. Roll out behind output-style opt-in first; measure before defaulting.
- **F2 (single approval owner) may break agents that legitimately need to reconfirm.** Refactor agents (e.g. `refactor_cleaner`) sometimes encounter new scope they couldn't anticipate. The rule must permit "return to main thread with clarification" — it cannot collapse to "subagent never asks".
- **F5 (conflict validator) is best-effort string match.** Semantic conflicts (rules that contradict but use different phrasing) slip through. Catalogue grows by hand. Useful as a regression guard, not a general detector.
- **Cumulative load.** F1+F2+F3+F4 all edit UAP. Net effect should reduce UAP size; verify line count against [[rc-13-claude-md-bloat]] budget after applying.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-13-claude-md-bloat]] — bloat amplifies conflict impact
- [[rc-17-advisory-only-rules]] — conflicts hit advisory rules hardest
