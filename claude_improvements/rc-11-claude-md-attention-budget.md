---
tags: [claude-improvements, phase3, root-cause, layer-B]
phase: 3
rc-id: RC-11
layer: B
created: 2026-06-27
symptoms: [S-026]
---

# RC-11 — CLAUDE.md attention budget exceeded

## Mechanism

The model attends approximately 150 instructions reliably; the harness system prompt itself consumes around 50, leaving ~100 budget for user-supplied CLAUDE.md content ([[02-external-research#R5]] item 6; Anthropic CHANGELOG `v2.1.169` explicitly added a "CLAUDE.md is too long" warning — [[02-external-research#R1.5]]). This user's effective stack on devbox-setup is **509 lines** combining `USER_AUTHORITY_PROTOCOL.md` (216) + project (196) + workspace (97) — 2.5×–5× over the practitioner-consensus budget ([[03-current-config-map#6. CLAUDE.md size and bloat]]). Rules attended last (e.g. "Never add Co-Authored-By trailers" at line 142 of UAP) drop with the highest frequency. The mechanism is harness-level (the attention mechanism cannot be patched) but the *content* sent into it is fully under user control.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-026]] (Co-Authored-By keeps reappearing despite explicit ban), all rule-adherence drift cases (see overview: "Drives all rule-drop cases")
- External:
  - [[02-external-research#R1.5]] Anthropic CHANGELOG `v2.1.169` "CLAUDE.md is too long" warning scaled to model context window
  - [[02-external-research#R2.3]] GitHub #53459: "CLAUDE.md rules are silently dropped … violated across multi-paragraph outputs, including outputs explicitly about instruction following"
  - [[02-external-research#R3.2]] practitioner consensus: keep CLAUDE.md ≤200 lines
  - [[02-external-research#R5]] item 6
- Config gaps: [[03-current-config-map#6. CLAUDE.md size and bloat]] — full size table (509 effective lines on this repo); [[03-current-config-map#5. Inter-asset conflicts and orphans]] — bloat amplifies conflicts because model picks the rule it last attended

## Fix proposals

### F1 — Trim `USER_AUTHORITY_PROTOCOL.md` to ≤150 lines

- **Surface:** CLAUDE.md (USER_AUTHORITY_PROTOCOL.md)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — must preserve all binding rules; risk losing nuance
- **Approach:** edit `roles/devbox/files/dot_claude/USER_AUTHORITY_PROTOCOL.md` to ≤150 lines. Move all worked examples (Disclosure-block example, Iteration-mode `[§N CHANGED]` template example, Reconnaissance-ladder examples, "Avoid:" list) into skills. Keep only: (a) Helpfulness Contract paragraph, (b) Approval-required trigger table, (c) Enumerated Stop Conditions list, (d) self-checks, (e) Git/Language one-liners, (f) Cross-Cutting Rules — but as bullets pointing to skills, not as paragraphs.
- **Steps:**
  1. Audit current 216 lines for moveable content.
  2. Move Disclosure-block example + Reconnaissance ladder examples to skill `question-as-deliverable` (proposed in RC-07 F5) or new `inquiry-discipline` skill.
  3. Move Voice anti-pattern catalogue to `code-comments` or new `voice-discipline` skill.
  4. Move worked Iteration-mode template to `iteration` output-style.
  5. Verify ≤150 lines and all binding rules still represented.
  6. `make claude-push` to redeploy.
- **Touches/replaces:** `USER_AUTHORITY_PROTOCOL.md` (replaces), several existing skills (extend).

### F2 — Deduplicate against per-project CLAUDE.md

- **Surface:** CLAUDE.md
- **Effort:** medium
- **Impact:** medium
- **Risk:** low
- **Approach:** audit `/Users/kirillabrosimov/Projects/CLAUDE.md` (workspace, 97 lines) and `/Users/kirillabrosimov/Projects/devbox-setup/CLAUDE.md` (project, 196 lines) against UAP. Move anything redundant out of the project files. Keep project CLAUDE.md to ≤50 lines for project-unique content only (tool commands, architecture pointers). Workspace CLAUDE.md likewise ≤50 lines (just navigation tooling map).
- **Steps:**
  1. Diff project + workspace CLAUDE.md against UAP — list overlaps.
  2. For each overlap, decide canonical location (UAP wins if it's a universal rule; project CLAUDE.md wins if it's project-specific).
  3. Edit project + workspace CLAUDE.md to remove duplicates.
  4. Verify final stack ≤200 lines.
- **Touches/replaces:** `Projects/CLAUDE.md`, `Projects/devbox-setup/CLAUDE.md`.

### F3 — Move "Code Projects Only" section to a skill loaded conditionally

- **Surface:** CLAUDE.md (UAP) + new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** the `Code Projects Only` section (UAP lines 156–212, ~57 lines including Go formatting, agent workflow opt-in, cross-cutting rules) applies only in code projects, not when editing notes or skills. Move to new skill `code-project-rules` with `alwaysApply: false` and a description that triggers on detection of source files (`.go`, `.py`, `.ts`, `.tsx`). Saves ~57 lines from the always-on stack.
- **Steps:**
  1. New `roles/devbox/files/dot_claude/skills/code-project-rules/SKILL.md`.
  2. Move UAP §"Code Projects Only" section verbatim.
  3. Frontmatter description triggers on code file edits, project workflow setup, agent dispatch.
  4. Delete the moved section from UAP, leaving a one-line pointer.
- **Touches/replaces:** UAP, new skill.

### F4 — settings.json `enabledPlugins` audit removing unused

- **Surface:** settings.json
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** audit `settings.json` `enabledPlugins` list (per [[03-current-config-map#1. Inventory at a glance]] 40 skills total, but not all need to be in `enabledPlugins`). Each enabled plugin loads its description into the system prompt — accumulates attention cost. Remove plugins not actively used in any session over last 30 days. Use `bin/eval_skills.py` or transcript-mining to identify.
- **Steps:**
  1. List currently-enabled plugins from `settings.json`.
  2. For each, grep transcripts (or use harness telemetry if available) for last invocation.
  3. Remove plugins not invoked in ≥ 30 days (or never).
  4. Document removal rationale in commit message.
- **Touches/replaces:** `settings.json`.

### F5 — Factor "Cross-Cutting Rules" list into individual `alwaysApply: true` skill backrefs

- **Surface:** CLAUDE.md (UAP) — no-code restructure
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** UAP §"Cross-Cutting Rules" (lines 198–212, ~15 bullets) currently contains brief reminders pointing to skills (`see project-preferences skill`, `see code-comments skill`, etc.). Each bullet is already in a skill with `alwaysApply: true`. Delete the entire list from UAP — the skills enforce the rules independently. Saves ~15 lines and removes one inter-asset duplication source.
- **Steps:**
  1. Verify each bullet in UAP §"Cross-Cutting Rules" has a matching `alwaysApply: true` skill.
  2. Delete the section from UAP.
  3. Replace with a single line: `Cross-cutting rules are enforced by alwaysApply: true skills. See skills/ for the catalogue.`
  4. `make claude-push`.
- **Touches/replaces:** UAP.

## Acceptance signal

- Effective CLAUDE.md stack ≤ 200 lines in any project (measured: UAP + project + workspace).
- Anthropic harness "CLAUDE.md is too long" warning ([[02-external-research#R1.5]]) does not fire on this user's setup.
- S-026 (Co-Authored-By leak) drops to ≤ 5% of commit messages (was: recurring per feedback note).
- Instruction-adherence drift measurable via transcript grep — count of "I will follow X" claims followed by X violation drops.
- Rule conflicts (e.g. one-question-at-a-time vs batched, [[03-current-config-map#Conflict 5.1]]) eliminated by removing duplicate rules.

## Trade-offs and counter-evidence

- F1+F3 risk: moving rules into skills means rules become advisory rather than load-bearing. Mitigation: any rule that is *categorical* (Stop Conditions, approval gates) must STAY in UAP — only examples and elaborations move out.
- F4 (plugin audit) risk: removing a plugin may break a workflow the user uses irregularly. Mitigation: keep an "audit log" of removed plugins for easy re-enable.
- Counter-evidence on attention-budget number: [[02-external-research#R3.2]] practitioner consensus is ≤200 lines but no Anthropic-published exact number. The 150-instruction figure is from community measurement, not docs. Mitigation: target ≤150 as conservative anchor.
- Counter-evidence on bloat-causes-drift causation: [[02-external-research#R2.3]] GitHub #53459 shows rule drop happening on *short* prompts too. Bloat is necessary but not sufficient — also addressed by [[rc-17-advisory-only-rules]].
- The April-23 postmortem ([[02-external-research#R2.1]]) shows Anthropic itself tried hardcoded brevity caps and reverted after a 3% eval drop — bluntly trimming text without preserving rule semantics carries quality risk. F1 must be done by *moving content*, not deleting.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-13-claude-md-bloat]] (Layer C variant: same problem from configuration choices angle)
- [[rc-14-inter-asset-conflicts]] (bloat amplifies these)
- [[rc-17-advisory-only-rules]] (parallel: even rules at high attention slip without enforcement)
