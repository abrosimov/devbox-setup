---
tags: [claude-improvements, phase3, root-cause, layer-C]
phase: 3
rc-id: RC-17
layer: C
created: 2026-06-27
symptoms: [S-003, S-005, S-006, S-008, S-011]
---

# RC-17 — Brevity, reconnaissance, and citation rules are CLAUDE.md text only — no deterministic enforcement

## Mechanism

[[02-external-research#R3.2]] documents the practitioner consensus: "Hooks for 100% enforcement. CLAUDE.md is advisory (~70% followed). Hooks are deterministic." The deployed `dot_claude/` configuration loads brevity (UAP §Voice), reconnaissance-before-action (UAP §Discipline Protocol), and citation discipline (UAP §Voice "Cite verifiable claims") as CLAUDE.md text only. [[03-current-config-map#3.2]] and [[03-current-config-map#3.12]] confirm: no PostStop hook flags output > N lines without citations; no Stop hook validates that file/note references resolve to `path:line` form; no hook checks that an agent did a Read before emitting code-related claims. The result is exactly the ~70% adherence rate — symptoms S-003 (cites without context), S-005 (graphomania), S-006 (re-stating), S-008 (questions without context), S-011 (pub-talk) all fire despite explicit UAP rules forbidding them. The model is not refusing to follow the rule; it is being trained to balance many competing pressures and the advisory pressure loses to the helpfulness/completeness gradient ([[rc-02-helpfulness-as-artefact]]).

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-003]] (cites without context), [[01-symptoms-inventory#S-005]] (graphomania), [[01-symptoms-inventory#S-006]] (restating), [[01-symptoms-inventory#S-008]] (questions without context), [[01-symptoms-inventory#S-011]] (pub-talk).
- External: [[02-external-research#R3.2]] hooks deterministic / CLAUDE.md ~70%; [[02-external-research#R1.1]] Anthropic verbatim `<investigate_before_answering>` exists as a promptable snippet but not enforced; [[02-external-research#R2.1]] Anthropic ≤25/≤100 word cap experiment + 3% eval drop on revert.
- Config gaps: [[03-current-config-map#3.2]] no PostStop output-length hook; [[03-current-config-map#3.8]] reconnaissance ladder advisory; [[03-current-config-map#3.12]] citations advisory.
- Reflection: [[04-reflection-evidence#RC-ref-1]] helpfulness gradient defeats advisory brevity.

## Fix proposals

### F1 — PostStop scan for unresolved citations (path-less code mentions)

- **Surface:** hook (new bin script + `hooks.json` Stop entry)
- **Effort:** medium
- **Impact:** high
- **Risk:** low — informational; no block.
- **Approach:** Deterministic. Stop hook scans the final assistant message for patterns matching `[\w_-]+\.(go|py|ts|tsx|md|yaml|json)` (file refs), Markdown links, and `d\d{2,}` style shorthand references (the S-003 "see d32" pattern). For each match, check whether the surrounding sentence carries a `path:line` anchor or quoted snippet. If not, emit `additionalContext`: "N unresolved references in your output — add `path:line` or quoted snippet for each." Non-blocking; visibility only.
- **Steps:**
  1. Create `bin/stop_citation_audit.py` — regex scan, contextual check, emit warning list.
  2. Register in `hooks.json` Stop matcher alongside `stop_format`, `stop_lint_gate`.
  3. Cover with test in `bin/tests/test_stop_citation_audit.py`.
- **Touches/replaces:** new `bin/stop_citation_audit.py`; `hooks.json`.

### F2 — Output-style requiring `<citation>` tags for any code/note reference

- **Surface:** output-style
- **Effort:** low
- **Impact:** medium
- **Risk:** low — opt-in.
- **Approach:** New output-style `cited`. Mandates every reference to a file, note, function, or external doc be wrapped: `<citation src="path/file.go:42">brief verbatim quote or description</citation>`. Pairs with F1 — the style produces structured citations; the hook audits compliance. Suitable as default for `/techne-implement`, `/techne-plan`, `/techne-review` where citation density matters.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/output-styles/cited.md`.
  2. Document trigger in `commands/techne-implement.md`, `commands/techne-plan.md`, `commands/techne-review.md`.
- **Touches/replaces:** new output-style; minor command edits.

### F3 — PostToolUse(Write) hook: new .md must include ≥1 `path:line` citation per assertion

- **Surface:** hook (new bin script + `hooks.json` PostToolUse)
- **Effort:** medium
- **Impact:** medium
- **Risk:** medium — false positives on pure-prose notes.
- **Approach:** Deterministic. PostToolUse(Write) matcher on `**/*.md` files. Counts assertions (sentences ending with period that contain technical noun phrases — heuristic). Counts citations (`path:line`, URLs, `[[wiki-link]]`). When citation-density < threshold (e.g. 1 per 5 assertions), emit `additionalContext` flagging the file. Excludes paths matching `templates/`, `output-styles/`, `agents/`, `skills/` (definitions, not claims).
- **Steps:**
  1. Create `bin/post_write_citation_density.py`.
  2. Implement assertion/citation counter with documented heuristic.
  3. Register in `hooks.json` PostToolUse(Write) with path-include filter.
  4. Cover with test.
- **Touches/replaces:** new `bin/post_write_citation_density.py`; `hooks.json`.

### F4 — Stop hook flags output > N lines without citation density ≥ K

- **Surface:** hook (extension of F1 or new)
- **Effort:** low (if combined with F1)
- **Impact:** high
- **Risk:** low — informational.
- **Approach:** Deterministic brevity guard. Stop hook counts output lines; when >150 lines AND citation density < K (e.g. <1 per 30 lines), emit `additionalContext`: "Long output without citation density — likely pub-talk per UAP §Voice. Consider rewriting in delta-only or brevity-strict mode." Directly targets S-005 (graphomania) and S-011 (pub-talk).
- **Steps:**
  1. Extend `bin/stop_citation_audit.py` (from F1) with line-count + density check.
  2. Tune thresholds against representative session corpus before enforcing.
- **Touches/replaces:** `bin/stop_citation_audit.py`.

### F5 — Per-SE-agent `tools:` constraint forcing LSP/Read before Edit

- **Surface:** agent-frontmatter (no-code)
- **Effort:** low
- **Impact:** medium
- **Risk:** medium — over-tightening tools breaks legitimate flows.
- **Approach:** No-code change. Tighten `tools:` frontmatter on `software_engineer_{go,python,frontend}` agents to enforce a `Read` or LSP call before `Edit` is reachable. Implementation route: do NOT remove `Edit` from the tool list (that breaks the agent). Instead, document the rule in agent body + reference `pre_write_existing_guard.py` (already exists per [[03-current-config-map#3.8]]) and extend its match patterns to cover Edit (currently only Write). This is partly a hook tweak, partly an agent-body rule pointer.
- **Steps:**
  1. Edit `bin/pre_write_existing_guard.py` to also match `Edit` and `MultiEdit` tools (currently Write only).
  2. Update `hooks.json` PreToolUse matchers to include Edit/MultiEdit for that hook.
  3. Edit agent body in 3 SE agents to state the rule explicitly with reference to the hook.
- **Touches/replaces:** `bin/pre_write_existing_guard.py`; `hooks.json`; `agents/software_engineer_*.md`.

## Acceptance signal

- `bin/stop_citation_audit.py` exists; emits warnings on ≥80% of synthetic uncited-reference outputs.
- `bin/post_write_citation_density.py` exists; flags >50% of pure-pub-talk MD files in retro corpus.
- Re-test S-003 in 10 fresh sessions: ≥7 outputs include `path:line` anchors when referencing files/notes.
- Re-test S-005/S-011 in 10 long-output sessions: ≥6 exhibit higher citation density or shorter length post-warning.
- `pre_write_existing_guard.py` blocks Edits to unread files in 100% of synthetic test cases.

## Trade-offs and counter-evidence

- **Anthropic reverted ≤25/≤100 word brevity caps after a 3% eval drop** ([[02-external-research#R2.1]]). Hard brevity hooks risk the same regression — keep F4 as warn-only initially, measure quality before tightening.
- **F2 (cited output-style) burns tokens** for citation tags. Worth it for plan/spec/review outputs; not for chat. Keep opt-in.
- **F3 (citation-density hook) heuristic is brittle.** Counting "assertions" by sentence shape is approximate; pure-prose notes (decision logs, retrospectives) will fire false positives. Mitigate via path exclusion list; tune thresholds empirically.
- **F5 (Read-before-Edit enforcement) breaks tight-loop edits** where the agent legitimately remembers a file from earlier in the session. `pre_write_existing_guard.py` already handles "previously read" state; ensure the extension preserves that.
- **Practitioner counter** ([[02-external-research#R3.1]]): "Semantic eval confirms baselines on current models already exhibit 0% preamble … rules targeting those behaviors carry input cost without changing output." Over-engineering brevity hooks against a model that's already concise on simple tasks burns tokens. Apply to long-output paths only.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-02-helpfulness-as-artefact]] — model-side pressure that defeats advisory rules
- [[rc-13-claude-md-bloat]] — bloat amplifies advisory drop
- [[rc-25-citation-not-enforced]] — adjacent verification gap
