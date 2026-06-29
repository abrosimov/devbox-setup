---
tags: [claude-improvements, phase3, root-cause, layer-C]
phase: 3
rc-id: RC-16
layer: C
created: 2026-06-27
symptoms: [S-014, S-015, S-023]
---

# RC-16 — No skill or template prescribes the `[USER]`/`[DRAFT]` facts-list scaffold

## Mechanism

Direct map of [[04-reflection-evidence#RC-ref-2]]: "Without a maintained facts list, the model treats every prior token in its own draft as having equivalent epistemic weight to the user's stated facts. A number derived inside a previous draft becomes a fact in the next turn. The draft becomes its own source of truth." The reflection lists a concrete corrective — a numbered facts list with `[USER]`/`[DRAFT]` tags, each `[USER]` entry anchored to a specific user message — and the corrective is nowhere in `dot_claude/`. No skill, no template, no command, no hook prompts the model to instantiate this scaffold. The model rolls its own ad-hoc paraphrase ("So, let me restate what you said…") which becomes the next draft's source-of-truth and produces strange conclusions (S-014). Without the scaffold, the model cannot distinguish "user said this in message N" from "I inferred this two turns ago"; the scaffold is the only mechanism that promotes a draft fact to a confirmed fact via explicit user conversion.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-014]] (paraphrase → odd conclusions), [[01-symptoms-inventory#S-015]] (random unsupported assumptions), [[01-symptoms-inventory#S-023]] (bullshit detector).
- External: [[02-external-research#R1.1]] Anthropic "Ground responses in quotes" — quotation-before-claim pattern; [[02-external-research#R3.5]] XML conventions (`<document>`, `<source>`).
- Config gaps: [[03-current-config-map#3.6 Repetition / restating user words]] — only `proposal_discipline.py` covers a sliver; broader "restate then act on restatement" failure mode unaddressed.
- Reflection: [[04-reflection-evidence#RC-ref-2]] — primary mechanism; [[04-reflection-evidence#RC-ref-4]] — "user is the dataset, not the reviewer".

## Fix proposals

### F1 — `templates/facts-list.md` with `[USER]`/`[DRAFT]` convention

- **Surface:** new template
- **Effort:** low
- **Impact:** high
- **Risk:** low
- **Approach:** Minimal artefact. Markdown template with the exact format from reflection: numbered list, each entry tagged `[USER msg-NN: "verbatim quote"]` or `[DRAFT — inadmissible until confirmed]`. Comment block at top documents promotion rule: a `[DRAFT]` item becomes `[USER]` only when the user explicitly confirms — not when the model decides it sounds right. Stored at `roles/devbox/files/dot_claude/templates/facts-list.md`.
- **Steps:**
  1. Create the template file with worked example (e.g. CV-iteration scenario from reflection.md).
  2. Document in `commands/techne-facts.md` (see F5).
  3. Reference from new `working-memory-discipline` skill (F2).
- **Touches/replaces:** new `templates/facts-list.md`.

### F2 — `working-memory-discipline` skill (alwaysApply false)

- **Surface:** new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low — opt-in.
- **Approach:** Skill formalises when a facts-list is required (long sessions, biographical/spec/CV content, any task where user provides ground truth incrementally) and the rules for promotion (`[DRAFT]` → `[USER]` only on explicit user confirmation). Body cites reflection.md sections 1-7 and the template. Triggered automatically by `UserPromptSubmit` hook (F3) on signals (long session, fact-dense user message) or explicitly via `/techne-facts` (F5).
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/skills/working-memory-discipline/SKILL.md`.
  2. Frontmatter `alwaysApply: false` with clear trigger description.
  3. Body: when-to-use, scaffold rules, promotion rules, anti-patterns.
- **Touches/replaces:** new skill file.

### F3 — UserPromptSubmit hook injects facts-list reminder for non-trivial sessions

- **Surface:** hook (extend or new)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low — informational.
- **Approach:** Deterministic nudge. New (or extension to `proposal_discipline.py`) UserPromptSubmit hook checks: (a) session turn count > N (e.g. ≥5); (b) prior user message length > M (e.g. ≥200 chars suggesting fact-density); (c) absence of an existing `<facts>...</facts>` block in the conversation. When all hold, emit `additionalContext`: "Long fact-dense session — instantiate working-memory-discipline scaffold using templates/facts-list.md before drafting the next response."
- **Steps:**
  1. Extend `bin/proposal_discipline.py` OR create `bin/user_prompt_facts_nudge.py`.
  2. Implement the three-condition check.
  3. Register in `hooks.json` UserPromptSubmit.
  4. Cover with test.
- **Touches/replaces:** `bin/proposal_discipline.py` (or new bin script); `hooks.json`.

### F4 — Output-style requiring numbered facts list in long sessions

- **Surface:** output-style
- **Effort:** low
- **Impact:** medium
- **Risk:** low — opt-in.
- **Approach:** New output-style `facts-anchored` that requires every assertion about user state (biography, project state, spec content) to carry a footnote-style `[F-NN]` reference to the facts list. If no facts list is present, the model must emit one in the first turn the style is active. Pairs with F1-F3. Suitable as default for `/techne-plan`, `/techne-domain-analysis`, CV-iteration sessions.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/output-styles/facts-anchored.md`.
  2. Document trigger in `commands/techne-plan.md`, `commands/techne-domain-analysis.md` as recommended style.
- **Touches/replaces:** new output-style file; minor edits to 2 command files.

### F5 — `/techne-facts` command

- **Surface:** command
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Explicit user invocation. `/techne-facts` instantiates the facts-list template inline in the conversation, prefilled by scanning the conversation so far. User reviews and confirms entries to convert `[DRAFT]` → `[USER]`. From that point on the facts list is the authoritative ground truth; subsequent drafts cite by `[F-NN]`.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/commands/techne-facts.md`.
  2. Body: read `templates/facts-list.md`, scan conversation, propose `[DRAFT]` entries for confirmation, finalise.
  3. Reference from `commands/techne-guide.md`.
- **Touches/replaces:** new command file; `commands/techne-guide.md`.

## Acceptance signal

- `templates/facts-list.md` exists with the exact `[USER]`/`[DRAFT]` convention from reflection.md.
- Skill `working-memory-discipline` exists and is referenced by ≥3 long-session commands.
- In 10 fresh long sessions (e.g. CV, spec, plan), ≥7 instantiate a facts list within the first 3 turns.
- `proposal_discipline.py` (or new hook) emits the facts-list nudge in sessions meeting the trigger criteria.
- Re-test S-014 / S-015: in 10 retrospective replays of failed sessions, model no longer fabricates `[USER]`-grade facts from prior `[DRAFT]` content.

## Trade-offs and counter-evidence

- **Facts-list adds output overhead.** Every turn that references the list costs tokens to surface it. For short sessions this is pure cost. F3 trigger condition prevents activation in short sessions; F4 output-style is opt-in.
- **Promotion rule depends on the model honouring it.** The rule "promote `[DRAFT]` to `[USER]` only on explicit confirmation" is itself an advisory rule. The model that drifts on facts may also drift on the promotion rule. Mitigation: F4 output-style enforces footnote citation, making drift visible.
- **Anthropic-side `<document>`/`<source>` convention** ([[02-external-research#R3.5]]) is the model's training-anchored citation pattern; the facts-list convention is closer to that than to arbitrary inline tags — increases adherence likelihood.
- **`<facts>` tag may collide** with future Anthropic conventions or harness UI parsing. Pick tag name carefully (`<facts-list>` is more specific) and document in skill.
- **F5 (`/techne-facts`) overlaps with `/techne-next`** which already reads state snapshots. Coordinate scope: `/techne-next` resumes work, `/techne-facts` audits ground truth — keep distinct.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
- [[rc-06-no-working-memory]] — model-internal cause
- [[rc-26-no-bullshit-detector]] — adjacent verification gap
