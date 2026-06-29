---
tags: [claude-improvements, phase3, root-cause, layer-E]
phase: 3
rc-id: RC-27
layer: E
created: 2026-06-27
symptoms: [S-004]
---

# RC-27 — Output ordering is not preserved against user-named items

## Mechanism

When the user enumerates items in a specific order (numbered list, table rows, file paths in sequence, options A/B/C) and asks for per-item processing, the assistant silently re-orders the response. Concrete examples exist in project `oicm-8015` ([[01-symptoms-inventory#S-004]]). The cause: the model treats output structure as a presentational choice rather than as data fidelity, and groups items by similarity, severity, or fix-effort even when the user's order encoded priority or dependency. The verification layer has zero coverage — `stop_format` and `stop_lint_gate` run code-shaped checks but nothing diffs ordered-list cardinality and order against the user's last message ([[03-current-config-map#3.11 Out-of-order responses / interleaving]]). Reflection adjacent: RC-ref-5 (sycophantic gap-filling) extends scope; this RC compresses or shuffles scope.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-004]]
- External: [[02-external-research#R3.1]] (XML tag extraction `<answer>` to enforce structured output), [[02-external-research#R4.1]] (Chroma Research — position effects in long context; ordering is meaningful)
- Config gaps: [[03-current-config-map#3.11 Out-of-order responses]] — "no dedicated mechanism"

## Fix proposals (≥5)

### F1 — Stop hook detecting ordering mismatch against user's last enumeration

- **Surface:** hook (new `bin/stop_order_check.py`, registered on `Stop`)
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — false positives when user explicitly asks "regroup by …"; needs intent detector
- **Approach:** Extract last user-message enumeration (numbered list, lettered options, sequence of `path:` tokens, table column). Extract corresponding sequence from final assistant message. Compute Levenshtein on the index sequences. When edit distance > 0 and the user did not include a "regroup" intent keyword, emit warning with the two sequences side by side. Non-blocking.
- **Steps:**
  1. Implement `roles/devbox/files/dot_claude/bin/stop_order_check.py`.
  2. Extract enumeration regex set: `^\s*\d+\.\s`, `^\s*[A-Z]\)\s`, `^\s*-\s` (when ≥3 items), `path:line` tokens.
  3. Intent allowlist: "regroup", "rerank", "sort by", "prioritise", "cluster".
  4. Register on `Stop` matcher in `hooks.json`.
  5. Unit tests in `bin/tests/test_stop_order_check.py`.
- **Touches/replaces:** `hooks.json`, sibling to `stop_format.py`.

### F2 — Output-style: preserve-order-of-user-named-items rule

- **Surface:** output-style (edit existing default or new `output-styles/order-preserving.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — text-only rule
- **Approach:** Add explicit rule: "When the user enumerates items, mirror their order in your response. If you must regroup, restate the original order first, then explain the regrouping with rationale." Lift the wording from reflection's "minimum verifiable increment" pattern.
- **Steps:**
  1. Create `roles/devbox/files/dot_claude/output-styles/order-preserving.md`.
  2. Add worked counter-example: user gave `[F2, F4, F1, F3]`; bad response sorts to `[F1, F2, F3, F4]`; good response keeps `[F2, F4, F1, F3]`.
- **Touches/replaces:** none.

### F3 — Per-agent template: numbered-emit pattern

- **Surface:** agent body (edit reviewer/summary-class agents — `code_reviewer.md`, `meta_reviewer.md`, `consistency_checker.md`, `freshness_auditor.md`, `content_reviewer.md`)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — no-code edit
- **Approach:** Add a `## Order preservation` section: "For each item in the user's enumeration, emit one corresponding output block, in the same order. Use the user's exact identifier (number/letter/path). Do not merge two of their items into one block without flagging." This makes the rule visible to the agents most prone to regrouping (reviewers).
- **Steps:**
  1. Add the section to 5 named agent files.
  2. Cross-link to `order-preservation` skill (F5).
- **Touches/replaces:** 5 agent files in `agents/`.

### F4 — New command `/techne-order-check`

- **Surface:** command (new `commands/techne-order-check.md`)
- **Effort:** low
- **Impact:** low
- **Risk:** low — opt-in
- **Approach:** `/techne-order-check` runs `stop_order_check.py` against the last assistant message and the last user enumeration explicitly, printing the diff. Manual escape valve when the hook is in warn-only mode.
- **Steps:**
  1. Create `commands/techne-order-check.md`.
  2. Wire to invoke the hook script in standalone mode.
- **Touches/replaces:** none.

### F5 — New skill `order-preservation`

- **Surface:** skill (new `skills/order-preservation/SKILL.md`)
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low — advisory; only one new skill per RC budget used here
- **Approach:** Skill ≤60 lines: order-preservation rules, restate-then-regroup pattern, table-column fidelity, path-list fidelity. `alwaysApply: false`; triggered when prompt contains a list of ≥3 enumerated items.
- **Steps:**
  1. Scaffold via `skill-builder`.
  2. Frontmatter trigger list: numbered-list patterns, "for each", "process these", "review the following".
- **Touches/replaces:** none.

## Acceptance signal

- `stop_order_check.py` warning count drops to <1 per session after two weeks of adaptation.
- Sample of 10 review-class agent outputs over a week: ≥9 preserve the user's input order or explicitly restate-then-regroup with rationale.
- `oicm-8015`-style examples re-tested: response order matches input.
- `/techne-order-check` diffs return empty on the next 10 invocations.
- Regression test fixtures in `bin/tests/` cover numbered-list, lettered-option, path-list, table-row shapes.

## Trade-offs and counter-evidence

The intent allowlist (F1) will leak both directions: legitimate user "regroup" requests will sometimes be misdetected (false negative on the warning side; harmless) and silent regroupings without intent keywords will be flagged when the regrouping was actually wanted (false positive). Start warn-only. F3 risks rule duplication across 5 agents — the standard CLAUDE.md-bloat hazard ([[03-current-config-map#6]]); mitigate by having each agent reference `order-preservation` skill rather than inline the rule body. Order preservation has no documented Anthropic counter-evidence — this gap is not on Anthropic's published radar. F5 is the one allowed new skill for this RC; do not add a second.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-21-monolithic-and-duplicate-outputs]] (sibling output-shape RC)
- [[rc-25-citation-not-enforced]] (sibling verification-layer RC)
