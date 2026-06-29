---
tags: [claude-improvements, phase3, root-cause, layer-C]
phase: 3
rc-id: RC-15
layer: C
created: 2026-06-27
symptoms: [S-010, S-017, S-018, S-019, S-020, S-021, S-022, S-024]
---

# RC-15 — No asset encodes Fisher's-maxim engineering posture

## Mechanism

Eight symptoms in [[01-symptoms-inventory]] cluster under "engineering-attitude" — push-back without substance (S-010, S-017), wheel-reinvention (S-018), developer-not-engineer behaviour (S-019), fear of stack swaps citing test parity (S-020), false-dichotomy acceptance (S-021), no kill-two-birds overlap scanning (S-022), external locus of control (S-024). [[03-current-config-map#3.5 Engineering attitude]] confirms: no dedicated skill encodes this stance. `fpf-thinking` exists but is opt-in problem-framing; `diverge-synthesize-select` covers option generation, not posture. The user explicitly named the gap in source feedback: "ты инженер, у тебя есть задача и все доступное вокруг. Нерешаемых задач нет. Чего-то не хватает - создай" (Fisher's maxim — no unsolvable tasks; build what's missing). RLHF anti-sycophancy training in 4.7 ([[02-external-research#R2.4]]) actively pushes the model toward "hypothesis disproven" arguing loops that the missing skill would counter. The absence is structural — there is no body of text the model can attend that prescribes the alternative posture.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-010]], [[01-symptoms-inventory#S-017]], [[01-symptoms-inventory#S-018]], [[01-symptoms-inventory#S-019]], [[01-symptoms-inventory#S-020]], [[01-symptoms-inventory#S-021]], [[01-symptoms-inventory#S-022]], [[01-symptoms-inventory#S-024]].
- External: [[02-external-research#R2.4]] MindStudio arguing-loop write-up; [[02-external-research#R2.6]] abhs.in false-dichotomy confirmation; [[02-external-research#R2.3]] GH #53459 "walks back proposals on the next turn without integrating the user's objection".
- Config gaps: [[03-current-config-map#3.5 Engineering attitude]] — explicit gap; closest assets (`fpf-thinking`, `diverge-synthesize-select`) opt-in and off-target.
- Reflection: [[04-reflection-evidence#RC-ref-5]] — sycophantic gap-filling is the dual-failure of missing posture.

## Fix proposals

### F1 — New `engineering-attitude` skill, alwaysApply true

- **Surface:** new skill
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — adds always-on attention cost; mitigated by trimming UAP per [[rc-13-claude-md-bloat]].
- **Approach:** Single new skill encoding the five missing patterns: Fisher's maxim (no unsolvable tasks; if something is missing, build it or name what would unblock you), false-dichotomy detector ("if you produced two options, propose a third before committing"), shadow-mode + continuous-backward-compat (CBC) defaults for stack swaps, kill-two-birds overlap scan, internal locus of control. Body uses concrete examples lifted from user feedback (temporal-vs-hand-rolled-DAG; CV draft session).
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/skills/engineering-attitude/SKILL.md` with `alwaysApply: true`.
  2. Five sections: Fisher's Maxim, Anti-False-Dichotomy, Shadow-Mode + CBC, Overlap Scan, Internal Locus.
  3. Each section: 1 paragraph rule + 1 concrete example + 1 anti-pattern.
  4. Reference from `code-writing-protocols` and all `software_engineer_*` agents.
- **Touches/replaces:** new skill file; `code-writing-protocols/SKILL.md`; `agents/software_engineer_{go,python,frontend}.md`.

### F2 — Reviewer agent extension with attitude checks

- **Surface:** agent extension
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Extend `code_reviewer` and `meta_reviewer` agent frontmatter + body with a new review checkpoint: "Attitude check — does the implementation pattern-match push-back, false-dichotomy, or reinvent-wheel? If yes, flag and suggest the shadow-mode / overlap-scan / Fisher response." Reviewer fires on every code change; catches attitude failures at gate.
- **Steps:**
  1. Edit `agents/code_reviewer.md` — add Attitude Check to review checklist.
  2. Edit `agents/meta_reviewer.md` — add same check at PR level.
  3. Reference the new `engineering-attitude` skill.
- **Touches/replaces:** `agents/code_reviewer.md`; `agents/meta_reviewer.md`.

### F3 — Per-SE-agent reference to attitude skill (no-code)

- **Surface:** agent-frontmatter
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** Cheap no-code change. Add `engineering-attitude` to the explicit skills list in each `software_engineer_*.md` agent frontmatter and to the agent body's "Required reading" section. Reinforces the rule when SE agent loads, not only when alwaysApply fires.
- **Steps:**
  1. Edit `agents/software_engineer_go.md`, `software_engineer_python.md`, `software_engineer_frontend.md`.
  2. Append `engineering-attitude` to skills list.
  3. Mention in Required Reading section.
- **Touches/replaces:** three agent files.

### F4 — `engineer-posture` output-style

- **Surface:** output-style
- **Effort:** low
- **Impact:** low
- **Risk:** low — opt-in style.
- **Approach:** Lightweight output style users can switch into for engineering-heavy tasks. Output style emits a brief `<posture-check>` block before code proposals: "Is this a false dichotomy? (Y/N). Is there an existing library/pattern? (Y/N). Is the kill-two-birds opportunity scanned? (Y/N)". Forces the model to assert against the checklist visibly. Pairs with F1 — the skill is the rule, the output style is the audit trail.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/output-styles/engineer-posture.md`.
  2. Document trigger in `commands/techne-implement.md` as opt-in flag.
- **Touches/replaces:** new output-style file; `commands/techne-implement.md`.

### F5 — UserPromptSubmit nudge when prior turn contained push-back patterns

- **Surface:** hook (extend `proposal_discipline.py` or new)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low
- **Approach:** Deterministic detector. New UserPromptSubmit hook (or extension of `proposal_discipline.py`) scans the previous assistant turn for push-back markers — "this is impossible because", "this won't work", "I disagree", "but the problem is" — without an accompanying suggestion of an alternative. When detected, inject `additionalContext`: "Previous turn contained push-back. Apply engineering-attitude skill — no unsolvable tasks; propose what would unblock you or build the missing piece." Catches the arguing loop before round 2.
- **Steps:**
  1. Extend `bin/proposal_discipline.py` with `_detect_pushback_markers(prior_turn) -> bool`.
  2. When detected, emit `additionalContext` referencing `engineering-attitude` skill.
  3. Cover with test in `bin/tests/test_proposal_discipline.py`.
- **Touches/replaces:** `bin/proposal_discipline.py`; `bin/tests/test_proposal_discipline.py`.

## Acceptance signal

- New skill `engineering-attitude` exists with `alwaysApply: true` and is referenced by all 3 SE agents + code_reviewer.
- In 10 fresh sessions involving stack-change questions, ≥7 propose shadow-mode or CBC pattern without the user prompting.
- In 10 sessions where the model would have pushed back, ≥7 produce a constructive third option instead of the arguing loop.
- `proposal_discipline.py` detects ≥80% of push-back-without-alternative patterns in a small labelled corpus.
- User-perceived "developer vs engineer" gap reported as narrowed in next round of feedback.

## Trade-offs and counter-evidence

- **Skill bloat risk.** Adding an alwaysApply skill costs attention. Mitigation: pair with [[rc-13-claude-md-bloat]] F1 (UAP trim of ~70 lines) to net-decrease the always-on stack.
- **Attitude rules are deeply advisory.** Hooks (F5) can detect anti-patterns but cannot enforce constructive posture — they can nudge only. CLAUDE.md style rules degrade at ~70% adherence ([[02-external-research#R3.2]]); attitude rules likely fare worse.
- **RLHF training is the upstream cause** ([[02-external-research#R2.4]], [[rc-01-rlhf-pushback-loop]]). Skill-layer intervention works around model-internal pressure; cannot eliminate it. Expected partial-mitigation, not solution.
- **Fisher's maxim has a failure mode** — "no unsolvable tasks" can degenerate into reckless over-build (S-018 wheel-reinvention). The skill must explicitly pair "build what's missing" with "first scan for existing solution" — otherwise it just trades one failure for another.
- **F4 (output-style) adds output overhead.** Posture-check block burns tokens; only worth it on engineering-heavy sessions. Keep opt-in.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-01-rlhf-pushback-loop]] — upstream model-internal cause
- [[rc-08-sycophantic-gap-filling]] — dual failure mode
