---
tags: [claude-improvements, phase3, root-cause, layer-A]
phase: 3
rc-id: RC-03
layer: A
created: 2026-06-27
symptoms: [S-005, S-011, S-033]
---

# RC-03 — 4.8 calibrates response length to perceived task complexity

## Mechanism

Anthropic documents verbatim: "Claude Opus 4.8 calibrates response length to how complex it judges the task to be, rather than defaulting to a fixed verbosity. This usually means shorter answers on simple lookups and **much longer ones on open-ended analysis**" ([[02-external-research#R1.2]]). The mechanism is not a bug — it is a deliberate post-training. The failure mode: open-ended analytical prompts ("what do you think about X", "analyse Y", "ultrathink") are perceived as complex even when the user wants a 3-sentence answer. The model produces 1,500-token analyses by default. Anthropic's documented fix is a verbatim snippet: `Provide concise, focused responses. Skip non-essential context, and keep examples minimal.` Counter-evidence is sharp: Anthropic shipped a ≤25/≤100 word platform-level cap and reverted after a 3% eval drop ([[02-external-research#R2.1]]). Blunt caps hurt quality. The fix is *shape* discipline (`<answer>` extraction, structured output) plus context-specific brevity, not word-count limits.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-005]] (Opus 4.8 graphoman), [[01-symptoms-inventory#S-011]] (pub-talk not facts), [[01-symptoms-inventory#S-033]] (monolithic spec/domain outputs)
- External: [[02-external-research#R1.2]] (verbatim "much longer on open-ended analysis"), [[02-external-research#R2.1]] (≤25/≤100 cap reverted, 3% eval drop), [[02-external-research#R3.1]] (`Provide concise, focused responses…` verbatim snippet), [[02-external-research#R6.5]] ("Be concise. If I don't ask for detail, give me 2-3 sentences maximum."), [[02-external-research#R3.5]] (XML `<answer>` extraction)
- Config gaps: [[03-current-config-map#4. Gaps and weaknesses]] §3.2 — anti-graphomania advisory only; no Stop hook flags long output

## Fix proposals

### F1 — Per-agent system-prompt clause with the Anthropic verbatim snippet

- **Surface:** agent-frontmatter (no-code)
- **Effort:** low
- **Impact:** medium
- **Risk:** low — additive 2 lines per agent
- **Approach:** Append to every agent's system prompt: `Provide concise, focused responses. Skip non-essential context, and keep examples minimal.` ([[02-external-research#R1.2]] verbatim). Anthropic-shipped exact wording is the documented optimum. Apply to all 28 agents.
- **Steps:**
  1. Add the clause to each agent's `system_prompt` or equivalent field in `agents/*.md` frontmatter.
  2. Bulk-apply via a one-off script; commit per-agent edits.
- **Touches/replaces:** 28 agent files.

### F2 — `brevity-strict` output-style with `<answer>` extraction

- **Surface:** output-style
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — opt-in; XML extraction may confuse some downstream consumers
- **Approach:** New `output-styles/brevity-strict.md` mandates: (a) all final user-facing content wrapped in `<answer>…</answer>`; (b) reasoning lives in `<thinking>…</thinking>` (compacted out by harness if supported); (c) max 5 sentences in `<answer>` unless explicitly asked. Per [[02-external-research#R3.5]] this is the strongest known shape-control technique.
- **Steps:**
  1. Write `output-styles/brevity-strict.md`.
  2. Attach to `focus_coach`, `code_reviewer`, `meta_reviewer`, `consistency_checker` — agents whose value is short verdicts.
  3. Document trade-offs (XML may break downstream Markdown rendering).
- **Touches/replaces:** new output-style; 4 agent frontmatters.

### F3 — Stop hook flagging output length above a context-aware threshold

- **Surface:** hook (new bin script)
- **Effort:** medium
- **Impact:** medium
- **Risk:** medium — false positives on legitimate long analyses
- **Approach:** New `stop_verbosity_audit.py` computes assistant final-message word count. Threshold matrix: chat reply >300 words, agent-final >800 words → emit `additionalContext` warning (not block) with "Output exceeds verbosity threshold; consider whether the user requested this depth." If the prior user turn contains "brief", "short", "tl;dr", "fact density" — threshold drops to 150 words and becomes a block.
- **Steps:**
  1. Implement `bin/stop_verbosity_audit.py`.
  2. Register under `Stop` chained after `proposal_discipline`.
  3. Start as nudge-only; promote to block only on explicit brevity-request prompts.
- **Touches/replaces:** `hooks.json`, new `bin/` script.

### F4 — UserPromptSubmit injection: "if the question fits one paragraph, answer in one paragraph"

- **Surface:** hook (extend existing or new)
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** Extend `proposal_discipline.py` UserPromptSubmit to detect lookup-shaped prompts ("what is X", "where does Y live", short single-question forms) and inject `additionalContext`: "Lookup detected. Answer in ≤3 sentences with file:line citations. No preamble, no follow-up suggestions unless asked."
- **Steps:**
  1. Extend `proposal_discipline.py` with a lookup-detector regex.
  2. Test on a corpus of recent prompts.
- **Touches/replaces:** `bin/proposal_discipline.py`.

### F5 — `/effort` setting calibration for analysis-shaped commands

- **Surface:** commands (techne-*)
- **Effort:** low
- **Impact:** low
- **Risk:** low
- **Approach:** Audit `techne-think`, `techne-domain-analysis`, `techne-options`, `techne-plan` — they are the prompts most likely to trigger "open-ended analysis = long output". Add explicit brevity directive to each command's prompt: include the Anthropic snippet ([[02-external-research#R1.2]]) and a maximum word target per output section. No new code.
- **Steps:**
  1. Edit each of the four commands to embed the brevity clause at the top of the prompt.
  2. Optionally set `effort: high` (not `xhigh`) for these — higher-effort 4.8 outputs are sometimes *more* verbose.
- **Touches/replaces:** 4 command files.

## Acceptance signal

- Average assistant final-message length on chat turns drops by ≥30% vs baseline (sampled over 2 weeks).
- `stop_verbosity_audit.py` block rate on explicit-brevity prompts ≤5% — meaning the system honours brevity requests.
- Manual audit of 20 random `techne-think` / `techne-options` outputs: ≥15 fit on one screen of monospace text.
- User-reported "graphoman" complaints → 0 over 4 weeks.
- `<answer>` tag adoption verified on `brevity-strict` output-style turns ≥90%.

## Trade-offs and counter-evidence

- **Critical counter-evidence:** Anthropic's own ≤25/≤100 word cap caused a 3% eval drop ([[02-external-research#R2.1]]). Hard caps hurt task accuracy. None of the proposed fixes use absolute caps for substantive work — F3 uses context-aware thresholds and starts as nudge-only.
- The model is *trained* to expand on open-ended prompts. The fixes work with the grain (shape discipline, XML extraction) not against it (word caps). Expect ~70% adherence on F1 since CLAUDE.md/agent-frontmatter clauses are advisory ([[02-external-research#R5]] item 6).
- [[02-external-research#R3.1]] notes: "Semantic eval confirms baselines on current models already exhibit 0% preamble … rules targeting those behaviors carry input cost without changing output." Over-prompting against preamble is wasted tokens. Anti-graphomania prompts should target the actual failure mode (open-ended analytical expansion), not preamble.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- Adjacent: [[rc-02-helpfulness-as-artefact]], [[rc-12-no-platform-brevity-cap]], [[rc-21-monolithic-and-duplicate-outputs]]
