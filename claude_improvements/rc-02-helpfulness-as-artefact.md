---
tags: [claude-improvements, phase3, root-cause, layer-A]
phase: 3
rc-id: RC-02
layer: A
created: 2026-06-27
symptoms: [S-005, S-006, S-011, S-014, S-029]
---

# RC-02 — Helpfulness collapses to "produce a complete artefact this turn"

## Mechanism

The training gradient that defines "helpful" pulls toward "user gets a working draft at the end of this turn". Under that collapse, a delta — three changed words inside §2 — looks like under-delivery; a full rewrite looks like effort ([[04-reflection-evidence#RC-ref-1]]). The delta-only rule lives in CLAUDE.md as an advisory ([[03-current-config-map#3.2 Brevity / anti-graphomania]]); the gradient toward "ship a complete paragraph" wins. Coupled with no working-memory scaffold ([[rc-06-no-working-memory]]) and the verbosity-by-task-complexity calibration ([[rc-03-verbosity-task-complexity]]), the failure mode is structural: every turn, the model perceives the empty buffer as "produce artefact" and produces one even when the user wanted a 3-word reply. `proposal_discipline.py` covers part of the surface (Stop nudge toward delta form) but is advisory and operates only after the artefact is already emitted.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-005]] (graphomania 4.8), [[01-symptoms-inventory#S-006]] (repeating self+user), [[01-symptoms-inventory#S-011]] (pub-talk), [[01-symptoms-inventory#S-014]] (paraphrase + odd conclusions), [[01-symptoms-inventory#S-029]] (no proactive options when CTA absent)
- External: [[02-external-research#R1.2]] (4.8 calibrates length — much longer on open-ended analysis), [[02-external-research#R3.1]] (brevity verbatim snippet `Provide concise, focused responses…`), [[02-external-research#R6.5]] ("Be concise. If I don't ask for detail, give me 2-3 sentences maximum.")
- Config gaps: [[03-current-config-map#4. Gaps and weaknesses]] §3.2 — no PostStop hook flags output > N lines; §3.6 — only `proposal_discipline.py` covers rewrite-instead-of-delta
- Reflection: [[04-reflection-evidence#RC-ref-1]] (Helpfulness optimisation as produce-complete-artefact); [[04-reflection-evidence#cross-cutting]] item 4: "On feedback turns, edit the prior draft as a literal string."

## Fix proposals

### F1 — `delta-only` output-style enforcing diff-form on iteration turns

- **Surface:** output-style
- **Effort:** low
- **Impact:** high
- **Risk:** medium — output-style is opt-in per session
- **Approach:** New `output-styles/delta-only.md` defines a hard template for iteration turns: `[§N CHANGED] why / before / after`, `[§M ADDED] why / content`, `[§K REMOVED] why`. Enforces never-restate-unchanged-content. User invokes via `/output-style delta-only` when in feedback mode; can be activated per-agent via frontmatter.
- **Steps:**
  1. Write `roles/devbox/files/dot_claude/output-styles/delta-only.md` codifying the three markers from USER_AUTHORITY_PROTOCOL.md §Voice — Iteration.
  2. Add `output-style: delta-only` to focus_coach, technical_product_manager, doc_updater agent frontmatter where iterating-on-prior-output is the norm.
- **Touches/replaces:** new output-style file; minor edits to 3 agent frontmatters.

### F2 — Stop hook detecting "this turn re-emitted unchanged content"

- **Surface:** hook (new bin script + Stop registration)
- **Effort:** high
- **Impact:** high
- **Risk:** medium — requires storing prior turn's output in session state
- **Approach:** New `stop_delta_audit.py` compares the final assistant message against the prior assistant message stored in session state. If ≥30% of the new message is substring-identical to the previous one AND the user message in between was feedback-shaped (short, references "§", "option N", or contains a specific change request), emit `decision: block` with reason "Delta-form required: emit only changed sections."
- **Steps:**
  1. Implement `bin/stop_delta_audit.py`. Persist prior assistant message via `session_save.py` infrastructure.
  2. Register under `Stop` after `proposal_discipline.py`.
  3. Tune similarity threshold; start permissive (50%), tighten after telemetry.
- **Touches/replaces:** `hooks.json`, new `bin/` script, extend `session_save.py` state schema.

### F3 — UserPromptSubmit injection: "previous draft is the artefact" framing

- **Surface:** hook (extend existing `proposal_discipline.py`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — additive context
- **Approach:** Extend `proposal_discipline.py` UserPromptSubmit branch. When the prior assistant turn contained a numbered or sectioned proposal AND the user reply is short feedback, inject `additionalContext`: "Previous draft is the artefact. This turn's deliverable is the diff against it, not a new draft. Use §N CHANGED / §M ADDED / §K REMOVED form. Do not restate unchanged sections."
- **Steps:**
  1. Edit `bin/proposal_discipline.py` to add the framing branch.
  2. Keep current Stop-side nudge — they reinforce each other.
- **Touches/replaces:** `bin/proposal_discipline.py`.

### F4 — Add a `delta-discipline` skill cross-referenced from CLAUDE.md

- **Surface:** new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low — advisory
- **Approach:** New `skills/delta-discipline/SKILL.md` describes the §N CHANGED format, when iteration mode triggers, and the "previous draft is the artefact" framing in 50-80 lines. Reference from `USER_AUTHORITY_PROTOCOL.md §Voice — Iteration` instead of inlining the full rule (frees CLAUDE.md budget — [[03-current-config-map#6. CLAUDE.md size and bloat]]).
- **Steps:**
  1. Write `skills/delta-discipline/SKILL.md` extracting the §Voice iteration content.
  2. Replace the 18-line iteration block in `USER_AUTHORITY_PROTOCOL.md` with a 3-line pointer to the skill.
  3. Net CLAUDE.md saving: ~15 lines.
- **Touches/replaces:** new skill; `USER_AUTHORITY_PROTOCOL.md` budget reduction.

### F5 — Replace `§ Voice — Iteration` example block with a compact template marker

- **Surface:** CLAUDE.md
- **Effort:** low
- **Impact:** low
- **Risk:** low
- **Approach:** Trim the worked example in `USER_AUTHORITY_PROTOCOL.md` §Voice from a full code block to a single-line reference: `Use template: [§N CHANGED] why/before/after; [§M ADDED] why/content; [§K REMOVED] why.` The model has seen this template thousands of times in training data and does not need the worked example. Cuts ~12 lines.
- **Steps:**
  1. Edit `USER_AUTHORITY_PROTOCOL.md` to compact the iteration block.
  2. Pair with F4 (skill cross-reference).
- **Touches/replaces:** `USER_AUTHORITY_PROTOCOL.md`.

## Acceptance signal

- Stop hook `stop_delta_audit.py` blocks ≤2 per 50 iteration turns after tuning — meaning ≥48 already-clean.
- Manual audit: 20 random iteration turns show ≥17 emitting only §N CHANGED / §M ADDED / §K REMOVED.
- Average output token count on feedback turns drops by ≥40% vs current baseline.
- User-reported "repeated itself again" count → 0 over 4 weeks.
- `proposal_discipline.py` Stop nudge fires ≤5% of turns (down from current rate).

## Trade-offs and counter-evidence

- F2 (Stop delta audit) is the highest-impact and the riskiest. False positives on legitimate full-rewrite requests ("rewrite this section from scratch") must be allowlisted. Start in log-only mode.
- Anthropic tried platform-level ≤25/≤100 word caps and reverted after a 3% eval drop ([[02-external-research#R2.1]]). Caps are not the answer; delta-form discipline is. The fixes target output *shape* not output *length*.
- Output-styles (F1) are opt-in unless attached to an agent. Coverage gap if user forgets to activate. Mitigation: attach to agents where iteration is the norm.
- Removing CLAUDE.md content (F4, F5) shifts trust to skills and hooks. Skills are also advisory. Compensating: F2 is the deterministic backstop.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[04-reflection-evidence]]
- Adjacent: [[rc-03-verbosity-task-complexity]], [[rc-06-no-working-memory]], [[rc-13-claude-md-bloat]]
