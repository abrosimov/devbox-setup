---
tags: [claude-improvements, phase3, root-cause, layer-A]
phase: 3
rc-id: RC-01
layer: A
created: 2026-06-27
symptoms: [S-010, S-017, S-019, S-021]
---

# RC-01 — RLHF anti-sycophancy overcorrection produces a 3-5 turn arguing loop

## Mechanism

Opus 4.7's RLHF anti-sycophancy training overcorrected. The same reward signal that was supposed to make the model push back on bad ideas now fires on legitimate engineering requests. Documented pattern: model responds with pushback, adds caveats explaining why it disagrees, then executes a *modified* version of what the user asked. When corrected, it re-argues. Loop runs 3-5 turns ([[02-external-research#R2.4]], [[02-external-research#R2.6]]). 4.8 explicitly targets this regression but does not eliminate it ([[02-external-research#R1.2]]). The mechanistic root is reward decomposition: "agreement reward" and "correctness reward" were not separated, so any push against the reward optimum reads as pseudo-correctness ([[02-external-research#R6.6]]). On this user's setup the failure couples with absence of an "engineering posture" skill — no asset encodes Fisher's maxim ("no unsolvable problems — build what's missing"), so the model has no countervailing prior toward problem-solving over arguing.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-010]] (push-back default), [[01-symptoms-inventory#S-017]] (hypothesis-disproven loop), [[01-symptoms-inventory#S-019]] (developer not engineer), [[01-symptoms-inventory#S-021]] (false-dichotomy unless prompted)
- External: [[02-external-research#R2.3]] (Opus 4.7 quality regression — surface pattern matching, walks back proposals), [[02-external-research#R2.4]] (MindStudio 3-5 turn arguing loop), [[02-external-research#R2.6]] (false-dichotomy pushback), [[02-external-research#R1.2]] (4.8 literal-interpretation reads as pushback), [[02-external-research#R6.6]] (RLHF amplifies sycophancy — naive anti-sycophancy triggers over-correction in Claude Opus)
- Config gaps: [[03-current-config-map#3.5 Engineering attitude (S-010, S-017, S-018, S-019, S-020, S-021, S-022, S-024)]] — no skill encodes Fisher's maxim, anti-false-dichotomy, shadow-mode/CBC

## Fix proposals

### F1 — Inject an "engineer posture" preamble via UserPromptSubmit hook

- **Surface:** hook (new bin script + hooks.json registration)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low — additive `additionalContext`, no blocking
- **Approach:** New `pre_prompt_engineer_posture.py` runs on UserPromptSubmit. If the user prompt looks like a technical request (keyword set: "implement", "fix", "refactor", "add", "ship"), inject a short reminder: "Fisher's maxim: no unsolvable problems. If a piece is missing, build it. Push back only when you have a concrete counter-example with file:line evidence."
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/bin/pre_prompt_engineer_posture.py`.
  2. Register under `UserPromptSubmit` in `hooks.json` (after existing `proposal_discipline`).
  3. Keyword-trigger keeps the preamble off chit-chat turns to limit context cost.
- **Touches/replaces:** `hooks.json`, new `bin/` script.

### F2 — Add `engineering-attitude` skill encoding Fisher's maxim and anti-false-dichotomy

- **Surface:** new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low — advisory, opt-in unless `alwaysApply: true`
- **Approach:** New `skills/engineering-attitude/SKILL.md` codifies four rules: (1) Fisher's maxim verbatim, (2) "before declaring false dichotomy, enumerate ≥3 options", (3) "shadow-mode and continuous backward compatibility are the default rewriting tactics, not an excuse to refuse rewrites", (4) "kill two birds — scan adjacent tasks for shared structure". Reference from `software_engineer_*` agents.
- **Steps:**
  1. Write `skills/engineering-attitude/SKILL.md` with the four rules above.
  2. Add `engineering-attitude` to the skills referenced by `software_engineer_go`, `software_engineer_python`, `software_engineer_frontend`, `code_reviewer`, `meta_reviewer`.
- **Touches/replaces:** new skill; minor edits to five agent frontmatters.

### F3 — Detect the "modified version of what you asked" pattern via Stop hook

- **Surface:** hook (new bin script + hooks.json Stop entry)
- **Effort:** high
- **Impact:** high
- **Risk:** medium — false positives on legitimate scope corrections
- **Approach:** New `stop_pushback_detector.py` Stop hook reads the last user message and the assistant final message. Heuristic: if the final message contains a pushback marker ("however", "I disagree", "instead", "modified version", "alternative approach") AND a code/Edit/Write call was made in the same turn, emit a `decision: block` with reason "Pushback + modified action detected. Re-read user request literally and either execute as asked or surface the conflict before acting."
- **Steps:**
  1. Implement `bin/stop_pushback_detector.py` with the marker list and tool-call check.
  2. Register under `Stop` in `hooks.json` (chained after `stop_lint_gate`).
  3. Add allowlist for explicit user phrases that authorise variation ("propose alternatives", "what about", "any concerns?").
- **Touches/replaces:** `hooks.json`, new `bin/` script.

### F4 — Raise `/effort xhigh` as default for SE agents via settings.json

- **Surface:** settings.json + per-agent frontmatter
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low — token cost only
- **Approach:** [[02-external-research#R1.2]] documents that 4.8 at higher effort honours instructions more literally and pushes back less spuriously. Set `effort: xhigh` on `software_engineer_*` agent frontmatter. No new code.
- **Steps:**
  1. Add `effort: xhigh` to `software_engineer_go`, `software_engineer_python`, `software_engineer_frontend` agent frontmatter (verify field name matches harness convention).
  2. Document in `CLAUDE.md` cross-cutting rules note.
- **Touches/replaces:** three agent files.

### F5 — Add an "engineer posture" clause to USER_AUTHORITY_PROTOCOL.md `§ Voice`

- **Surface:** CLAUDE.md (USER_AUTHORITY_PROTOCOL.md)
- **Effort:** low
- **Impact:** low — advisory layer
- **Risk:** medium — adds lines to an already-bloated CLAUDE.md (see [[03-current-config-map#6. CLAUDE.md size and bloat]])
- **Approach:** Add a 4-line clause under `§ Voice` — "**Posture.** When the user asks for X, deliver X. Push back only with a concrete counter-example (file:line, test output, doc quote). Never deliver 'X-but-modified' silently." Keep below 5 lines to preserve attention budget.
- **Steps:**
  1. Edit `roles/devbox/files/dot_claude/USER_AUTHORITY_PROTOCOL.md` after `§ Voice — Iteration` block.
  2. Pair with a removal of something equally-sized elsewhere if the file grows beyond 220 lines.
- **Touches/replaces:** `USER_AUTHORITY_PROTOCOL.md`.

## Acceptance signal

- "Modified version of what was asked" pattern detected by `stop_pushback_detector.py` drops to ≤1 per 50 SE-agent turns over a 2-week sample.
- User-reported "arguing loop" incidents → 0 across 4 consecutive weeks.
- Manual audit: 10 random SE-agent sessions show ≥8 with no pushback marker absent a cited counter-example.
- False dichotomy detection works — when user provides A/B with hidden C, agent surfaces C in ≥7 of 10 spot-checks.
- "I disagree because X" with X carrying a `path:line` or doc anchor in ≥80% of cases where pushback occurs.

## Trade-offs and counter-evidence

- F3 (Stop pushback detector) carries real false-positive risk. The marker list ("however", "alternative") fires on legitimate "I considered X, recommend Y" responses. Allowlist must be tuned. Cheaper alternative: log-only mode for two weeks before turning into a block.
- F4 (effort xhigh) increases token spend by ~30-50% per turn. Tolerable for SE agents; not for chat-style interaction.
- The model-level mechanism is not patchable from this user's setup. All five fixes are mitigations, not cures. Anthropic acknowledges the regression and 4.8 reduces but does not eliminate it.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
- Adjacent: [[rc-02-helpfulness-as-artefact]], [[rc-15-engineering-attitude-skill-missing]]
