---
tags: [claude-improvements, phase3, root-cause, layer-E]
phase: 3
rc-id: RC-25
layer: E
created: 2026-06-27
symptoms: [S-003, S-008]
---

# RC-25 — Citation discipline is advisory, not enforced

## Mechanism

The protocol mandates `path:line` for verifiable claims (UAP `§ Voice` line 57–61) and `self-contained-options` requires concrete identifiers in option labels. Enforcement is rhetorical only: nothing scans the final message for bare identifiers like `d32`, `do_something()`, `frontend.spec`, or `users.go` lacking a surrounding path or quote. Identifiers that look like notes (`d-NNN`), filenames (`*.ext`), or symbol references slip through and force the user to spend their own context resolving them ([[01-symptoms-inventory#S-003]]). The same gap exists for question bodies: options say "decide on d32, here are options" rather than "in `vault/notes/d-032.md:14` we wrote '…'" ([[01-symptoms-inventory#S-008]]). Surface: verification layer is missing — current `stop_*` hooks only run lint and format, not message-content audit.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-003]], [[01-symptoms-inventory#S-008]]
- External: [[02-external-research#R3.5]] (Anthropic XML conventions — quote-then-answer reduces hallucination), [[02-external-research#R1.1]] (`<investigate_before_answering>` — "Never speculate about code you have not opened")
- Config gaps: [[03-current-config-map#3.12 Citations / file:line references]] — advisory rule only, no PostStop hook
- Reflection: [[04-reflection-evidence#RC-ref-4]] (user-as-dataset — claims need anchors), [[04-reflection-evidence#RC-ref-2]] (no working memory; bare identifiers compound this)

## Fix proposals (≥5)

### F1 — Stop hook scanning for bare identifiers without paths

- **Surface:** hook (new `bin/stop_citation_audit.py`, registered on `Stop` in `hooks.json`)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — false positives on prose mentions ("see the dashboard"); needs allowlist of identifier shapes that require paths
- **Approach:** Run regex over the final assistant message looking for code-ish (`[A-Za-z_][A-Za-z0-9_]*\.[a-z]{1,4}` filename-like, `d-?\d{2,4}` decision-note-like, `[A-Z][A-Za-z]+::[A-Z][A-Za-z]+`, ``\w+\(\)`` function-call, `S-\d{3}` symptom-id) tokens. For each token, require a nearby `path/` substring or backtick-quoted path within ±5 tokens. Emit `additionalContext` listing offending bare identifiers; non-blocking (no exit-2) — first-pass warning, not gate.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/bin/stop_citation_audit.py` modelled on `stop_lint_gate.py`.
  2. Add `BARE_IDENTIFIER_REGEXES` list with conservative patterns; document false-positive policy in module docstring.
  3. Register under `Stop` matcher in `hooks.json` alongside `stop_format`, `stop_lint_gate`.
  4. Emit JSON via `_claude_lib.hooks.emit_additional_context` with `severity=warn`.
  5. Add unit tests in `bin/tests/test_stop_citation_audit.py` covering the d-NNN, *.ext, symbol::Other shapes.
- **Touches/replaces:** `bin/stop_lint_gate.py` (sibling), `hooks.json` (registration block lines ~120-160).

### F2 — Output-style mandating `<citation>` and `<source>` tags

- **Surface:** output-style (new `output-styles/cite-strict.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — opt-in style; no behaviour change unless activated
- **Approach:** Define style requiring every code reference to use `<citation path="…" lines="N-M">…</citation>` and every URL reference to use `<source href="…">…</source>`. Add explicit examples and counter-examples. Reuses Anthropic XML convention pattern ([[02-external-research#R3.5]]).
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/output-styles/cite-strict.md`.
  2. Document activation: `/output-style cite-strict`.
  3. Cross-link from `agent-base-protocol/SKILL.md` "see also" block.
- **Touches/replaces:** none (greenfield style).

### F3 — Tighten `self-contained-options` skill with citation validator script

- **Surface:** bin script + skill cross-ref (new `bin/validate_ask_options.py`, called manually from `/techne-options`)
- **Effort:** medium
- **Impact:** medium
- **Risk:** low — opt-in via command
- **Approach:** Script parses a draft `AskUserQuestion` payload (JSON or YAML), checks each option label contains at least one `path:line`-shaped token or backtick-quoted identifier, and rejects options that reference prior turns ("as we discussed"). Wired into `techne-options` command as a pre-emit check.
- **Steps:**
  1. Implement validator in `roles/devbox/files/dot_claude/bin/validate_ask_options.py`.
  2. Extend `skills/self-contained-options/SKILL.md` with a section "Validator" linking to the script.
  3. Reference from `commands/techne-options.md` as the verification step.
- **Touches/replaces:** `skills/self-contained-options/SKILL.md`, `commands/techne-options.md`.

### F4 — Per-SE-agent system-prompt clause

- **Surface:** agent-frontmatter / agent body (edit `agents/software_engineer_*.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — pure text addition, ~3 lines per agent
- **Approach:** Add a "Citation discipline" block to `software_engineer_go.md`, `software_engineer_python.md`, `software_engineer_frontend.md`, `code_reviewer.md`, `meta_reviewer.md`: "Every reference to code, notes, decisions, or PRs MUST include a resolvable anchor — `path/file.ext:NN` for code, `vault://notes/d-NNN.md` for decisions, URL for external. Bare identifiers are forbidden in the final assistant message." No-code change. Counter-evidence: rule duplication risks attention dilution; mitigate by referencing a single skill instead of inlining.
- **Steps:**
  1. Add the clause to the 5 named agents.
  2. Cross-reference `skills/citation-discipline` (see F5) instead of repeating the rule body.
- **Touches/replaces:** 5 agent files in `agents/`.

### F5 — New skill `citation-discipline`

- **Surface:** skill (new `skills/citation-discipline/SKILL.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — advisory; counter-evidence below
- **Approach:** Single skill (≤80 lines) codifying: required anchor shapes per artefact class (code/note/decision/URL/issue), forbidden bare-identifier shapes, recommended quote-first pattern from Anthropic conventions, and a self-check checklist before message emit. `alwaysApply: false`; triggered by code/notes references in the prompt.
- **Steps:**
  1. Use `skill-builder` to scaffold under `skills/citation-discipline/`.
  2. Frontmatter: `triggers: [path:, vault:, d-, decision, file:, line:]`.
  3. Body: anchor schemas + quote-first examples + checklist.
- **Touches/replaces:** none.

## Acceptance signal

- Random sample of 10 assistant final-messages over a week shows ≥9 with every code/note reference carrying a resolvable anchor.
- `stop_citation_audit.py` warnings drop to <1 per session after first week of corrective adaptation.
- `AskUserQuestion` option labels never reference prior turns ("as we discussed", "the earlier option") without restating the anchor.
- `/techne-review` agent flags zero bare-identifier citations on the next 5 PR reviews.
- `validate_ask_options.py` rejects synthetic bad-option fixtures with 100% recall in tests.

## Trade-offs and counter-evidence

Anthropic reverted a ≤25/≤100 word brevity cap after a 3% eval drop ([[02-external-research#R2.1]]). A strict citation-tag mandate (F2) is structurally similar — it adds output tokens. Mitigation: keep `<citation>` optional in default style; activate `cite-strict` per command when audit-grade output is required, not globally. F4 risks rule duplication and CLAUDE.md-style attention dilution ([[03-current-config-map#6 CLAUDE.md size]]) — keep the per-agent clause to one sentence pointing at the skill. F1 has false-positive risk on prose mentions; the warn-only initial mode lets us tune the regex without blocking.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-26-no-bullshit-detector]] (verification layer sibling)
- [[rc-16-no-facts-list-scaffold]] (working-memory anchor)
