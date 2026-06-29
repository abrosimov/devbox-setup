---
tags: [claude-improvements, phase3, root-cause, layer-C]
phase: 3
rc-id: RC-19
layer: C
created: 2026-06-27
symptoms: [S-028]
---

# RC-19 — Skill invocation is advisory; model bypasses skill and patches code directly

## Mechanism

The `Skill` tool is documented in agent instructions ("invoke <skill> when you see <trigger>") but the runtime treats invocation as a discretionary tool call. When a user prompt or PostToolUse signal matches a skill's trigger (e.g. lint failure → `lint-discipline`), the model can ignore the recommendation and proceed straight to an `Edit`/`Write` patching the code, because that path produces a visible artefact while invoking the skill produces only context. This is layer-C (configuration) — the asset (the skill) exists, but no enforcement surface forbids bypass. `validate_skill_evals.py` only verifies that skills *can* be evaluated; it does not detect at runtime when a skill *should* have been invoked. The failure mode compounds RC-02 (helpfulness-as-artefact: skill output looks like stalling) and RC-17 (advisory-only rules).

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-028]]
- External: [[02-external-research#R3.2]] ("CLAUDE.md is advisory (~70% followed). Hooks are deterministic."), [[02-external-research#R1.2]] (4.8 favours reasoning over tool calls — fewer Skill invocations by default)
- Config gaps: [[03-current-config-map#3.14 Sub-agent skill suppression (S-028)]] — only `validate_skill_evals.py` partial; no PreToolUse hook for skill-trigger match
- Reflection: [[04-reflection-evidence#RC-ref-1]] (artefact-bias makes Edit feel more productive than Skill invocation)

## Fix proposals (≥5)

### F1 — PreToolUse(Edit|Write|MultiEdit) hook detecting skill-trigger match

- **Surface:** new bin script + hook registration
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — false positives forbid legitimate edits; allowlist needed
- **Approach:** A new `pre_edit_skill_trigger_guard.py` reads the active skill index (`~/.claude/skills/*/SKILL.md` frontmatter `trigger_evals.json`), matches the most recent user prompt + tool-call history against trigger phrases, and if a skill clearly matches (e.g. lint failure → `lint-discipline`) exits 2 with `additionalContext` = "invoke skill `<name>` first via Skill tool".
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/bin/pre_edit_skill_trigger_guard.py`.
  2. Build trigger index from `skills/*/trigger_evals.json` + frontmatter `description` field.
  3. Match against UserPromptSubmit cache + last 3 tool results.
  4. Register in `hooks.json` under `PreToolUse(Edit|Write|MultiEdit)`.
  5. Allowlist `escalate=true` env var for explicit bypass.
- **Touches/replaces:** `hooks.json`, new bin script.

### F2 — UserPromptSubmit hook injecting skill-suggestion as `additionalContext`

- **Surface:** new bin script + hook registration
- **Effort:** low
- **Impact:** medium
- **Risk:** low — pure advisory, no forbid
- **Approach:** Before forbidding the bypass (F1), give the model a chance to self-correct: a UserPromptSubmit hook scans the prompt for skill triggers and prepends a one-line nudge "matches skill `<name>` — consider Skill tool".
- **Steps:**
  1. Create `bin/user_prompt_skill_hint.py`.
  2. Match prompt against skill `description` fields (cached on startup).
  3. Emit `additionalContext` with top-1 match + invocation reminder.
  4. Register under `UserPromptSubmit`.
- **Touches/replaces:** `hooks.json`.

### F3 — Expand `trigger_evals.json` coverage to all 40 skills

- **Surface:** test fixtures + validator
- **Effort:** high
- **Impact:** medium
- **Risk:** low
- **Approach:** Today only a subset of skills have `trigger_evals.json`. Without coverage, F1/F2 cannot match reliably. Add fixtures for every skill, then `make eval-skills` covers the full library.
- **Steps:**
  1. Audit `skills/*/` for missing `trigger_evals.json`.
  2. For each missing skill, write ≥5 positive + ≥3 negative prompts.
  3. Run `make eval-skills` and tune descriptions until ≥80% per-skill F1.
  4. Wire CI to fail on missing fixtures.
- **Touches/replaces:** `skills/*/trigger_evals.json`, `bin/validate_skill_evals.py`.

### F4 — Per-skill `alwaysApply: true` audit (no-code, frontmatter-only)

- **Surface:** skill frontmatter
- **Effort:** low
- **Impact:** medium
- **Risk:** medium — too many always-applied skills bloats context (RC-13)
- **Approach:** Skills that encode hard rules (e.g. `lint-discipline`, `code-comments`, `agent-base-protocol`) should be `alwaysApply: true`; skills that are reference material (e.g. `mcp-storybook`, `python-monolith`) stay opt-in. Bypass is harder when a skill is already in context.
- **Steps:**
  1. List all 40 skills with current `alwaysApply` flag.
  2. Classify each: hard-rule vs reference. Hard-rule → always; reference → opt-in.
  3. Edit frontmatter only; no script changes.
  4. Re-measure CLAUDE.md effective stack against RC-13 budget.
- **Touches/replaces:** `skills/*/SKILL.md` frontmatter.

### F5 — New skill `skill-invocation-discipline`

- **Surface:** new skill
- **Effort:** low
- **Impact:** low-medium (advisory only)
- **Risk:** low
- **Approach:** A meta-skill that documents when bypassing a skill is acceptable (rare) and the protocol for invoking it (`Skill` tool, not paraphrase). Referenced from `agent-base-protocol` and `code-writing-protocols`. Cheap reinforcement only — the deterministic gate is F1.
- **Steps:**
  1. Create `skills/skill-invocation-discipline/SKILL.md`.
  2. Document trigger-match rule + acceptable bypass criteria (e.g. user explicitly says "skip skill").
  3. Reference from `agent-base-protocol` "Skill discipline" section.
  4. Add `trigger_evals.json`.
- **Touches/replaces:** `skills/agent-base-protocol/SKILL.md` (add cross-reference).

## Acceptance signal

- For sessions where lint fails after an Edit, the next assistant action is a `Skill` call to `lint-discipline` ≥90% of the time (eval).
- `pre_edit_skill_trigger_guard.py` exit-2 rate visible in hook logs; rate trending to zero as model adapts.
- `make eval-skills` reports ≥80% F1 on every skill with `trigger_evals.json`.
- No regressions in session-completion time (F1 must not bottleneck routine edits).
- User stops seeing "Claude patched code instead of running skill X" complaints in feedback notes.

## Trade-offs and counter-evidence

- F1 risks blocking legitimate edits when the trigger matcher has false positives. The escalate env var is the release valve; tune thresholds via F3.
- F4 (always-apply audit) collides with RC-13 (CLAUDE.md bloat) — making more skills always-applied costs context. Classification must be ruthless.
- F5 is a new skill, but adds context that RC-13 warns against. Justified because it directly mitigates RC-19; counter-balance by trimming an existing low-impact skill.
- Anthropic evidence ([[02-external-research#R2.1]]) shows blunt enforcement (≤25/≤100 word caps) caused 3% eval drop. F1's exit-2 must be narrow — match must be confident.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory#S-028]]
- [[02-external-research#R3.2]]
- [[03-current-config-map#3.14 Sub-agent skill suppression (S-028)]]
- [[rc-17-advisory-only-rules]]
- [[rc-23-role-boundary-violations]]
