---
tags: [claude-improvements, phase3, root-cause, layer-B]
phase: 3
rc-id: RC-12
layer: B
created: 2026-06-27
symptoms: [S-005, S-011, S-033]
---

# RC-12 — No platform-level brevity cap

## Mechanism

Claude Code's harness has no turn-level brevity enforcement. Anthropic itself tried hardcoded `≤25 words between tool calls / ≤100 words final response` system-prompt caps from April 16–20 2026 and reverted them after a **3% eval drop** ([[02-external-research#R2.1]]). The reversal proves blunt caps hurt quality on complex tasks while still failing to address verbosity on open-ended prompts where length calibrates to *perceived* complexity ([[02-external-research#R1.2]]). The result: no platform brake on graphomania. User-side mitigations must be **nuanced** — context-aware, task-tier aware, and reversible — rather than fixed-character caps.

## Evidence trail

- Symptoms: [[01-symptoms-inventory#S-005]] verbatim "Последний Opus 4.8 - графоман", [[01-symptoms-inventory#S-011]] "Должен давать сухой текст-фактуру. Не формат «попиздели с тохой и омаром в пабе»", [[01-symptoms-inventory#S-033]] (monolithic spec/domain files)
- External:
  - [[02-external-research#R2.1]] April-23 postmortem — `≤25/≤100 word` cap reverted after 3% eval drop
  - [[02-external-research#R1.2]] Opus 4.8 "calibrates response length to how complex it judges the task" — verbatim fix: `Provide concise, focused responses. Skip non-essential context, and keep examples minimal.`
  - [[02-external-research#R1.1]] verbatim acknowledgement of 4.5/4.6 over-engineering tendency
  - [[02-external-research#R3.1]] XML `<answer>` tag pattern as documented mitigation; caveat about 0% preamble baseline
  - [[02-external-research#R5]] item 10 (restating largely solved on 4.6+; new failure is open-ended over-elaboration)
- Config gaps: [[03-current-config-map#3.2]] "No PostStop hook flags output > N lines. Multi-screen agent reports go uncaught"

## Fix proposals

### F1 — output-style enforcing `<answer>` tag with per-tier line budget

- **Surface:** output-style
- **Effort:** medium
- **Impact:** high
- **Risk:** medium — too tight on Tier 3 tasks risks the 3% eval drop Anthropic measured
- **Approach:** new output-style `brevity-tiered.md` that requires every final response to wrap the user-facing answer in `<answer>` tags. The style states per-tier budgets: **Tier 1** (routine: formatting, dead code, narration comments) ≤20 lines, **Tier 2** (single-feature edit, single-file refactor) ≤80 lines, **Tier 3** (architecture, design, multi-file refactor) budget-aware — model declares budget up-top (`<answer budget="200 lines, rationale: multi-file refactor across 4 modules">`). Reasoning happens *outside* the answer tag (Anthropic XML convention — [[02-external-research#R3.5]]).
- **Steps:**
  1. New `roles/devbox/files/dot_claude/output-styles/brevity-tiered.md`.
  2. Define tier classification heuristic with examples.
  3. Define `<answer budget="N lines, rationale: ...">` schema.
  4. Cross-link to `code-writing-protocols` skill (Tier 1 routine task mode already defined there).
  5. Document opt-in.
- **Touches/replaces:** new output-style.

### F2 — Stop hook flags final outputs > N lines without inline citations

- **Surface:** hook
- **Effort:** medium
- **Impact:** medium-high
- **Risk:** medium — risk false positives on legitimate long-form deliverables
- **Approach:** new `bin/stop_brevity_audit.py` triggered on `Stop`. Parses final assistant message; if line count exceeds threshold (default 80 for general, 200 for explicitly long tasks) AND inline-citation density is below threshold (< 1 citation per 30 lines: a citation is `path:line`, URL, doc anchor, or `<answer budget>` declaration), emit warning into `additionalContext` for next turn: `[Brevity audit] Last turn was N lines with M citations. Verify density justifies length. Consider delta-only iteration next turn.`
- **Steps:**
  1. New `bin/stop_brevity_audit.py`.
  2. Parse last assistant message from transcript.
  3. Line count + citation regex match.
  4. Conditional warning emit.
  5. Register on `Stop` in `hooks.json`.
- **Touches/replaces:** `hooks.json`, new bin script. Adjacent to existing `stop_format.py`, `stop_lint_gate.py`, `proposal_discipline.py` on Stop.

### F3 — Per-agent system prompt brevity hint by task tier

- **Surface:** agent-frontmatter
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** add a one-line clause to each SE agent's system prompt based on the agent's task class. `software_engineer_*` agents handle Tier 2 mostly: `Aim for ≤80 lines per turn unless the change requires more — if so, declare budget and rationale up-front.` `refactor_cleaner`, `doc_updater`: Tier 1 default, `Aim for ≤20 lines.` `architect`, `technical_product_manager`, `implementation_planner`: Tier 3, `Declare budget at start of turn with rationale.` Inserted in agent definition file frontmatter or in body.
- **Steps:**
  1. Edit ~12 agent files in `roles/devbox/files/dot_claude/agents/`.
  2. Add one-line tier-specific clause to each.
  3. `make claude-push`.
- **Touches/replaces:** ~12 agent definition files.

### F4 — Skill `output-length-budget` (new, advisory)

- **Surface:** new skill
- **Effort:** low
- **Impact:** medium
- **Risk:** low
- **Approach:** new skill `output-length-budget` with `alwaysApply: true`, ~100 lines. Encodes: (a) tier classification with concrete examples; (b) the verbatim Anthropic snippet `Provide concise, focused responses. Skip non-essential context, and keep examples minimal.` ([[02-external-research#R1.2]]); (c) anti-pattern catalogue: restating user as conclusion, padding to look thorough, hedging on a verifiable claim, full rewrites of numbered proposals (use Iteration mode); (d) self-audit pattern: end of turn, count lines vs declared budget; (e) explicit reference to Anthropic's reverted ≤25/≤100 cap with the 3% eval drop as cautionary tale.
- **Steps:**
  1. New `roles/devbox/files/dot_claude/skills/output-length-budget/SKILL.md`.
  2. Frontmatter `alwaysApply: true`.
  3. Cross-link from `code-writing-protocols`, `agent-base-protocol § Voice`, `code-comments`.
- **Touches/replaces:** new skill.

### F5 — Command `/techne-brief` for quick-mode toggle

- **Surface:** command
- **Effort:** low
- **Impact:** low-medium
- **Risk:** low
- **Approach:** new `commands/techne-brief.md`. When user invokes, sets a session-scoped flag (state file `${CLAUDE_PROJECT_DIR}/.claude/session/<id>.brief`) that the F2 Stop-hook and F1 output-style read to apply *tighter* tier budgets (Tier 1 ≤10 lines, Tier 2 ≤40 lines, Tier 3 ≤120 lines). Reversed by `/techne-brief off` or auto-expires next session. Gives the user a one-keystroke brevity escalation when the session is drifting verbose.
- **Steps:**
  1. New `commands/techne-brief.md`.
  2. State file write logic — single bool.
  3. F1 output-style reads state file and adjusts budgets.
  4. F2 hook reads same state file and adjusts threshold.
  5. Document in `00-MoC`.
- **Touches/replaces:** new command file; F1, F2 read shared state file.

## Acceptance signal

- Over 50 turns, median line count drops by ≥ 30% vs baseline.
- ≥ 90% of final responses contain `<answer>` tag wrap (F1).
- F2 Stop-hook warning fires < 10% of turns after first month tuning.
- User-reported "графоман" complaints decline measurably.
- Tier 1 turns (routine tasks) average ≤ 20 lines per response.
- `/techne-brief` invoked when needed but not chronically — chronic invocation signals tier classification needs tuning.

## Trade-offs and counter-evidence

- **The central counter-evidence**: [[02-external-research#R2.1]] Anthropic's ≤25/≤100 word cap caused 3% eval drop and was reverted in 4 days. Blunt caps measurably hurt quality. F1, F3, F5 must be tier-aware, not single-threshold.
- F1 (`<answer>` tag) risk: [[02-external-research#R3.1]] caveat — "Semantic eval confirms baselines on current models already exhibit 0% preamble … rules targeting those behaviors carry input cost without changing output." If 4.7/4.8 are already terse on Tier 1 tasks, the tag adds cost without benefit. Mitigation: F1 budget annotations matter most for Tier 3, where over-elaboration is the actual symptom.
- F2 (line-count Stop hook) risk: false positives on legitimate long deliverables (a full plan, a domain analysis). Mitigation: threshold is *warning*, not block; tier declaration in `<answer budget>` allows quiet exemption.
- F3 risks attention-budget pressure across 12 agents — see [[rc-11-claude-md-attention-budget]]. Mitigation: one-line per agent.
- F4 (skill) is purely advisory; [[02-external-research#R3.1]] suggests advisory anti-preamble rules waste tokens on already-compliant models. Mitigation: skill triggers on Tier 3 / open-ended verbs, not on every prompt.
- Counter-evidence on tier classification: a single Russian phrase "графоман" is the trigger user-side, but the model's perception of "complexity" ([[02-external-research#R1.2]]) is what drives length. Output-style F1 must be coupled with explicit tier declaration to engage the right calibration.

## See also

- [[10-root-causes-overview]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[03-current-config-map]]
- [[rc-03-verbosity-task-complexity]] (parent: Layer A weights driver — 4.8 calibrates length to perceived complexity)
- [[rc-02-helpfulness-as-artefact]] (parent gradient)
- [[rc-21-monolithic-and-duplicate-outputs]] (downstream: pipeline-level graphomania)
