---
tags: [claude-improvements, phase3, root-cause, layer-A]
phase: 3
rc-id: RC-04
layer: A
created: 2026-06-27
symptoms: [S-001]
---

# RC-04 — Opus 4.7+ tokenizer charges 12-35% more tokens for same English text

## Mechanism

Opus 4.7 introduced a new tokenizer. Anthropic documents verbatim: "Compared to models before Claude Opus 4.7, the same text produces roughly 30% more tokens" ([[02-external-research#R1.4]]). Community measurements put the figure at 12-18% for typical English ([[02-external-research#R2.5]]) and up to 35% for prose-heavy text. The nominal 1M context window is unchanged; the *effective* content capacity shrunk silently by ~25%. This is a hidden multiplier on every other context-pressure failure mode: when the user reports "performance degrades past 55% fill" ([[01-symptoms-inventory#S-001]]), that 55% on a 4.7 token-counter represents the equivalent of ~70% on a 4.6 counter for the same English. The "context rot" cliff ([[02-external-research#R4.1]], [[02-external-research#R4.5]]) arrives earlier in wall-clock terms. The fix is not patchable at the model layer — the tokenizer is fixed in the weights. Mitigation: (a) compress prose at the input side, (b) lower autocompact thresholds to match the effective shrink, (c) prefer identifiers/numbers/citations over prose in agent outputs.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-001]] (degrades past 55% fill — but the 55% is itself denser tokens)
- External: [[02-external-research#R1.4]] (verbatim "30% more tokens"), [[02-external-research#R2.5]] (12-18% English cost regression), [[02-external-research#R4.5]] (practitioner thresholds cluster 50-60% for the soft cliff, but evidence is from 4.7-era tokens), [[02-external-research#R4.6]] (autocompact buffer reduced 45K → 33K — Anthropic adapting to denser tokens)
- Config gaps: [[03-current-config-map#3.1 Context-window management (S-001, S-041)]] — `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80` is **higher** than current practice suggests, not lower. No statusline shows effective-content percentage.

## Fix proposals

### F1 — Lower `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to 60

- **Surface:** settings.json (no-code)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — reversible single-value change
- **Approach:** Current value is `80` ([[03-current-config-map#3.1]]). With ~25% effective shrink, the practitioner soft-cliff threshold of 50-60% ([[02-external-research#R4.5]]) on 4.6-era tokens maps to ~40-48% on 4.7+ tokens. Setting autocompact to `60` triggers earlier — at the actual soft cliff. Practitioner literature ([[02-external-research#R3.4]]) recommends manual `/compact` at 40-60%.
- **Steps:**
  1. Edit `settings.json` `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` from `80` to `60`.
  2. Document the rationale in a comment or `editing-claude-config` skill note.
- **Touches/replaces:** `settings.json`.

### F2 — Statusline shows tokens-as-effective-percentage with model adjustment

- **Surface:** settings.json (statusLine) + new bin script
- **Effort:** medium
- **Impact:** medium
- **Risk:** low
- **Approach:** New `bin/statusline_token_meter.py` reads Claude Code's session token count, applies a model-aware adjustment (1.0 for 4.6 and earlier, 0.77 for 4.7+ to translate back to "4.6-equivalent" fill), and emits a coloured `[ctx: 47%→61% effective]` indicator. The user gets a tactile sense of effective fill.
- **Steps:**
  1. Implement `bin/statusline_token_meter.py` reading the relevant Claude Code session metadata.
  2. Wire to `settings.json` `statusLine.script`.
  3. Colour scale: green ≤40%, amber 40-55%, red ≥55% (effective).
- **Touches/replaces:** `settings.json`, new `bin/` script.

### F3 — UserPromptSubmit injection at ≥40% effective fill: "context-budget reminder"

- **Surface:** hook (extend existing or new)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low — additive context, ~30 tokens per turn at threshold
- **Approach:** New `pre_prompt_context_budget.py` UserPromptSubmit hook. When effective fill ≥40%, inject `additionalContext`: "Context budget: 40% effective fill. Prefer file:line citations over re-quoting. Use identifiers, not paraphrases. Consider `/clear` + handoff file if this thread is getting long." Threshold tied to F2's effective-percentage logic.
- **Steps:**
  1. Implement `bin/pre_prompt_context_budget.py`.
  2. Register under `UserPromptSubmit`.
  3. Suppress the injection if the prior assistant turn already emitted it (avoid hammering).
- **Touches/replaces:** `hooks.json`, new `bin/` script.

### F4 — `lexical-density` skill encoding "identifiers over prose" discipline

- **Surface:** new skill
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low — advisory
- **Approach:** New `skills/lexical-density/SKILL.md` (50-80 lines) codifies: (a) prefer `path:line` over "in the X file", (b) prefer numbers over adjectives ("reduced 794 → 502 lines" beats "significant reduction"), (c) prefer commit SHAs over commit descriptions, (d) prefer function-name + file-line over "the function that does X". `alwaysApply: false` — referenced from agents that produce reports.
- **Steps:**
  1. Write `skills/lexical-density/SKILL.md`.
  2. Reference from `code_reviewer`, `meta_reviewer`, `consistency_checker`, `doc_updater`, `freshness_auditor`.
- **Touches/replaces:** new skill; 5 agent frontmatters.

### F5 — Update USER_AUTHORITY_PROTOCOL.md §Voice to cite specific densification value

- **Surface:** CLAUDE.md (no-code)
- **Effort:** low
- **Impact:** low
- **Risk:** low
- **Approach:** Existing line "Prefer numbers and identifiers over adjectives" can be sharpened with the tokenizer fact: "On 4.7+, identical text costs ~25% more tokens than on 4.6. Prefer numbers and identifiers over adjectives — they survive paraphrase compression." A one-line annotation that gives the model a *reason* (the model is more compliant when it understands cost).
- **Steps:**
  1. Edit `USER_AUTHORITY_PROTOCOL.md` §Voice — Default — the "Prefer numbers" line.
- **Touches/replaces:** `USER_AUTHORITY_PROTOCOL.md`.

## Acceptance signal

- Autocompact fires at ≥60% measured threshold consistently (verified by session_save logs).
- Statusline shows effective-percentage indicator visible to user across ≥95% of sessions.
- User self-reported "S-001 55% cliff" incident rate drops by ≥50% (user restarts sessions earlier or at higher effective utilisation).
- Manual audit of 10 agent reports: ≥7 prefer file:line citations and numbers over prose.
- Average tokens-per-assistant-turn declines ≥10% after F4 lexical-density skill propagates.

## Trade-offs and counter-evidence

- F1 (autocompact 60) trades earlier compaction friction for fewer in-session quality cliffs. Compaction itself is a regression vector ([[rc-10-compaction-derailment]]) — fresh-session-with-handoff is strictly better than compaction ([[02-external-research#R1.1]]). The right policy may be: lower autocompact AND replace with handoff suggestion.
- F2 (statusline) does not change model behaviour; it changes user behaviour. Low direct impact, high indirect impact.
- F3 (40% reminder) costs ~30 tokens per turn after threshold, which compounds. Suppression-on-repeat helps but not fully.
- The tokenizer fix is not patchable from here. All five mitigations target user awareness and downstream behaviour, not the underlying densification.
- Mitigations stack with [[rc-09-long-context-soft-cliff]] and [[rc-10-compaction-derailment]] — these three RCs share a common defence layer (effective-fill awareness + handoff-over-compaction).

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- Adjacent: [[rc-09-long-context-soft-cliff]], [[rc-10-compaction-derailment]], [[rc-03-verbosity-task-complexity]]
