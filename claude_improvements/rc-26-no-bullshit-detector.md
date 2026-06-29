---
tags: [claude-improvements, phase3, root-cause, layer-E]
phase: 3
rc-id: RC-26
layer: E
created: 2026-06-27
symptoms: [S-023]
---

# RC-26 — No counter-evidence audit ("bullshit detector")

## Mechanism

Assertions in the assistant's output are not audited against the conversation's verifiable facts. The user explicitly flagged the gap and asked "how?!" ([[01-symptoms-inventory#S-023]]). The closest existing control is the `code-reviewer` agent's counter-evidence checks via `go-review-checklist`, but those fire only on review turns and only on Go code. There is no general-purpose pre-emit audit that asks: *did the user say this? is the assertion specific? can it be falsified? is there contradicting evidence in scope? am I quoting or paraphrasing?* Reflection identified the same mechanism — the draft itself becomes a source of facts ([[04-reflection-evidence#RC-ref-2]], [[04-reflection-evidence#RC-ref-4]]) — and verifying that the assistant is the dataset, not the user, is the corrective. Surface: verification layer, message-content audit.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-023]]
- External: [[02-external-research#R3.5]] (quote-relevant-parts pattern reduces hallucination), [[02-external-research#R2.2]] (Stella Laurenzo — "when thinking is shallow, the model defaults to the cheapest action … dodge responsibility for failures")
- Config gaps: [[03-current-config-map#3.9 Bullshit detection / counter-evidence]] — no dedicated mechanism; user explicit gap
- Reflection: [[04-reflection-evidence#RC-ref-2]] (no working memory of confirmed facts), [[04-reflection-evidence#RC-ref-4]] (user holds ground truth — not the draft)

## Fix proposals (≥5)

### F1 — Stop hook: assertion-class tag audit against facts file

- **Surface:** hook (new `bin/stop_assertion_audit.py`, registered on `Stop`)
- **Effort:** high
- **Impact:** high
- **Risk:** medium — needs facts-list scaffold (see RC-16); without it the audit has nothing to check against
- **Approach:** Parse final message for assertions tagged `[VERIFIED]`/`[INFERRED]`/`[ASSUMED]` (mandated by F4 output-style). Emit warning when assertions are untagged. Look up `[VERIFIED]` claims against the conversation's facts file (`.claude/session/facts.md`) — if not present, downgrade to `[INFERRED]`. Non-blocking; emits diagnostic via `additionalContext`.
- **Steps:**
  1. Implement `roles/devbox/files/dot_claude/bin/stop_assertion_audit.py`.
  2. Define facts-file schema (one entry per line, `[USER msg-id] fact`).
  3. Wire to `Stop` matcher in `hooks.json`.
  4. Coordinate with `rc-16-no-facts-list-scaffold` to ensure the facts file exists.
- **Touches/replaces:** `hooks.json`, depends on facts-list scaffold from RC-16.

### F2 — Pre-Edit hook flagging draft-file assertions without anchors

- **Surface:** hook (new `bin/pre_edit_assertion_guard.py`, registered on `PreToolUse(Edit|Write|MultiEdit)`)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low — exit-2 only on clearly assertion-class agent-draft files (paths matching `agents/*.md`, `skills/*/SKILL.md`, `plans/*.md`)
- **Approach:** When the target path matches an agent/skill draft pattern, scan the new content for declarative claims (`MUST`, `ALWAYS`, `NEVER`, factual numbers, percent figures) and check each one against a sidecar `facts.json` file in the same directory. Block (exit 2) when claims contradict the facts list; warn otherwise.
- **Steps:**
  1. Implement `pre_edit_assertion_guard.py` modelled on `pre_edit_lint_guard.py`.
  2. Define sidecar `facts.json` format (assertion → evidence path:line).
  3. Add `PreToolUse(Edit|Write|MultiEdit)` registration in `hooks.json`.
- **Touches/replaces:** `hooks.json`, `bin/_claude_lib/`.

### F3 — Extend existing `meta_reviewer` agent with counter-evidence checklist

- **Surface:** agent body (edit `agents/meta_reviewer.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — meta-reviewer already exists; only adds a checklist section. No-code.
- **Approach:** Add five-question audit to the meta-reviewer's review template: (1) did the user state this? (2) is the assertion specific (numbers, paths, dates)? (3) can it be falsified by a tool call? (4) is there contradicting evidence in scope? (5) am I quoting or paraphrasing? Each draft review answers the five questions explicitly; if any answer is "no/unknown", the assertion is downgraded or removed.
- **Steps:**
  1. Add `## Counter-evidence audit (5 questions)` section to `agents/meta_reviewer.md`.
  2. Cross-reference from `agents/code_reviewer.md` "delegate to meta_reviewer for high-stakes claims".
- **Touches/replaces:** `agents/meta_reviewer.md`, `agents/code_reviewer.md`.

### F4 — Output-style requiring assertion tags

- **Surface:** output-style (new `output-styles/assertion-tagged.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** medium — output-token cost; opt-in mitigates
- **Approach:** Style requires every assertion-class statement (those containing factual claims, MUSTs, percentages, dates, named entities) to carry `[VERIFIED path:line]`, `[INFERRED reason]`, or `[ASSUMED reason]`. Opinions/voice statements exempt. Activated per `/techne-audit-claim` command and during meta-review.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/output-styles/assertion-tagged.md`.
  2. Document activation; pair with F5 command.
  3. Cross-link from `meta_reviewer.md`.
- **Touches/replaces:** none (greenfield style).

### F5 — New command `/techne-audit-claim`

- **Surface:** command (new `commands/techne-audit-claim.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — opt-in command
- **Approach:** `/techne-audit-claim <claim>` invokes `meta_reviewer` with `assertion-tagged` output-style, focused on a single user-provided claim. Returns: tag-classification + evidence chain or "could not verify". Lets user spot-check the assistant on demand without restructuring the whole session.
- **Steps:**
  1. Create `commands/techne-audit-claim.md` following the `techne-` prefix convention ([[03-current-config-map#2]]).
  2. Wire to `meta_reviewer` agent.
- **Touches/replaces:** none (greenfield command).

### F6 — New skill `counter-evidence-audit`

- **Surface:** skill (new `skills/counter-evidence-audit/SKILL.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — advisory
- **Approach:** Codify the five-question audit, three-tag taxonomy, and the "draft is not a source of facts" rule from reflection. `alwaysApply: false`; triggered when the prompt contains "verify", "audit", "claim", "is it true that …", or when meta-review is invoked.
- **Steps:**
  1. Scaffold under `skills/counter-evidence-audit/` via `skill-builder`.
  2. Include worked examples drawn from [[04-reflection-evidence#RC-ref-2]].
- **Touches/replaces:** none.

## Acceptance signal

- `/techne-audit-claim` returns specific evidence trail (path:line or "no evidence") on every invocation.
- Sample of 5 multi-turn sessions over a week shows no detected fabricated entity (name, number, date) entering a draft without `[VERIFIED]` tag.
- `meta_reviewer` review reports include the 5-question audit in ≥9 of 10 invocations.
- `stop_assertion_audit.py` warnings drop steadily after the facts-list scaffold (RC-16) ships.
- User can name a recent answer and `/techne-audit-claim` flags the unsupported parts.

## Trade-offs and counter-evidence

The five-question audit duplicates partial logic in `go-review-checklist` ([[03-current-config-map#3.9]]) — risk of conflict and maintenance hazard ([[03-current-config-map#5 Inter-asset conflicts]]). Mitigate by extracting the shared core into `counter-evidence-audit` and having both consume it. Output-tagging (F4) inflates tokens — keep opt-in. Anthropic's reverted brevity caps ([[02-external-research#R2.1]]) warn against mandatory output-shape constraints; F4 stays per-command, not global. The audit cannot detect bullshit the user themselves seeded into the conversation — it only catches drift between the assistant's own claims and the conversation's stated facts. Pair with RC-16 (facts list) and RC-25 (citation enforcement) for full coverage.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
- [[rc-25-citation-not-enforced]] (sibling — claims need anchors)
- [[rc-16-no-facts-list-scaffold]] (dependency — audit needs a facts source)
