---
tags: [claude-improvements, phase3, root-cause, layer-A]
phase: 3
rc-id: RC-06
layer: A
created: 2026-06-27
symptoms: [S-014, S-015]
---

# RC-06 — No working-memory scaffold; own prior draft becomes source-of-truth

## Mechanism

Without a maintained facts list, the model treats every prior token in its own draft as having equivalent epistemic weight to the user's stated facts. A number derived inside a previous draft becomes a "fact" in the next turn; the draft becomes its own source of truth ([[04-reflection-evidence#RC-ref-2]]). Compounded by [[04-reflection-evidence#RC-ref-4]] — the model operates as if a domain can be reconstructed from internal plausibility ("a person at Bumble for 11 years probably did X"). Wrong epistemic stance: the user is not a reviewer of guesses, the user is the dataset. Concrete corrective from reflection: numbered facts list with `[USER]`/`[DRAFT]` tags, each `[USER]` entry anchored to a specific user message ("Bumble PHP → C/Go: user message 14:23, exact wording 'switched teams in 2020'"), `[DRAFT]` items inadmissible until converted by user. The Anthropic platform-side analogue is "structured note-taking persists state outside of the context window" ([[02-external-research#R6.4]] — Effective context engineering). This user's setup has zero coverage ([[03-current-config-map#4. Gaps and weaknesses]] §3.6 — only `proposal_discipline.py` and only for one repetition class).

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-014]] (paraphrases user, draws odd conclusions), [[01-symptoms-inventory#S-015]] (random unsupported assumptions up front)
- External: [[02-external-research#R6.4]] (Anthropic — structured note-taking persists state outside context window), [[02-external-research#R1.1]] ("Ground responses in quotes" before answering), [[02-external-research#R3.5]] (XML `<source>`/`<document>` for multi-doc with provenance metadata)
- Config gaps: [[03-current-config-map#3.6 Repetition / restating user words (S-006, S-009, S-014, S-034)]] — only `proposal_discipline.py`; [[03-current-config-map#3.9 Bullshit detection / counter-evidence (S-023)]] — no dedicated mechanism
- Reflection: [[04-reflection-evidence#RC-ref-2]] (no explicit working memory), [[04-reflection-evidence#RC-ref-4]] (user holds ground truth), [[04-reflection-evidence#cross-cutting]] items 2-3 (maintain facts list, check noun-phrases against it)

## Fix proposals

### F1 — `facts-list.md` template with `[USER]`/`[DRAFT]` discipline

- **Surface:** template
- **Effort:** low
- **Impact:** medium
- **Risk:** low — opt-in template
- **Approach:** New `templates/facts-list.md` defines the format: numbered list, each entry `[USER]` or `[DRAFT]`, `[USER]` carries a quoted anchor to a specific user message, `[DRAFT]` is inadmissible until converted. Agents reference this template when starting non-trivial sessions. Reflection.md cross-cutting item 2 verbatim: "Maintain a facts list in the first reply; re-emit when it changes."
- **Steps:**
  1. Write `roles/devbox/files/dot_claude/templates/facts-list.md` with the format + 2 worked examples.
  2. Reference from `agent-base-protocol` skill and `code-writing-protocols`.
  3. Optional: scaffold into `/techne-implement` and `/techne-plan` command preambles.
- **Touches/replaces:** new template; minor edits to 2 skills.

### F2 — PostToolUse hook validating new claims against facts-list

- **Surface:** hook (new bin script)
- **Effort:** high
- **Impact:** high
- **Risk:** medium — requires reliable claim extraction
- **Approach:** New `post_claim_facts_check.py` PostToolUse(Edit|Write) hook. When the agent emits content containing factual claims (names, numbers, dates, decisions), check the in-session facts-list state file. Claims not backed by a `[USER]` entry trigger `additionalContext` warning: "Claim 'X' not in facts list. Either anchor to a user message or mark `[DRAFT]` and confirm before persisting."
- **Steps:**
  1. Implement `bin/post_claim_facts_check.py` reading a session-state `facts-list.json`.
  2. Use simple noun-phrase extraction (proper nouns, numbers, decisions).
  3. Persist facts-list state via `session_save.py` infrastructure.
  4. Start as warning-only; promote to block when accuracy ≥80%.
- **Touches/replaces:** `hooks.json`, new `bin/` script, `session_save.py` schema extension.

### F3 — `working-memory-discipline` skill encoding the seven cross-cutting correctives

- **Surface:** new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low — advisory
- **Approach:** New `skills/working-memory-discipline/SKILL.md` codifies the seven cross-cutting items from [[04-reflection-evidence#cross-cutting]]: Disclosure block, facts list maintenance, noun-phrase check, delta-on-feedback, batched questions, terse-feedback-is-scoped, never-let-draft-be-fact-source. Cross-references the `facts-list.md` template.
- **Steps:**
  1. Write `skills/working-memory-discipline/SKILL.md`.
  2. Set `alwaysApply: true` if budget allows; else reference from SE / planner / TPM agents.
- **Touches/replaces:** new skill.

### F4 — `/techne-facts` command for explicit facts-list refresh

- **Surface:** command
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** New `commands/techne-facts.md` dumps the current facts-list and prompts the agent to re-derive from user messages only. Forces a periodic reset against drift. Pairs with [[02-external-research#R6.4]] structured-note-taking.
- **Steps:**
  1. Write `commands/techne-facts.md` with prompt: "(1) Read all user messages in this session. (2) Emit a numbered `[USER]`-only facts list. (3) Flag any claims in your prior drafts that are not in this list."
  2. Document in `techne-guide`.
- **Touches/replaces:** new command.

### F5 — Add `§ Working Memory` clause to USER_AUTHORITY_PROTOCOL.md

- **Surface:** CLAUDE.md (no-code)
- **Effort:** low
- **Impact:** low
- **Risk:** medium — adds lines to bloated CLAUDE.md ([[03-current-config-map#6. CLAUDE.md size and bloat]])
- **Approach:** Insert 4-line `§ Working memory` clause: "Maintain a facts list `[USER]`/`[DRAFT]` for non-trivial sessions. `[USER]` items anchor to a specific user message. `[DRAFT]` items are inadmissible until user-confirmed. Never let your own prior draft be a source of facts." Pair with F3 skill — CLAUDE.md gives the rule, skill gives the protocol.
- **Steps:**
  1. Edit `USER_AUTHORITY_PROTOCOL.md` to add 4-line clause after `§ Discipline Protocol — Inquiry`.
  2. Offset budget cost by trimming verbose example elsewhere (e.g. F4/F5 of RC-02).
- **Touches/replaces:** `USER_AUTHORITY_PROTOCOL.md`.

## Acceptance signal

- Facts-list template referenced in ≥80% of `/techne-implement` and `/techne-plan` sessions.
- `post_claim_facts_check.py` warning fires ≤5% of edits after tuning — meaning claims are anchored.
- User-reported S-014 "draws odd conclusions from paraphrase" incidents → 0 over 4 weeks.
- Manual audit: 10 random non-trivial sessions show a maintained facts-list visible in the assistant working area.
- `[DRAFT]`-tagged items never appear in final delivered artefacts without prior user conversion.

## Trade-offs and counter-evidence

- F2 (claim-facts hook) is the highest-impact and the technically hardest. Noun-phrase extraction is noisy; the hook will misfire. Start in warning-only mode for ≥4 weeks before promoting to block.
- F1 (template) and F3 (skill) are advisory — model can ignore the protocol on any given turn. The deterministic backstop is F2.
- The discipline costs tokens — maintaining a numbered facts list adds 100-300 tokens per turn for moderate sessions. Offsets: fewer paraphrase-induced rabbit holes (RC-ref-4 cost is multi-turn rework).
- Adding CLAUDE.md content (F5) directly conflicts with [[rc-13-claude-md-bloat]]. Must pair with offsetting deletion elsewhere.
- The pattern is well-documented in Anthropic's own engineering blog ([[02-external-research#R6.4]] — "structured note-taking … pulled back as needed") so the prior on adherence is good. Skill-only adherence ([[02-external-research#R5]] item 6) is ~70%; hook-backed reaches ~100% on the hooked surface.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
- Adjacent: [[rc-02-helpfulness-as-artefact]], [[rc-07-asymmetric-ask-vs-guess]], [[rc-16-no-facts-list-scaffold]], [[rc-26-no-bullshit-detector]]
