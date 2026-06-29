---
tags: [claude-improvements, phase3, root-cause, layer-B]
phase: 3
rc-id: RC-09
layer: B
created: 2026-06-27
symptoms: [S-001]
---

# RC-09 — Long-context soft cliff at ~50–60% before autocompact

## Mechanism

Claude Code's context-window quality degrades monotonically from the first token, with a practitioner-observed "soft cliff" around 50–60% fill — well before the harness autocompact triggers at ~75–80% ([[02-external-research#R4.5]]). Architectural drivers include RoPE long-term decay, softmax concentration, causal attention asymmetry, and attention sinks ([[02-external-research#R4.2]]). Anthropic's own MRCR v2 benchmark shows Opus 4.6 drops from 93% recall at 256K to 76% at 1M ([[02-external-research#R4.4]]). The user's setting `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80` ([[03-current-config-map#3.1]]) raises threshold but does not help the cliff that precedes it. Mitigation requires statusline visibility, prompt-injected reminders to rotate sessions, and lowering the override threshold to land before the cliff.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-001]] verbatim "Заметил что Клод код опус 4.7 начинает дико тупить когда заполненность контекста подход к 55%"
- External:
  - [[02-external-research#R4.1]] Chroma Research "Context Rot" — monotonic decay from first token
  - [[02-external-research#R4.2]] Lost in the Middle — ≥30% accuracy drop mid-context
  - [[02-external-research#R4.4]] Anthropic MRCR v2: 93% → 76% from 256K to 1M
  - [[02-external-research#R4.5]] Practitioner thresholds: MindStudio "starts degrading at around 50% full", Spacecake "At 60% capacity the model is repeating itself"
  - [[02-external-research#R1.1]] Anthropic verbatim: "When a context window is cleared, consider starting with a brand new context window rather than using compaction"
- Config gaps: [[03-current-config-map#3.1]] "No proactive `~/.claude` hook detects context fill ≥ 50% and emits a warning into `additionalContext`. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80` is too late"

## Fix proposals

### F1 — Statusline with context-fill colour bands

- **Surface:** settings.json + new bin script
- **Effort:** medium
- **Impact:** high
- **Risk:** low
- **Approach:** add a `statusLine` script that reads current context-fill percentage from the harness's exposed env or transcript size proxy and displays it with colour bands: green < 40%, amber 40–60%, red > 60%. User sees in real time when they cross the cliff and can manually rotate.
- **Steps:**
  1. New `bin/statusline_context_fill.py` — read `CLAUDE_CONTEXT_TOKENS_USED` and `CLAUDE_CONTEXT_LIMIT` env vars (or fall back to transcript byte-size estimate ÷ 4).
  2. Output coloured string `[ctx 38%]` / `[ctx 52%]` / `[ctx 64%]` using terminal escape codes.
  3. Configure `statusLine.type: "command"`, `statusLine.command: "~/.claude/bin/statusline_context_fill.py"` in `settings.json`.
  4. Document the bands in `dot_claude/README.md`.
- **Touches/replaces:** `settings.json`, new bin script.

### F2 — UserPromptSubmit hook injects rotation reminder above 50%

- **Surface:** hook
- **Effort:** medium
- **Impact:** high
- **Risk:** low-medium — too many reminders cause habituation/noise
- **Approach:** new `bin/user_prompt_context_rotation_hint.py` triggered on `UserPromptSubmit`. Compute context-fill % from transcript size or env. At ≥ 50% emit `additionalContext`: `[Context fill: N%] Soft cliff at 50-60%. Consider: 1) finish current turn with deliverable file write, 2) run /techne-log to save state, 3) /clear and resume in fresh session via /techne-next.` At ≥ 65% escalate to `[Context fill: N%] HIGH. Quality has likely degraded. Strong recommendation to rotate now.`
- **Steps:**
  1. New `bin/user_prompt_context_rotation_hint.py`.
  2. Use same fill calculation as F1.
  3. Threshold tiers: 50%, 65%, 75%.
  4. Suppress reminder if last reminder fired within 3 user messages (avoid spam).
  5. Register on `UserPromptSubmit` in `hooks.json`.
- **Touches/replaces:** `hooks.json`, new bin script. Adjacent to existing `proposal_discipline.py`, `session_save.py`.

### F3 — Lower `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` from 80 to 60

- **Surface:** settings.json
- **Effort:** low
- **Impact:** medium-high
- **Risk:** medium — premature compaction loses recent context, may force re-establishment of task state
- **Approach:** edit `settings.json` `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` from `80` to `60`. Aligns autocompact trigger with empirical cliff. Combined with `session_save.py` and `pre_compact_mask.py` already in place, the loss is bounded.
- **Steps:**
  1. Edit `roles/devbox/files/dot_claude/settings.json`.
  2. Set `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "60"`.
  3. Document the trade-off in `dot_claude/README.md`.
  4. Cross-link to [[rc-10-compaction-derailment]] mitigations.
- **Touches/replaces:** `settings.json`.

### F4 — output-style with auto-compact-suggestion at 50%

- **Surface:** output-style
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** extend default output-style (or new `context-aware.md`) to require: when the model's own internal context-fill estimate exceeds 50%, append a one-line suggestion at end of every turn: `[Context rotation suggested: <reason>. Suggested next: /techne-log + /clear.]` This is advisory but uses the model's own size-awareness rather than relying on env-injected hint.
- **Steps:**
  1. New `roles/devbox/files/dot_claude/output-styles/context-aware.md` (or append to default).
  2. Define the trigger condition and the one-line suggestion format.
  3. Document opt-in.
- **Touches/replaces:** new or extended output-style file.

### F5 — Skill `context-rotation-discipline` (new, advisory)

- **Surface:** new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** new skill `context-rotation-discipline` with `alwaysApply: true`, ~100 lines. Encodes: (a) cite the cliff evidence ([[02-external-research#R4.5]]); (b) sequence for rotation — save state via `/techne-log`, write deliverables to file, `/clear`, resume via `/techne-next`; (c) "subagent for context-bounded subtask" pattern ([[02-external-research#R3.3]]); (d) explicit anti-pattern: do not rely on autocompact alone — Anthropic itself recommends fresh session ([[02-external-research#R1.1]]).
- **Steps:**
  1. New `roles/devbox/files/dot_claude/skills/context-rotation-discipline/SKILL.md`.
  2. Frontmatter `alwaysApply: true`.
  3. Cross-link from `agent-base-protocol`, `editing-claude-config`, `iterative-retrieval`.
- **Touches/replaces:** new skill.

## Acceptance signal

- Statusline reading visible in ≥ 95% of session turns past first 5 minutes.
- User-reported "Claude is degrading" complaints decline measurably session-over-session.
- Median session length before voluntary `/clear` decreases (sessions rotated proactively rather than dragged past cliff).
- Autocompact-triggered turns reduce by ≥ 50% (sessions hit voluntary rotation at 60% before autocompact at 60%).
- Telemetry: hook log shows reminder fired at 50%, action taken (clear or save) within 3 turns in ≥ 60% of cases.

## Trade-offs and counter-evidence

- F3 (lower threshold to 60): shorter sessions force more rotation overhead. Counter-evidence: Anthropic CHANGELOG `v2.1.21` "Fixed auto-compact triggering too early" ([[02-external-research#R1.5]]) — Anthropic recently moved threshold *up*, suggesting too-aggressive compaction has its own costs. Mitigation: tune via measurement; 60 is starting point, can be adjusted per session class.
- F2 (rotation hint) risk: notification fatigue. Mitigation: 3-message suppression window.
- F1 (statusline): only effective if user actually looks at it. Practitioner evidence from [[02-external-research#R3.4]] supports statusline-based warnings (zenn.dev article cited).
- The 55% anchor from user feedback is not directly citable from literature — [[02-external-research#R4.5]] clusters at 50–60% as practitioner range, 75–77% as autocompact. 55% is an interpolation. F3 picks 60% as the boundary of the practitioner cluster; can tune lower if needed.
- Counter to all advisory fixes: model attends ~150 instructions ([[02-external-research#R5]] item 6). Adding skill F5 has CLAUDE.md attention-budget cost — see [[rc-11-claude-md-attention-budget]].

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-10-compaction-derailment]] (sibling: rotation pairs with safe compaction)
- [[rc-04-tokenizer-densification]] (parallel: tokenizer densification compounds the cliff)
